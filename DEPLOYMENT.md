# Deployment Guide: Agri-Mitra on AWS

This document describes how the entire Agri-Mitra application is deployed on AWS.

## Architecture Overview

| Component | AWS Service | Region |
|---|---|---|
| Frontend | AWS Amplify | ap-south-1 |
| Backend API | Lambda + API Gateway (HTTP API) | ap-south-1 |
| Database | DynamoDB (6 tables) | ap-south-1 |
| File Storage | S3 (2 buckets) | ap-south-1 |
| AI Model | Amazon Bedrock (Nova Lite) | ap-south-1 |
| Embeddings | Amazon Bedrock (Titan Embed v2) | ap-south-1 |
| Secrets | AWS Secrets Manager | ap-south-1 |
| Data Fetchers | Lambda (4 scheduled functions) | ap-south-1 |
| Infrastructure | AWS CDK (Python) | — |

## Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js 18+ and npm
- Python 3.12+ and pip
- AWS CDK CLI (`npm install -g aws-cdk`)

## 1. Infrastructure Deployment (CDK)

The infrastructure is defined in `infra/` using AWS CDK (Python).

```bash
cd infra
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT_ID/ap-south-1

# Deploy all stacks
cdk deploy --all --require-approval never
```

This creates 4 stacks:
- **AgriMitraData** — DynamoDB tables + S3 buckets
- **AgriMitraSecurity** — Secrets Manager entries for API keys
- **AgriMitraBackend** — Lambda function + API Gateway HTTP API
- **AgriMitraLambdas** — Scheduled Lambda data fetchers

After deployment, note the API Gateway endpoint URL from the output.

## 2. Configure Secrets

Store external API keys in Secrets Manager:

```bash
aws secretsmanager put-secret-value \
  --secret-id agri-mitra/openweather-api-key \
  --secret-string '{"api_key":"YOUR_OPENWEATHER_KEY"}' \
  --region ap-south-1

aws secretsmanager put-secret-value \
  --secret-id agri-mitra/news-api-key \
  --secret-string '{"api_key":"YOUR_NEWS_API_KEY"}' \
  --region ap-south-1

aws secretsmanager put-secret-value \
  --secret-id agri-mitra/data-gov-api-key \
  --secret-string '{"api_key":"YOUR_DATA_GOV_KEY"}' \
  --region ap-south-1
```

## 3. Enable Bedrock Model Access

Go to the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/) in ap-south-1:

1. Navigate to **Model access** in the left sidebar
2. Request access for:
   - **Amazon Nova Lite** (used for chat reasoning and tool use)
   - **Amazon Titan Text Embeddings V2** (used for policy document RAG)

Model access is typically granted instantly for Amazon's own models.

## 4. Seed Initial Data

Populate DynamoDB with sample data:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python seed_data.py
```

This seeds: 60 mandi prices, 15 weather records, 20 news items, 8 policy documents (with embeddings), and 3 sample farmer profiles.

## 5. Backend Lambda Deployment

The Lambda is deployed by CDK (step 1), but for code-only updates:

```bash
cd backend
zip -r /tmp/lambda-backend.zip simple_lambda_handler.py

aws lambda update-function-code \
  --function-name agri-mitra-backend \
  --zip-file fileb:///tmp/lambda-backend.zip \
  --region ap-south-1
```

**Lambda configuration:**
- Runtime: Python 3.12
- Handler: `simple_lambda_handler.handler`
- Memory: 1536 MB
- Timeout: 60 seconds
- Tracing: X-Ray active

## 6. Frontend Deployment (Amplify)

### Option A: Manual Deployment

```bash
cd frontend

# Update API endpoint in src/services/api.ts
# Set BASE_URL to your API Gateway endpoint

npm install
npm run build

# Zip the build output
cd dist && zip -r /tmp/frontend.zip . && cd ..

# Deploy to Amplify
aws amplify create-deployment \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --region ap-south-1

# Upload to the presigned URL from the output
curl -T /tmp/frontend.zip "PRESIGNED_URL_FROM_OUTPUT"

# Start deployment
aws amplify start-deployment \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --job-id JOB_ID_FROM_OUTPUT \
  --region ap-south-1
```

### Option B: GitHub-Connected Deployment

1. Create an Amplify app in the AWS Console connected to your GitHub repo
2. Amplify uses `amplify.yml` for build settings
3. Every push to `main` triggers automatic build and deploy

### Amplify App Setup (First Time)

```bash
aws amplify create-app \
  --name agri-mitra-frontend \
  --region ap-south-1

aws amplify create-branch \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --region ap-south-1
```

## 7. Update Frontend API Endpoint

After CDK deployment, update the API base URL in the frontend:

```typescript
// frontend/src/services/api.ts
const BASE_URL = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/api";
```

## Current Deployed URLs

| Resource | URL |
|---|---|
| Frontend | https://main.d1v8d9313puioo.amplifyapp.com |
| API Gateway | https://2j6vbtud08.execute-api.ap-south-1.amazonaws.com/api |
| Health Check | https://2j6vbtud08.execute-api.ap-south-1.amazonaws.com/health |

## Cost Considerations

- **Lambda:** Pay per invocation. 1536 MB × 60s max = ~$0.0015 per chat request
- **DynamoDB:** Pay per request billing — minimal cost for low traffic
- **Bedrock (Nova Lite):** ~$0.00006/1K input tokens, ~$0.00024/1K output tokens
- **Amplify:** Free tier covers 1000 build minutes/month + 15 GB hosting
- **S3:** Minimal cost; uploads auto-expire after 7 days
- **Voice features:** Free (browser-native Web Speech API, no AWS cost)

Estimated monthly cost for light usage (100 chats/day): **$5-15/month**.

## Troubleshooting

**Chat not responding:**
- Check Lambda logs: `aws logs tail /aws/lambda/agri-mitra-backend --region ap-south-1`
- Verify Bedrock model access is enabled for Nova Lite

**Dashboard showing no data:**
- Run `python seed_data.py` to populate tables
- Check DynamoDB tables have items: `aws dynamodb scan --table-name agri-mitra-mandi-prices --select COUNT --region ap-south-1`

**Upload failing:**
- Verify the uploads S3 bucket exists and Lambda has `s3:PutObject` permission
- Check Lambda logs for multipart parsing errors

**CDK deployment failing:**
- Ensure CDK is bootstrapped: `cdk bootstrap`
- Check you're in the correct AWS region/account
