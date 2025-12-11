"""
AWS Resource Classes for terraform2sheet

This module defines classes for each AWS resource type.
Each class is responsible for:
- Parsing resource data from plan.json
- Filtering attributes based on exclusion rules
- Flattening nested values
- Generating markdown table output
"""

# List of supported AWS resource types
ALL_RESOURCES = [
    "aws_iam_role",
    "aws_iam_policy",
    "aws_iam_role_policy_attachment",
    "aws_s3_bucket",
    "aws_s3_bucket_cors_configuration",
    "aws_s3_bucket_versioning",
]


class BaseResourceClass:
    """Base class for AWS resources with common functionality"""

    view_class = "DefaultView"
    generate_this_table = True
    priority = 0  # Higher priority resources appear first in the output
    custom_descriptions = {}

    def __init__(self, resource, schema=None, resource_registry=None, config=None):
        """
        Initialize resource instance.

        Args:
            resource: Resource data from plan.json
            schema: Schema data from schema.json for this resource type
            resource_registry: Dictionary of all resource instances (for relationships)
            config: Configuration data with expressions/references from plan.json
        """
        self.resource = resource
        self.schema = schema
        self.resource_registry = resource_registry
        self.config = config
        self.address = resource.get("address", "")
        self.name = resource.get("name", "")
        self.type = resource.get("type", "")
        self.values = resource.get("values", {})

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
        return block_schema.get('block', {})

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

    def _format_value(self, value):
        """Format a value for display in markdown table"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, str):
            # Escape pipe characters for markdown tables
            return value.replace('|', '\\|')
        else:
            return str(value)

    def _get_required_status(self, attr_name):
        """Get required/optional status for an attribute"""
        attr_info = self._get_attribute_info(attr_name)
        if not attr_info:
            return "-"

        if attr_info.get('required', False):
            return "Yes"
        elif attr_info.get('optional', False):
            return "No"
        else:
            return "-"

    def _get_default_value(self, attr_name):
        """Get default value for an attribute"""
        attr_info = self._get_attribute_info(attr_name)
        if not attr_info:
            return "-"

        if attr_info.get('computed', False):
            return "(computed)"

        # Could add more sophisticated default value detection here
        return "-"

    def gen_data(self):
        """
        Generate structured data for rendering.

        Returns:
            dict: {
                'resource_type': str,  # e.g., "aws_iam_role"
                'resource_name': str,  # e.g., "lambda_role"
                'resource_address': str,  # e.g., "aws_iam_role.lambda_role"
                'attributes': [
                    {
                        'name': str,        # e.g., "assume_role_policy"
                        'value': Any,       # e.g., "{...json...}"
                        'required': str,    # "Yes" / "No" / "-"
                        'default': str,     # "(computed)" / "false" / "-"
                        'description': str, # 説明文
                    },
                    ...
                ]
            }
        """
        flattened = self._flatten_values(self.values)

        attributes = []
        for item in flattened:
            attr_name = item['key']
            attr_value = item['value']

            attributes.append({
                'name': attr_name,
                'value': attr_value,
                'required': self._get_required_status(attr_name),
                'default': self._get_default_value(attr_name),
                'description': self._get_description(attr_name),
            })

        return {
            'resource_type': self.type,
            'resource_name': self.name,
            'resource_address': self.address,
            'attributes': attributes,
        }

    def gen_table(self):
        """
        Generate markdown table with columns:
        - Parameter: attribute name (flattened)
        - Value: actual value from plan.json
        - Required: Yes/No/-
        - Default: default value or (computed) or -
        - Description: from schema.json or custom_descriptions

        Returns:
            str: Markdown formatted table
        """
        # Flatten all values
        flattened = self._flatten_values(self.values)

        if not flattened:
            return ""

        # Build markdown table
        lines = []
        lines.append("| パラメータ | 値 | 必須 | デフォルト | 説明 |")
        lines.append("|-----------|-----|------|-----------|------|")

        for item in flattened:
            key = item['key']
            value = self._format_value(item['value'])
            required = self._get_required_status(key)
            default = self._get_default_value(key)
            description = self._get_description(key)

            lines.append(f"| {key} | {value} | {required} | {default} | {description} |")

        return "\n".join(lines)


class AWS_IAM_ROLE(BaseResourceClass):
    """IAM Role resource"""

    view_class = "IAMView"
    generate_this_table = True
    priority = 100  # High priority for IAM resources

    # Custom Japanese descriptions
    custom_descriptions = {
        "name": "IAM Roleの名前",
        "assume_role_policy": "このRoleを引き受けることができるエンティティを定義するポリシー(JSON形式)",
        "description": "IAM Roleの説明",
        "max_session_duration": "セッションの最大継続時間(秒)。デフォルトは3600秒(1時間)",
        "force_detach_policies": "Role削除時にアタッチされているポリシーを強制的にデタッチするかどうか",
        "path": "IAM Roleのパス。デフォルトは/",
        "permissions_boundary": "このRoleに設定するアクセス許可の境界のARN",
        "tags.Name": "リソースの名前を示すタグ",
        "attached_policies": "このRoleにアタッチされているIAMポリシーのARN一覧",
    }

    def __init__(self, resource, schema=None, resource_registry=None, config=None):
        super().__init__(resource, schema, resource_registry, config)
        self.attached_policies = []  # Will be populated by attachment resources

    def gen_data(self):
        """
        Override to include attached_policies in attributes.
        """
        data = super().gen_data()

        # Add attached_policies to attributes
        for i, policy_arn in enumerate(self.attached_policies):
            data['attributes'].append({
                'name': f'attached_policies[{i}]',
                'value': policy_arn,
                'required': '-',
                'default': '-',
                'description': self.custom_descriptions.get('attached_policies', ''),
            })

        return data

    def gen_table(self):
        """
        Generate markdown table including attached policies.
        Overrides the base class method to add attached_policies.
        """
        # Flatten all values from the resource
        flattened = self._flatten_values(self.values)

        # Add attached policies to the flattened list
        if self.attached_policies:
            for i, policy_arn in enumerate(self.attached_policies):
                flattened.append({
                    'key': f'attached_policies[{i}]',
                    'value': policy_arn
                })

        if not flattened:
            return ""

        # Build markdown table
        lines = []
        lines.append("| パラメータ | 値 | 必須 | デフォルト | 説明 |")
        lines.append("|-----------|-----|------|-----------|------|")

        for item in flattened:
            key = item['key']
            value = self._format_value(item['value'])
            required = self._get_required_status(key)
            default = self._get_default_value(key)
            description = self._get_description(key)

            lines.append(f"| {key} | {value} | {required} | {default} | {description} |")

        return "\n".join(lines)


class AWS_IAM_POLICY(BaseResourceClass):
    """IAM Policy resource"""

    view_class = "IAMView"
    generate_this_table = True
    priority = 90  # Slightly lower priority than IAM Role

    # Custom Japanese descriptions
    custom_descriptions = {
        "name": "IAM Policyの名前",
        "policy": "ポリシードキュメント(JSON形式)。リソースへのアクセス権限を定義",
        "description": "IAM Policyの説明",
        "path": "IAM Policyのパス。デフォルトは/",
        "tags.Name": "リソースの名前を示すタグ",
    }


class AWS_S3_BUCKET(BaseResourceClass):
    """S3 Bucket resource"""

    view_class = "S3View"
    generate_this_table = True
    priority = 50  # Medium priority for storage resources

    # Custom Japanese descriptions
    custom_descriptions = {
        "bucket": "S3バケットの名前。グローバルで一意である必要があります",
        "force_destroy": "バケット削除時に中身が空でなくても強制的に削除するかどうか",
        "tags.Name": "リソースの名前を示すタグ",
        "timeouts": "リソース作成・更新・削除のタイムアウト設定",
    }


class AWS_S3_BUCKET_CORS_CONFIGURATION(BaseResourceClass):
    """S3 Bucket CORS Configuration resource"""

    view_class = "S3View"
    generate_this_table = True
    priority = 45  # Medium priority, slightly lower than bucket

    # Custom Japanese descriptions
    custom_descriptions = {
        "bucket": "CORS設定を適用するS3バケットのID",
        "cors_rule": "CORSルールの配列。各ルールは許可されるオリジン、メソッド等を定義",
        "cors_rule.allowed_headers": "許可されるHTTPヘッダーのリスト。*はすべてのヘッダーを許可",
        "cors_rule.allowed_methods": "許可されるHTTPメソッド(GET, POST, PUT, DELETE等)",
        "cors_rule.allowed_origins": "許可されるオリジン(ドメイン)のリスト。*はすべてのオリジンを許可",
        "cors_rule.expose_headers": "クライアントに公開されるレスポンスヘッダーのリスト",
        "cors_rule.max_age_seconds": "ブラウザがプリフライトリクエストの結果をキャッシュする秒数",
    }


class AWS_S3_BUCKET_VERSIONING(BaseResourceClass):
    """S3 Bucket Versioning resource"""

    view_class = "S3View"
    generate_this_table = True
    priority = 45  # Medium priority, slightly lower than bucket

    # Custom Japanese descriptions
    custom_descriptions = {
        "bucket": "バージョニング設定を適用するS3バケットのID",
        "versioning_configuration": "バージョニングの設定",
        "versioning_configuration.status": "バージョニングのステータス(Enabled/Suspended/Disabled)",
        "versioning_configuration.mfa_delete": "MFA削除の有効化ステータス",
    }


class AWS_IAM_ROLE_POLICY_ATTACHMENT(BaseResourceClass):
    """IAM Role Policy Attachment resource (does not generate its own table)"""

    generate_this_table = False  # This resource is integrated into the parent IAM Role

    def __init__(self, resource, schema=None, resource_registry=None, config=None):
        super().__init__(resource, schema, resource_registry)

        # Extract role and policy information
        role_name = self.values.get("role")
        policy_arn = self.values.get("policy_arn")

        # If policy_arn is None, try to get it from configuration references
        if policy_arn is None and config:
            expressions = config.get('expressions', {})
            policy_arn_expr = expressions.get('policy_arn', {})
            references = policy_arn_expr.get('references', [])

            # references format: ["aws_iam_policy.xxx.arn", "aws_iam_policy.xxx"]
            if references:
                # Use the first reference (the full one with .arn)
                ref = references[0]
                # Create a pending marker with the resource reference
                policy_arn = f"(pending) {ref.replace('.arn', '')}"

        # Find the parent IAM Role and add policy info
        if resource_registry and role_name and policy_arn:
            # Look up the IAM Role instance by the actual role name (not Terraform resource name)
            for address, instance in resource_registry.items():
                if instance.type == "aws_iam_role":
                    # Compare with the actual IAM role name from values
                    instance_role_name = instance.values.get("name")
                    if instance_role_name == role_name:
                        # Add the policy ARN to the role's attached_policies list
                        if hasattr(instance, 'attached_policies'):
                            instance.attached_policies.append(policy_arn)
                        break
