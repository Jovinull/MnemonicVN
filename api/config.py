from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/vividnexus"

    LLM_BASE_URL: str = "http://localhost:1234/v1"
    LLM_API_KEY: str = "lm-studio"
    LLM_CHAT_MODEL: str = "qwen2.5-coder-7b-instruct"
    LLM_EMBEDDING_MODEL: str = "nomic-embed-text-v1.5.f32"
    EMBEDDING_DIM: int = 768

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Motor do mundo
    WORLD_TICK_INTERVAL_SECONDS: int = 10
    WORLD_MINUTES_PER_TICK: int = 15
    WORLD_START_TIME: str = "06:00"


settings = Settings()
