"""Model-provider adapter for NVIDIA NIM.

The agent graph depends on LangChain's chat-model interface rather than directly on
NVIDIA's SDK. NVIDIA's hosted NIM endpoint is OpenAI-compatible, so the provider
can be swapped later without changing the graph, tools, state, or product schemas.
"""

from __future__ import annotations

from functools import lru_cache
import os

from langchain_openai import ChatOpenAI


DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"


@lru_cache(maxsize=1)
def get_model() -> ChatOpenAI:
    """Return the configured NVIDIA Nemotron chat model."""

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is required to run the live agent.")

    return ChatOpenAI(
        model=os.getenv("NVIDIA_MODEL", DEFAULT_MODEL),
        base_url=os.getenv("NVIDIA_BASE_URL", DEFAULT_BASE_URL),
        api_key=api_key,
        temperature=1.0,
        max_retries=2,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": True,
                "force_nonempty_content": True,
            }
        },
    )
