#!/usr/bin/env python3
"""
tfp2ps.py - Terraform Plan to Parameter Sheet

Convert Terraform plan JSON to markdown parameter tables.
Reads plan.json and optionally schema.json to generate detailed resource documentation.
"""

import os
import sys
import json
import argparse
from collections import defaultdict

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.aws_resources import ALL_RESOURCES


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="""\
Convert Terraform plan JSON to markdown tables.
Reads plan.json and optionally schema.json to generate detailed resource documentation.
""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
    parser.add_argument(
        "-o", "--output",
        metavar="output-prefix",
        default="output",
        help="output file prefix or directory"
    )
    parser.add_argument(
        "-s", "--schema",
        metavar="schema-file",
        default=None,
        help="schema.json file for attribute descriptions"
    )
    parser.add_argument(
        "file",
        metavar="input-file",
        help="plan.json input file"
    )
    options = parser.parse_args()

    if not os.path.isfile(options.file):
        raise Exception("The input file does not exist.")
    if options.schema and not os.path.isfile(options.schema):
        raise Exception("The schema file does not exist.")

    return options


def load_plan(plan_file):
    """Load plan.json file"""
    with open(plan_file, 'r') as f:
        return json.load(f)


def load_schema(schema_file):
    """Load schema.json file"""
    if not schema_file:
        return {}

    with open(schema_file, 'r') as f:
        schema_data = json.load(f)

    # Extract resource schemas for AWS provider
    provider_schemas = schema_data.get('provider_schemas', {})
    aws_provider = provider_schemas.get('registry.terraform.io/hashicorp/aws', {})
    resource_schemas = aws_provider.get('resource_schemas', {})

    return resource_schemas


def extract_resources(plan_data):
    """Extract resources from plan.json"""
    # Get resources from planned_values.root_module
    root_module = plan_data.get('planned_values', {}).get('root_module', {})
    resources = root_module.get('resources', [])

    # Also check for resources in child_modules
    child_modules = root_module.get('child_modules', [])
    for module in child_modules:
        resources.extend(module.get('resources', []))

    return resources


def extract_configuration(plan_data):
    """Extract configuration (including expressions/references) from plan.json"""
    config_root = plan_data.get('configuration', {}).get('root_module', {})
    config_resources = config_root.get('resources', [])

    # Build a map: address -> configuration
    config_map = {}
    for resource in config_resources:
        address = resource.get('address')
        if address:
            config_map[address] = resource

    return config_map


def process_resources(resources, resource_schemas, config_map=None):
    """
    Process all resources and create resource instances.

    Args:
        resources: List of resource data from plan.json
        resource_schemas: Schema data for all resource types
        config_map: Configuration map with expressions/references (optional)

    Returns:
        tuple: (resource_registry, skipped_types)
    """
    import lib.aws_resources as aws_resources

    resource_registry = {}
    skipped_types = set()

    if config_map is None:
        config_map = {}

    for resource in resources:
        resource_type = resource.get('type')

        # Check if resource type is supported
        if resource_type not in ALL_RESOURCES:
            if resource_type not in skipped_types:
                print(f"Warning: Skipping unsupported resource type: {resource_type}")
                skipped_types.add(resource_type)
            continue

        # Get schema for this resource type
        schema = resource_schemas.get(resource_type, {})

        # Get configuration for this resource (if available)
        resource_address = resource.get('address')
        config = config_map.get(resource_address, {})

        # Convert resource type to class name (e.g., "aws_iam_role" -> "AWS_IAM_ROLE")
        class_name = resource_type.upper()
        resource_class = getattr(aws_resources, class_name, None)

        if resource_class is None:
            # This should not happen if ALL_RESOURCES is properly maintained
            print(f"Error: Class {class_name} not found for supported type {resource_type}")
            continue

        # Instantiate resource class
        instance = resource_class(
            resource,
            schema=schema,
            resource_registry=resource_registry,
            config=config
        )

        # Register instance
        if resource_address:
            resource_registry[resource_address] = instance

    return resource_registry, skipped_types


def generate_output_files(resource_registry, output_prefix):
    """
    Generate markdown output files grouped by sheet attribute.

    Args:
        resource_registry: Dictionary of resource instances
        output_prefix: Output directory or file prefix
    """
    # Group resources by sheet
    sheets = defaultdict(list)

    for address, instance in resource_registry.items():
        if instance.generate_this_table:
            sheet_name = instance.sheet
            sheets[sheet_name].append(instance)

    # Create output directory if it doesn't exist
    output_dir = output_prefix
    if not output_dir.endswith('/'):
        # Check if it's a directory or file prefix
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            pass
        else:
            # Treat as directory
            os.makedirs(output_dir, exist_ok=True)
    else:
        os.makedirs(output_dir, exist_ok=True)

    # Generate markdown file for each sheet
    for sheet_name, instances in sheets.items():
        output_file = os.path.join(output_dir, sheet_name)

        # Sort instances by priority (higher priority first), then by type, then by name
        sorted_instances = sorted(
            instances,
            key=lambda x: (-x.priority, x.type, x.name)
        )

        with open(output_file, 'w') as f:
            # Write file header
            resource_type_name = sorted_instances[0].type if sorted_instances else "Resources"
            f.write(f"# {resource_type_name.upper()}\n\n")

            # Write each resource's table
            for instance in sorted_instances:
                # Resource section header (format: resource_type.resource_name)
                f.write(f"## {instance.type}.{instance.name}\n\n")

                # Generate and write table
                table = instance.gen_table()
                if table:
                    f.write(table)
                    f.write("\n\n")

        print(f"Generated: {output_file}")


def main():
    """Main entry point"""
    try:
        options = parse_args()

        # Load plan.json
        print(f"Loading plan file: {options.file}")
        plan_data = load_plan(options.file)

        # Load schema.json if provided
        resource_schemas = {}
        if options.schema:
            print(f"Loading schema file: {options.schema}")
            resource_schemas = load_schema(options.schema)

        # Extract resources from plan
        resources = extract_resources(plan_data)
        print(f"Found {len(resources)} resources in plan")

        # Extract configuration (including references)
        config_map = extract_configuration(plan_data)

        # Process resources
        resource_registry, skipped_types = process_resources(resources, resource_schemas, config_map)
        print(f"Processed {len(resource_registry)} supported resources")

        if skipped_types:
            print(f"Skipped {len(skipped_types)} unsupported resource types")

        # Generate output files
        generate_output_files(resource_registry, options.output)

        print("Done!")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
