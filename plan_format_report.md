# Terraform Plan JSON構造調査レポート

## 概要

本レポートは、Terraform planのJSON出力形式を分析し、パラメーターシート生成のための変数・参照展開方法について調査した結果をまとめる。

## 1. Terraform Plan JSON全体構造

### 1.1 トップレベル構成要素

Terraform planのJSON出力(`terraform show -json plan.json`)は以下の主要セクションで構成される:

```json
{
  "format_version": "1.2",
  "terraform_version": "1.14.0",
  "planned_values": { ... },
  "resource_changes": [ ... ],
  "configuration": { ... },
  "relevant_attributes": [ ... ],
  "variables": { ... },
  "timestamp": "...",
  "applyable": true,
  "complete": true,
  "errored": false
}
```

### 1.2 各セクションの役割

| セクション | 説明 | パラメーターシート生成での用途 |
|-----------|------|----------------------------|
| `format_version` | JSON形式のバージョン (現在は"1.2") | バージョン互換性確認 |
| `terraform_version` | Terraformのバージョン | ドキュメント記載用 |
| `planned_values` | 展開済みの計画値（参照解決済み） | **主要なデータソース** |
| `resource_changes` | リソースの変更内容 (`before`, `after`, `actions`) | 変更タイプの把握 |
| `configuration` | 元の設定（変数・参照を含む） | **参照関係の追跡** |
| `relevant_attributes` | 他のリソースから参照される属性のリスト | 依存関係の可視化 |
| `variables` | 入力変数とその値 | 変数展開 |

## 2. パラメーター値の取得方法

### 2.1 planned_values セクション

**最も重要なデータソース**。すべての変数・参照が展開済みの最終値を含む。

#### 構造例（sample002/plan.jsonより）

```json
{
  "planned_values": {
    "root_module": {
      "resources": [
        {
          "address": "aws_iam_role.lambda_role",
          "type": "aws_iam_role",
          "name": "lambda_role",
          "values": {
            "name": "sample002-lambda-role",
            "description": "IAM role for Lambda with attached policies",
            "assume_role_policy": "{\"Statement\":[...],...}",
            "tags": {
              "Environment": "development",
              "Name": "sample002-lambda-role"
            }
          }
        }
      ]
    }
  }
}
```

**特徴:**
- すべての値が展開済み（`constant_value`、変数参照、リソース属性参照すべて解決済み）
- パラメーターシート生成には主にこのセクションを使用
- 計算済み属性（`id`, `arn`など）は`after_unknown`に記載される

### 2.2 configuration セクション

元の設定を保持。参照関係を追跡するために使用。

#### 構造例

```json
{
  "configuration": {
    "root_module": {
      "resources": [
        {
          "address": "aws_iam_role_policy_attachment.lambda_cloudwatch_attach",
          "type": "aws_iam_role_policy_attachment",
          "expressions": {
            "policy_arn": {
              "references": [
                "aws_iam_policy.cloudwatch_logs_policy.arn",
                "aws_iam_policy.cloudwatch_logs_policy"
              ]
            },
            "role": {
              "references": [
                "aws_iam_role.lambda_role.name",
                "aws_iam_role.lambda_role"
              ]
            }
          }
        }
      ]
    }
  }
}
```

**expressionsの種類:**
1. **constant_value**: 定数値
   ```json
   "name": {
     "constant_value": "sample002-lambda-role"
   }
   ```

2. **references**: 他のリソース/変数への参照
   ```json
   "role": {
     "references": [
       "aws_iam_role.lambda_role.name",
       "aws_iam_role.lambda_role"
     ]
   }
   ```

3. **空オブジェクト `{}`**: `jsonencode()`やheredocなど複雑な式
   ```json
   "policy": {}
   ```

## 3. 変数と参照の展開方法

### 3.1 基本方針

**パラメーターシート生成では、`planned_values`セクションを主に使用する。**

理由:
- すべての変数・参照が既に展開済み
- 最終的にAWSに適用される値を表示できる
- 実装がシンプル

### 3.2 現在の実装分析（bin/tfp2ps.py）

現在のコードは既にこの方針を採用している:

```python
def extract_resources(plan_data):
    """Extract resources from plan.json"""
    # Get resources from planned_values.root_module
    root_module = plan_data.get('planned_values', {}).get('root_module', {})
    resources = root_module.get('resources', [])
    return resources
```

```python
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
```

**処理フロー:**
1. `planned_values`からリソースと展開済み値を取得
2. `configuration`から参照情報を取得（将来の拡張用）
3. 各リソースインスタンスに両方を渡す

### 3.3 参照の解決パターン

#### パターン1: 単純な参照（現在のサンプル）

```hcl
resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.cloudwatch_logs_policy.arn
}
```

