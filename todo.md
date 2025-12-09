# TODO List - terraform2sheet

## Phase 1: 基本機能実装 ✅ 完了

### 1. sample000の準備 ✅
- [x] `sample000/`ディレクトリを作成
- [x] `sample000/main.tf`を作成
  - IAM Role 1つ
  - S3 Bucket 1つ
  - シンプルな属性のみ
  - tagsにNameを含める
- [x] Terraformを実行
  ```bash
  cd sample000/
  terraform init
  terraform plan -out=tfplan
  terraform show -json tfplan > plan.json
  ```
- [x] `plan.json`が正しく生成されることを確認

### 2. lib/aws_resources.pyの基本構造 ✅
- [x] `lib/`ディレクトリを作成
- [x] `lib/aws_resources.py`を作成
- [x] `ALL_RESOURCES`リストを定義
  - `"aws_iam_role"`
  - `"aws_iam_policy"`
  - `"aws_s3_bucket"`
- [x] 基本クラス構造を定義
  - `sheet`属性
  - `generate_this_table`属性
  - `priority`属性（新規追加）
  - `custom_descriptions`属性(オプション)
  - `__init__(self, resource, schema=None, resource_registry=None)`
  - `gen_table(self)`メソッド（完全実装）

### 3. 属性フィルタリング機能 ✅
- [x] `_should_exclude_attribute(self, attr_name)`メソッドを実装
  - `id`, `arn`, `tags_all`を除外
  - `tags.*`を除外(`tags.Name`は残す)
  - computed-onlyの属性を除外
- [ ] ユニットテストを作成(オプション)

### 4. 値のフラット化機能 ✅
- [x] `_flatten_values(self, values, prefix="")`メソッドを実装
  - 辞書をドット記法で展開
  - 配列をインデックス記法で展開
  - ネストされた構造を再帰的に処理
  - フィルタリング機能と統合
- [ ] ユニットテストを作成(オプション)

### 5. スキーマ情報取得機能 ✅
- [x] `_get_attribute_info(self, attr_name)`メソッドを実装
  - ルート属性名を抽出
  - `attributes`から取得を試行
  - `block_types`から取得を試行
- [x] `_get_nested_schema(self, block_schema, path)`メソッドを実装(簡易版)
- [x] `_get_description(self, attr_name)`メソッドを実装
  - `custom_descriptions`を優先
  - `schema.json`の`description`をフォールバック

### 6. bin/tfp2ps.pyの作成 ✅
- [x] `bin/`ディレクトリを作成
- [x] `bin/tfp2ps.py`を作成
- [x] `parse_args()`関数を実装
  - `-o, --output`オプション
  - `-s, --schema`オプション
  - `file`引数(plan.json)
  - `--version`オプション
  - ファイル存在チェック
- [x] `main()`関数の骨格を作成
  - plan.json読み込み
  - schema.json読み込み(オプション)
  - `ALL_RESOURCES`のインポート

### 7. リソース処理ループ ✅
- [x] `main()`関数にリソース処理ループを実装
  - `planned_values.root_module.resources`から取得
  - リソースタイプが`ALL_RESOURCES`に含まれるかチェック
  - 未対応リソースは警告を出力してスキップ
  - 重複警告を避ける(`set`で管理)
- [x] リソースクラスの動的読み込み
  - リソースタイプからクラス名に変換
  - `getattr()`でクラスを取得
- [x] `resource_registry`を作成
  - リソースアドレスをキーにインスタンスを格納

### 8. AWS_IAM_ROLEクラスの実装 ✅
- [x] `AWS_IAM_ROLE`クラスを定義
  - `sheet = "IAM.md"`
  - `generate_this_table = True`
  - `priority = 100`（新規追加）
  - `__init__()`メソッド
- [x] `gen_table()`メソッドを実装
  - `_flatten_values()`を呼び出し
  - マークダウン表のヘッダーを生成
  - 各行を生成(パラメータ, 値, 必須, デフォルト, 説明)
  - マークダウン文字列を返す

### 9. AWS_S3_BUCKETクラスの実装 ✅
- [x] `AWS_S3_BUCKET`クラスを定義
  - `sheet = "S3.md"`
  - `generate_this_table = True`
  - `priority = 50`（新規追加）
  - `__init__()`メソッド
- [x] `gen_table()`メソッドを実装

### 10. マークダウン出力機能 ✅
- [x] `main()`関数にファイル出力処理を追加
  - `generate_this_table = True`のリソースをフィルタ
  - `sheet`属性でグループ化
  - `priority`でソート（新規追加）
  - 各グループごとにマークダウンファイルを生成
  - 出力ディレクトリの作成
