"""Data shapes for the chat API and the agent."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# ---------- limits (keep the model bill small) ----------

MAX_MESSAGE_CHARS = 500  # one user message
MAX_HISTORY_TURNS = 10  # earlier messages sent along with the new one
MAX_HISTORY_TURN_CHARS = 1500  # any single earlier message
MAX_PRODUCT_CARDS = 4


# ---------- HTTP request / response ----------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []


class ProductCard(BaseModel):
    id: str
    name: str
    price: float
    image_url: str


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = []


# ---------- agent ----------

class ShopReply(BaseModel):
    """Structured output the agent must return."""

    reply: str = Field(description="What to say to the shopper. Short, warm, and accurate.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="IDs of up to 4 recommended products, taken from search_products results.",
    )


@dataclass
class ChatDeps:
    """Per-request state shared with tools. Records every product the tool returned,
    so product cards can only show real catalogue items the agent actually looked up."""

    seen_products: dict[str, ProductCard] = field(default_factory=dict)
