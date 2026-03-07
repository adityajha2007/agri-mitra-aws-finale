# Agri-Mitra Infrastructure

AWS CDK infrastructure for the Agri-Mitra agricultural assistant application.

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Synthesize CloudFormation templates
cdk synth

# Deploy all stacks
cdk deploy --all

# Deploy with email alerts
cdk deploy --all --context alarm_email=your@email.com
```

## Stack Architecture

### 1. AgriMitraData
**Purpose**: Data layer with DynamoDB tables and S3 buckets

**Resources**:
- 6 DynamoDB tables (farmers, conversations, mandi_prices, weather, news, policy_docs)
- 2 S3 buckets (policies, uploads)

**Dependencies**: None

### 2. AgriMitraSecurity
**Purpose**: Security layer with secrets and WAF

**Resources**:
- 3 Secrets Manager secrets (OpenWeather, News API, Data.gov.in)
- WAF Web ACL with rate limiting and managed rules

**Dependencies**: None

### 3. AgriMitraBackend
**Purpose**: ECS Fargate service running FastAPI + LangGraph

**Resources**:
- VPC with 2 AZs
- ECS Cluster with Container Insights
- Fargate Service with auto-scaling (1-4 tasks)
- Application Load Balancer
- X-Ray sidecar container

**Dependencies**: AgriMitraData, AgriMitraSecurity

### 4. AgriMitraLambdas
**Purpose**: Scheduled Lambda functions for data fetching

**Resources**:
- 4 Lambda functions (fetch_prices, fetch_weather, fetch_news, process_docs)
- EventBridge rules for scheduling
- X-Ray tracing enabled

**Dependencies**: AgriMitraData, AgriMitraSecurity

### 5. AgriMitraApiGateway
**Purpose**: API Gateway with VPC Link to ALB

**Resources**:
- HTTP API Gateway
- VPC Link
- Route definitions
- Access logging
- WAF association

**Dependencies**: AgriMitraBackend, AgriMitraSecurity

### 6. AgriMitraMonitoring
**Purpose**: CloudWatch monitoring and alarms

**Resources**:
- CloudWatch Dashboard
- 8+ CloudWatch Alarms
- SNS topic for notifications
- Metric filters

**Dependencies**: AgriMitraBackend, AgriMitraLambdas, AgriMitraData

### 7. AgriMitraCdn (Optional)
**Purpose**: CloudFront distribution for global delivery

**Resources**:
- CloudFront distribution
- Cache policies
- Security headers
- Custom domain support

**Dependencies**: AgriMitraApiGateway

**Note**: Only deployed when `custom_domain` and `certificate_arn` context variables are provided.

## Directory Structure

```
infra/
├── app.py                      # CDK app entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── stacks/
    ├── __init__.py
    ├── data_stack.py           # DynamoDB + S3
    ├── security_stack.py       # Secrets + WAF
    ├── backend_stack.py        # ECS Fargate
    ├── lambda_stack.py         # Lambda functions
    ├── api_gateway_stack.py    # API Gateway
    ├── monitoring_stack.py     # CloudWatch
    └── cdn_stack.py            # CloudFront
```

## Configuration

### Context Variables

Set via `--context` flag or `cdk.json`:

```bash
# Email for alarm notifications
cdk deploy --all --context alarm_email=your@email.com

# Custom domain for CloudFront
cdk deploy --all \
  --context custom_domain=api.yourdomain.com \
  --context certificate_arn=arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT-ID
```

### Environment Variables

The stacks automatically configure environment variables for:
- DynamoDB table names
- S3 bucket names
- AWS region
- Secrets Manager ARNs

## Deployment

### Prerequisites

1. AWS CLI configured with credentials
2. AWS CDK CLI installed (`npm install -g aws-cdk`)
3. Python 3.12+ with virtual environment
4. Docker installed (for container builds)
5. Bootstrapped CDK environment

### Bootstrap (One-time)

```bash
cdk bootstrap aws://ACCOUNT-ID/ap-south-1
```

### Deploy

```bash
# Preview changes
cdk diff

# Deploy all stacks
cdk deploy --all

# Deploy specific stack
cdk deploy AgriMitraBackend

# Skip approval prompts (for CI/CD)
cdk deploy --all --require-approval never
```

### Destroy

```bash
# Destroy all stacks
cdk destroy --all

# Destroy specific stack
cdk destroy AgriMitraBackend
```

## Post-Deployment

### 1. Configure API Keys

```bash
aws secretsmanager put-secret-value \
  --secret-id agri-mitra/openweather-api-key \
  --secret-string '{"api_key":"YOUR_KEY"}' \
  --region ap-south-1
```

### 2. Configure S3 Event Notification

Due to circular dependency, this must be done manually:

```bash
# Get bucket name and Lambda ARN
export POLICIES_BUCKET=$(aws s3 ls | grep agrimitra.*policies | awk '{print $3}')
export LAMBDA_ARN=$(aws lambda get-function --function-name agri-mitra-process-policy-docs --region ap-south-1 --query 'Configuration.FunctionArn' --output text)

