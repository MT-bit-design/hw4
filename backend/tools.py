"""Agent tools. Read-only; they only query the `catalogue` and `inventory` tables.

- search_products:     find products by words and/or budget
- get_product_details: name, description, price for one product id
- get_stock:           quantity for one size, or all six sizes, for one product id
"""

import logging
import re
import sqlite3
from pathlib import Path

from pydantic_ai import RunContext

from db import connect_readonly
from models import (
    MAX_PAGE_CARDS,
    SHORT_DESCRIPTION_CHARS,
    SIZES,
    ChatDeps,
    ProductCard,
    ProductDetails,
    SearchRecord,
    SizeStock,
    StockInfo,
    ToolError,
)

log = logging.getLogger("campus_customs.tools")

MAX_RESULTS = 8  # products listed back to the model (the page can get up to MAX_PAGE_CARDS)
STOPWORDS = {
    "a", "an", "and", "any", "are", "do", "for", "have", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "show", "some", "the", "to", "want", "with", "you", "your", "yale",
    "what", "which", "does", "got", "looking", "find", "need", "under", "less", "than", "below",
    "how", "much", "many", "please", "can", "could", "would", "there", "these", "those", "this",
    "that", "get", "buy", "all", "sell", "carry", "options",
}
HAYSTACK = "lower(name || ' ' || garment_type || ' ' || description || ' ' || colors || ' ' || search_tags)"
CARD_COLUMNS = "product_id, name, price, image_file_path, garment_type, description"

# Accepted spellings -> canonical size. Keys are lower-case with spaces, dots, and hyphens removed.
SIZE_ALIASES = {
    "xs": "XS", "xsmall": "XS", "extrasmall": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "xlarge": "XL", "extralarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xxlarge": "XXL", "2xlarge": "XXL", "doublexl": "XXL", "extraextralarge": "XXL",
}
SIZE_SORT = "CASE size " + " ".join(f"WHEN '{s}' THEN {i}" for i, s in enumerate(SIZES)) + " ELSE 99 END"

NOT_FOUND = ToolError(
    error="product_not_found",
    message="No product has that id. Use search_products to find the right id first.",
)
LOOKUP_FAILED = ToolError(
    error="lookup_failed",
    message="The product database couldn't be checked right now.",
)


def image_url(image_file_path: str) -> str:
    return f"/api/images/{Path(image_file_path).name}"


def normalize_size(raw: str) -> str | None:
    """'small' -> 'S', 'xl' -> 'XL', '2XL' -> 'XXL'; anything else -> None."""
    key = re.sub(r"[\s.\-_]", "", raw.lower())
    return SIZE_ALIASES.get(key)


def short_description(text: str, limit: int = SHORT_DESCRIPTION_CHARS) -> str:
    """First sentence or ~110 characters, cut at a word boundary."""
    first = text.split(". ")[0].rstrip(".")
    if len(first) <= limit:
        return first + "."
    return first[:limit].rsplit(" ", 1)[0].rstrip(",;") + "…"


def card_from_row(row: sqlite3.Row) -> ProductCard:
    """Build a card from a database row (needs the CARD_COLUMNS)."""
    return ProductCard(
        id=row["product_id"],
        name=row["name"],
        price=row["price"],
        image_url=image_url(row["image_file_path"]),
        garment_type=row["garment_type"],
        short_description=short_description(row["description"]),
    )


def _remember(ctx: RunContext[ChatDeps], row: sqlite3.Row) -> ProductCard:
    """Record a product the agent looked up, so the reply may show it as a card."""
    card = card_from_row(row)
    ctx.deps.seen_products[card.id] = card
    return card


