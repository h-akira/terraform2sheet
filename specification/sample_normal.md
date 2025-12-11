# Terraform2Sheet 出力仕様書（通常表示）

このドキュメントは、terraform2sheetツールがTerraform plan.jsonからHTML形式のテーブルを生成する際の出力形式を説明します。

**サンプルHTML**: [sample_normal.html](./sample_normal.html)

## 概要

terraform2sheetは、Terraform planの結果（plan.json）を読み込み、各リソースの属性を見やすいHTMLテーブル形式で出力します。

## 出力形式の特徴

### 1. テーブル構造

各リソースは以下の列を持つテーブルとして表現されます：

| 列名 | 説明 |
|------|------|
| パラメータ | 属性名（ネストレベルに応じて複数列に展開） |
| 値 | plan.jsonから取得した実際の値 |
| 必須 | Yes（必須）/ No（オプション）/ -（computed-only） |
| デフォルト | デフォルト値、または (computed) |
| 説明 | 属性の説明（schema.jsonまたはcustom_descriptionsから取得） |

### 2. セル結合のルール

#### ヘッダー行
- ネストレベルが複数ある場合、「パラメータ」ヘッダーは全てのパラメータ列を横方向に結合（colspan）

#### データ行
- **同じパラメータ名が連続する場合**: 縦方向に結合（rowspan）
- **配列の要素**: Index列で区別
- **単純な属性**: 全てのパラメータ列を横方向に結合（colspan）

## 例1: 単純な属性のみ

