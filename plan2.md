# terraform2sheet Phase 2.5: HTML出力対応

## 概要
Markdown形式からHTML形式へ出力を移行する。HTMLを採用する理由：
- **セルの結合**: 同じリソース内で属性名が重複する場合にrowspanを使用可能
- **CSS適用**: テーブルのスタイリング、カラーコーディング、レスポンシブデザインが可能
- **リッチな表現**: アイコン、ツールチップ、折りたたみなどのインタラクティブ要素を追加可能

## アーキテクチャ変更

### 現在の構造
```
bin/tfp2ps.py
  ↓ インスタンス化
lib/aws_resources.py (BaseResourceClass, AWS_IAM_ROLE, etc.)
  ↓ gen_table() でMarkdown文字列を返す
出力ファイル (IAM.md, S3.md)
```

### 新しい構造
```
bin/tfp2ps.py
  ↓ インスタンス化
lib/aws_resources.py (BaseResourceClass, AWS_IAM_ROLE, etc.)
  ↓ データ構造を返す（gen_data()メソッド）
lib/views.py (BaseView, IAMView, S3View, etc.)
  ↓ HTML生成（render()メソッド）
出力ファイル (IAM.html, S3.html)
```

## 設計方針

### 1. 責務の分離

#### リソースクラス (lib/aws_resources.py)
- **責務**: データの抽出・加工のみ
- **変更点**:
  - `gen_table()` → `gen_data()`に変更
  - Markdown文字列を返すのではなく、構造化されたデータを返す
  - `sheet`属性 → `view_class`属性に変更（Viewクラス名を指定）

#### Viewクラス (lib/views.py)
- **責務**: HTMLの生成とスタイリング
- **役割**:
  - リソースインスタンスのリストを受け取る
  - HTML形式のテーブルを生成
  - CSSスタイルを適用
  - ファイル出力

### 2. lib/aws_resources.pyの変更

#### 2.1 BaseResourceClassの変更

```python
class BaseResourceClass:
    # 変更前: sheet = "IAM.md"
    # 変更後: view_classを指定（文字列でクラス名）
    view_class = "DefaultView"  # "IAMView", "S3View", etc.

    generate_this_table = True
    priority = 0
    custom_descriptions = {}

    def __init__(self, resource, schema=None, resource_registry=None, config=None):
        # 既存のまま
        pass

    def gen_data(self):
        """
        Generate structured data for rendering.

        Returns:
            dict: {
                'resource_type': str,  # e.g., "aws_iam_role"
                'resource_name': str,  # e.g., "lambda_role"
                'resource_address': str,  # e.g., "aws_iam_role.lambda_role"
                'attributes': [
                    {
                        'name': str,        # e.g., "assume_role_policy"
                        'value': Any,       # e.g., "{...json...}"
                        'required': str,    # "Yes" / "No" / "-"
                        'default': str,     # "(computed)" / "false" / "-"
                        'description': str, # 説明文
                    },
                    ...
                ]
            }
        """
        flattened = self._flatten_values(self.values)

        attributes = []
        for item in flattened:
            attr_name = item['key']
            attr_value = item['value']

            # Get schema info
            attr_info = self._get_attribute_info(attr_name)

            # Determine required/optional/computed
            required = "-"
            if attr_info:
                if attr_info.get('required', False):
                    required = "Yes"
                elif attr_info.get('optional', False):
                    required = "No"

            # Determine default value
            default = "-"
            if attr_info and attr_info.get('computed', False):
                default = "(computed)"

            # Get description
            description = self._get_description(attr_name)

            attributes.append({
                'name': attr_name,
                'value': attr_value,
                'required': required,
                'default': default,
                'description': description,
            })

        return {
            'resource_type': self.type,
            'resource_name': self.name,
            'resource_address': self.address,
            'attributes': attributes,
        }

    # 既存のメソッドはそのまま残す
    # _should_exclude_attribute(), _flatten_values(),
    # _get_attribute_info(), _get_nested_schema(), _get_description()
```

#### 2.2 各リソースクラスの変更例

