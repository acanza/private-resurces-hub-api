from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ResourcesConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    REGION: str = Field(default="eu-west-3", validation_alias="AWS_REGION")
    S3_BUCKET: str = Field(validation_alias="S3_BUCKET_NAME")
    DYNAMODB_TABLE: str = Field(validation_alias="DYNAMODB_TABLE_NAME")
    CF_DISTRIBUTION_DOMAIN: str = Field(
        default="", validation_alias="PRIVATE_DISTRIBUTION_DOMAIN_NAME"
    )
    CF_KEY_PAIR_ID: str = Field(default="", validation_alias="CLOUDFRONT_KEY_PAIR_ID")
    CF_SECRET_NAME: str = Field(default="", validation_alias="CF_SECRET_NAME")  # noqa: S105
    CF_COOKIE_MAX_AGE_SECONDS: int = 3600


resources_settings = ResourcesConfig()
