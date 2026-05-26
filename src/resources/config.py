from pydantic_settings import BaseSettings, SettingsConfigDict


class ResourcesConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AWS_", env_file=".env", extra="ignore")

    REGION: str = "us-east-1"
    S3_BUCKET: str
    DYNAMODB_TABLE: str


resources_settings = ResourcesConfig()
