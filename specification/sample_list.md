# Terraform2Sheet 一覧表示仕様書

このドキュメントは、terraform2sheetツールでリソースを一覧形式で表示する際の出力形式を説明します。

**サンプルHTML**: [sample_list.html](./sample_list.html)

## 概要

IAM RoleやIAM Policyのように多数存在するリソースについては、一覧表示形式で出力します。この形式では、各リソースが1行で表示され、長い内容（JSONなど）は展開可能な形式で提供されます。

## 一覧表示の特徴

### 1. テーブル構造

一覧表示では、各リソースを1行で表現します。列の構成はリソースタイプによって異なりますが、基本的な構造は以下の通りです：

#### AWS IAM Role

| 列名 | 説明 | 幅 |
|------|------|-----|
| Role名 | リソース名 | 200px |
| 説明 | リソースの用途 | 150px |
| 信頼関係 | Assume Role Policy（展開可能） | 300px |
| アタッチされたポリシー | ポリシーARNのリスト | 300px |

#### AWS IAM Policy

| 列名 | 説明 | 幅 |
|------|------|-----|
| Policy名 | リソース名 | 250px |
| 説明 | ポリシーの用途 | 150px |
| ポリシードキュメント | ポリシーの内容（展開可能） | 400px |

## 実装のポイント

### 1. 列幅の固定

テーブルヘッダーに `style="width: XXpx;"` を指定することで、列幅を固定し、長いコンテンツによるレイアウト崩れを防止します。

```html
<th style="width: 200px;">Role名</th>
<th style="width: 150px;">説明</th>
<th style="width: 300px;">信頼関係</th>
```

### 2. 長いコンテンツの折りたたみ

JSONなどの長いコンテンツは `<details>` と `<summary>` タグを使用して折りたたみ可能にします。

```html
<details>
  <summary>信頼関係を表示</summary>
  <div class="expandable-content">{
  "Version": "2012-10-17",
  "Statement": [...]
}</div>
</details>
```

**CSSスタイル**:
- `max-height: 300px; overflow-y: auto;` でスクロール可能に
- モノスペースフォントで表示
- 背景色とボーダーで視覚的に区別

### 3. 複数項目のリスト表示

ポリシーARNなどの複数項目は、スタイル付きリストで表示します。

```html
<ul class="item-list">
  <li class="item-list-entry">
    <div class="item-value">arn:aws:iam::aws:policy/service-role/...</div>
  </li>
  <li class="item-list-entry pending">
    <div class="item-value">(pending) arn:aws:iam::123456789012:policy/...</div>
  </li>
</ul>
```

**特徴**:
- リストマーカーなし（`list-style: none`）
- 項目間に境界線（`border-bottom: 1px solid #e1e4e8`）
- `(pending)` 項目はオレンジ色で表示

### 4. ペンディング値の表現

apply前で確定していない値は、`(pending)` プレフィックスを付けて表示します。

```
(pending) arn:aws:iam::123456789012:policy/custom-lambda-policy
```

カスタマー管理ポリシーの場合も、ARN形式で表示します：
- AWSマネージドポリシー: `arn:aws:iam::aws:policy/...`
- カスタマー管理ポリシー: `arn:aws:iam::123456789012:policy/...`

### 5. CSSクラス

| クラス名 | 用途 | スタイル |
|---------|------|---------|
| `resource-name` | リソース名 | モノスペースフォント、青色、太字 |
| `expandable-content` | 展開可能なコンテンツ（JSON等） | モノスペースフォント、背景色、スクロール可能 |
| `item-list` | 項目リスト | リストマーカーなし |
| `item-list-entry` | リスト内の各項目 | 境界線あり |
| `item-value` | 項目の値 | モノスペースフォント、小さめ、グレー |
| `pending` | ペンディング値 | オレンジ色、イタリック |

### 6. ホバー効果

テーブル行にマウスオーバーすると、背景色が変わります。

```css
tbody tr:hover {
    background-color: #f6f8fa;
}
```

### 7. サマリーのスタイル

展開/折りたたみのサマリー部分は、クリック可能であることを示すスタイルが適用されます。

```css
summary {
    cursor: pointer;
    color: #0366d6;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 3px;
}
summary:hover {
    background-color: #f1f8ff;
}
```

## 使用例

### IAM Role 一覧

5つのIAM Roleが表示されます：
1. **lambda_execution_role**: Lambda関数の実行ロール
   - 信頼関係: lambda.amazonaws.com
   - ポリシー: AWSマネージド1つ + カスタマー管理1つ（pending）

2. **ec2_instance_role**: EC2インスタンス用のロール
   - 信頼関係: ec2.amazonaws.com
   - ポリシー: AWSマネージド2つ + カスタマー管理1つ（pending）

3. **ecs_task_execution_role**: ECSタスク実行用のロール
   - 信頼関係: ecs-tasks.amazonaws.com（条件付き）
   - ポリシー: AWSマネージド1つ + カスタマー管理2つ（pending）

4. **rds_monitoring_role**: RDS拡張モニタリング用
   - 信頼関係: monitoring.rds.amazonaws.com
   - ポリシー: AWSマネージド1つ

5. **codebuild_service_role**: CodeBuildプロジェクト用
   - 信頼関係: codebuild.amazonaws.com
   - ポリシー: カスタマー管理3つ（すべてpending）

### IAM Policy 一覧

3つのカスタマー管理ポリシーが表示されます：
1. **custom-lambda-policy**: Lambda用のカスタムポリシー
   - CloudWatch Logsへの書き込み権限
   - DynamoDBへのアクセス権限

2. **s3-access-policy**: S3バケットへのアクセス権限
   - オブジェクトの読み書き削除
   - バケットのリスト表示

3. **ecr-pull-policy**: ECRからのイメージプル権限
   - 認証トークンの取得
   - イメージのダウンロード

## まとめ

一覧表示形式は以下の特徴を持ちます：

1. **コンパクトな表示**: 1リソース1行で表示
2. **展開可能なコンテンツ**: 長いJSON等はクリックで展開
3. **視覚的な整理**: 固定幅、スタイル付きリスト、色分け
4. **ペンディング値の明示**: apply前の未確定値を明確に表示

これにより、多数のリソースを効率的にレビューできる形式を提供します。
