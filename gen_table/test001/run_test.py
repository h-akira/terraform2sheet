#!/usr/bin/env python3
"""
Test runner for gen_table microservice - Test001

This test uses the IAM Role example from table_spec.md
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gen_table import generate_resource_table


def main():
    # Load test data
    with open('resource_data.json', 'r', encoding='utf-8') as f:
        resource_data = json.load(f)

    with open('resource_schema.json', 'r', encoding='utf-8') as f:
        resource_schema = json.load(f)

    # Generate table
    html = generate_resource_table(
        resource_data,
        resource_schema
    )

    # Write output
    with open('output.html', 'w', encoding='utf-8') as f:
        # Add basic HTML structure
        f.write('<!DOCTYPE html>\n')
        f.write('<html>\n')
        f.write('<head>\n')
        f.write('  <meta charset="UTF-8">\n')
        f.write('  <title>Test001 - IAM Role</title>\n')
        f.write('  <style>\n')
        f.write('    table { border-collapse: collapse; width: 100%; }\n')
        f.write('    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n')
        f.write('    th { background-color: #f2f2f2; font-weight: bold; }\n')
        f.write('    .param-name { font-family: monospace; font-weight: bold; }\n')
        f.write('    .param-value { font-family: monospace; }\n')
        f.write('    .index-cell { text-align: center; background-color: #f9f9f9; }\n')
        f.write('    .required-yes { color: #d73a49; font-weight: bold; }\n')
        f.write('    .required-no { color: #6f42c1; }\n')
        f.write('    .pending { color: #e36209; font-style: italic; }\n')
        f.write('  </style>\n')
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('  <h1>Test001 - IAM Role</h1>\n')
        f.write('  <h2>aws_iam_role.lambda_role</h2>\n')
        f.write(html)
        f.write('\n</body>\n')
        f.write('</html>\n')

    print("✓ Table generated successfully: output.html")


if __name__ == '__main__':
    main()
