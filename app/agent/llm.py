"""Lazy LLM factory.

Instantiating the chat model at import time forced an API key to exist just to
import any module that touched the agent. This factory defers creation until a
model is actually needed and caches a single instance.
"""
from functools import lru_cache

from app.utils.config import config


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0):
    """Return a cached ChatOpenAI instance.

    Imported lazily so that `import app.agent.tools` does not require the
    OpenAI SDK to be configured (e.g. during tests).
    """
    from langchain_openai import ChatOpenAI

    if not config.is_api_key_configured():
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file "
            "(see .env.example) before processing claims."
        )

    return ChatOpenAI(
        model=config.model_name,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
        temperature=temperature,
    )