[サンプルHTML - 例1](./sample_normal.html#例1-単純な属性のみaws_example_resourcesimple)

### 入力データ（plan.json）

```json
{
  "address": "aws_example_resource.simple",
  "type": "aws_example_resource",
  "name": "simple",
  "values": {
    "aaa": "value_aaa",
    "bbb": "value_bbb",
    "ccc": 123
  }
}
```

### 出力結果

- 各属性が1行ずつ表示
- ネストがないため、パラメータ列は1つ（max_depth=1）
- Index列は使用されない

### テーブルイメージ

```
| パラメータ | 値          | 必須 | デフォルト | 説明 |
|-----------|-------------|------|-----------|------|
| aaa       | value_aaa   | Yes  | -         | ... |
| bbb       | value_bbb   | No   | default_bbb | ... |
| ccc       | 123         | No   | -         | ... |
```

## 例2: 配列属性

[サンプルHTML - 例2](./sample_normal.html#例2-配列属性aws_example_resourcearray)

### 入力データ（plan.json）

```json
{
  "address": "aws_example_resource.array",
  "type": "aws_example_resource",
  "name": "array",
  "values": {
    "name": "example_name",
    "tags": ["tag_value_1", "tag_value_2", "tag_value_3"]
  }
}
```

### フラット化後のデータ

terraform2sheetは配列を自動的にフラット化します：

```
name -> "example_name"
tags[0] -> "tag_value_1"
tags[1] -> "tag_value_2"
tags[2] -> "tag_value_3"
```

### 出力結果

- `name`: 単純な属性として1行
- `tags`: パラメータ名が縦結合（rowspan=3）、Index列に1, 2, 3

### テーブルイメージ

```
| パラメータ | Index | 値            | 必須 | デフォルト | 説明 |
|-----------|-------|---------------|------|-----------|------|
| name      | -     | example_name  | Yes  | -         | ... |
| tags      | 1     | tag_value_1   | No   | -         | ... |
|           | 2     | tag_value_2   | No   | -         | ... |
|           | 3     | tag_value_3   | No   | -         | ... |
```

## 例3: ネストされた配列

[サンプルHTML - 例3](./sample_normal.html#例3-ネストされた配列aws_example_resourcenested)

### 入力データ（plan.json）

```json
{
  "address": "aws_example_resource.nested",
  "type": "aws_example_resource",
  "name": "nested",
  "values": {
    "name": "nested_example",
    "rules": [
      {
        "name": "rule_1",
        "methods": ["GET", "POST", "PUT"],
        "priority": 100
      },
      {
        "name": "rule_2",
        "methods": ["DELETE"],
        "priority": 200
      }
    ],
    "enabled": true
  }
}
```

### フラット化後のデータ

```
name -> "nested_example"
rules[0].name -> "rule_1"
rules[0].methods[0] -> "GET"
rules[0].methods[1] -> "POST"
rules[0].methods[2] -> "PUT"
rules[0].priority -> 100
rules[1].name -> "rule_2"
rules[1].methods[0] -> "DELETE"
rules[1].priority -> 200
enabled -> true
```

### 出力結果

#### ネストレベル
- max_depth = 2（rules -> methods の2レベル）
- パラメータヘッダーは4列分（2レベル × 2列/レベル）を横結合

#### セル結合
1. **rules**: rowspan=8（rules[0]とrules[1]の全要素）
2. **rules[0]のIndex**: rowspan=5（rules[0]の5つの属性）
3. **methods（rules[0]内）**: rowspan=3（3つのメソッド）
4. **rules[1]のIndex**: rowspan=3（rules[1]の3つの属性）

### テーブルイメージ

```
| パラメータ | Index | パラメータ | Index | 値             | 必須 | デフォルト | 説明 |
|-----------|-------|-----------|-------|----------------|------|-----------|------|
| name (colspan=4)           |       |       | nested_example | Yes  | -         | ... |
| rules     | 1     | name      | -     | rule_1         | No   | -         | ... |
|           |       | methods   | 1     | GET            | No   | -         | ... |
|           |       |           | 2     | POST           | No   | -         | ... |
|           |       |           | 3     | PUT            | No   | -         | ... |
|           |       | priority  | -     | 100            | No   | -         | ... |
|           | 2     | name      | -     | rule_2         | No   | -         | ... |
|           |       | methods   | 1     | DELETE         | No   | -         | ... |
|           |       | priority  | -     | 200            | No   | -         | ... |
| enabled (colspan=4)        |       |       | true           | No   | false     | ... |
```

## 例4: 参照とペンディング値

[サンプルHTML - 例4](./sample_normal.html#例4-参照とペンディング値aws_example_resourcereferences)

### 入力データ（plan.json + configuration）

#### planned_values
```json
{
  "address": "aws_example_resource.references",
  "values": {
    "name": "example_with_refs",
    "computed_id": null,
    "attached_items": [
      "arn:aws:service::123456789012:resource/existing-item",
      null,
      null
    ]
  }
}
```

#### configuration
```json
{
  "address": "aws_example_resource.references",
  "expressions": {
    "attached_items": {
      "references": [
        ["aws_example_item.item_a.arn", "aws_example_item.item_a"],
        ["aws_example_item.item_b.arn", "aws_example_item.item_b"]
      ]
    }
  }
}
```

### 出力結果

- **computed_id**: nullで、(computed)として表示
- **attached_items[0]**: 具体的なARN値（既存リソース）
- **attached_items[1]**: `(pending) aws_example_item.item_a`（参照から解決）
- **attached_items[2]**: `(pending) aws_example_item.item_b`（参照から解決）

### ペンディング値の解決ルール

1. plan.jsonの`planned_values`でnullの場合
2. `configuration`セクションから`expressions.{attr_name}.references`を取得
3. 参照配列の最初の要素から`.arn`などを除去
4. `(pending) {resource_address}`形式で表示

### テーブルイメージ

```
| パラメータ       | Index | 値                                           | 必須 | デフォルト | 説明 |
|-----------------|-------|----------------------------------------------|------|-----------|------|
| name            | -     | example_with_refs                            | Yes  | -         | ... |
| computed_id     | -     | null                                         | -    | (computed)| ... |
| attached_items  | 1     | arn:aws:service::123456789012:resource/...   | -    | -         | ... |
|                 | 2     | (pending) aws_example_item.item_a            | -    | -         | ... |
|                 | 3     | (pending) aws_example_item.item_b            | -    | -         | ... |
```

## CSSクラス

出力HTMLでは以下のCSSクラスを使用しています：

| クラス名 | 用途 | スタイル |
|---------|------|---------|
| `param-name` | パラメータ名 | モノスペースフォント、青色 |
| `param-value` | 値 | モノスペースフォント |
| `index-cell` | Index列 | 水色背景、太字、中央揃え |
| `required-yes` | 必須（Yes） | 赤色、太字 |
| `required-no` | オプション（No） | グレー |
| `computed` | (computed)値 | 紫色、イタリック |
| `pending` | (pending)値 | オレンジ色、イタリック |

## 属性フィルタリング

以下の属性は自動的に除外されます：

- `id`: AWS側で自動生成されるリソースID
- `arn`: AWS側で自動生成されるARN
- `tags_all`: Terraformが自動生成するタグ
- `tags.*`: `tags.Name`を除くすべてのタグ属性
- computed-onlyの属性（`required`も`optional`もfalseで`computed`のみがtrue）

## gen_data()の戻り値

リソースクラスの`gen_data()`メソッドは以下の構造を返します：

```python
{
    'resource_type': 'aws_example_resource',
    'resource_name': 'nested',
    'resource_address': 'aws_example_resource.nested',
    'attributes': [
        {
            'name': 'name',              # フラット化された属性名
            'value': 'nested_example',   # 値
            'required': 'Yes',           # Yes / No / -
            'default': '-',              # デフォルト値 or (computed) or -
            'description': '説明文'       # schema.jsonまたはcustom_descriptionsから
        },
        {
            'name': 'rules[0].name',
            'value': 'rule_1',
            'required': 'No',
            'default': '-',
            'description': 'ルールの配列'
        },
        # ... 全属性分
    ]
}
```

## まとめ

terraform2sheetは以下の特徴を持つHTML出力を生成します：

1. **階層構造の可視化**: ネストされたデータを複数の列で表現
2. **効率的なセル結合**: 重複する情報を縦・横方向に結合
3. **配列の明示**: Index列で配列要素を明確に識別
4. **参照の解決**: apply前でもリソース参照を表示（pending表記）
5. **カラーコーディング**: CSSで重要度や状態を視覚的に表現

これにより、Terraformで管理されるインフラストラクチャの構成を、人間が読みやすく理解しやすい形式で文書化できます。
