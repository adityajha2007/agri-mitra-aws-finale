"""CDK Stack: Lambda-based backend (no Docker required) with API Gateway."""

from aws_cdk import (
    Duration,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

from stacks.data_stack import DataStack


class LambdaBackendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        data_stack: DataStack,
        secrets: dict = None,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # --- Environment Variables ---
        environment_vars = {
            "AGRI_MITRA_AWS_REGION": "ap-south-1",
            "AGRI_MITRA_DYNAMODB_TABLE_FARMERS": data_stack.farmers_table.table_name,
            "AGRI_MITRA_DYNAMODB_TABLE_CONVERSATIONS": data_stack.conversations_table.table_name,
            "AGRI_MITRA_DYNAMODB_TABLE_MANDI_PRICES": data_stack.mandi_prices_table.table_name,
            "AGRI_MITRA_DYNAMODB_TABLE_WEATHER": data_stack.weather_table.table_name,
            "AGRI_MITRA_DYNAMODB_TABLE_NEWS": data_stack.news_table.table_name,
            "AGRI_MITRA_DYNAMODB_TABLE_POLICY_DOCS": data_stack.policy_docs_table.table_name,
            "AGRI_MITRA_S3_BUCKET_POLICIES": data_stack.policies_bucket.bucket_name,
            "AGRI_MITRA_S3_BUCKET_UPLOADS": data_stack.uploads_bucket.bucket_name,
        }

        # Add secrets if provided
        if secrets:
            if "openweather" in secrets:
                environment_vars["OPENWEATHER_SECRET_ARN"] = secrets["openweather"].secret_arn
            if "data_gov" in secrets:
                environment_vars["DATA_GOV_SECRET_ARN"] = secrets["data_gov"].secret_arn
            if "twilio" in secrets:
                environment_vars["TWILIO_SECRET_ARN"] = secrets["twilio"].secret_arn

        # --- Lambda Function for Backend ---
        self.backend_function = _lambda.Function(
            self, "BackendFunction",
            function_name="agri-mitra-backend",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="simple_lambda_handler.handler",
            code=_lambda.Code.from_asset(
                "../backend",
                exclude=[".venv", ".venv/*", "tests", "tests/*", ".pytest_cache",
                         ".hypothesis", "__pycache__", "*.pyc", ".DS_Store",
                         "seed_data.py", "lambda_handler.py", "app/*"],
            ),
            timeout=Duration.seconds(60),
            memory_size=1536,
            environment=environment_vars,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # --- IAM Permissions ---

        # DynamoDB access
        for table in [
            data_stack.farmers_table,
            data_stack.conversations_table,
            data_stack.mandi_prices_table,
            data_stack.weather_table,
            data_stack.news_table,
            data_stack.policy_docs_table,
        ]:
            table.grant_read_write_data(self.backend_function)

        # S3 access
        data_stack.policies_bucket.grant_read(self.backend_function)
        data_stack.uploads_bucket.grant_read_write(self.backend_function)

        # Bedrock access
        self.backend_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:ApplyGuardrail"],
                resources=["*"],
            )
        )

        # X-Ray access
        self.backend_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

        # Secrets Manager access (if secrets provided)
        if secrets:
            for secret in secrets.values():
                secret.grant_read(self.backend_function)

        # --- HTTP API Gateway ---
        self.http_api = apigwv2.HttpApi(
            self, "BackendAPI",
            api_name="agri-mitra-api",
            description="API Gateway for Agri-Mitra agricultural assistant",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],  # Update with your frontend domain
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_headers=["*"],
                max_age=Duration.days(1),
            ),
        )

        # Lambda integration
        lambda_integration = integrations.HttpLambdaIntegration(
            "LambdaIntegration",
            self.backend_function,
        )

        # Add routes
        self.http_api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=lambda_integration,
        )

        # --- Access Logging ---
        log_group = logs.LogGroup(
            self, "ApiGatewayLogs",
            log_group_name="/aws/apigateway/agri-mitra",
            retention=logs.RetentionDays.ONE_WEEK,
        )

        stage = self.http_api.default_stage.node.default_child
        stage.access_log_settings = apigwv2.CfnStage.AccessLogSettingsProperty(
            destination_arn=log_group.log_group_arn,
            format='$context.requestId $context.error.message $context.error.messageString',
        )

        # --- Outputs ---
        self.api_endpoint = self.http_api.url
