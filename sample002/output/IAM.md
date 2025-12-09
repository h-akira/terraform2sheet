# AWS_IAM_ROLE

## aws_iam_role.lambda_role

| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| assume_role_policy | {"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"}}],"Version":"2012-10-17"} | - | - | このRoleを引き受けることができるエンティティを定義するポリシー(JSON形式) |
| description | IAM role for Lambda with attached policies | - | - | IAM Roleの説明 |
| force_detach_policies | false | - | - | Role削除時にアタッチされているポリシーを強制的にデタッチするかどうか |
| max_session_duration | 3600 | - | - | セッションの最大継続時間(秒)。デフォルトは3600秒(1時間) |
| name | sample002-lambda-role | - | - | IAM Roleの名前 |
| path | / | - | - | IAM Roleのパス。デフォルトは/ |
| permissions_boundary | null | - | - | このRoleに設定するアクセス許可の境界のARN |
| tags.Name | sample002-lambda-role | - | - | リソースの名前を示すタグ |
| attached_policies[0] | arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole | - | - | このRoleにアタッチされているIAMポリシーのARN一覧 |
| attached_policies[1] | (pending) aws_iam_policy.cloudwatch_logs_policy | - | - | このRoleにアタッチされているIAMポリシーのARN一覧 |
| attached_policies[2] | (pending) aws_iam_policy.s3_access_policy | - | - | このRoleにアタッチされているIAMポリシーのARN一覧 |

## aws_iam_policy.cloudwatch_logs_policy

| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| description | Policy for CloudWatch Logs access | - | - | IAM Policyの説明 |
| name | sample002-cloudwatch-logs-policy | - | - | IAM Policyの名前 |
| path | / | - | - | IAM Policyのパス。デフォルトは/ |
| policy | {"Statement":[{"Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Effect":"Allow","Resource":"arn:aws:logs:*:*:*"}],"Version":"2012-10-17"} | - | - | ポリシードキュメント(JSON形式)。リソースへのアクセス権限を定義 |
| tags.Name | sample002-cloudwatch-logs-policy | - | - | リソースの名前を示すタグ |

## aws_iam_policy.s3_access_policy

| パラメータ | 値 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| description | Policy for S3 read/write access | - | - | IAM Policyの説明 |
| name | sample002-s3-access-policy | - | - | IAM Policyの名前 |
| path | /custom/ | - | - | IAM Policyのパス。デフォルトは/ |
| policy | {"Statement":[{"Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Effect":"Allow","Resource":"arn:aws:s3:::my-sample-bucket/*"},{"Action":["s3:ListBucket"],"Effect":"Allow","Resource":"arn:aws:s3:::my-sample-bucket"}],"Version":"2012-10-17"} | - | - | ポリシードキュメント(JSON形式)。リソースへのアクセス権限を定義 |
| tags.Name | sample002-s3-access-policy | - | - | リソースの名前を示すタグ |

