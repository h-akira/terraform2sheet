# AWS_IAM_ROLE

## another_role

| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| assume_role_policy | {"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"}}],"Version":"2012-10-17"} | Yes | - | このRoleを引き受けることができるエンティティを定義するポリシー(JSON形式) |
| description | Another IAM role for testing priority | No | - | IAM Roleの説明 |
| force_detach_policies | false | No | - | Role削除時にアタッチされているポリシーを強制的にデタッチするかどうか |
| max_session_duration | 3600 | No | - | セッションの最大継続時間(秒)。デフォルトは3600秒(1時間) |
| name | another-lambda-role | No | (computed) | IAM Roleの名前 |
| path | / | No | - | IAM Roleのパス。デフォルトは/ |
| permissions_boundary | null | No | - | このRoleに設定するアクセス許可の境界のARN |
| tags.Name | another-role | No | - | リソースの名前を示すタグ |

## sample_role

| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| assume_role_policy | {"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"}}],"Version":"2012-10-17"} | Yes | - | このRoleを引き受けることができるエンティティを定義するポリシー(JSON形式) |
| description | Sample IAM role for Lambda function | No | - | IAM Roleの説明 |
| force_detach_policies | false | No | - | Role削除時にアタッチされているポリシーを強制的にデタッチするかどうか |
| max_session_duration | 3600 | No | - | セッションの最大継続時間(秒)。デフォルトは3600秒(1時間) |
| name | sample-lambda-role | No | (computed) | IAM Roleの名前 |
| path | / | No | - | IAM Roleのパス。デフォルトは/ |
| permissions_boundary | null | No | - | このRoleに設定するアクセス許可の境界のARN |
| tags.Name | sample-lambda-role | No | - | リソースの名前を示すタグ |

## sample_policy

| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| description | Sample IAM policy for testing priority | No | - | IAM Policyの説明 |
| name | sample-policy | No | (computed) | IAM Policyの名前 |
| path | / | No | - | IAM Policyのパス。デフォルトは/ |
| policy | {"Statement":[{"Action":["s3:GetObject","s3:PutObject"],"Effect":"Allow","Resource":"arn:aws:s3:::my-bucket/*"}],"Version":"2012-10-17"} | Yes | - | ポリシードキュメント(JSON形式)。リソースへのアクセス権限を定義 |
| tags.Name | sample-policy | No | - | リソースの名前を示すタグ |

