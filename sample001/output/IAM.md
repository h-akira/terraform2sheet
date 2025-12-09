# AWS_IAM_ROLE

## aws_iam_role.role_with_timeouts

| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| assume_role_policy | {"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"}}],"Version":"2012-10-17"} | - | - | このRoleを引き受けることができるエンティティを定義するポリシー(JSON形式) |
| description | IAM role to test nested timeouts block | - | - | IAM Roleの説明 |
| force_detach_policies | false | - | - | Role削除時にアタッチされているポリシーを強制的にデタッチするかどうか |
| max_session_duration | 3600 | - | - | セッションの最大継続時間(秒)。デフォルトは3600秒(1時間) |
| name | role-with-timeouts | - | - | IAM Roleの名前 |
| path | / | - | - | IAM Roleのパス。デフォルトは/ |
| permissions_boundary | null | - | - | このRoleに設定するアクセス許可の境界のARN |
| tags.Name | role-with-timeouts | - | - | リソースの名前を示すタグ |

