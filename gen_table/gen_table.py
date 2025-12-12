"""
Terraform2Sheet Table Generation Microservice

This module generates HTML tables from resource data, schema, and descriptions.
Based on specification: specification/table_spec.md
"""

import re
from typing import Dict, List, Any, Optional


def generate_resource_table(
    resource_data: dict,
    resource_schema: dict
) -> str:
    """
    Generate HTML table for a single resource.

    Args:
        resource_data: Resource parameter names and values
        resource_schema: Resource type schema definition (may include custom descriptions)

    Returns:
        HTML string containing the table
    """
    # Flatten nested resource data
    flattened_attrs = _flatten_attributes(resource_data)

    # Integrate data from all sources
    table_rows = []
    for attr in flattened_attrs:
        row = _generate_table_row(
            attr['name'],
            attr['value'],
            resource_schema
        )
        table_rows.append(row)

    # Structure attributes for rendering
    structured_attrs = _structure_attributes(table_rows)

    # Determine max depth
    max_depth = _get_max_depth(structured_attrs)

    # Generate HTML
    html_parts = []
    html_parts.append('<table>')
    html_parts.append(_generate_table_header(max_depth))
    html_parts.append('<tbody>')
    html_parts.extend(_render_structured_attributes(structured_attrs, max_depth))
    html_parts.append('</tbody>')
    html_parts.append('</table>')

    return '\n'.join(html_parts)


def _flatten_attributes(resource_data: dict, prefix: str = '') -> List[Dict[str, Any]]:
    """
    Flatten nested resource data into a list of attributes.

    Args:
        resource_data: Nested dictionary or list
        prefix: Current attribute name prefix

    Returns:
        List of {name, value} dictionaries
    """
    result = []

    if isinstance(resource_data, dict):
        for key, value in resource_data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key

            if isinstance(value, (dict, list)):
                result.extend(_flatten_attributes(value, new_prefix))
            else:
                result.append({'name': new_prefix, 'value': value})

    elif isinstance(resource_data, list):
        for index, item in enumerate(resource_data):
            new_prefix = f"{prefix}[{index}]"

            if isinstance(item, (dict, list)):
                result.extend(_flatten_attributes(item, new_prefix))
            else:
                result.append({'name': new_prefix, 'value': item})

    return result


def _generate_table_row(
    attr_name: str,
    attr_value: Any,
    resource_schema: dict
) -> dict:
    """
    Generate table row data for a single attribute.

    Args:
        attr_name: Attribute name (may be nested like "ingress[0].from_port")
        attr_value: Attribute value
        resource_schema: Resource schema

    Returns:
        Dictionary with parameter, value, required, description
    """
    # Extract top-level attribute name
    top_level_name = attr_name.split('[')[0].split('.')[0]

    # Get schema for this attribute
    attribute_schema = resource_schema.get("block", {}).get("attributes", {}).get(top_level_name, {})

    # Determine required flag
    required_flag = _get_required_flag(attribute_schema)

    # Get description from schema
    description = _get_description(attribute_schema)

    return {
        'name': attr_name,
        'value': attr_value,
        'required': required_flag,
        'description': description
    }


def _get_required_flag(attribute: dict) -> str:
    """
    Determine required flag from schema attribute.

    Args:
        attribute: Schema attribute definition

    Returns:
        "Yes" (required), "No" (optional), or "-" (computed-only)
    """
    if attribute.get("required"):
        return "Yes"
    elif attribute.get("optional"):
        return "No"
    elif attribute.get("computed"):
        return "-"
    else:
        return "No"


def _get_description(attribute_schema: dict) -> str:
    """
    Get description from attribute schema.

    Args:
        attribute_schema: Attribute schema definition

    Returns:
        Description string (empty if not present)
    """
    description = attribute_schema.get("description", "")
    return description if description else ""


def _structure_attributes(table_rows: List[dict]) -> List[dict]:
    """
    Parse attribute names into structured format with nesting levels.

    Args:
        table_rows: List of table row data

    Returns:
        List of structured attribute dictionaries
    """
    structured = []

    for row in table_rows:
        name = row['name']
        levels = []

        # Parse the name to extract all levels
        # Pattern: name[index].name[index]...
        remaining = name
        while remaining:
            # Match: name[index] or just name
            match = re.match(r'^([^\[\.]*)(?:\[(\d+)\])?\.?', remaining)
            if not match:
                break

            param_name = match.group(1)
            param_index = match.group(2)

            if param_name:  # Skip empty names
                levels.append({
                    'name': param_name,
                    'index': str(int(param_index) + 1) if param_index else None
                })

            # Move to the next part
            remaining = remaining[match.end():]

        structured.append({
            'levels': levels,
            'row': row
        })

    return structured


def _get_max_depth(structured_attrs: List[dict]) -> int:
    """
    Get the maximum nesting depth across all attributes.

    Args:
        structured_attrs: List of structured attributes

    Returns:
        Maximum depth
    """
    if not structured_attrs:
        return 1
    return max(len(item['levels']) for item in structured_attrs)


