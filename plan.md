# terraform2sheet プロジェクト計画書

## 概要
`terraform plan`の実行結果(JSON形式)を解析し、全リソースと全パラメータをマークダウン形式の表に出力するツールを作成する。

## 目的
- Terraformで管理されるAWSリソースの構成を可視化
- リソースごとに整理された表形式のドキュメント生成
- リソース間の関連性(例: IAM RoleとPolicy Attachmentの関係)の可視化

## システム構成

```
terraform2sheet/
├── bin/
│   └── tfp2ps.py          # メインスクリプト
├── lib/
│   ├── aws_resources.py   # AWSリソースクラス定義
│   └── table_generator.py # 表生成ユーティリティ(検討中)
├── sample/
│   └── schema.json        # Terraform provider schema
├── sample000/             # テストケース1
│   ├── main.tf            # サンプルのTerraformコード
│   ├── plan.json          # terraform show -json の出力
│   └── output/            # 生成された出力ファイル
│       ├── IAM.md
│       ├── S3.md
│       └── ...
├── sample001/             # テストケース2
│   ├── main.tf
│   ├── modules/           # サンプルモジュール
│   ├── plan.json
│   └── output/
│       └── ...
└── sample002/             # テストケース3
    └── ...
```

## 機能要件

### 1. メインスクリプト (bin/tfp2ps.py)
- **入力**:
  - `plan.json`: `terraform plan -out=tfplan && terraform show -json tfplan > plan.json`で生成
  - `schema.json`: Terraform provider schemaファイル(オプション。指定されない場合は説明列を空にする)
- **出力**: リソースタイプごとに分類されたマークダウンファイル群
- **コマンドライン引数**:
  - `input-file`: 入力plan.jsonファイルパス(必須)
  - `-s, --schema`: schema.jsonファイルパス(オプション)
  - `-o, --output`: 出力ファイル/ディレクトリのプレフィックス(デフォルト: "output")
  - `--version`: バージョン情報表示

**処理フロー**:
1. `plan.json`を読み込み、全リソースを取得
2. `schema.json`を読み込み(指定されている場合)
3. `lib.aws_resources.ALL_RESOURCES`をインポート
4. 各リソースに対して:
   - リソースタイプが`ALL_RESOURCES`に含まれているかチェック
   - 含まれていない場合は警告を出力してスキップ
   - 含まれている場合は対応するクラスをインスタンス化
   - スキーマ情報も渡す
   - `resource_registry`に登録
5. Association/Attachment系リソースを処理して親リソースを更新
6. `generate_this_table = True`のリソースのみ、`sheet`属性でグループ化
7. 各グループ(sheet)ごとにマークダウンファイルを生成

**argparse実装例**:
```python
def parse_args():
  import argparse
  parser = argparse.ArgumentParser(description="""\
Convert Terraform plan JSON to markdown tables.
Reads plan.json and optionally schema.json to generate detailed resource documentation.
""", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
  parser.add_argument("-o", "--output", metavar="output-prefix", default="output",
                      help="output file prefix or directory")
  parser.add_argument("-s", "--schema", metavar="schema-file", default=None,
                      help="schema.json file for attribute descriptions")
  parser.add_argument("file", metavar="input-file", help="plan.json input file")
  options = parser.parse_args()
  if not os.path.isfile(options.file):
    raise Exception("The input file does not exist.")
  if options.schema and not os.path.isfile(options.schema):
    raise Exception("The schema file does not exist.")
  return options
```

**メイン処理の実装例**:
```python
def main():
  import json
  from lib.aws_resources import ALL_RESOURCES

  options = parse_args()

  # Load plan.json
  with open(options.file, 'r') as f:
    plan_data = json.load(f)

  # Load schema.json if provided
  resource_schemas = {}
  if options.schema:
    with open(options.schema, 'r') as f:
      schema_data = json.load(f)
      resource_schemas = schema_data.get('provider_schemas', {}).get(
        'registry.terraform.io/hashicorp/aws', {}).get('resource_schemas', {})

  # Extract resources from plan
  resources = plan_data.get('planned_values', {}).get('root_module', {}).get('resources', [])

  # Process resources
  resource_registry = {}
  skipped_types = set()

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

    # Instantiate resource class
    # ... (class instantiation logic)

  # Generate output files
  # ... (output generation logic)
```