**configuration:**
```json
"expressions": {
  "role": {
    "references": ["aws_iam_role.lambda_role.name", "aws_iam_role.lambda_role"]
  },
  "policy_arn": {
    "references": ["aws_iam_policy.cloudwatch_logs_policy.arn", ...]
  }
}
```

**planned_values (展開済み):**
```json
"values": {
  "role": "sample002-lambda-role",
  "policy_arn": "arn:aws:iam::123456789012:policy/sample002-cloudwatch-logs-policy"
}
```

→ `planned_values`を使えば、`"sample002-lambda-role"`という展開済みの値が得られる。

#### パターン2: 変数を使用する場合（サンプルには未使用）

```hcl
variable "environment" {
  default = "development"
}

resource "aws_iam_role" "example" {
  name = "role-${var.environment}"
  tags = {
    Environment = var.environment
  }
}
```

**variables セクション:**
```json
"variables": {
  "environment": {
    "value": "development"
  }
}
```

**configuration:**
```json
"expressions": {
  "name": {
    "references": ["var.environment"]
  }
}
```

**planned_values:**
```json
"values": {
  "name": "role-development"
}
```

→ やはり`planned_values`に展開済み値が入る。

#### パターン3: ローカル値を使用する場合

```hcl
locals {
  common_tags = {
    Project = "terraform2sheet"
    Environment = var.environment
  }
}

resource "aws_s3_bucket" "example" {
  tags = local.common_tags
}
```

**制限事項（重要）:**
- `configuration`セクションには`locals`の展開後の値は含まれない
- しかし、`planned_values`には最終的な展開済み値が含まれる

→ `planned_values`を使用することで、この問題も回避できる。

## 4. relevant_attributes セクション

他のリソースから参照される属性を列挙。

### 4.1 構造例（sample002/plan.json）

```json
"relevant_attributes": [
  {
    "resource": "aws_iam_policy.cloudwatch_logs_policy",
    "attribute": ["arn"]
  },
  {
    "resource": "aws_iam_role.lambda_role",
    "attribute": ["name"]
  },
  {
    "resource": "aws_iam_policy.s3_access_policy",
    "attribute": ["arn"]
  }
]
```

### 4.2 活用方法

1. **依存関係グラフの作成**: どのリソースがどの属性を参照しているか可視化
2. **パラメーターシートでの参照表示**:
   - `role = "sample002-lambda-role"` → `role = aws_iam_role.lambda_role.name (展開値: "sample002-lambda-role")`
3. **ドリフト検出**: 外部から変更された属性の影響範囲を特定

## 5. 実装における課題と解決策

### 5.1 課題1: 参照元の情報をどう表示するか

**現状:** パラメーターシートには展開済み値のみを表示
```
| role | sample002-lambda-role |
```

**改善案:** 参照元も併記
```
| role | sample002-lambda-role (← aws_iam_role.lambda_role.name) |
```

**実装方法:**
1. `configuration`の`expressions`から参照を取得
2. `references`配列の最初の要素を使用（例: `"aws_iam_role.lambda_role.name"`）
3. パラメーターシート生成時に両方を表示

```python
# 擬似コード
def get_value_with_reference(resource_address, attr_name, config_map):
    config = config_map.get(resource_address, {})
    expressions = config.get('expressions', {})
    expr = expressions.get(attr_name, {})

    value = resource['values'][attr_name]  # 展開済み値

    if 'references' in expr:
        ref = expr['references'][0]  # 参照元
        return f"{value} (← {ref})"
    elif 'constant_value' in expr:
        return value  # 定数
    else:
        return value  # 複雑な式（jsonencode等）
```

### 5.2 課題2: 複雑な式（jsonencode、heredoc等）

**現状:** `expressions`が空オブジェクト`{}`の場合
```json
"expressions": {
  "policy": {}
}
```

**問題点:**
- 元のHCL式を取得できない
- `planned_values`には展開済みJSON文字列が入る

**解決策:**
- `planned_values`の展開済み値を使用（現在の実装）
- 必要に応じて、JSON文字列を整形して表示

```python
# JSON文字列の整形例
policy_json = resource['values']['policy']
policy_dict = json.loads(policy_json)
formatted = json.dumps(policy_dict, indent=2)
```

### 5.3 課題3: 計算済み属性（after_unknown）

**問題:** `id`, `arn`などの計算済み属性は`planned_values`に含まれない

**after_unknown の例:**
```json
"after_unknown": {
  "arn": true,
  "id": true,
  "policy_id": true
}
```

**現在の実装:**
- `_should_exclude_attribute()`で`id`, `arn`を除外
- これは正しいアプローチ（ユーザー設定値ではないため）

### 5.4 課題4: ネスト構造の深いリソース

**例:** S3バケットのCORS設定（sample001/plan.json）