- [x] マークダウンファイルの構造
  - `# リソースタイプ名`
  - `## リソース名`
  - 表

### 11. sample000でのテスト ✅
- [x] スクリプトを実行
  ```bash
  python3 bin/tfp2ps.py -s sample/schema.json -o sample000/output sample000/plan.json
  ```
- [x] `sample000/output/IAM.md`が生成されることを確認
- [x] `sample000/output/S3.md`が生成されることを確認
- [x] 表の内容が正しいことを確認
  - id, arnが除外されている
  - tags.*が除外されている(tags.Nameは残る)
  - 値が正しく展開されている
- [x] priority機能が正しく動作することを確認（追加テスト）
  - IAM.mdでIAM Role（priority=100）がIAM Policy（priority=90）より先に表示

### 12. 追加機能（Phase 1完了後）✅
- [x] `AWS_IAM_POLICY`クラスを追加
  - `sheet = "IAM.md"`
  - `generate_this_table = True`
  - `priority = 90`
- [x] priority機能を実装
  - `BaseResourceClass`に`priority`属性を追加
  - 出力時にpriorityでソート（降順）
  - plan.mdにpriority機能を文書化
- [x] priority機能のテスト
  - 複数のリソースタイプを含むTerraformコードを作成
  - IAM.mdにIAM RoleとIAM Policyの両方を出力
  - priority順に正しくソートされることを確認

### 13. custom_descriptions機能のテスト ✅
- [x] AWS_IAM_ROLEにcustom_descriptionsを追加
  - name, assume_role_policy, description等の日本語説明を定義
- [x] AWS_IAM_POLICYにcustom_descriptionsを追加
  - name, policy, description等の日本語説明を定義
- [x] AWS_S3_BUCKETにcustom_descriptionsを追加
  - bucket, force_destroy, timeouts等の日本語説明を定義
- [x] スクリプトを実行して出力を確認
  - custom_descriptionsの説明が優先的に表示されることを確認
  - schema.jsonよりも優先されることを確認
  - ネストされた属性(tags.Name)にも適用されることを確認

---

## Phase 2: ネストと関連性対応

### 14. sample001の準備 ✅
- [x] `sample001/`ディレクトリを作成
- [x] `sample001/main.tf`を作成
  - S3 Bucket with tags
  - S3 Bucket with CORS configuration (aws_s3_bucket_cors_configuration)
  - S3 Bucket with versioning (aws_s3_bucket_versioning)
  - IAM Role with timeouts
- [x] `plan.json`を生成
- [x] 新しいリソースタイプをALL_RESOURCESに追加
  - `aws_s3_bucket_cors_configuration`
  - `aws_s3_bucket_versioning`
- [x] 新しいリソースクラスを定義
  - AWS_S3_BUCKET_CORS_CONFIGURATION
  - AWS_S3_BUCKET_VERSIONING
  - custom_descriptionsも追加

### 15. sample001でのテスト ✅
- [x] スクリプトを実行
- [x] ネストされた値が正しく展開されることを確認
  - `cors_rule[0].allowed_methods[0]`, `cors_rule[0].allowed_methods[1]`など
  - `cors_rule[0].allowed_origins[0]`, `cors_rule[0].allowed_origins[1]`など
  - `cors_rule[1].allowed_methods[0]`など（複数のcors_rule）
  - `versioning_configuration[0].status`など
- [x] tags.Nameのみ残っていることを確認
- [x] 配列とオブジェクトの多重ネストが正しく展開されることを確認

### 16. ネストされたblock_typesの完全対応（将来の拡張）
- [ ] `_get_nested_schema()`メソッドを完全実装
  - パスをパースして再帰的にスキーマを辿る
  - `block_types.{name}.block.attributes.{key}`に対応
- [ ] ユニットテストを作成
- 注: 現在の簡易実装でも基本的なネスト展開は動作している

### 17. sample002の準備 ✅
- [x] `sample002/`ディレクトリを作成
- [x] `sample002/main.tf`を作成
  - IAM Role
  - IAM Policy (2つ: s3_access_policy, cloudwatch_logs_policy)
  - IAM Role Policy Attachment (3つ: マネージドポリシー + 2つのカスタムポリシー)
- [x] `plan.json`を生成

