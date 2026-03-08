#!/usr/bin/env python3
"""AWS CDK app entry point for Agri-Mitra infrastructure - Lambda Backend (No Docker)."""

import aws_cdk as cdk

from stacks.data_stack import DataStack
from stacks.security_stack import SecurityStack
from stacks.lambda_backend_stack import LambdaBackendStack
from stacks.lambda_stack import LambdaStack

app = cdk.App()

env = cdk.Environment(region="ap-south-1")

# Get optional parameters from context
alarm_email = app.node.try_get_context("alarm_email")

# --- Deploy Stacks ---

# 1. Data layer (DynamoDB + S3)
data = DataStack(app, "AgriMitraData", env=env)

# 2. Security layer (Secrets Manager + WAF)
security = SecurityStack(app, "AgriMitraSecurity", env=env)

# 3. Lambda Backend (replaces ECS Fargate - no Docker needed!)
backend = LambdaBackendStack(
    app,
    "AgriMitraBackend",
    data_stack=data,
    secrets={
        "openweather": security.openweather_secret,
        "news_api": security.news_api_secret,
        "data_gov": security.data_gov_secret,
        "twilio": security.twilio_secret,
    },
    env=env,
)

# 4. Lambda functions for scheduled tasks
lambdas = LambdaStack(
    app,
    "AgriMitraLambdas",
    data_stack=data,
    secrets={
        "openweather": security.openweather_secret,
        "news_api": security.news_api_secret,
        "data_gov": security.data_gov_secret,
    },
    env=env,
)

# --- Outputs ---
cdk.CfnOutput(
    backend,
    "ApiGatewayEndpoint",
    value=backend.api_endpoint,
    description="API Gateway endpoint URL",
)

cdk.CfnOutput(
    backend,
    "BackendFunctionName",
    value=backend.backend_function.function_name,
    description="Lambda backend function name",
)

cdk.CfnOutput(
    security,
    "SecretsManagerInstructions",
    value=f"Update secrets: aws secretsmanager put-secret-value --secret-id agri-mitra/openweather-api-key --secret-string '{{\"api_key\":\"YOUR_KEY\"}}' --region ap-south-1",
    description="Instructions to update API keys in Secrets Manager",
)

app.synth()