def _generate_table_header(max_depth: int) -> str:
    """
    Generate HTML table header.

    Args:
        max_depth: Maximum nesting depth

    Returns:
        HTML string for table header
    """
    parts = ['<thead>', '  <tr>']

    if max_depth > 0:
        colspan = max_depth * 2  # Each level has parameter + index
        parts.append(f'    <th colspan="{colspan}">パラメータ</th>')

    parts.append('    <th>値</th>')
    parts.append('    <th>必須</th>')
    parts.append('    <th>説明</th>')
    parts.append('  </tr>')
    parts.append('</thead>')

    return '\n'.join(parts)


def _render_structured_attributes(structured_attrs: List[dict], max_depth: int) -> List[str]:
    """
    Render structured attributes with proper cell merging.

    Args:
        structured_attrs: List of structured attributes
        max_depth: Maximum nesting depth

    Returns:
        List of HTML table row strings
    """
    html_rows = []
    rowspan_counters = {}  # Track how many rows each level should span

    # First pass: calculate rowspans
    for item in structured_attrs:
        levels = item['levels']

        for depth in range(len(levels)):
            level = levels[depth]

            # Key for the full path including indices (for index cells)
            full_key = tuple((l['name'], l['index']) for l in levels[:depth+1])
            if full_key not in rowspan_counters:
                rowspan_counters[full_key] = 0
            rowspan_counters[full_key] += 1

            # Key for parameter name only (for parameter name cells)
            name_key = tuple((l['name'], l['index']) for l in levels[:depth]) + (level['name'], None)
            if name_key not in rowspan_counters:
                rowspan_counters[name_key] = 0
            rowspan_counters[name_key] += 1

    # Second pass: render rows
    rendered_cells = {}  # Track which cells have been rendered

    for item in structured_attrs:
        levels = item['levels']
        row = item['row']

        row_parts = ['  <tr>']

        # Count occupied columns (including rowspan-merged cells)
        occupied_cols = 0

        # Render each level (parameter + index pairs)
        is_simple_attr = len(levels) == 1 and levels[0]['index'] is None
        if is_simple_attr and max_depth > 1:
            # Simple attribute - merge across all parameter/index columns
            level = levels[0]
            key = tuple((l['name'], l['index']) for l in levels)
            should_render = key not in rendered_cells

            if should_render:
                rowspan = rowspan_counters.get(key, 1)
                rendered_cells[key] = True
                colspan = max_depth * 2
                occupied_cols = colspan

                row_parts.append(
                    f'    <td class="param-name" rowspan="{rowspan}" colspan="{colspan}">'
                    f'{_escape_html(level["name"])}</td>'
                )
            else:
                # Cell is rowspan-merged from previous row, but still occupies columns
                occupied_cols = max_depth * 2
        else:
            # Nested attributes - render each level normally
            for depth in range(max_depth):
                if depth < len(levels):
                    level = levels[depth]

                    # Key for parameter name cell
                    name_key = tuple((l['name'], l['index']) for l in levels[:depth]) + (level['name'], None)
                    # Key for index cell
                    index_key = tuple((l['name'], l['index']) for l in levels[:depth+1])

                    # Render parameter name cell
                    should_render_name = name_key not in rendered_cells
                    if should_render_name:
                        name_rowspan = rowspan_counters.get(name_key, 1)
                        rendered_cells[name_key] = True
                        row_parts.append(
                            f'    <td class="param-name" rowspan="{name_rowspan}">'
                            f'{_escape_html(level["name"])}</td>'
                        )
                    # Count column even if rowspan-merged
                    occupied_cols += 1

                    # Render index cell
                    should_render_index = index_key not in rendered_cells
                    if should_render_index:
                        index_rowspan = rowspan_counters.get(index_key, 1)
                        rendered_cells[index_key] = True

                        if level['index']:
                            row_parts.append(
                                f'    <td class="index-cell" rowspan="{index_rowspan}">'
                                f'{level["index"]}</td>'
                            )
                        else:
                            row_parts.append(f'    <td rowspan="{index_rowspan}">-</td>')
                    # Count column even if rowspan-merged
                    occupied_cols += 1

            # After rendering all actual levels, fill remaining columns
            # Total columns should be max_depth * 2
            remaining_cols = (max_depth * 2) - occupied_cols
            if remaining_cols > 0:
                row_parts.append(f'    <td colspan="{remaining_cols}"></td>')

        # Value
        value_class = "param-value"
        value_str = str(row['value'])
        if value_str.startswith('(pending)'):
            value_class += " pending"
        row_parts.append(f'    <td class="{value_class}">{_escape_html(value_str)}</td>')

        # Required (with color coding)
        required_class = ""
        if row['required'] == "Yes":
            required_class = "required-yes"
        elif row['required'] == "No":
            required_class = "required-no"
        row_parts.append(f'    <td class="{required_class}">{row["required"]}</td>')

        # Description
        row_parts.append(f'    <td>{_escape_html(row["description"])}</td>')

        row_parts.append('  </tr>')
        html_rows.append('\n'.join(row_parts))

    return html_rows


def _escape_html(text: Any) -> str:
    """
    Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        Escaped string
    """
    if text is None:
        return ""
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#39;')
    return text