### 2. リソースクラス設計 (lib/aws_resources.py)

#### 2.1 対応リソースの管理

ファイルの冒頭で対応するリソースタイプのリストを定義:

```python
# List of supported AWS resource types
ALL_RESOURCES = [
    "aws_iam_role",
    "aws_iam_policy",
    "aws_iam_role_policy_attachment",
    "aws_s3_bucket",
    "aws_vpc",
    "aws_subnet",
    "aws_security_group",
    "aws_instance",
    "aws_lambda_function",
    "aws_rds_instance",
    # Add more resource types as needed
]
```

**動作**:
- メインスクリプトでリソースを処理する際、リソースタイプが`ALL_RESOURCES`に含まれているかチェック
- 含まれていない場合は標準出力に警告メッセージを表示してスキップ
- 例: `Warning: Skipping unsupported resource type: aws_elasticache_cluster`

#### 2.2 基本クラス構造
各AWSリソースタイプに対応するクラスを定義:

```python
class BaseResourceClass:
    sheet = "出力先ファイル名.md"
    generate_this_table = True/False
    priority = 0  # Higher priority resources appear first in the output (default: 0)
    # Custom descriptions for attributes (optional, for future use)
    # If defined, these override schema.json descriptions
    custom_descriptions = {
        # "attribute_name": "日本語の説明",
    }

    def __init__(self, resource, schema=None):
        """
        Args:
            resource: Resource data from plan.json
            schema: Schema data from schema.json for this resource type
        """
        self.resource = resource
        self.schema = schema  # Schema information for this resource type
        self.name = resource.get("name")
        # Initialize resource-specific attributes
        pass

    def gen_table(self):
        """
        Generate markdown table with columns:
        - Parameter: attribute name (flattened, e.g., "tags.Environment", "cors_rule[0].allowed_methods[1]")
        - Value: actual value from plan.json (scalar values only after flattening)
        - Required: Yes/No/-
        - Default: default value or (computed) or -
        - Description: from schema.json or custom_descriptions

        The values are flattened recursively:
        - Objects: dot notation (tags.Environment)
        - Arrays: index notation (cors_rule[0])
        - Nested: combined (cors_rule[0].allowed_methods[1])

        Returns:
            str: Markdown formatted table
        """
        return "markdown_text"

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
        return block_schema.get('block', {}).get('attributes', {})

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
```

#### 2.2 リソースの分類

**表を生成するリソース (generate_this_table = True)**:
- `aws_s3_bucket` → S3.md
- `aws_iam_role` → IAM.md
- `aws_iam_policy` → IAM.md
- `aws_vpc` → Network.md
- `aws_subnet` → Network.md
- `aws_security_group` → Network.md
- `aws_instance` → EC2.md
- `aws_lambda_function` → Lambda.md
- `aws_rds_instance` → RDS.md
- など

**表を生成しないリソース (generate_this_table = False)**:
- `aws_iam_role_policy_attachment` → 親リソース(IAM Role)に情報を統合
- `aws_iam_policy_attachment` → 親リソース(IAM Role)に情報を統合
- `aws_route_table_association` → 親リソース(Subnet)に情報を統合
- など

#### 2.2.1 リソースの優先順位 (priority)

同じマークダウンファイル（同じ`sheet`値）に複数のリソースタイプが出力される場合、`priority`クラス変数によって表示順序を制御できる。

**ソートルール**:
1. **priority降順**: 高い値が先に表示される
2. **リソースタイプ名昇順**: 同じpriorityの場合はアルファベット順
3. **リソース名昇順**: 同じタイプの場合は名前順

**priority値の目安**:
- `100`: IAM Role など、最も重要なリソース
- `90`: IAM Policy など、重要度が高いリソース
- `50`: S3 Bucket など、中程度の重要度
- `0`: デフォルト値（優先順位なし）

**例**:
```python
class AWS_IAM_ROLE(BaseResourceClass):
    sheet = "IAM.md"
    priority = 100  # High priority

class AWS_IAM_POLICY(BaseResourceClass):
    sheet = "IAM.md"
    priority = 90   # Slightly lower priority

class AWS_S3_BUCKET(BaseResourceClass):
    sheet = "S3.md"
    priority = 50   # Medium priority
```