# Add Lambda permission
aws lambda add-permission \
  --function-name agri-mitra-process-policy-docs \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::$POLICIES_BUCKET \
  --region ap-south-1

# Configure notification (create notification.json first)
aws s3api put-bucket-notification-configuration \
  --bucket $POLICIES_BUCKET \
  --notification-configuration file://notification.json
```

### 3. Verify Deployment

```bash
# Check ECS service
aws ecs describe-services \
  --cluster agri-mitra-cluster \
  --services agri-mitra-service \
  --region ap-south-1

# Test health endpoint
curl https://YOUR-API-ID.execute-api.ap-south-1.amazonaws.com/health
```

## Monitoring

### CloudWatch Dashboard

View at: https://console.aws.amazon.com/cloudwatch/home?region=ap-south-1#dashboards:name=agri-mitra-monitoring

### Logs

```bash
# ECS logs
aws logs tail /ecs/agri-mitra-service --follow --region ap-south-1

# Lambda logs
aws logs tail /aws/lambda/agri-mitra-fetch-weather --follow --region ap-south-1

# API Gateway logs
aws logs tail /aws/apigateway/agri-mitra --follow --region ap-south-1
```

### X-Ray Traces

View at: https://console.aws.amazon.com/xray/home?region=ap-south-1#/service-map

## Cost Optimization

See `../COST_OPTIMIZATION.md` for detailed strategies.

### Quick Wins

1. Enable VPC Endpoints for S3, DynamoDB, Bedrock
2. Use Fargate Spot for non-critical tasks
3. Right-size ECS tasks based on metrics
4. Enable S3 Intelligent-Tiering
5. Reduce CloudWatch log retention

### Estimated Costs

- **Low traffic**: $30-45/month
- **Medium traffic**: $80-120/month
- **After optimization**: 60-78% reduction possible

## Troubleshooting

### CDK Synthesis Fails

```bash
# Check Python dependencies
pip list | grep aws-cdk

# Reinstall if needed
pip install -r requirements.txt
```

### Deployment Fails

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name AgriMitraBackend \
  --region ap-south-1

# Check CDK diff
cdk diff AgriMitraBackend
```

### ECS Task Not Starting

```bash
# Check task definition
aws ecs describe-task-definition \
  --task-definition agri-mitra-service \
  --region ap-south-1

# Check task failures
aws ecs describe-tasks \
  --cluster agri-mitra-cluster \
  --tasks TASK-ARN \
  --region ap-south-1
```

### Lambda Function Errors

```bash
# Check function configuration
aws lambda get-function \
  --function-name agri-mitra-fetch-weather \
  --region ap-south-1

# View recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/agri-mitra-fetch-weather \
  --filter-pattern "ERROR" \
  --region ap-south-1
```

## Security

### IAM Roles

All resources use least-privilege IAM roles:
- ECS Task Role: DynamoDB, S3, Bedrock, Secrets Manager, X-Ray
- Lambda Execution Roles: DynamoDB, S3, Bedrock, Secrets Manager, X-Ray

### Network Security

- ECS tasks run in private subnets
- ALB in public subnets
- Security groups restrict traffic
- VPC Link for API Gateway → ALB

### Data Protection

- S3 encryption at rest (SSE-S3)
- DynamoDB encryption at rest
- TLS in transit (ALB, API Gateway)
- Secrets Manager for API keys

## Updates

### Update Infrastructure

```bash
# Preview changes
cdk diff

# Apply updates
cdk deploy --all
```

### Update Dependencies

```bash
# Update CDK
pip install --upgrade aws-cdk-lib

# Update all dependencies
pip install --upgrade -r requirements.txt
```

### Rollback

```bash
# CDK doesn't support automatic rollback
# Redeploy previous version or use CloudFormation console
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths: ['infra/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install CDK
        run: npm install -g aws-cdk
      
      - name: Install dependencies
        run: |
          cd infra
          pip install -r requirements.txt
      
      - name: Deploy
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          cd infra
          cdk deploy --all --require-approval never
```

## Best Practices

1. ✅ Always run `cdk diff` before deploying
2. ✅ Use context variables for environment-specific configs
3. ✅ Tag all resources for cost tracking
4. ✅ Enable MFA for production accounts
5. ✅ Use separate AWS accounts for dev/staging/prod
6. ✅ Regularly review AWS Trusted Advisor
7. ✅ Set up AWS Budgets for cost control
8. ✅ Keep CDK and dependencies updated
9. ✅ Document custom configurations
10. ✅ Test disaster recovery procedures

## Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review X-Ray traces
3. Check CloudWatch Alarms
4. Review CDK documentation
5. Consult AWS Support

## License

See main repository LICENSE file.
