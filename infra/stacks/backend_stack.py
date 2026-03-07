"""CDK Stack: ECS Fargate service + API Gateway for the FastAPI backend."""

from aws_cdk import (
    Duration,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
)
from constructs import Construct

from stacks.data_stack import DataStack


class BackendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        data_stack: DataStack,
        secrets: dict = None,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # --- VPC ---

        self.vpc = ec2.Vpc(
            self, "AgriMitraVpc",
            max_azs=2,
            nat_gateways=1,
        )

        # --- ECS Cluster ---

        cluster = ecs.Cluster(
            self, "AgriMitraCluster",
            vpc=self.vpc,
            cluster_name="agri-mitra-cluster",
            container_insights=True,  # Enable Container Insights
        )

        # --- Fargate Service with ALB ---

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
            "AWS_XRAY_TRACING_NAME": "agri-mitra-backend",
            "AWS_XRAY_DAEMON_ADDRESS": "xray-daemon:2000",
        }

        # Add secrets if provided
        task_secrets = {}
        if secrets:
            if "openweather" in secrets:
                task_secrets["OPENWEATHER_API_KEY"] = ecs.Secret.from_secrets_manager(
                    secrets["openweather"], "api_key"
                )
            if "news_api" in secrets:
                task_secrets["NEWS_API_KEY"] = ecs.Secret.from_secrets_manager(
                    secrets["news_api"], "api_key"
                )
            if "data_gov" in secrets:
                task_secrets["DATA_GOV_API_KEY"] = ecs.Secret.from_secrets_manager(
                    secrets["data_gov"], "api_key"
                )

        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "AgriMitraService",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset("../backend"),
                container_port=8000,
                environment=environment_vars,
                secrets=task_secrets if task_secrets else None,
                enable_logging=True,
            ),
            public_load_balancer=True,
        )

        # Enable X-Ray tracing
        self.fargate_service.task_definition.add_container(
            "xray-daemon",
            image=ecs.ContainerImage.from_registry("amazon/aws-xray-daemon:latest"),
            cpu=32,
            memory_limit_mib=256,
            port_mappings=[
                ecs.PortMapping(container_port=2000, protocol=ecs.Protocol.UDP)
            ],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="xray"),
        )

        # Health check
        self.fargate_service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
            interval=Duration.seconds(30),
        )

        # Auto-scaling
        scaling = self.fargate_service.service.auto_scale_task_count(
            min_capacity=1, max_capacity=4
        )
        scaling.scale_on_cpu_utilization(
            "CpuScaling", target_utilization_percent=70
        )

        # --- IAM Permissions ---

        task_role = self.fargate_service.task_definition.task_role

        # DynamoDB access
        for table in [
            data_stack.farmers_table,
            data_stack.conversations_table,
            data_stack.mandi_prices_table,
            data_stack.weather_table,
            data_stack.news_table,
            data_stack.policy_docs_table,
        ]:
            table.grant_read_write_data(task_role)

        # S3 access
        data_stack.policies_bucket.grant_read(task_role)
        data_stack.uploads_bucket.grant_read_write(task_role)

        # Bedrock access
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # X-Ray access
        task_role.add_to_policy(
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
                secret.grant_read(task_role)