**出力例** (IAM.mdに両方のリソースタイプが含まれる場合):
1. すべてのIAM Role（priority=100）
   - アルファベット順: another_role → sample_role
2. すべてのIAM Policy（priority=90）
   - アルファベット順: policy_a → policy_b

#### 2.3 実装例

**IAM Roleクラス(日本語説明を追加した例)**:
```python
class AWS_IAM_ROLE:
    sheet = "IAM.md"
    generate_this_table = True
    priority = 100  # High priority for IAM resources

    # Optional: Custom Japanese descriptions
    custom_descriptions = {
        "name": "IAM Roleの名前",
        "assume_role_policy": "このRoleを引き受けることができるエンティティを定義するポリシー",
        "description": "IAM Roleの説明",
        "max_session_duration": "セッションの最大継続時間(秒)",
    }

    def __init__(self, resource, schema=None):
        self.resource = resource
        self.schema = schema
        self.name = resource.get("name")
        self.values = resource.get("values", {})
        self.attached_policies = []  # Will be populated by attachment resources

    def gen_table(self):
        # Generate table with all attributes from values
        # Including attached_policies if any
        pass
```

**IAM Policy Attachmentクラス(親リソースに情報を統合する例)**:
```python
class AWS_IAM_ROLE_POLICY_ATTACHMENT:
    generate_this_table = False

    def __init__(self, resource, schema=None, resource_registry=None):
        self.resource = resource
        self.schema = schema
        self.values = resource.get("values", {})

        # Find the parent IAM Role and add policy info
        role_name = self.values.get("role")
        policy_arn = self.values.get("policy_arn")

        if resource_registry and role_name:
            # Look up the IAM Role instance
            role_address = f"aws_iam_role.{role_name}"
            if role_address in resource_registry:
                role_instance = resource_registry[role_address]
                role_instance.attached_policies.append(policy_arn)
```

#### 2.4 リソース間の関連性処理
Association/Attachment系リソースは、以下の方法で親リソースに統合:
1. 全リソースを一度メモリ上に読み込む
2. `resource_registry`ディクショナリでリソースアドレスをキーに全インスタンスを管理
3. Association/Attachment系リソースを処理し、対応する親リソースのクラスインスタンスを検索・更新
4. 親リソースの`gen_table()`メソッドで関連情報も含めて出力

### 3. スキーマ情報の活用

#### 3.1 schema.jsonからの情報取得
`sample/schema.json`には各リソースタイプの詳細なスキーマ情報が含まれている:

```json
{
  "provider_schemas": {
    "registry.terraform.io/hashicorp/aws": {
      "resource_schemas": {
        "aws_s3_bucket": {
          "block": {
            "attributes": {
              "bucket": {
                "type": "string",
                "description": "Bucket name description",
                "optional": true,
                "computed": true
              },
              "force_destroy": {
                "type": "bool",
                "optional": true
              },
              "assume_role_policy": {
                "type": "string",
                "required": true
              }
            }
          }
        }
      }
    }
  }
}
```

**スキーマから取得可能な情報**:
- `type`: パラメータの型 (string, bool, number, list, map等)
- `description`: パラメータの説明(英語)
- `required`: 必須パラメータかどうか
- `optional`: オプションパラメータかどうか
- `computed`: Terraformが自動計算する値かどうか
- `deprecated`: 非推奨かどうか

**ネストされた属性のスキーマ取得**:

schema.jsonには`attributes`と`block_types`の2種類の構造がある:

1. **attributes**: 単純な属性(文字列、数値、単純なリストなど)
   ```json
   "attributes": {
     "bucket": {
       "type": "string",
       "description": "Bucket name",
       "optional": true
     }
   }
   ```

2. **block_types**: 複雑なネストされた構造(オブジェクト、構造化されたブロック)
   ```json
   "block_types": {
     "timeouts": {
       "nesting_mode": "single",
       "block": {
         "attributes": {
           "create": {
             "type": "string",
             "description": "Timeout for create operations",
             "optional": true
           }
         }
       }
     },
     "cors_rule": {
       "nesting_mode": "list",
       "block": {
         "attributes": {
           "allowed_methods": {
             "type": ["list", "string"],
             "description": "Allowed HTTP methods"
           }
         }
       }
     }
   }
   ```

