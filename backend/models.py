"""Data shapes for the chat API and the agent."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# ---------- limits (keep the model bill small) ----------

MAX_MESSAGE_CHARS = 500  # one user message
MAX_HISTORY_TURNS = 10  # earlier messages sent along with the new one
MAX_HISTORY_TURN_CHARS = 1500  # any single earlier message
MAX_PRODUCT_CARDS = 4  # small cards inside the chat panel
MAX_PAGE_CARDS = 12  # full cards in the "Picked for you" section of the Products page
SHORT_DESCRIPTION_CHARS = 110


# ---------- HTTP request / response ----------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []


class ProductCard(BaseModel):
    """One product, as drawn in the chat panel and on the page. Always built from a database row."""

    id: str
    name: str
    price: float
    image_url: str
    garment_type: str
    short_description: str


class PageResults(BaseModel):
    """Search results for the Products page.

    `products` empty  -> the search found nothing: the page clears any old results.
    """

    query: str  # what was searched, shown as the section label
    total: int  # how many products matched in the catalogue
    products: list[ProductCard]  # up to MAX_PAGE_CARDS, in search order


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = []  # chat panel cards (max MAX_PRODUCT_CARDS)
    page_results: PageResults | None = None  # None -> leave the page as it is


# ---------- tool results (what the model sees) ----------

SIZES = ("XS", "S", "M", "L", "XL", "XXL")


class ProductDetails(BaseModel):
    """get_product_details result."""

    id: str
    name: str
    garment_type: str
    description: str
    price: str  # pre-formatted, e.g. "$58.00", so the model quotes it exactly


class SizeStock(BaseModel):
    size: str  # one of SIZES
    quantity: int
    sold_out: bool


class StockInfo(BaseModel):
    """get_stock result."""

    id: str
    name: str
    sizes: list[SizeStock]  # the one requested size, or all six in XS..XXL order
    in_stock_sizes: list[str]  # every size with quantity > 0, for "what else do you have?"


class ToolError(BaseModel):
    """Returned instead of a result when a lookup can't answer."""

    error: Literal["product_not_found", "invalid_size", "lookup_failed"]
    message: str


# ---------- agent ----------

class ShopReply(BaseModel):
    """Structured output the agent must return."""

    reply: str = Field(description="What to say to the shopper. Short, warm, and accurate.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="IDs of up to 4 recommended products, taken from search_products results.",
    )
    show_on_page: bool = Field(
        default=False,
        description=(
            "True when the shopper is browsing a kind of item (e.g. 'what hoodies do you have?', "
            "'gray crewnecks under $60') and your last search_products results should be shown on the page. "
            "False for questions about one specific product, stock or price checks, and off-topic messages."
        ),
    )
    off_topic: bool = Field(
        default=False,
        description="True when the message isn't about the Campus Customs shop (restaurants, homework, news...).",
    )


@dataclass
class SearchRecord:
    """One search_products call: what was asked and the cards it returned (up to MAX_PAGE_CARDS)."""

    query: str
    total: int
    cards: list[ProductCard]


@dataclass
class ChatDeps:
    """Per-request state shared with tools. Records every product a tool returned,
    so cards (chat or page) can only show real catalogue items the agent actually looked up."""

    seen_products: dict[str, ProductCard] = field(default_factory=dict)
    searches: list[SearchRecord] = field(default_factory=list)
