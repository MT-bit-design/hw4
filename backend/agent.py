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
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from audit import audited
from models import ChatDeps, ChatTurn, ShopReply
from tools import get_my_account, get_product_details, get_stock, search_by_size, search_products

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
DEFAULT_MODEL = "gpt-5.6-luna"

# Hard caps per chat reply, so one message can't run up the bill.
MAX_OUTPUT_TOKENS = 600
# search -> details -> stock can take 3 tool calls plus the final answer.
USAGE_LIMITS = UsageLimits(request_limit=5, tool_calls_limit=5, total_tokens_limit=16_000)


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


def context_instructions(ctx: RunContext[ChatDeps]) -> str:
    """Per-request facts for the agent, built on the server from the session and a validated page.
    The email is deliberately not included here; it's only available through get_my_account."""
    deps = ctx.deps
    lines = ["## This conversation"]
    if deps.customer:
        name = "".join(ch for ch in deps.customer.first_name if ch.isalpha() or ch in " -'.")[:40].strip()
        lines.append(f"- The shopper is logged in. First name: {name or 'unknown'}.")
    else:
        lines.append("- The shopper is a guest (not logged in). You don't know their name.")
    if deps.viewed_product:
        p = deps.viewed_product
        lines.append(
            f"- The shopper is viewing this product page right now; \"this\" / \"it\" means this item: "
            f"id `{p.id}`, name \"{p.name}\", {p.garment_type}, price {p.price}, "
            f"colors from the catalogue: {', '.join(p.colors) or 'not listed'}."
        )
    elif deps.page_path:
        lines.append(f"- The shopper is on the page `{deps.page_path}` (not a single product page).")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, ShopReply]:
    """Built once on first use, so the server still starts without a key."""
    return Agent(
        build_model(),
        deps_type=ChatDeps,
        output_type=ShopReply,
        instructions=[load_prompt(), context_instructions],
        # Every tool call is recorded for the audit trail (audit.py); signatures and docstrings are unchanged.
        tools=[audited(t) for t in (search_products, search_by_size, get_product_details, get_stock, get_my_account)],
        model_settings={"max_tokens": MAX_OUTPUT_TOKENS},
        retries=1,
    )


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """History (saved, or browser-supplied for guests) becomes plain user/assistant text turns, never instructions."""
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


async def run_chat(
    message: str, history: list[ChatTurn], deps: ChatDeps
) -> tuple[ShopReply, ChatDeps, list[ModelMessage]]:
    """Run the agent. Also returns the full message list, so a price-check correction can continue it."""
    result = await get_agent().run(
        message,
        message_history=to_message_history(history),
        deps=deps,
        usage_limits=USAGE_LIMITS,
    )
    return result.output, deps, result.all_messages()


async def rerun_with_correction(
    correction: str, messages: list[ModelMessage], deps: ChatDeps
) -> ShopReply:
    """One follow-up turn asking the agent to fix its reply (same deps, so tool results still count)."""
    result = await get_agent().run(correction, message_history=messages, deps=deps, usage_limits=USAGE_LIMITS)
    return result.output
