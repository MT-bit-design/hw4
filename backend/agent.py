"""The Campus Customs shop agent (PydanticAI + OpenAI via Portkey).

- System prompt: read from prompts/prompt.md when the agent is first built.
- Model: CHAT_MODEL env var (default gpt-5.6-luna), called through Portkey's
  OpenAI-compatible gateway using PORTKEY_API_KEY from backend/.env.
"""

import os
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep server logs clean

from openai import AsyncOpenAI  # noqa: E402
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from models import ChatDeps, ChatTurn, ShopReply
from tools import search_products

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
DEFAULT_MODEL = "gpt-5.6-luna"

# Hard caps per chat reply, so one message can't run up the bill.
MAX_OUTPUT_TOKENS = 600
USAGE_LIMITS = UsageLimits(request_limit=4, tool_calls_limit=3, total_tokens_limit=12_000)


class ChatNotConfigured(RuntimeError):
    """Raised when the Portkey key is missing."""


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def model_name() -> str:
    return os.getenv("CHAT_MODEL", DEFAULT_MODEL)


def build_model() -> OpenAIChatModel:
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key or api_key.startswith("your-"):
        raise ChatNotConfigured("PORTKEY_API_KEY is not set in backend/.env")
    # Optional: only needed if the Portkey key has no default provider/config attached.
    provider_slug = os.getenv("PORTKEY_PROVIDER", "").strip()
    headers = createHeaders(api_key=api_key, provider=provider_slug) if provider_slug else createHeaders(api_key=api_key)
    client = AsyncOpenAI(
        base_url=PORTKEY_GATEWAY_URL,
        api_key=api_key,
        default_headers=headers,
        timeout=30,
        max_retries=1,
    )
    return OpenAIChatModel(model_name(), provider=OpenAIProvider(openai_client=client))


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, ShopReply]:
    """Built once on first use, so the server still starts without a key."""
    return Agent(
        build_model(),
        deps_type=ChatDeps,
        output_type=ShopReply,
        instructions=load_prompt(),
        tools=[search_products],
        model_settings={"max_tokens": MAX_OUTPUT_TOKENS},
        retries=1,
    )


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Browser-supplied history becomes plain user/assistant text turns (never instructions)."""
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


async def run_chat(message: str, history: list[ChatTurn]) -> tuple[ShopReply, ChatDeps]:
    deps = ChatDeps()
    result = await get_agent().run(
        message,
        message_history=to_message_history(history),
        deps=deps,
        usage_limits=USAGE_LIMITS,
    )
    return result.output, deps
