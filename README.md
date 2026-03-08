# Agri-Mitra

A GenAI-powered agricultural assistant for Indian farmers, built on AWS. Chat with an AI agent that can look up mandi prices, weather forecasts, agricultural news, government policies, and diagnose crop diseases from photos — via web or WhatsApp, in Hindi, English or any rewgional language

**Live:** [https://main.d1v8d9313puioo.amplifyapp.com](https://main.d1v8d9313puioo.amplifyapp.com)

## Features

- **AI Chat Agent** — ReAct agent with 6 tools (prices, weather, news, policy search, crop image analysis, calculations)
- **WhatsApp Integration** — Chat via WhatsApp with text, images, and voice notes (Twilio)
- **Voice Input/Output** — Speak your questions and hear responses (browser-native, free)
- **Crop Image Diagnosis** — Upload a photo of your crop for disease/pest identification
- **Dashboard** — At-a-glance view of mandi prices, weather, and agricultural news
- **Multilingual** — Responds in the same language you ask in (Hindi, English, etc.)
- **Content Safety** — Bedrock Guardrails filter all responses; AWS WAF protects the API
- **Markdown Responses** — Rich formatted answers with headings, lists, and bold text

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| Backend | AWS Lambda (Python 3.12), API Gateway HTTP API |
| AI | Amazon Nova Prompt Router (reasoning), Nova Lite (vision), Titan Embeddings (RAG) |
| Content Safety | Bedrock Guardrails, AWS WAF (rate limiting + OWASP rules) |
| Audio | Amazon Transcribe (WhatsApp voice notes) |
| WhatsApp | Twilio Webhook |
| Database | DynamoDB (6 tables) |
| Storage | S3 (policies + crop images) |
| Secrets | AWS Secrets Manager (4 keys) |
| Hosting | AWS Amplify |
| Observability | X-Ray tracing, CloudWatch logging |
| Infrastructure | AWS CDK (Python) |

## Project Structure

```
agri-mitra-aws-finale/
├── backend/
│   ├── simple_lambda_handler.py   # Main Lambda — ReAct agent + all API routes + WhatsApp webhook
│   ├── seed_data.py               # One-time DynamoDB data seeder
│   ├── app/                       # FastAPI app (alternative backend, not deployed)
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Split-layout shell (dashboard + chat)
│   │   ├── components/Chat/       # ChatPanel, ChatInput (voice), MessageBubble (markdown)
│   │   ├── components/Dashboard/  # DashboardPanel, WeatherWidget, PriceTicker, NewsFeed
│   │   └── services/api.ts        # API client
│   ├── tailwind.config.js
│   └── amplify.yml
├── infra/                         # AWS CDK stacks
│   ├── app.py                     # CDK app entry point
│   └── stacks/                    # DataStack, SecurityStack, LambdaBackendStack, LambdaStack
├── lambdas/                       # Scheduled data fetcher Lambdas
│   ├── fetch_mandi_prices/
│   ├── fetch_weather/
│   ├── fetch_news/
│   └── process_policy_docs/
├── design.md                      # Architecture and design document
├── requirements.md                # Functional requirements
├── DEPLOYMENT.md                  # AWS deployment guide

```

## Quick Start

### Frontend (local development)

```bash
cd frontend
npm install
npm run dev
```

The frontend connects to the deployed API by default. To use a local backend, update `BASE_URL` in `src/services/api.ts`.

### Backend (local development)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with FastAPI (uses app/ directory)
uvicorn app.main:app --reload --port 8000
```

### Deploy to AWS

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions. Summary:

```bash
# 1. Deploy infrastructure
cd infra && cdk deploy --all

# 2. Seed data
cd backend && python seed_data.py

# 3. Build and deploy frontend
cd frontend && npm run build
# Then deploy dist/ to Amplify (see DEPLOYMENT.md)
```

### Run Tests

```bash
cd backend
pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/chat` | Send message to ReAct agent |
| POST | `/api/upload` | Upload crop image (multipart) |
| GET | `/api/dashboard/prices` | Get mandi prices |
| GET | `/api/dashboard/weather` | Get weather data |
| GET | `/api/dashboard/news` | Get agricultural news |
| POST | `/sms` | Twilio WhatsApp/SMS webhook |
| GET | `/health` | Health check |

## Documentation

- **[design.md](design.md)** — Architecture, data models, agent design, WhatsApp flow
- **[requirements.md](requirements.md)** — Functional requirements and acceptance criteria
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Step-by-step AWS deployment guide

