# Requirements: Agri-Mitra

## Introduction

Agri-Mitra is a GenAI-powered agricultural assistant for Indian farmers. It provides crop price lookups, weather forecasts, agricultural news, government policy search, crop disease diagnosis via image upload, and general agricultural advice — through a web chat interface with voice support and a WhatsApp channel.

## Requirements

### 1. Conversational Interface

**User Story:** As a farmer, I want to chat with the system using text, voice, or images in my preferred language.

**Acceptance Criteria:**
1. The system shall accept text input and respond conversationally
2. The system shall accept image uploads of crops and provide analysis (pest/disease identification, health assessment)
3. The system shall respond in the same language as the user's input (Hindi, English, and other Indian languages)
4. The system shall support voice input via browser Speech Recognition API
5. The system shall support voice output via browser Speech Synthesis API, with auto-detection of Hindi vs English
6. The system shall maintain conversation context using client-side history (last 10 messages)
7. Assistant responses shall render as formatted Markdown (headings, lists, bold)

### 2. WhatsApp Channel

**User Story:** As a farmer, I want to interact with the assistant via WhatsApp without downloading a separate app.

**Acceptance Criteria:**
1. The system shall accept WhatsApp text messages via Twilio webhook and respond with agent output
2. The system shall accept WhatsApp image messages, download them with Twilio authentication, describe them using Bedrock Vision, and pass the description to the agent
3. The system shall accept WhatsApp voice notes, transcribe them using Amazon Transcribe, and pass the transcription to the agent
4. WhatsApp conversation history shall be stored in DynamoDB and loaded for context (last 10 messages)
5. Long-running queries shall be handled via async Lambda self-invocation to avoid Twilio's 15-second timeout
6. The system shall respond with TwiML-formatted messages

### 3. ReAct Agent and Tool Orchestration

**User Story:** As a farmer, I want the system to automatically determine what information I need and fetch it.

**Acceptance Criteria:**
1. The ReAct agent shall analyze user intent and select appropriate tools
2. The agent shall execute up to 5 reasoning iterations per query
3. When a tool fails, the agent shall provide an informative fallback response
4. The agent shall combine results from multiple tools into coherent answers
5. The agent shall prioritize location-specific information when context is available
6. All chat responses shall pass through Bedrock Guardrails for content safety

### 4. Market Prices

**User Story:** As a farmer, I want current mandi prices so I can decide when and where to sell.

**Acceptance Criteria:**
1. The dashboard shall display recent mandi prices with crop name, market, price per quintal, and state
2. The chat agent shall query prices by crop name, state, or market via the `get_mandi_prices` tool
3. Price data shall be refreshed every 6 hours from data.gov.in via scheduled Lambda

### 5. Weather Information

**User Story:** As a farmer, I want weather forecasts with agricultural advice for my area.

**Acceptance Criteria:**
1. The dashboard shall display current weather with temperature, humidity, rainfall, and agricultural advisory
2. The chat agent shall provide location-specific weather via the `get_weather` tool
3. Weather data shall be refreshed every 3 hours from OpenWeatherMap via scheduled Lambda

### 6. Agricultural News

**User Story:** As a farmer, I want recent agricultural news relevant to my work.

**Acceptance Criteria:**
1. The dashboard shall display recent agricultural news with title, summary, source link, and category tags
2. The chat agent shall query news by category via the `get_news` tool
3. News data shall be refreshed every 12 hours via scheduled Lambda

### 7. Policy and Scheme Search (RAG)

**User Story:** As a farmer, I want to find government schemes and policies relevant to me.

**Acceptance Criteria:**
1. The agent shall use semantic search (embeddings + cosine similarity) to find relevant policy documents
2. New policy documents uploaded to S3 shall be automatically embedded via Lambda trigger
3. The agent shall synthesize information from retrieved documents into clear answers

### 8. Crop Image Analysis

**User Story:** As a farmer, I want to upload a photo of my crop and get diagnosis/advice.

**Acceptance Criteria:**
1. The system shall accept image uploads via multipart form data (web) or WhatsApp media (Twilio)
2. Uploaded images shall be stored in S3 with 7-day auto-expiry
3. The agent shall analyze images using Nova Lite Vision (direct model, bypassing prompt router and guardrail to avoid false positives on agricultural imagery)
4. The S3 key shall be embedded in the user message so the agent can invoke `analyze_crop_image`
5. Uploaded images shall show as inline previews in the web chat history

### 9. Agricultural Calculations

**User Story:** As a farmer, I want yield and cost calculations for planning.

**Acceptance Criteria:**
1. The `calculate` tool shall perform deterministic calculations (yield estimation, cost analysis, profit margins, best market selection)
2. The agent shall explain methodology and assumptions used
3. Invalid inputs shall be validated with clear error messages

### 10. Dashboard

**User Story:** As a farmer, I want key information at a glance without chatting.

**Acceptance Criteria:**
1. The dashboard shall show mandi prices, weather, and news in a single panel
2. Dashboard data shall load from dedicated REST endpoints (`/api/dashboard/*`)
3. Loading states shall show skeleton placeholders; errors shall show a dismissible banner
4. On desktop, the dashboard shall be visible alongside chat (40/60 split layout)
5. On mobile, dashboard and chat shall be switchable via bottom tab bar

### 11. Performance and Reliability

**Acceptance Criteria:**
1. API responses shall complete within 60 seconds (Lambda timeout)
2. The frontend shall show a typing indicator while awaiting chat responses
3. External service failures shall not crash the system; cached data shall be used as fallback
4. S3 uploaded images shall auto-expire after 7 days
5. WhatsApp responses shall complete within 15 seconds or be handled asynchronously

### 12. Security

**Acceptance Criteria:**
1. All S3 buckets shall block public access with encryption at rest
2. Lambda shall use least-privilege IAM roles scoped to specific resources
3. External API keys (OpenWeather, News, data.gov.in, Twilio) shall be stored in AWS Secrets Manager
4. AWS WAF shall enforce rate limiting (2000 req/5min per IP), OWASP managed rules, and bot detection
5. Bedrock Guardrails shall filter all chat responses for content safety
6. API Gateway shall log all requests to CloudWatch; Lambda shall have X-Ray tracing enabled
7. All data shall be encrypted at rest (S3-managed) and in transit (TLS)
