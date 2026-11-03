"""Typed environment variables, read once from the project's .env file."""

from pathlib import Path
from typing import Literal

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
    # ChatGroq sets no timeout by default, so without this a stalled call hangs its thread forever.
    llm_timeout_seconds: float = 60
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
    # Lesson 19: which store answers policy searches; Qdrant is a search copy of Postgres, kept in sync by the worker.
    vector_store: Literal["pgvector", "qdrant"] = "pgvector"
    qdrant_url: str | None = None  # unset: nothing is copied to Qdrant
    # Lesson 19B load test: without these, HNSW + tenant filter returned fewer than 10 results for 4%-sized companies.
    pgvector_iterative_scan: Literal["off", "strict_order", "relaxed_order"] = "strict_order"
    pgvector_ef_search: int = 200
    chat_history_max_tokens: int = 2000  # earlier conversation a specialist sees; the current turn is always kept

    # LangSmith tracing (cloud); off unless LANGSMITH_TRACING=true and a key is set.
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "opspilot-dev"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_mask_pii: bool = True  # phones/emails/CNICs become [phone]/[email]/[cnic] before traces leave the process

    # Signs every login token; anyone who has it can pretend to be any user, so it stays in .env only.
    jwt_secret_key: SecretStr | None = None
    # Links in emails start with this.
    public_base_url: str = "http://127.0.0.1:8000"
    # Password seed_data gives the fake demo customers and staff; local testing only.
    demo_password: SecretStr | None = None


env = Env()