```json
"cors_rule": [
  {
    "allowed_headers": ["*"],
    "allowed_methods": ["GET", "POST", "PUT"],
    "allowed_origins": ["https://example.com", "https://test.example.com"],
    "expose_headers": ["ETag", "x-amz-request-id"],
    "max_age_seconds": 3600
  },
  {
    "allowed_methods": ["GET"],
    "allowed_origins": ["*"],
    "max_age_seconds": 3000
  }
]
```

**現在の実装:** `_flatten_values()`でフラット化
```
cors_rule[0].allowed_methods[0] = GET
cors_rule[0].allowed_methods[1] = POST
cors_rule[0].allowed_methods[2] = PUT
...
```

**改善の余地:**
- 配列・オブジェクトをテーブル形式で表示
- 見やすい階層表示

## 6. ベストプラクティスと推奨事項

### 6.1 基本方針

1. **`planned_values`を主要データソースとする**
   - すべての変数・参照が展開済み
   - 実際にAWSに適用される値を表示

2. **`configuration`を補助的に使用**
   - 参照元の情報を取得
   - パラメーターシートに`(← 参照元)`として併記

3. **`relevant_attributes`で依存関係を可視化**
   - 将来的にリソース間の依存グラフを生成

### 6.2 実装の優先順位

#### 優先度: 高
1. ✅ `planned_values`からの値取得（実装済み）
2. ✅ 計算済み属性の除外（実装済み）
3. ✅ ネスト構造のフラット化（実装済み）

#### 優先度: 中
4. ⚠️ **参照元の併記** （未実装）
   - `role = "sample002-lambda-role" (← aws_iam_role.lambda_role.name)`

5. ⚠️ **複雑な式の検出と表示** （部分実装）
   - `jsonencode()`や heredoc の識別
   - JSON文字列の整形表示

#### 優先度: 低
6. ❌ 依存関係グラフの生成
7. ❌ ネスト構造の階層表示

### 6.3 参照元併記の実装例

[lib/aws_resources.py](lib/aws_resources.py) の`BaseResourceClass`に追加:

```python
def _get_reference_info(self, attr_name):
    """
    Get reference information for an attribute from configuration.

    Args:
        attr_name: attribute name (e.g., "role", "policy_arn")

    Returns:
        str: reference path (e.g., "aws_iam_role.lambda_role.name") or None
    """
    if not self.config:
        return None

    expressions = self.config.get('expressions', {})
    expr = expressions.get(attr_name, {})

    if 'references' in expr and expr['references']:
        return expr['references'][0]

    return None

def _format_value_with_reference(self, attr_name, value):
    """
    Format a value with its reference source (if any).

    Args:
        attr_name: attribute name
        value: the expanded value

    Returns:
        str: formatted value with reference info
    """
    ref = self._get_reference_info(attr_name)

    if ref:
        return f"{value} (← {ref})"
    else:
        return str(value)
```

## 7. まとめ

### 7.1 主要な知見

1. **Terraform plan JSONの構造**
   - `planned_values`: すべて展開済み（パラメーターシートの主データソース）
   - `configuration`: 元の設定・参照情報（参照元表示に使用）
   - `relevant_attributes`: 依存関係の追跡

2. **変数・参照の展開**
   - Terraformが既にすべて展開済み
   - `planned_values`を使用すれば、手動での展開は不要
   - ローカル値も展開済み（`configuration`には含まれない制限があるが、`planned_values`で解決）

3. **現在の実装状況**
   - 基本機能は実装済み
   - 参照元の併記などの拡張機能が未実装

### 7.2 今後の開発方針

#### 短期（Phase 1）
- 参照元併記機能の実装
- JSON文字列の整形表示
- ドキュメントの充実

#### 中期（Phase 2）
- より複雑なリソースタイプのサポート拡大
- ネスト構造の見やすい表示
- 変数使用時のテストケース追加

#### 長期（Phase 3）
- 依存関係グラフの可視化
- インタラクティブなHTML出力
- カスタマイズ可能なテンプレート

## 参考資料

### 公式ドキュメント
- [JSON Output Format | Terraform | HashiCorp Developer](https://developer.hashicorp.com/terraform/internals/json-format) - Terraform plan JSON形式の公式仕様

### サンプルデータ
- [sample000/plan.json](sample000/plan.json) - IAM、S3の基本例
- [sample001/plan.json](sample001/plan.json) - S3 CORS、バージョニングの複雑な設定
- [sample002/plan.json](sample002/plan.json) - IAMロール、ポリシー、アタッチメントの参照関係

### 主要な発見
1. すべてのサンプルで`variables`セクションが空 → 変数を使用したテストケースの追加が必要
2. `configuration.expressions`が空`{}`の場合は`jsonencode()`などの複雑な式を表す
3. `relevant_attributes`で参照される属性を網羅的に把握可能

---

**最終更新:** 2025-12-11
**調査者:** Claude
**バージョン:** 1.0
