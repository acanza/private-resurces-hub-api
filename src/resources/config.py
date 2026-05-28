from pydantic_settings import BaseSettings, SettingsConfigDict


class ResourcesConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AWS_", env_file=".env", extra="ignore"
    )

    REGION: str = "eu-west-3"
    S3_BUCKET: str
    DYNAMODB_TABLE: str
    CF_DISTRIBUTION_DOMAIN: str = ""
    CF_KEY_PAIR_ID: str = ""
    CF_PRIVATE_KEY: str = ""
    CF_COOKIE_MAX_AGE_SECONDS: int = 3600


resources_settings = ResourcesConfig()
