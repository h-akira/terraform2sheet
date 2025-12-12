#!/usr/bin/env python3
"""
Test runner for gen_table microservice - Test003

This test uses irregular nesting depths to verify generic JSON support
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
        f.write('  <title>Test003 - Irregular Nesting Depths</title>\n')
        f.write('  <style>\n')
        f.write('    table { border-collapse: collapse; width: 100%; font-size: 14px; }\n')
        f.write('    th, td { border: 1px solid #ddd; padding: 6px; text-align: left; }\n')
        f.write('    th { background-color: #f2f2f2; font-weight: bold; }\n')
        f.write('    .param-name { font-family: monospace; font-weight: bold; background-color: #fafafa; }\n')
        f.write('    .param-value { font-family: monospace; }\n')
        f.write('    .index-cell { text-align: center; background-color: #f0f0f0; font-weight: bold; }\n')
        f.write('    .required-yes { color: #d73a49; font-weight: bold; }\n')
        f.write('    .required-no { color: #6f42c1; }\n')
        f.write('    .pending { color: #e36209; font-style: italic; }\n')
        f.write('  </style>\n')
        f.write('</head>\n')
        f.write('<body>\n')
        f.write('  <h1>Test003 - Irregular Nesting Depths</h1>\n')
        f.write('  <h2>Generic JSON Structure (Non-AWS)</h2>\n')
        f.write('  <p>This test verifies that the table generator handles:</p>\n')
        f.write('  <ul>\n')
        f.write('    <li>Simple values (string, number, bool)</li>\n')
        f.write('    <li>Shallow arrays</li>\n')
        f.write('    <li>Very deep nesting (5 levels)</li>\n')
        f.write('    <li>Mixed depths in the same structure</li>\n')
        f.write('  </ul>\n')
        f.write(html)
        f.write('\n</body>\n')
        f.write('</html>\n')

    print("✓ Table generated successfully: output.html")


if __name__ == '__main__':
    main()
