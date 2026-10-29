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
    # Retries on 429/5xx; the provider SDK waits for its retry-after header (up to 60s) between tries.
    llm_max_retries: int = 6
    # Local multilingual embedding model (FastEmbed); 384 dimensions, see infra/llm/embeddings.py.
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # Optional so Django still starts without a key; accepts the generic or the provider-specific name.
    llm_api_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("LLM_API_KEY", "GROQ_API_KEY"))

    kafka_bootstrap_servers: str = "localhost:9092"
    redis_url: str = "redis://localhost:6379/0"

    # Lesson 16B switches, so each optimization can be measured on/off as its own LangSmith experiment.
    orchestrator_triage: bool = True  # one triage call instead of guard_input + supervisor
    rag_search_limit: int = 3  # chunks per policy search (was 5)
    rag_skip_confident_grade: bool = True  # skip the LLM grade when vector and keyword search agree on the top chunk

    # LangSmith tracing (cloud); off unless LANGSMITH_TRACING=true and a key is set.
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "opspilot-dev"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_mask_pii: bool = True  # phones/emails/CNICs become [phone]/[email]/[cnic] before traces leave the process

    # Shared key for the staff approval API until JWT roles exist; unset = staff API refuses everyone.
    staff_api_key: SecretStr | None = None


env = Env()
