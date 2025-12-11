# HTML出力への移行計画（簡易版）

## なぜHTML化するのか

- **セル結合が可能**: 同じ説明を持つ行をまとめられる
- **CSSでスタイリング**: 色分け、見やすいデザイン
- **リンク**: リソース間の参照関係をクリック可能に

## アーキテクチャの変更

### 現在（Markdown出力）
```
Resource → gen_table() → Markdown文字列 → .mdファイル
```

### 変更後（HTML出力）
```
Resource → gen_data() → データ(dict) → View → HTML文字列 → .htmlファイル
```

## 変更が必要な箇所

### 1. lib/aws_resources.py のリソースクラス

#### 変更前
```python
class AWS_IAM_ROLE(BaseResourceClass):
    sheet = "IAM.md"  # ファイル名を直接指定

    def gen_table(self):
        # Markdown文字列を返す
        return "| パラメータ | 値 |\n|---|---|\n..."
```

#### 変更後
```python
class AWS_IAM_ROLE(BaseResourceClass):
    view_class = "IAMView"  # Viewクラス名を指定

    def gen_data(self):
        # データ構造を返す（表示方法は指定しない）
        return {
            'resource_type': 'aws_iam_role',
            'resource_name': 'lambda_role',
            'resource_address': 'aws_iam_role.lambda_role',
            'attributes': [
                {
                    'name': 'assume_role_policy',
                    'value': '{...json...}',
                    'required': 'Yes',
                    'default': '-',
                    'description': 'このRoleを引き受け...',
                },
                # ...
            ]
        }
```

**ポイント**: リソースクラスは「データを用意するだけ」。表示方法は知らない。

### 2. lib/views.py を新規作成

```python
class BaseView:
    output_file = "default.html"

    def __init__(self, resources):
        self.resources = resources  # リソースインスタンスのリスト

    def render(self):
        # HTMLを生成して返す
        html = "<html>..."
        for resource in self.resources:
            data = resource.gen_data()
            html += self._render_table(data)
        return html

    def write_file(self, output_dir):
        # ファイルに書き込む
        html = self.render()
        # output_dir/IAM.html などに保存


class IAMView(BaseView):
    output_file = "IAM.html"


class S3View(BaseView):
    output_file = "S3.html"
```

**ポイント**: Viewクラスは「データを受け取ってHTMLに変換するだけ」。データの中身は知らない。

### 3. bin/tfp2ps.py のメインロジック

#### 変更前
```python
# リソースをsheetでグループ化
groups = {}  # "IAM.md" -> [resource1, resource2, ...]
for resource in resources:
    sheet = resource.sheet
    groups[sheet].append(resource)

# 各グループごとにMarkdownファイルを生成
for sheet, instances in groups.items():
    with open(sheet, 'w') as f:
        for instance in instances:
            f.write(instance.gen_table())
```

#### 変更後
```python
# リソースをview_classでグループ化
groups = {}  # "IAMView" -> [resource1, resource2, ...]
for resource in resources:
    view_class_name = resource.view_class
    groups[view_class_name].append(resource)

# 各グループごとにHTMLファイルを生成
from lib import views
for view_class_name, instances in groups.items():
    ViewClass = getattr(views, view_class_name)  # 例: IAMView
    view = ViewClass(instances)
    view.write_file(output_dir)
```

**ポイント**: メインロジックはほぼ同じ。`sheet`の代わりに`view_class`でグループ化するだけ。

## 役割分担

| クラス | 役割 | 知っていること | 知らないこと |
|--------|------|---------------|-------------|
| **Resource** | データ抽出 | plan.jsonの構造、属性の意味 | HTMLの作り方 |
| **View** | HTML生成 | HTMLの作り方、CSS | plan.jsonの構造 |
| **Main** | 全体調整 | ResourceとViewの繋ぎ方 | 個別の処理の詳細 |

## 実装手順

1. **lib/views.py を作成**
   - BaseView, IAMView, S3View を実装

2. **lib/aws_resources.py を修正**
   - BaseResourceClass に `gen_data()` メソッドを追加
   - `sheet` → `view_class` に変更

3. **bin/tfp2ps.py を修正**
   - sheet でのグループ化 → view_class でのグループ化に変更
   - Markdown出力 → View経由でHTML出力に変更

4. **テスト**
   - sample000 で実行して IAM.html, S3.html が生成されるか確認

## gen_data()の戻り値（データ構造）

```python
{
    'resource_type': str,        # 例: "aws_iam_role"
    'resource_name': str,        # 例: "lambda_role"
    'resource_address': str,     # 例: "aws_iam_role.lambda_role"
    'attributes': [
        {
            'name': str,         # 例: "assume_role_policy"
            'value': Any,        # 例: "{...json...}"
            'required': str,     # "Yes" / "No" / "-"
            'default': str,      # "(computed)" / "false" / "-"
            'description': str,  # 説明文
        },
        # ... 全属性分
    ]
}
```

このデータ構造さえ守れば、Viewは自由にHTML/CSS/JavaScriptを使って表示できる。

## 移行のメリット

1. **関心の分離**: データ処理と表示が完全に分離される
2. **拡張性**: 新しいView（例: JSONView, ExcelView）を簡単に追加可能
3. **保守性**: HTMLの変更はViewだけ、データ構造の変更はResourceだけを修正すればOK
