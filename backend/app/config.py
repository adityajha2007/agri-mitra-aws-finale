from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    aws_region: str = "ap-south-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_vision_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"

    dynamodb_table_farmers: str = "agri-mitra-farmers"
    dynamodb_table_conversations: str = "agri-mitra-conversations"
    dynamodb_table_mandi_prices: str = "agri-mitra-mandi-prices"
    dynamodb_table_weather: str = "agri-mitra-weather-cache"
    dynamodb_table_news: str = "agri-mitra-news"
    dynamodb_table_policy_docs: str = "agri-mitra-policy-documents"

    s3_bucket_policies: str = "agri-mitra-policies"
    s3_bucket_uploads: str = "agri-mitra-uploads"

    default_farmer_id: str = "farmer-001"

    class Config:
        env_file = ".env"
        env_prefix = "AGRI_MITRA_"


settings = Settings()
