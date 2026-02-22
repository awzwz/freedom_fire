"""Application configuration via Pydantic Settings.

NOTE: We explicitly map common .env variable names (DATABASE_URL, OPENAI_API_KEY,
OPENAI_MODEL, etc.) to avoid silent misconfiguration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://fire:fire@localhost:5433/fire_db",
        validation_alias="DATABASE_URL",
    )

    # OpenAI
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    google_maps_api_key: str = Field(default="", validation_alias="GOOGLE_MAPS_API_KEY")

    # Geocoder
    geocoder_user_agent: str = Field(
        default="fire-routing-engine",
        validation_alias="GEOCODER_USER_AGENT",
    )

    # App
    debug: bool = Field(default=False, validation_alias="DEBUG")
    csv_data_path: str = Field(default="data", validation_alias="CSV_DATA_PATH")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
