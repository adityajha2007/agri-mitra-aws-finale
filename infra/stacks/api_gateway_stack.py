"""CDK Stack: API Gateway with VPC Link to ALB."""

from aws_cdk import (
    Duration,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_logs as logs,
    aws_wafv2 as wafv2,
)
from constructs import Construct


class ApiGatewayStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        alb_listener,
        vpc,
        web_acl_arn: str = None,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # --- VPC Link ---
        vpc_link = apigwv2.VpcLink(
            self, "AgriMitraVpcLink",
            vpc=vpc,
            vpc_link_name="agri-mitra-vpc-link",
        )

        # --- HTTP API Gateway ---
        self.http_api = apigwv2.HttpApi(
            self, "AgriMitraAPI",
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

        # --- ALB Integration ---
        alb_integration = integrations.HttpAlbIntegration(
            "ALBIntegration",
            alb_listener,
            vpc_link=vpc_link,
        )

        # --- Routes ---
        # Chat endpoint
        self.http_api.add_routes(
            path="/api/chat",
            methods=[apigwv2.HttpMethod.POST],
            integration=alb_integration,
        )

        # Dashboard endpoints
        self.http_api.add_routes(
            path="/api/dashboard/{proxy+}",
            methods=[apigwv2.HttpMethod.GET],
            integration=alb_integration,
        )

        # Upload endpoint
        self.http_api.add_routes(
            path="/api/upload",
            methods=[apigwv2.HttpMethod.POST],
            integration=alb_integration,
        )

        # Health check
        self.http_api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=alb_integration,
        )

        # --- Access Logging ---
        log_group = logs.LogGroup(
            self, "ApiGatewayLogs",
            log_group_name="/aws/apigateway/agri-mitra",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        stage = self.http_api.default_stage.node.default_child
        stage.access_log_settings = apigwv2.CfnStage.AccessLogSettingsProperty(
            destination_arn=log_group.log_group_arn,
            format='$context.requestId $context.error.message $context.error.messageString',
        )

        # --- Associate WAF Web ACL (if provided) ---
        if web_acl_arn:
            # Get the stage ARN from the API
            stage_arn = f"arn:aws:apigateway:{Stack.of(self).region}::/apis/{self.http_api.http_api_id}/stages/{self.http_api.default_stage.stage_name}"
            
            wafv2.CfnWebACLAssociation(
                self, "WebACLAssociation",
                resource_arn=stage_arn,
                web_acl_arn=web_acl_arn,
            )

        # --- Outputs ---
        self.api_endpoint = self.http_api.url
