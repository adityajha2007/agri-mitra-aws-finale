"""CDK Stack: DynamoDB tables and S3 buckets."""

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
)
from constructs import Construct


class DataStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # --- DynamoDB Tables ---

        self.farmers_table = dynamodb.Table(
            self, "FarmersTable",
            table_name="agri-mitra-farmers",
            partition_key=dynamodb.Attribute(
                name="farmer_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.conversations_table = dynamodb.Table(
            self, "ConversationsTable",
            table_name="agri-mitra-conversations",
            partition_key=dynamodb.Attribute(
                name="farmer_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.mandi_prices_table = dynamodb.Table(
            self, "MandiPricesTable",
            table_name="agri-mitra-mandi-prices",
            partition_key=dynamodb.Attribute(
                name="crop_name", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="market_date", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.weather_table = dynamodb.Table(
            self, "WeatherTable",
            table_name="agri-mitra-weather-cache",
            partition_key=dynamodb.Attribute(
                name="district", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="date", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.news_table = dynamodb.Table(
            self, "NewsTable",
            table_name="agri-mitra-news",
            partition_key=dynamodb.Attribute(
                name="category", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.policy_docs_table = dynamodb.Table(
            self, "PolicyDocsTable",
            table_name="agri-mitra-policy-documents",
            partition_key=dynamodb.Attribute(
                name="doc_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- S3 Buckets ---

        self.policies_bucket = s3.Bucket(
            self, "PoliciesBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.uploads_bucket = s3.Bucket(
            self, "UploadsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(7)),
            ],
        )