def _singular(word: str) -> str:
    """'hoodies' -> 'hoodie', 'crewnecks' -> 'crewneck', 'zips' -> 'zip'; leaves 'dress', 'gas' alone."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _keywords(query: str) -> list[str]:
    """Search words: lower-case, no filler words, singular, and at least 2 characters
    (single characters like "1" or "s" match almost everything)."""
    words = re.findall(r"[a-z0-9]+", query.lower())
    out: list[str] = []
    for w in words:
        if len(w) < 2 or w in STOPWORDS:
            continue
        w = _singular(w)
        if w not in out:
            out.append(w)
    return out[:8]


def _filters(words: list[str], max_price: float | None, require_all: bool) -> tuple[str, str, list, list]:
    """Build (score_sql, where_sql, score_params, where_params). Every value is a ? parameter."""
    score_sql = " + ".join([f"({HAYSTACK} LIKE ?)"] * len(words)) or "0"
    score_params = [f"%{w}%" for w in words]
    where, where_params = ["1 = 1"], []
    if words:
        where.append(f"({score_sql}) {'=' if require_all else '>='} ?")
        where_params += score_params + [len(words) if require_all else 1]
    if max_price is not None:
        where.append("price <= ?")
        where_params.append(float(max_price))
    return score_sql, " AND ".join(where), score_params, where_params


def _search(words: list[str], max_price: float | None, require_all: bool) -> tuple[list[sqlite3.Row], int]:
    """Return (up to MAX_PAGE_CARDS rows ranked by keyword hits, total matching count).
    With no keywords, rows within the price filter come back cheapest first."""
    score_sql, where_sql, score_params, where_params = _filters(words, max_price, require_all)
    order = "score DESC, name" if words else "price, name"
    with connect_readonly() as conn:
        rows = conn.execute(
            f"SELECT {CARD_COLUMNS}, ({score_sql}) AS score FROM catalogue "
            f"WHERE {where_sql} ORDER BY {order} LIMIT ?",
            score_params + where_params + [MAX_PAGE_CARDS],
        ).fetchall()
        total = conn.execute(f"SELECT count(*) FROM catalogue WHERE {where_sql}", where_params).fetchone()[0]
    return rows, total


def search_products(
    ctx: RunContext[ChatDeps],
    query: str,
    max_price: float | None = None,
    limit: int = 5,
) -> dict:
    """Search the Campus Customs catalogue. Use it for browsing ("what hoodies do you have?")
    and to turn a product name into an id.

    Args:
        query: What the shopper wants, e.g. "hoodie", "gray crewneck", "baseball left chest crewneck", "gift".
        max_price: Optional highest price in dollars. Pass it whenever the shopper gives a budget.
        limit: How many products to list back to you (1-8). Up to 12 can be shown on the page.

    Returns `match`, `total_found` (how many products match in the whole catalogue), and `products`.
    Each product has `id`, `name`, `price` (formatted, e.g. "$68.00"), and `matches_all_words`.
    `match` is:
    - "all_words": every product listed contains every query word.
    - "some_words": no product contains every word; these match some of them, best first.
    - "price_only": nothing matched the words, so these are products within `max_price`, cheapest first.
    - "none": nothing found.
    Does not include descriptions or stock; use get_product_details / get_stock with the `id`.
    """
    limit = max(1, min(int(limit), MAX_RESULTS))
    words = _keywords(query)

    try:
        rows, total, match = [], 0, "none"
        if words:
            # Prefer products that contain every word; fall back to partial matches.
            rows, total = _search(words, max_price, require_all=True)
            match = "all_words" if rows else "none"
            if not rows:
                rows, total = _search(words, max_price, require_all=False)
                match = "some_words" if rows else "none"
        if not rows and max_price is not None:
            # No usable words (or words like "gift" that appear in no product text): use the budget alone.
            rows, total = _search([], max_price, require_all=False)
            match = "price_only" if rows else "none"
    except sqlite3.Error:
        log.warning("search_products failed", exc_info=True)
        return LOOKUP_FAILED.model_dump()

    cards = [_remember(ctx, r) for r in rows]
    # The page shows these exact cards (never anything the model writes).
    ctx.deps.searches.append(SearchRecord(query=query.strip()[:60], total=total, cards=cards))
    return {
        "match": match,
        "total_found": total,
        "products": [
            {
                "id": c.id,
                "name": c.name,
                "price": f"${c.price:.2f}",
                "matches_all_words": bool(words) and r["score"] == len(words),
            }
            for c, r in zip(cards[:limit], rows)
        ],
    }


def get_product_details(ctx: RunContext[ChatDeps], product_id: str) -> ProductDetails | ToolError:
    """Look up one product's name, garment type, full description, and exact price.

    Args:
        product_id: The product `id` from search_products (e.g. "baseball-left-chest-crewneck").
    """
    try:
        with connect_readonly() as conn:
            row = conn.execute(
                "SELECT product_id, name, garment_type, description, price, image_file_path "
                "FROM catalogue WHERE product_id = ?",
                (product_id.strip(),),
            ).fetchone()
    except sqlite3.Error:
        log.warning("get_product_details failed", exc_info=True)
        return LOOKUP_FAILED
    if row is None:
        return NOT_FOUND
    _remember(ctx, row)
    return ProductDetails(
        id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        price=f"${row['price']:.2f}",
    )


def get_stock(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None) -> StockInfo | ToolError:
    """Look up live stock for one product.

    Args:
        product_id: The product `id` from search_products.
        size: Optional size as the shopper wrote it ("small", "xl", "XXL", "2XL", ...).
            Leave empty to get all six sizes (XS, S, M, L, XL, XXL).

    `sizes` holds the requested size (or all six) with exact `quantity` and `sold_out`.
    `in_stock_sizes` always lists every size that is available, for suggesting alternatives.
    """
    wanted = None
    if size is not None and size.strip():
        wanted = normalize_size(size)
        if wanted is None:
            return ToolError(
                error="invalid_size",
                message=f"'{size[:20]}' isn't a size we carry. Sizes are XS, S, M, L, XL, and XXL.",
            )

    try:
        with connect_readonly() as conn:
            product = conn.execute(
                f"SELECT {CARD_COLUMNS} FROM catalogue WHERE product_id = ?",
                (product_id.strip(),),
            ).fetchone()
            if product is None:
                return NOT_FOUND
            stock = conn.execute(
                f"SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY {SIZE_SORT}",
                (product["product_id"],),
            ).fetchall()
    except sqlite3.Error:
        log.warning("get_stock failed", exc_info=True)
        return LOOKUP_FAILED

    _remember(ctx, product)
    all_sizes = [SizeStock(size=r["size"], quantity=r["quantity"], sold_out=r["quantity"] <= 0) for r in stock]
    shown = [s for s in all_sizes if s.size == wanted] if wanted else all_sizes
    if wanted and not shown:  # size row missing from inventory: treat as unavailable, never guess
        shown = [SizeStock(size=wanted, quantity=0, sold_out=True)]
    return StockInfo(
        id=product["product_id"],
        name=product["name"],
        sizes=shown,
        in_stock_sizes=[s.size for s in all_sizes if not s.sold_out],
    )