```python
class AWS_IAM_ROLE(BaseResourceClass):
    view_class = "IAMView"  # 変更: sheet → view_class
    generate_this_table = True
    priority = 100

    custom_descriptions = {
        "name": "IAM Roleの名前",
        "assume_role_policy": "このRoleを引き受けることができるエンティティを定義するポリシー(JSON形式)",
        # ... 既存のまま
    }

    def __init__(self, resource, schema=None, resource_registry=None, config=None):
        super().__init__(resource, schema, resource_registry, config)
        self.attached_policies = []

    def gen_data(self):
        """
        Override to include attached_policies in attributes.
        """
        data = super().gen_data()

        # Add attached_policies to attributes
        for i, policy_arn in enumerate(self.attached_policies):
            data['attributes'].append({
                'name': f'attached_policies[{i}]',
                'value': policy_arn,
                'required': '-',
                'default': '-',
                'description': 'このRoleにアタッチされているIAMポリシーのARN一覧',
            })

        return data
```

```python
class AWS_IAM_POLICY(BaseResourceClass):
    view_class = "IAMView"  # 同じViewを共有
    generate_this_table = True
    priority = 90

    custom_descriptions = {
        "name": "IAM Policyの名前",
        # ...
    }

class AWS_S3_BUCKET(BaseResourceClass):
    view_class = "S3View"
    generate_this_table = True
    priority = 50

    custom_descriptions = {
        "bucket": "S3バケット名",
        # ...
    }
```

### 3. lib/views.pyの新規作成

#### 3.1 基本構造

```python
"""
View classes for HTML output generation.

Each view class is responsible for:
- Receiving a list of resource instances
- Generating HTML tables with proper styling
- Writing output to HTML files
"""

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
    }
    th {
        font-weight: 600;
    }
    tbody tr:hover {
        background-color: #f6f8fa;
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
        Render a single resource as HTML table.

        Args:
            data: dict from resource.gen_data()

        Returns:
            str: HTML for this resource
        """
        html_parts = []

        # Resource heading
        html_parts.append(f'<h2>{data["resource_address"]}</h2>')

        # Table
        html_parts.append('<table>')

        # Table header
        html_parts.append('<thead>')
        html_parts.append('  <tr>')
        html_parts.append('    <th>パラメータ</th>')
        html_parts.append('    <th>値</th>')
        html_parts.append('    <th>必須</th>')
        html_parts.append('    <th>デフォルト</th>')
        html_parts.append('    <th>説明</th>')
        html_parts.append('  </tr>')
        html_parts.append('</thead>')

        # Table body
        html_parts.append('<tbody>')
        for attr in data['attributes']:
            html_parts.append('  <tr>')

            # Parameter name
            html_parts.append(f'    <td class="param-name">{self._escape_html(attr["name"])}</td>')

            # Value (with special formatting for pending/null)
            value_class = "param-value"
            value_str = str(attr['value'])
            if value_str.startswith('(pending)'):
                value_class += " pending"
            html_parts.append(f'    <td class="{value_class}">{self._escape_html(value_str)}</td>')

            # Required (with color coding)
            required_class = ""
            if attr['required'] == "Yes":
                required_class = "required-yes"
            elif attr['required'] == "No":
                required_class = "required-no"
            html_parts.append(f'    <td class="{required_class}">{attr["required"]}</td>')

            # Default (with special formatting for computed)
            default_class = ""
            if attr['default'] == "(computed)":
                default_class = "computed"
            html_parts.append(f'    <td class="{default_class}">{attr["default"]}</td>')

            # Description
            html_parts.append(f'    <td>{self._escape_html(attr["description"])}</td>')

            html_parts.append('  </tr>')
        html_parts.append('</tbody>')

        html_parts.append('</table>')

        return '\n'.join(html_parts)

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
```

#### 3.2 具体的なViewクラス

```python
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


class ComputeView(BaseView):
    """View for compute resources (EC2, Lambda, etc.)"""

    output_file = "Compute.html"

    def _get_page_title(self):
        return "AWS Compute Resources"


class DatabaseView(BaseView):
    """View for database resources (RDS, DynamoDB, etc.)"""

    output_file = "Database.html"

    def _get_page_title(self):
        return "AWS Database Resources"


class DefaultView(BaseView):
    """Default view for uncategorized resources"""

    output_file = "Other.html"

    def _get_page_title(self):
        return "Other AWS Resources"
```

