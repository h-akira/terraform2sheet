"""
AWS Resource Classes for terraform2sheet

This module defines classes for each AWS resource type.
Each class is responsible for:
- Parsing resource data from plan.json
- Filtering attributes based on exclusion rules
- Flattening nested values
- Generating markdown table output
"""

# List of supported AWS resource types
ALL_RESOURCES = [
    "aws_iam_role",
    "aws_iam_policy",
    "aws_s3_bucket",
]


class BaseResourceClass:
    """Base class for AWS resources with common functionality"""

    sheet = "default.md"
    generate_this_table = True
    priority = 0  # Higher priority resources appear first in the output
    custom_descriptions = {}

    def __init__(self, resource, schema=None, resource_registry=None):
        """
        Initialize resource instance.

        Args:
            resource: Resource data from plan.json
            schema: Schema data from schema.json for this resource type
            resource_registry: Dictionary of all resource instances (for relationships)
        """
        self.resource = resource
        self.schema = schema
        self.resource_registry = resource_registry
        self.address = resource.get("address", "")
        self.name = resource.get("name", "")
        self.type = resource.get("type", "")
        self.values = resource.get("values", {})

    def _should_exclude_attribute(self, attr_name):
        """
        Check if an attribute should be excluded from the output.

        Exclusion rules:
        - tags.*: Exclude all tags except tags.Name
        - tags_all.*: Exclude all (Terraform-generated)
        - id: Exclude (computed by AWS)
        - arn: Exclude (computed by AWS)
        - Attributes that are only computed (not required/optional)

        Args:
            attr_name: attribute name (e.g., "tags.Environment", "id", "arn")

        Returns:
            bool: True if should be excluded, False otherwise
        """
        # Always exclude these
        if attr_name in ['id', 'arn', 'tags_all']:
            return True

        # Exclude tags.* except tags.Name
        if attr_name.startswith('tags.') and attr_name != 'tags.Name':
            return True
        if attr_name.startswith('tags_all.'):
            return True

        # Check if attribute is computed-only (no required/optional)
        attr_info = self._get_attribute_info(attr_name)
        if attr_info:
            is_computed = attr_info.get('computed', False)
            is_required = attr_info.get('required', False)
            is_optional = attr_info.get('optional', False)

            # Exclude if only computed (not user-configurable)
            if is_computed and not is_required and not is_optional:
                return True

        return False

    def _flatten_values(self, values, prefix=""):
        """
        Recursively flatten nested values into a flat list.
        Excludes certain attributes based on _should_exclude_attribute().

        Args:
            values: dict or list to flatten
            prefix: current key prefix

        Returns:
            list of dict: [
                {'key': 'bucket', 'value': 'my-bucket'},
                {'key': 'tags.Name', 'value': 'my-resource'},
                {'key': 'cors_rule[0].allowed_methods[0]', 'value': 'GET'},
                ...
            ]
            (excluding id, arn, tags.* except Name, etc.)
        """
        result = []

        if isinstance(values, dict):
            for key, value in values.items():
                full_key = f"{prefix}.{key}" if prefix else key

                # Check if this attribute should be excluded
                if self._should_exclude_attribute(full_key):
                    continue

                if isinstance(value, (dict, list)):
                    result.extend(self._flatten_values(value, full_key))
                else:
                    result.append({'key': full_key, 'value': value})
        elif isinstance(values, list):
            for i, item in enumerate(values):
                full_key = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    result.extend(self._flatten_values(item, full_key))
                else:
                    result.append({'key': full_key, 'value': item})
        else:
            result.append({'key': prefix, 'value': values})

        return result

    def _get_attribute_info(self, attr_name):
        """
        Get schema information for an attribute (supports nested keys).

        Args:
            attr_name: attribute name, possibly nested (e.g., "tags.Environment", "cors_rule[0].allowed_methods[1]")

        Returns:
            dict: {
                'type': str,
                'required': bool,
                'optional': bool,
                'computed': bool,
                'description': str,
                'deprecated': bool
            }
        """
        if not self.schema:
            return {}

        # Parse the attribute name to get the root and nested path
        # e.g., "cors_rule[0].allowed_methods[1]" -> root="cors_rule", nested_path=...
        root_attr = attr_name.split('.')[0].split('[')[0]

        # Try to get from attributes first
        attributes = self.schema.get('block', {}).get('attributes', {})
        if root_attr in attributes:
            return attributes[root_attr]

        # Try to get from block_types for nested structures
        block_types = self.schema.get('block', {}).get('block_types', {})
        if root_attr in block_types:
            # Navigate nested path in block_types
            return self._get_nested_schema(block_types[root_attr], attr_name[len(root_attr):])

        return {}

    def _get_nested_schema(self, block_schema, path):
        """
        Navigate nested schema using path like ".create" or "[0].allowed_methods[1]"

        Args:
            block_schema: current block schema
            path: remaining path to navigate

        Returns:
            dict: schema information for the nested attribute
        """
        # Simplified implementation - returns the block schema for now
        # Full implementation would parse the path and navigate the schema tree
        return block_schema.get('block', {})

    def _get_description(self, attr_name):
        """
        Get description for an attribute (supports nested keys).
        Prioritizes custom_descriptions over schema.json.

        Args:
            attr_name: attribute name, possibly nested

        Returns:
            str: Description text
        """
        # Check custom descriptions first
        if hasattr(self, 'custom_descriptions') and attr_name in self.custom_descriptions:
            return self.custom_descriptions[attr_name]

        # For nested attributes, try to get description from root or parent
        root_attr = attr_name.split('.')[0].split('[')[0]
        if hasattr(self, 'custom_descriptions') and root_attr in self.custom_descriptions:
            return self.custom_descriptions[root_attr]

        # Fall back to schema description
        attr_info = self._get_attribute_info(attr_name)
        return attr_info.get('description', '')

    def _format_value(self, value):
        """Format a value for display in markdown table"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, str):
            # Escape pipe characters for markdown tables
            return value.replace('|', '\\|')
        else:
            return str(value)

    def _get_required_status(self, attr_name):
        """Get required/optional status for an attribute"""
        attr_info = self._get_attribute_info(attr_name)
        if not attr_info:
            return "-"

        if attr_info.get('required', False):
            return "Yes"
        elif attr_info.get('optional', False):
            return "No"
        else:
            return "-"

    def _get_default_value(self, attr_name):
        """Get default value for an attribute"""
        attr_info = self._get_attribute_info(attr_name)
        if not attr_info:
            return "-"

        if attr_info.get('computed', False):
            return "(computed)"

        # Could add more sophisticated default value detection here
        return "-"

    def gen_table(self):
        """
        Generate markdown table with columns:
        - Parameter: attribute name (flattened)
        - Value: actual value from plan.json
        - Required: Yes/No/-
        - Default: default value or (computed) or -
        - Description: from schema.json or custom_descriptions

        Returns:
            str: Markdown formatted table
        """
        # Flatten all values
        flattened = self._flatten_values(self.values)

        if not flattened:
            return ""

        # Build markdown table
        lines = []
        lines.append("| パラメータ | 値 | 必須 | デフォルト | 説明 |")
        lines.append("|-----------|-----|------|-----------|------|")

        for item in flattened:
            key = item['key']
            value = self._format_value(item['value'])
            required = self._get_required_status(key)
            default = self._get_default_value(key)
            description = self._get_description(key)

            lines.append(f"| {key} | {value} | {required} | {default} | {description} |")

        return "\n".join(lines)


class AWS_IAM_ROLE(BaseResourceClass):
    """IAM Role resource"""

    sheet = "IAM.md"
    generate_this_table = True
    priority = 100  # High priority for IAM resources

    # Custom Japanese descriptions
    custom_descriptions = {
        "name": "IAM Roleの名前",
        "assume_role_policy": "このRoleを引き受けることができるエンティティを定義するポリシー(JSON形式)",
        "description": "IAM Roleの説明",
        "max_session_duration": "セッションの最大継続時間(秒)。デフォルトは3600秒(1時間)",
        "force_detach_policies": "Role削除時にアタッチされているポリシーを強制的にデタッチするかどうか",
        "path": "IAM Roleのパス。デフォルトは/",
        "permissions_boundary": "このRoleに設定するアクセス許可の境界のARN",
        "tags.Name": "リソースの名前を示すタグ",
    }

    def __init__(self, resource, schema=None, resource_registry=None):
        super().__init__(resource, schema, resource_registry)
        self.attached_policies = []  # Will be populated by attachment resources


class AWS_IAM_POLICY(BaseResourceClass):
    """IAM Policy resource"""

    sheet = "IAM.md"
    generate_this_table = True
    priority = 90  # Slightly lower priority than IAM Role

    # Custom Japanese descriptions
    custom_descriptions = {
        "name": "IAM Policyの名前",
        "policy": "ポリシードキュメント(JSON形式)。リソースへのアクセス権限を定義",
        "description": "IAM Policyの説明",
        "path": "IAM Policyのパス。デフォルトは/",
        "tags.Name": "リソースの名前を示すタグ",
    }


class AWS_S3_BUCKET(BaseResourceClass):
    """S3 Bucket resource"""

    sheet = "S3.md"
    generate_this_table = True
    priority = 50  # Medium priority for storage resources

    # Custom Japanese descriptions
    custom_descriptions = {
        "bucket": "S3バケットの名前。グローバルで一意である必要があります",
        "force_destroy": "バケット削除時に中身が空でなくても強制的に削除するかどうか",
        "tags.Name": "リソースの名前を示すタグ",
        "timeouts": "リソース作成・更新・削除のタイムアウト設定",
    }
