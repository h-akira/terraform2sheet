"""
View classes for HTML output generation.

Each view class is responsible for:
- Receiving a list of resource instances
- Generating HTML tables with proper styling and cell merging
- Writing output to HTML files
"""

import re


class BaseView:
    """Base class for all views"""

    output_file = "default.html"  # Default output filename

    def __init__(self, resources):
        """
        Initialize view with resources.

        Args:
            resources: List of resource instances (all same view_class)
        """
        self.resources = resources

    def render(self):
        """
        Render HTML output.

        Returns:
            str: Complete HTML document
        """
        html_parts = []

        # HTML header
        html_parts.append(self._render_header())

        # CSS styles
        html_parts.append(self._render_styles())

        # Body start
        html_parts.append('<body>')
        html_parts.append(f'<h1>{self._get_page_title()}</h1>')

        # Sort resources by priority (desc), type (asc), name (asc)
        sorted_resources = sorted(
            self.resources,
            key=lambda x: (-x.priority, x.type, x.name)
        )

        # Render each resource
        for resource in sorted_resources:
            if resource.generate_this_table:
                data = resource.gen_data()
                html_parts.append(self._render_resource(data))

        # Body end
        html_parts.append('</body>')
        html_parts.append('</html>')

        return '\n'.join(html_parts)

    def _render_header(self):
        """Render HTML header"""
        return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>""".format(title=self._get_page_title())

    def _render_styles(self):
        """Render CSS styles"""
        return """<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
        margin: 20px;
        background-color: #f6f8fa;
    }
    h1 {
        color: #24292e;
        border-bottom: 3px solid #0366d6;
        padding-bottom: 10px;
    }
    h2 {
        color: #24292e;
        background-color: #e1e4e8;
        padding: 8px 12px;
        border-left: 4px solid #0366d6;
        margin-top: 30px;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 30px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    thead {
        background-color: #0366d6;
        color: white;
    }
    th, td {
        border: 1px solid #d1d5da;
        padding: 8px 12px;
        text-align: left;
        vertical-align: top;
    }
    th {
        font-weight: 600;
    }
    tbody tr:hover {
        background-color: #f6f8fa;
    }
    .index-cell {
        background-color: #f1f8ff;
        font-weight: 600;
        text-align: center;
        color: #0366d6;
        min-width: 50px;
    }
    .param-name {
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.9em;
        color: #032f62;
    }
    .param-value {
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.9em;
        word-break: break-all;
    }
    .required-yes {
        color: #d73a49;
        font-weight: 600;
    }
    .required-no {
        color: #6a737d;
    }
    .computed {
        color: #6f42c1;
        font-style: italic;
    }
    .pending {
        color: #e36209;
        font-style: italic;
    }
</style>"""

    def _get_page_title(self):
        """Get page title (override in subclass)"""
        return "Terraform Resources"

    def _render_resource(self, data):
        """
        Render a single resource as HTML table with cell merging for nested data.

        Args:
            data: dict from resource.gen_data()

        Returns:
            str: HTML for this resource
        """
        html_parts = []

        # Resource heading
        html_parts.append(f'<h2>{self._escape_html(data["resource_address"])}</h2>')

        # Parse attributes into structured format
        structured_attrs = self._structure_attributes(data['attributes'])

        # Determine the maximum nesting depth
        max_depth = self._get_max_depth(structured_attrs)

        # Table
        html_parts.append('<table>')

        # Table header (single merged header for all parameter/index columns)
        html_parts.append('<thead>')
        html_parts.append('  <tr>')
        if max_depth > 0:
            colspan = max_depth * 2  # Each level has parameter + index
            html_parts.append(f'    <th colspan="{colspan}">パラメータ</th>')
        html_parts.append('    <th>値</th>')
        html_parts.append('    <th>必須</th>')
        html_parts.append('    <th>デフォルト</th>')
        html_parts.append('    <th>説明</th>')
        html_parts.append('  </tr>')
        html_parts.append('</thead>')

        # Table body
        html_parts.append('<tbody>')
        html_parts.extend(self._render_structured_attributes(structured_attrs, max_depth))
        html_parts.append('</tbody>')

        html_parts.append('</table>')

        return '\n'.join(html_parts)

    def _structure_attributes(self, attributes):
        """
        Parse attribute names into structured format with nesting levels.

        Example:
        "cors_rule[0].allowed_methods[1]" ->
        {
            'levels': [
                {'name': 'cors_rule', 'index': '1'},
                {'name': 'allowed_methods', 'index': '2'}
            ],
            'attr': {...original attribute...}
        }
        """
        structured = []

        for attr in attributes:
            name = attr['name']
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
                'attr': attr
            })

        return structured

    def _get_max_depth(self, structured_attrs):
        """Get the maximum nesting depth across all attributes"""
        if not structured_attrs:
            return 1
        return max(len(item['levels']) for item in structured_attrs)

    def _render_structured_attributes(self, structured_attrs, max_depth):
        """
        Render structured attributes with proper cell merging.

        Returns:
            list of str: HTML table rows
        """
        html_rows = []
        prev_levels = [None] * max_depth
        rowspan_counters = {}  # Track how many rows each level should span

        # First pass: calculate rowspans
        # For parameter names (without considering index), we want to merge all consecutive same names
        for i, item in enumerate(structured_attrs):
            levels = item['levels']

            # For each depth level, calculate rowspan
            for depth in range(len(levels)):
                level = levels[depth]

                # Key for the full path including indices (for index cells)
                full_key = tuple((l['name'], l['index']) for l in levels[:depth+1])
                if full_key not in rowspan_counters:
                    rowspan_counters[full_key] = 0
                rowspan_counters[full_key] += 1

                # Key for parameter name only (for parameter name cells)
                # We want to merge consecutive cells with the same parameter name at this depth
                name_key = tuple((l['name'], l['index']) for l in levels[:depth]) + (level['name'], None)
                if name_key not in rowspan_counters:
                    rowspan_counters[name_key] = 0
                rowspan_counters[name_key] += 1

        # Second pass: render rows
        prev_levels = [None] * max_depth
        rendered_cells = {}  # Track which cells have been rendered

        for item in structured_attrs:
            levels = item['levels']
            attr = item['attr']

            row_parts = ['  <tr>']

            # Render each level (parameter + index pairs)
            # For simple attributes (depth 1 and no index), merge across all parameter/index columns
            is_simple_attr = len(levels) == 1 and levels[0]['index'] is None
            if is_simple_attr and max_depth > 1:
                # Simple attribute - merge the first cell across all parameter/index columns
                level = levels[0]
                key = tuple((l['name'], l['index']) for l in levels)
                should_render = key not in rendered_cells

                if should_render:
                    rowspan = rowspan_counters.get(key, 1)
                    rendered_cells[key] = True
                    colspan = max_depth * 2  # Each level has parameter + index columns

                    # Parameter name cell merged across all columns
                    row_parts.append(f'    <td class="param-name" rowspan="{rowspan}" colspan="{colspan}">{self._escape_html(level["name"])}</td>')
            else:
                # Nested attributes - render each level normally
                for depth in range(max_depth):
                    if depth < len(levels):
                        level = levels[depth]

                        # Key for parameter name cell (merges same names)
                        name_key = tuple((l['name'], l['index']) for l in levels[:depth]) + (level['name'], None)
                        # Key for index cell (unique per index)
                        index_key = tuple((l['name'], l['index']) for l in levels[:depth+1])

                        # Render parameter name cell
                        should_render_name = name_key not in rendered_cells
                        if should_render_name:
                            name_rowspan = rowspan_counters.get(name_key, 1)
                            rendered_cells[name_key] = True
                            row_parts.append(f'    <td class="param-name" rowspan="{name_rowspan}">{self._escape_html(level["name"])}</td>')

                        # Render index cell
                        should_render_index = index_key not in rendered_cells
                        if should_render_index:
                            index_rowspan = rowspan_counters.get(index_key, 1)
                            rendered_cells[index_key] = True

                            if level['index']:
                                row_parts.append(f'    <td class="index-cell" rowspan="{index_rowspan}">{level["index"]}</td>')
                            else:
                                row_parts.append(f'    <td rowspan="{index_rowspan}">-</td>')
                    else:
                        # Empty cells for shorter paths
                        # These are handled by rowspan from previous rows
                        pass

            # Value (with special formatting for pending/null)
            value_class = "param-value"
            value_str = str(attr['value'])
            if value_str.startswith('(pending)'):
                value_class += " pending"
            row_parts.append(f'    <td class="{value_class}">{self._escape_html(value_str)}</td>')

            # Required (with color coding)
            required_class = ""
            if attr['required'] == "Yes":
                required_class = "required-yes"
            elif attr['required'] == "No":
                required_class = "required-no"
            row_parts.append(f'    <td class="{required_class}">{attr["required"]}</td>')

            # Default (with special formatting for computed)
            default_class = ""
            if attr['default'] == "(computed)":
                default_class = "computed"
            row_parts.append(f'    <td class="{default_class}">{attr["default"]}</td>')

            # Description
            row_parts.append(f'    <td>{self._escape_html(attr["description"])}</td>')

            row_parts.append('  </tr>')
            html_rows.append('\n'.join(row_parts))

        return html_rows

    def _escape_html(self, text):
        """Escape HTML special characters"""
        if text is None:
            return ""
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text

    def write_file(self, output_dir):
        """
        Write HTML to file.

        Args:
            output_dir: Output directory path
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, self.output_file)
        html_content = self.render()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"Generated: {output_path}")


class IAMView(BaseView):
    """View for IAM resources"""

    output_file = "IAM.html"

    def _get_page_title(self):
        return "AWS IAM Resources"


class S3View(BaseView):
    """View for S3 resources"""

    output_file = "S3.html"

    def _get_page_title(self):
        return "AWS S3 Resources"


class NetworkView(BaseView):
    """View for network resources (VPC, Subnet, etc.)"""

    output_file = "Network.html"

    def _get_page_title(self):
        return "AWS Network Resources"


class DefaultView(BaseView):
    """Default view for uncategorized resources"""

    output_file = "Other.html"

    def _get_page_title(self):
        return "Other AWS Resources"