**descriptionの解決順序**:
1. `tags.Environment` → `attributes.tags.description` (親の説明を使用)
2. `timeouts.create` → `block_types.timeouts.block.attributes.create.description`
3. `cors_rule[0].allowed_methods[0]` → `block_types.cors_rule.block.attributes.allowed_methods.description`

### 4. 出力形式

#### 4.1 マークダウン表の拡張フォーマット

**基本形式** (ネストされた値を展開して表示):
```markdown
# リソースタイプ名

## リソース名1
| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| bucket | my-bucket-name | No | (computed) | Bucket name description |
| force_destroy | false | No | false | Whether to force destroy |
| tags.Name | my-resource-name | No | - | Resource name tag |
| cors_rule[0].allowed_methods[0] | GET | No | - | Allowed HTTP methods |
| cors_rule[0].allowed_methods[1] | POST | No | - | Allowed HTTP methods |
| cors_rule[0].allowed_origins[0] | * | No | - | Allowed origins |
| attached_policies[0] | arn:aws:iam::xxx:policy/p1 | - | - | Attached IAM policies (from attachment resources) |
| attached_policies[1] | arn:aws:iam::xxx:policy/p2 | - | - | Attached IAM policies (from attachment resources) |

## リソース名2
...
```

**注**:
- `id`, `arn`は除外される(AWS側で自動生成)
- `tags.*`は原則除外されるが、`tags.Name`のみ残る
- `tags_all.*`は除外される(Terraformが自動生成)
- Terraform変数や参照は`plan.json`で実際の値に展開済み

**表示の特徴**:
- 配列やオブジェクトは再帰的に展開され、すべての値が個別の行として表示される
- パラメータ名は`hoge[0].fuga.ccc`のような形式でネストを表現
- 配列のインデックスは`[0]`, `[1]`, `[2]`...と表記
- オブジェクトのキーは`.`で連結

**列の詳細**:
1. **パラメータ**: 属性名(ネストされた構造は`hoge[0].fuga.ccc`形式で表現)
   - トップレベル: `bucket`
   - オブジェクト: `tags.Name`, `timeouts.create` (tagsは原則除外、Nameのみ残す)
   - 配列: `cors_rule[0]`, `security_groups[1]`
   - ネスト: `cors_rule[0].allowed_methods[1]`
2. **値**: `plan.json`から取得した実際の設定値(展開後の単一値)
   - 変数参照は実際の値に展開される
3. **必須**:
   - `Yes`: `required: true`の場合
   - `No`: `optional: true`の場合
   - `-`: `computed: true`のみの場合(出力専用属性)
   - ネストされた属性の場合は親の属性の情報を使用
4. **デフォルト**:
   - `(computed)`: Terraformが自動計算する値
   - `false`, `null`, `""`: 型に応じたデフォルト値
   - `-`: デフォルト値なし
5. **説明**:
   - トップレベル属性: `schema.json`の`attributes.{name}.description`
   - ネストされたオブジェクト: `block_types.{name}.block.attributes.{key}.description`
   - 配列要素: 親配列のdescriptionまたは配列要素のスキーマのdescription
   - カスタム説明がある場合はそちらを優先(将来版)

**除外するフィールド**:
- **tags**: 原則として除外。ただし`tags.Name`は残す
- **tags_all**: 除外(Terraformが自動生成)
- **id**: リソースID(AWS側で自動生成されるため除外)
- **arn**: ARN(AWS側で自動生成されるため除外)
- その他、`computed: true`のみで`required/optional`がないフィールドは除外を検討

#### 4.2 ファイル分割方針
- リソースクラスの`sheet`属性に基づいて出力先を決定
- 同じ`sheet`値を持つリソースは同じファイルに出力
- ファイル名の例: `IAM.md`, `S3.md`, `Network.md`, `EC2.md`

**リソースの表示順序**:
同じファイル内では、以下の順序でリソースをソートして表示:
1. `priority`降順（高い値が先）
2. リソースタイプ名昇順
3. リソース名昇順

実装例:
```python
# Sort instances by priority (higher priority first), then by type, then by name
sorted_instances = sorted(
    instances,
    key=lambda x: (-x.priority, x.type, x.name)
)
```