### 18. Association/Attachment系の統合処理 ✅
- [x] `AWS_IAM_ROLE_POLICY_ATTACHMENT`クラスを実装
  - `generate_this_table = False`
  - `__init__()`で親リソースを検索
  - 親リソースの`attached_policies`リストに追加
  - `instance.values.get("name")`で実際のRole名と比較するよう修正
- [x] `AWS_IAM_ROLE`クラスを更新
  - `attached_policies = []`を追加（既に実装済み）
  - `gen_table()`をオーバーライドして`attached_policies`を展開して表示
  - custom_descriptionsに`attached_policies`の説明を追加
- [x] ALL_RESOURCESに`aws_iam_role_policy_attachment`を追加

### 19. sample002でのテスト ✅
- [x] スクリプトを実行
- [x] IAM RoleにPolicy情報が統合されることを確認
  - `attached_policies[0]`にAWSLambdaBasicExecutionRoleのARNが表示
  - カスタムポリシーはARNがknown after applyのため表示されない（期待通りの動作）
- [x] Policy Attachmentの表が生成されないことを確認（generate_this_table = False）

### 20. plan.jsonのconfigurationセクション活用 ✅
- [x] `extract_configuration()`関数を実装
  - plan.jsonの`configuration.root_module.resources`からリソース設定を抽出
  - リソースアドレスから設定情報へのマッピング（config_map）を作成
- [x] ベースクラスとサブクラスに`config`パラメータを追加
  - `BaseResourceClass.__init__()`に`config`パラメータを追加
  - `AWS_IAM_ROLE.__init__()`を更新
  - `AWS_IAM_ROLE_POLICY_ATTACHMENT.__init__()`を更新
- [x] リソース参照の解決機能を実装
  - policy_arnがnullの場合、configurationから参照情報を取得
  - `expressions.policy_arn.references`から参照先リソースを抽出
  - `(pending) aws_iam_policy.xxx`形式で未確定のARNを表示
- [x] sample002で再テスト
  - 3つすべてのポリシーアタッチメントが表示されることを確認
  - `attached_policies[0]`: AWSマネージドポリシーのARN（具体的な値）
  - `attached_policies[1]`: `(pending) aws_iam_policy.cloudwatch_logs_policy`
  - `attached_policies[2]`: `(pending) aws_iam_policy.s3_access_policy`
- [x] 全サンプルで動作確認
  - sample000、sample001も正常に動作することを確認

---

## Phase 3: リソース拡張とモジュール対応

### 21. sample003の準備
- [ ] `sample003/`ディレクトリを作成
- [ ] `sample003/modules/vpc/`を作成
- [ ] `sample003/modules/ec2/`を作成
- [ ] `sample003/main.tf`を作成
- [ ] `plan.json`を生成

### 22. 主要リソースクラスの追加
- [ ] `AWS_VPC`クラス
- [ ] `AWS_SUBNET`クラス
- [ ] `AWS_SECURITY_GROUP`クラス
- [ ] `AWS_INSTANCE`クラス
- [ ] `AWS_LAMBDA_FUNCTION`クラス
- [ ] `AWS_RDS_INSTANCE`クラス
- [ ] `ALL_RESOURCES`リストに追加
- [ ] 各クラスにpriorityを設定

### 23. sample003でのテスト
- [ ] スクリプトを実行
- [ ] モジュールを使ったリソースが正しく処理されることを確認
- [ ] 各リソースタイプの表が正しく生成されることを確認

---

## Phase 4: 機能拡張

### 24. 出力フォーマットのカスタマイズ
- [ ] コマンドラインオプションの追加
- [ ] 列の表示/非表示の切り替え
- [ ] 表のスタイルのカスタマイズ

### 25. フィルタリング機能の拡張
- [ ] 特定リソースタイプのみ出力
- [ ] 特定のsheetのみ出力
- [ ] 正規表現によるフィルタリング

### 26. テストコード作成
- [ ] pytestのセットアップ
- [ ] `_should_exclude_attribute()`のテスト
- [ ] `_flatten_values()`のテスト
- [ ] `_get_attribute_info()`のテスト
- [ ] 統合テスト

---

## その他のタスク

### ドキュメント
- [ ] README.mdを作成
- [ ] 各sampleXXX/ディレクトリにREADME.mdを作成
- [ ] .gitignoreを作成

### リファクタリング
- [ ] 共通処理をユーティリティ関数に分離
- [ ] エラーハンドリングの改善
- [ ] ロギング機能の追加

### その他
- [ ] バージョン情報の管理
- [ ] ライセンスファイルの追加
- [ ] CI/CDの設定
