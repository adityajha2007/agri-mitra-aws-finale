"""CDK Stack: Lambda functions for scheduled data fetching."""

from aws_cdk import (
    Duration,
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
)
from constructs import Construct

from stacks.data_stack import DataStack


class LambdaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        data_stack: DataStack,
        secrets: dict = None,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # --- Fetch Mandi Prices Lambda (every 6 hours) ---

        mandi_env = {
            "DYNAMODB_TABLE": data_stack.mandi_prices_table.table_name,
        }
        if secrets and "data_gov" in secrets:
            mandi_env["DATA_GOV_SECRET_ARN"] = secrets["data_gov"].secret_arn

        self.fetch_prices = _lambda.Function(
            self, "FetchMandiPrices",
            function_name="agri-mitra-fetch-mandi-prices",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambdas/fetch_mandi_prices"),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment=mandi_env,
            tracing=_lambda.Tracing.ACTIVE,  # Enable X-Ray
        )
        data_stack.mandi_prices_table.grant_write_data(self.fetch_prices)
        if secrets and "data_gov" in secrets:
            secrets["data_gov"].grant_read(self.fetch_prices)

        events.Rule(
            self, "FetchPricesSchedule",
            schedule=events.Schedule.rate(Duration.hours(6)),
            targets=[targets.LambdaFunction(self.fetch_prices)],
        )

        # --- Fetch Weather Lambda (every 3 hours) ---

        weather_env = {
            "DYNAMODB_TABLE": data_stack.weather_table.table_name,
        }
        if secrets and "openweather" in secrets:
            weather_env["OPENWEATHER_SECRET_ARN"] = secrets["openweather"].secret_arn

        self.fetch_weather = _lambda.Function(
            self, "FetchWeather",
            function_name="agri-mitra-fetch-weather",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambdas/fetch_weather"),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment=weather_env,
            tracing=_lambda.Tracing.ACTIVE,
        )
        data_stack.weather_table.grant_write_data(self.fetch_weather)
        if secrets and "openweather" in secrets:
            secrets["openweather"].grant_read(self.fetch_weather)

        events.Rule(
            self, "FetchWeatherSchedule",
            schedule=events.Schedule.rate(Duration.hours(3)),
            targets=[targets.LambdaFunction(self.fetch_weather)],
        )

        # --- Fetch News Lambda (every 12 hours) ---

        news_env = {
            "DYNAMODB_TABLE": data_stack.news_table.table_name,
        }
        if secrets and "news_api" in secrets:
            news_env["NEWS_API_SECRET_ARN"] = secrets["news_api"].secret_arn

        self.fetch_news = _lambda.Function(
            self, "FetchNews",
            function_name="agri-mitra-fetch-news",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambdas/fetch_news"),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment=news_env,
            tracing=_lambda.Tracing.ACTIVE,
        )
        data_stack.news_table.grant_write_data(self.fetch_news)
        if secrets and "news_api" in secrets:
            secrets["news_api"].grant_read(self.fetch_news)

        events.Rule(
            self, "FetchNewsSchedule",
            schedule=events.Schedule.rate(Duration.hours(12)),
            targets=[targets.LambdaFunction(self.fetch_news)],
        )

        # --- Process Policy Docs Lambda (S3 trigger) ---

        self.process_docs = _lambda.Function(
            self, "ProcessPolicyDocs",
            function_name="agri-mitra-process-policy-docs",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambdas/process_policy_docs"),
            timeout=Duration.minutes(10),
            memory_size=512,
            environment={
                "DYNAMODB_TABLE": data_stack.policy_docs_table.table_name,
            },
            tracing=_lambda.Tracing.ACTIVE,
        )
        data_stack.policy_docs_table.grant_write_data(self.process_docs)
        data_stack.policies_bucket.grant_read(self.process_docs)

        # Grant Bedrock access for embedding generation
        self.process_docs.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # Note: S3 trigger must be added manually after deployment to avoid circular dependency
        # Run: aws s3api put-bucket-notification-configuration --bucket BUCKET_NAME --notification-configuration file://notification.json

        # Store lambda functions for monitoring
        self.lambda_functions = {
            "fetch_prices": self.fetch_prices,
            "fetch_weather": self.fetch_weather,
            "fetch_news": self.fetch_news,
            "process_docs": self.process_docs,
        }