### 4. bin/tfp2ps.pyの変更

```python
def main():
    # ... (既存のplan.json, schema.json読み込み処理)

    # Process resources (既存のまま)
    resource_registry, skipped_types = process_resources(
        resources,
        resource_schemas,
        config_map
    )

    # Group resources by view_class (変更点)
    from lib import views
    view_groups = {}  # view_class名 -> リソースインスタンスのリスト

    for address, instance in resource_registry.items():
        if instance.generate_this_table:
            view_class_name = getattr(instance, 'view_class', 'DefaultView')

            if view_class_name not in view_groups:
                view_groups[view_class_name] = []

            view_groups[view_class_name].append(instance)

    # Generate output files using views (変更点)
    for view_class_name, instances in view_groups.items():
        # Get view class
        view_class = getattr(views, view_class_name, views.DefaultView)

        # Create view instance
        view = view_class(instances)

        # Write HTML file
        view.write_file(options.output)

    print("Done!")
```

## 移行計画

### Phase 2.5.1: View層の基本実装
1. `lib/views.py`を作成
   - `BaseView`クラスを実装
   - `IAMView`, `S3View`を実装
2. `lib/aws_resources.py`を修正
   - `BaseResourceClass.gen_data()`を実装
   - `AWS_IAM_ROLE.gen_data()`をオーバーライド
   - `sheet` → `view_class`に変更
3. `bin/tfp2ps.py`を修正
   - Viewによる出力処理に変更

### Phase 2.5.2: 既存サンプルでのテスト
1. sample000で実行
   - `IAM.html`, `S3.html`が生成されることを確認
2. sample001で実行
   - ネストされた値のHTML表示を確認
3. sample002で実行
   - Policy Attachmentが正しく表示されることを確認

### Phase 2.5.3: CSS/HTML拡張
1. より高度なスタイリング
   - カラーコーディング（resource typeごと）
   - ツールチップ（descriptionの詳細表示）
2. インタラクティブ機能
   - テーブルのソート
   - フィルタリング
   - 折りたたみ/展開

## HTMLの利点を活かした将来的な拡張

### 1. セルの結合 (rowspan)
同じリソース内で説明が重複する場合に使用:
```html
<tr>
  <td>cors_rule[0].allowed_methods[0]</td>
  <td>GET</td>
  <td rowspan="2">No</td>
  <td rowspan="2">-</td>
  <td rowspan="2">Allowed HTTP methods</td>
</tr>
<tr>
  <td>cors_rule[0].allowed_methods[1]</td>
  <td>POST</td>
</tr>
```

### 2. JSONの整形表示
`assume_role_policy`などのJSON値を整形して表示:
```html
<td class="param-value">
  <details>
    <summary>JSON Policy (クリックして展開)</summary>
    <pre><code class="language-json">{
  "Version": "2012-10-17",
  "Statement": [...]
}</code></pre>
  </details>
</td>
```

### 3. リソース間リンク
参照関係をハイパーリンクで表示:
```html
<td class="param-value pending">
  <a href="IAM.html#aws_iam_policy.s3_access_policy">
    (pending) aws_iam_policy.s3_access_policy
  </a>
</td>
```

### 4. 目次の自動生成
ページ上部に目次を追加:
```html
<nav class="toc">
  <h2>目次</h2>
  <ul>
    <li><a href="#aws_iam_role.lambda_role">aws_iam_role.lambda_role</a></li>
    <li><a href="#aws_iam_policy.cloudwatch_logs_policy">aws_iam_policy.cloudwatch_logs_policy</a></li>
  </ul>
</nav>
```

## まとめ

この設計により：
1. **責務分離**: リソースクラスはデータ抽出、Viewクラスは表示に専念
2. **拡張性**: 新しいViewを追加するだけで異なる出力形式に対応可能
3. **柔軟性**: HTML/CSSで豊富な表現が可能
4. **保守性**: 既存のリソースクラスの構造を大きく変えずに移行可能

まずはPhase 2.5.1として基本的なHTML出力を実装し、その後段階的にHTML/CSSの利点を活かした機能を追加していく。