## 非機能要件

### 拡張性
- 新しいAWSリソースタイプの追加が容易
- 各リソースクラスを独立して定義可能
- `sheet`属性の変更のみで出力先を変更可能

### 保守性
- メインスクリプトのコード量を最小化
- リソース処理ロジックはクラスに集約
- 共通処理はユーティリティ関数として分離

### エラーハンドリング
- 入力ファイルの存在チェック
- JSON形式の妥当性チェック
- 未対応のリソースタイプへの対応:
  - `ALL_RESOURCES`に含まれていないリソースタイプは警告を出力してスキップ
  - 同じリソースタイプの警告は1回のみ表示(重複を避けるため`set`で管理)
  - 例: `Warning: Skipping unsupported resource type: aws_elasticache_cluster`

## テストケース構成

各`sampleXXX/`ディレクトリには以下のファイルが含まれる:

### ディレクトリ構成
```
sampleXXX/
├── main.tf           # Terraformコード(リソース定義)
├── modules/          # Terraformモジュール(オプション)
├── plan.json         # terraform show -json tfplan の出力
└── output/           # スクリプトが生成するマークダウンファイル
    ├── IAM.md
    ├── S3.md
    ├── Network.md
    └── ...
```

### plan.jsonの生成方法
```bash
cd sampleXXX/
terraform init
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
```

### テストケースの想定

#### sample000: 基本的な単一リソース
- **目的**: 最小限の機能テスト
- **内容**:
  - IAM Role 1つ
  - S3 Bucket 1つ
  - シンプルな属性のみ(ネストなし)

#### sample001: ネストされた属性
- **目的**: 値のフラット化機能テスト
- **内容**:
  - S3 Bucket with tags (オブジェクト)
  - S3 Bucket with cors_rule (配列 + ネストされたオブジェクト)
  - IAM Role with timeouts (ネストされたブロック)

#### sample002: リソース間の関連性
- **目的**: Association/Attachment系の統合テスト
- **内容**:
  - IAM Role
  - IAM Policy
  - IAM Role Policy Attachment (親リソースに統合される)

#### sample003: モジュール使用
- **目的**: Terraformモジュールを使った複雑な構成
- **内容**:
  - modules/vpc/ (VPC, Subnet, Security Groupを定義)
  - modules/ec2/ (EC2 Instanceを定義)
  - main.tfでモジュールを呼び出し

### テスト実行フロー
```bash
# スクリプト実行
cd /path/to/terraform2sheet
python3 bin/tfp2ps.py -s sample/schema.json -o sample000/output/result sample000/plan.json

# 出力確認
ls sample000/output/
cat sample000/output/IAM.md
cat sample000/output/S3.md
```

### 期待される出力の検証
各テストケースの`output/`ディレクトリには、以下を確認:
1. 正しいファイル名で出力されているか(`IAM.md`, `S3.md`など)
2. マークダウン表が正しく生成されているか
3. ネストされた値が正しく展開されているか
4. schema.jsonからのdescriptionが正しく取得されているか
5. リソース間の関連が正しく統合されているか

### 開発ワークフロー

#### 新機能開発時の流れ
1. **テストケース作成**: `sampleXXX/main.tf`を作成
2. **plan.json生成**:
   ```bash
   cd sampleXXX/
   terraform init
   terraform plan -out=tfplan
   terraform show -json tfplan > plan.json
   ```
3. **機能実装**: `lib/aws_resources.py`や`bin/tfp2ps.py`を修正
4. **テスト実行**:
   ```bash
   cd /path/to/terraform2sheet
   python3 bin/tfp2ps.py -s sample/schema.json -o sampleXXX/output/result sampleXXX/plan.json
   ```
5. **出力確認**: `sampleXXX/output/*.md`の内容を確認
6. **問題があれば3-5を繰り返し**

#### .gitignoreの設定
```
# Terraform files
**/.terraform/
**/tfplan
**/terraform.tfstate*

# Generated plan.json (保持する場合はコメントアウト)
# **/plan.json

# Generated output files (保持する場合はコメントアウト)
# **/output/*.md

# Python
__pycache__/
*.pyc
*.pyo
```

