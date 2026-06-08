from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "dev"
    APP_TITLE: str = "Private Resources Hub API"
    APP_VERSION: str = "0.1.0"
    ALLOWED_ORIGINS: dict[str, list[str]] = {
        "dev": ["http://localhost:3000"],  # desarrollo
    }


settings = Settings()
