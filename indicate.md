# 指示書
`terraform plan`の実行結果を用い、terraformのコードから全リソース、全パラメータを抽出して表にまとめるためのスクリプトを作ろうと思う。
必要なファイルやClassについて下記に示す。
まずは要件をブラッシュアップしたい。plan.mdを作成せよ。

## bin/tfp2ps.py
`terraform plan`の実行結果のJsonファイルを読み、表をファイルに出力するスクリプト。後述のライブラリを用い、本ファイルに記述されるコード量は最小とすること。
### 要件
- argparseを用いること
```
def parse_args():
  import argparse
  parser = argparse.ArgumentParser(description="""\

""", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
  parser.add_argument("-o", "--output", metavar="output-file", default="output", help="output file")
  # parser.add_argument("-", "--", action="store_true", help="")
  parser.add_argument("file", metavar="input-file", help="input file")
  options = parser.parse_args()
  if not os.path.isfile(options.file): 
    raise Exception("The input file does not exist.") 
  return options
```

### lib/aws_resources.py
awsのリソースを処理するクラスを格納するファイル
### 要件
- 各リソースについて、下記のような形式でクラスを定義する
```
class AWS_IAM_ROLE:
  sheet = "IAM.md". # 最終的なアウトプットでは、この値に基づいてそれぞれ別のマークダウンファイルに出力する。出力先のマークダウンファイルを変えたいときはこのクラス変数を変えることになる。
  generate_this_table = True. # このリソースの表を作る場合はTrue。association/attachment系はFalse
  def __init__(self, resource):
    self.resource = resource
    self.name = resources["name"]. # terraform上での名前
    self.attached_policies = []. # 属性の特性に応じて
    return generate_this_table
  def gen_table(self)
    # table出力するためのコード
    # マークダウンのテキストを返す
    return マークダウンのテキスト

class AWS_IAM_POLICY_ATTACHMENT:
  generate_this_table = False
  def __init__(self, resource):
    # どうにかしてアタッチされるIAM RoleのAWS_IAM_ROLEクラスのself.attached_policesにIAM Policyの情報を入れる
```
なお、resourceは下記が一例。
```
{
   "address": "aws_s3_bucket.sample_bucket",
   "mode": "managed",
   "type": "aws_s3_bucket",
   "name": "sample_bucket",
   "provider_name": "registry.terraform.io/hashicorp/aws",
   "schema_version": 0,
   "values": {
    "bucket": "sample_bucket",
    "force_destroy": false,
    "tags": null,
    "timeouts": null
   },
   "sensitive_values": {
    "cors_rule": [],
    "grant": [],
    "lifecycle_rule": [],
    "logging": [],
    "object_lock_configuration": [],
    "replication_configuration": [],
    "server_side_encryption_configuration": [],
    "tags_all": {},
    "versioning": [],
    "website": []
   }
   }
```