#### README作成
各`sampleXXX/`ディレクトリにREADME.mdを作成し、以下を記載:
- テストケースの目的
- 含まれるリソースの種類
- 期待される出力の例
- 注意点

## 実装の優先順位

### Phase 1: 基本機能実装
1. **sample000の準備**
   - `sample000/main.tf`を作成(IAM Role, S3 Bucketのみ)
   - tagsにNameを含める
   - `terraform plan`を実行して`plan.json`を生成
2. `lib/aws_resources.py`に`ALL_RESOURCES`リストを定義
   - 初期は`aws_iam_role`, `aws_s3_bucket`のみ
3. メインスクリプトの骨格作成
4. JSON読み込み処理(plan.json, schema.json)
5. 未対応リソースのスキップ処理実装
6. 属性フィルタリング機能実装(`_should_exclude_attribute`メソッド)
   - id, arn, tags_allを除外
   - tags.*を除外(tags.Nameのみ残す)
   - computed-onlyの属性を除外
7. 値のフラット化機能実装(`_flatten_values`メソッド)
   - フィルタリングと統合
8. ネストされたキーに対応したスキーマ情報取得(`_get_attribute_info`, `_get_nested_schema`)
9. 基本的なリソースクラス実装
   - `AWS_IAM_ROLE`クラス
   - `AWS_S3_BUCKET`クラス
10. マークダウン出力機能
11. **sample000でテスト実行**
    - `sample000/output/IAM.md`, `S3.md`が生成されることを確認
    - id, arn, tags(Nameを除く)が除外されていることを確認

### Phase 2: ネストと関連性対応
12. **sample001の準備**
    - `sample001/main.tf`を作成(tags, cors_ruleなどネストされた属性を含む)
    - `plan.json`を生成
13. ネストされたblock_typesの完全対応(再帰的なスキーマナビゲーション)
14. **sample001でテスト実行**
    - ネストされた値が正しく展開されることを確認
    - tagsは除外されているが、tags.Nameは残っていることを確認
15. **sample002の準備**
    - `sample002/main.tf`を作成(IAM Role + Policy + Attachment)
    - `plan.json`を生成
16. Association/Attachment系の統合処理実装
    - `AWS_IAM_ROLE_POLICY_ATTACHMENT`クラス
    - `resource_registry`による親リソース更新
17. **sample002でテスト実行**
    - IAM RoleにPolicy情報が統合されることを確認

### Phase 3: リソース拡張とモジュール対応
18. **sample003の準備**
    - `sample003/main.tf`とモジュールを作成
    - `plan.json`を生成
19. 主要なAWSリソースタイプのクラス追加(`ALL_RESOURCES`への追加も含む)
    - VPC, Subnet, Security Group
    - EC2 Instance
    - Lambda Function
    - RDS Instance
20. **sample003でテスト実行**
    - モジュールを使ったリソースが正しく処理されることを確認

### Phase 4: 機能拡張
21. 出力フォーマットのカスタマイズ機能
22. フィルタリング機能の拡張(コマンドラインオプションで特定リソースのみ出力)
23. テストコード作成(pytestなど)

## 技術的課題と解決方針

### 課題1: リソース間の参照解決
**問題**: Attachment系リソースが参照する親リソースの特定
**解決策**:
- リソースの`address`をキーとした`resource_registry`ディクショナリで全インスタンスを管理
- Attachment系リソースの処理時に親リソースのインスタンスを検索・更新
- `__init__`メソッドで`resource_registry`を引数として受け取る

### 課題2: 動的なリソースクラスの読み込み
**問題**: リソースタイプからクラス名への変換と対応チェック
**解決策**:
```python
from lib.aws_resources import ALL_RESOURCES

# First check if resource type is supported
resource_type = resource["type"]
if resource_type not in ALL_RESOURCES:
    print(f"Warning: Skipping unsupported resource type: {resource_type}")
    continue

# Convert resource type to class name (e.g., "aws_iam_role" -> "AWS_IAM_ROLE")
class_name = resource_type.upper()
resource_class = getattr(aws_resources, class_name, None)

if resource_class is None:
    # This should not happen if ALL_RESOURCES is properly maintained
    print(f"Error: Class {class_name} not found for supported type {resource_type}")
    continue
```

