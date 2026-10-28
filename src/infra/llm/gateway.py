"""The one place that builds chat models, so the provider or model changes only in .env."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from config.env import env


class LLMNotConfigured(RuntimeError):
    pass


def get_chat_model(*, temperature: float = 0, model: str | None = None) -> BaseChatModel:
    if env.llm_api_key is None:
        raise LLMNotConfigured("Set LLM_API_KEY (or GROQ_API_KEY) in .env to use the LLM.")
    return init_chat_model(
        model or env.llm_model,
        api_key=env.llm_api_key.get_secret_value(),
        temperature=temperature,
        max_retries=env.llm_max_retries,
    )
