"""Typed environment variables, read once from the project's .env file."""

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    postgres_host: str = "localhost"
    postgres_port: int = 5433

    llm_model: str = "groq:openai/gpt-oss-120b"
    # Small fast model for the guardrail classifier; empty means "use llm_model".
    llm_guard_model: str | None = None
    # Optional so Django still starts without a key; accepts the generic or the provider-specific name.
    llm_api_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("LLM_API_KEY", "GROQ_API_KEY"))

    kafka_bootstrap_servers: str = "localhost:9092"
    redis_url: str = "redis://localhost:6379/0"


env = Env()