### 課題3: スキーマ情報とリソースインスタンスの紐付け
**問題**: 各リソースインスタンスに適切なスキーマ情報を渡す方法
**解決策**:
```python
# Load schema once
schemas = load_schema(schema_file)
resource_schemas = schemas['provider_schemas']['registry.terraform.io/hashicorp/aws']['resource_schemas']

# Get schema for specific resource type
resource_type = resource['type']  # e.g., 'aws_s3_bucket'
schema = resource_schemas.get(resource_type, {})

# Pass to resource instance
instance = ResourceClass(resource, schema=schema)
```

### 課題4: 複雑なネストされた値の展開
**問題**: `values`に含まれる配列やオブジェクトの表示方法
**解決策**: 配列・オブジェクトをフラット化して各要素を個別の行として表示

**展開ルール**:
- **単純な値** (string, bool, number, null): そのまま1行で表示
- **配列**: インデックス記法で展開
  - 例: `tags[0]`, `tags[1]`, `tags[2]`
- **オブジェクト**: ドット記法で展開
  - 例: `timeouts.create`, `timeouts.update`
- **ネストされた構造**: 組み合わせて展開
  - 例: `cors_rule[0].allowed_methods[0]`, `cors_rule[0].allowed_origins[1]`

**展開例**:
```python
# 入力データ
values = {
  "bucket": "my-bucket",
  "tags": {
    "Environment": "dev",
    "Project": "myapp"
  },
  "cors_rule": [
    {
      "allowed_methods": ["GET", "POST"],
      "allowed_origins": ["*"]
    }
  ]
}

# 展開後
# bucket → "my-bucket"
# tags.Environment → "dev"
# tags.Project → "myapp"
# cors_rule[0].allowed_methods[0] → "GET"
# cors_rule[0].allowed_methods[1] → "POST"
# cors_rule[0].allowed_origins[0] → "*"
```

**descriptionの対応**:
1. **トップレベル属性**: schema.jsonの`attributes`から直接取得
   - 例: `bucket` → schema.json内の`bucket`のdescription
2. **ネストされたオブジェクト**: schema.jsonの`block_types`から取得
   - 例: `timeouts.create` → `block_types.timeouts.block.attributes.create.description`
3. **配列要素**: 親の配列のdescriptionを使用
   - 例: `tags.Environment` → `tags`のdescription
   - 例: `cors_rule[0].allowed_methods[0]` → `cors_rule.allowed_methods`のdescription
4. **該当なし**: 空文字列

**実装方針**:
```python
def flatten_values(values, schema, prefix="", parent_desc=""):
    """
    Recursively flatten nested values.

    Returns:
        list of dict: [
            {
                'key': 'bucket',
                'value': 'my-bucket',
                'schema_info': {...},
                'description': '...'
            },
            {
                'key': 'tags.Environment',
                'value': 'dev',
                'schema_info': {...},
                'description': '...'
            },
            ...
        ]
    """
    result = []

    for key, value in values.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Recursively flatten object
            result.extend(flatten_values(value, schema, full_key))
        elif isinstance(value, list):
            # Flatten array elements
            for i, item in enumerate(value):
                array_key = f"{full_key}[{i}]"
                if isinstance(item, (dict, list)):
                    result.extend(flatten_values({f"[{i}]": item}, schema, full_key))
                else:
                    result.append({
                        'key': array_key,
                        'value': item,
                        'schema_info': get_schema_info(schema, full_key),
                        'description': get_nested_description(schema, full_key)
                    })
        else:
            # Simple value
            result.append({
                'key': full_key,
                'value': value,
                'schema_info': get_schema_info(schema, full_key),
                'description': get_nested_description(schema, full_key)
            })

    return result
```

### 課題5: 説明の言語切り替え
**問題**: schema.jsonの英語説明と、将来的に追加する日本語説明の両対応
**解決策**:
- リソースクラスに`custom_descriptions`属性(オプション)を定義
- `_get_description()`メソッドで優先順位を制御:
  1. `custom_descriptions`(日本語)が定義されていればそれを使用
  2. なければschema.jsonの`description`を使用
  3. どちらもなければ空文字列
- 将来的に環境変数やオプションで言語選択も可能に

### 課題6: 属性のフィルタリング
**問題**: id, arn, tagsなど、不要な属性を除外する必要がある
**解決策**:
- `_should_exclude_attribute()`メソッドで除外判定
- 除外ルール:
  1. `id`, `arn`, `tags_all`: 常に除外
  2. `tags.*`: `tags.Name`以外を除外
  3. computed-onlyの属性: required/optionalでない場合は除外
- `_flatten_values()`内で除外判定を実行

**実装例**:
```python
def _should_exclude_attribute(self, attr_name):
    # Always exclude
    if attr_name in ['id', 'arn', 'tags_all']:
        return True

    # Exclude tags.* except tags.Name
    if attr_name.startswith('tags.') and attr_name != 'tags.Name':
        return True

    # Exclude computed-only attributes
    attr_info = self._get_attribute_info(attr_name)
    if attr_info:
        is_computed = attr_info.get('computed', False)
        is_required = attr_info.get('required', False)
        is_optional = attr_info.get('optional', False)

        if is_computed and not is_required and not is_optional:
            return True

    return False
```

### 課題7: 変数と参照の展開
**問題**: Terraform変数や他リソースへの参照をどう扱うか
**解決策**:
- `terraform show -json tfplan`の出力では、すべての変数・参照が実際の値に展開済み
- スクリプト側で特別な処理は不要
- plan.jsonに含まれる値をそのまま使用すればOK

**例**:
```hcl
# main.tf
variable "bucket_name" {
  default = "my-bucket"
}

resource "aws_s3_bucket" "example" {
  bucket = var.bucket_name  # 変数参照
}
```

↓ `terraform show -json tfplan`

```json
{
  "values": {
    "bucket": "my-bucket"  // 変数が実際の値に展開済み
  }
}
```

## 想定される入力データ構造

```json
{
  "planned_values": {
    "root_module": {
      "resources": [
        {
          "address": "aws_s3_bucket.sample_bucket",
          "mode": "managed",
          "type": "aws_s3_bucket",
          "name": "sample_bucket",
          "values": {
            "bucket": "sample-bucket-name",
            ...
          }
        },
        ...
      ]
    }
  }
}
```

## 今後の検討事項

1. **日本語説明の充実**: 主要リソースの`custom_descriptions`を日本語で追加
2. **言語選択機能**: コマンドラインオプションで説明の言語(英語/日本語)を選択可能に
3. **複数環境対応**: dev/stg/prd環境の比較機能
4. **差分表示**: 変更前後の比較表示
5. **デフォルト値の充実**: schema.jsonに含まれないデフォルト値の補完
6. **他クラウドプロバイダー対応**: Azure、GCPへの拡張
7. **GUI版の開発**: Webインターフェースの提供
8. **自動実行**: CI/CDパイプラインへの組み込み

## まとめ

このツールにより、Terraformで管理されるインフラストラクチャの構成を、人間が読みやすいマークダウン形式のドキュメントとして自動生成できる。

**主な特徴**:
1. **詳細な属性情報**: パラメータの値だけでなく、必須/オプション、デフォルト値、説明も併記
2. **ネストされた値の完全展開**: 配列やオブジェクトを`hoge[0].fuga.ccc`形式で展開し、すべての値を可視化
3. **スマートフィルタリング**:
   - id, arn, tags_allなど自動生成される属性を除外
   - tagsは原則除外するが、tags.Nameのみ残す
   - computed-only属性を除外し、ユーザーが設定可能な属性のみ表示
4. **変数・参照の自動展開**: Terraform変数や他リソースへの参照は`plan.json`で実際の値に展開済み
5. **schema.json活用**: Terraform provider schemaから属性のメタ情報を自動取得
   - トップレベル属性は`attributes`から取得
   - ネストされた構造は`block_types`から取得
6. **日本語対応**: 将来的にカスタム説明を日本語で追加可能な設計
7. **リソース間関連**: Attachment/Association系リソースを親リソースに統合して表示
8. **優先順位制御**: `priority`によるリソース表示順序のカスタマイズが可能
9. **拡張性**: 新規リソースタイプやクラウドプロバイダーへの拡張が容易

これにより、インフラストラクチャの構成をチーム内で共有・レビューする際の理解を促進し、ドキュメント作成の手間を大幅に削減できる。
