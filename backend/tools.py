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
from models import SIZES, ChatDeps, ProductCard, ProductDetails, SizeStock, StockInfo, ToolError

log = logging.getLogger("campus_customs.tools")

MAX_RESULTS = 8
STOPWORDS = {
    "a", "an", "and", "any", "are", "do", "for", "have", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "show", "some", "the", "to", "want", "with", "you", "your", "yale",
}
HAYSTACK = "lower(name || ' ' || garment_type || ' ' || description || ' ' || colors || ' ' || search_tags)"

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


def _remember(ctx: RunContext[ChatDeps], row: sqlite3.Row) -> None:
    """Record a product the agent looked up, so the reply may show it as a card."""
    ctx.deps.seen_products[row["product_id"]] = ProductCard(
        id=row["product_id"], name=row["name"], price=row["price"], image_url=image_url(row["image_file_path"])
    )


def _keywords(query: str) -> list[str]:
    """Search words: lower-case, no filler words, and at least 2 characters
    (single characters like "1" or "s" match almost everything)."""
    words = re.findall(r"[a-z0-9]+", query.lower())
    return [w for w in words if len(w) >= 2 and w not in STOPWORDS][:8]


def _search(words: list[str], max_price: float | None, limit: int) -> list[sqlite3.Row]:
    """Rank catalogue rows by how many keywords they match (all values passed as ? parameters).
    With no keywords, returns rows within the price filter, cheapest first."""
    score_sql = " + ".join([f"({HAYSTACK} LIKE ?)"] * len(words)) or "0"
    params: list = [f"%{w}%" for w in words]
    where = ["1 = 1"]
    if words:
        where.append(f"({score_sql}) > 0")
        params += [f"%{w}%" for w in words]
    if max_price is not None:
        where.append("price <= ?")
        params.append(float(max_price))
    params.append(limit)
    order = "score DESC, name" if words else "price, name"

    sql = f"""
        SELECT product_id, name, price, image_file_path, ({score_sql}) AS score
        FROM catalogue
        WHERE {' AND '.join(where)}
        ORDER BY {order}
        LIMIT ?
    """
    with connect_readonly() as conn:
        return conn.execute(sql, params).fetchall()


def search_products(
    ctx: RunContext[ChatDeps],
    query: str,
    max_price: float | None = None,
    limit: int = 5,
) -> dict:
    """Search the Campus Customs catalogue. Use it to turn a product name into an id.

    Args:
        query: What the shopper wants, e.g. "navy hoodie", "baseball left chest crewneck", "gift".
        max_price: Optional highest price in dollars. Pass it whenever the shopper gives a budget.
        limit: How many results to return (1-8).

    Returns `match` and `products`. Each product has `id`, `name`, `price` (formatted, e.g. "$68.00"),
    `image_url`, and `matches_all_words` (true if every query word was found in that product).
    `match` is:
    - "keywords": products matched the query words, best first.
    - "price_only": nothing matched the words, so these are products within `max_price`, cheapest first.
    - "none": nothing found.
    Does not include descriptions or stock; use get_product_details / get_stock with the `id`.
    """
    limit = max(1, min(int(limit), MAX_RESULTS))
    words = _keywords(query)

    try:
        rows, match = [], "none"
        if words:
            rows = _search(words, max_price, limit)
            match = "keywords" if rows else "none"
        if not rows and max_price is not None:
            # No usable words (or words like "gift" that appear in no product text): use the budget alone.
            rows = _search([], max_price, limit)
            match = "price_only" if rows else "none"
    except sqlite3.Error:
        log.warning("search_products failed", exc_info=True)
        return LOOKUP_FAILED.model_dump()

    products = []
    for r in rows:
        _remember(ctx, r)
        products.append({
            "id": r["product_id"],
            "name": r["name"],
            "price": f"${r['price']:.2f}",
            "image_url": image_url(r["image_file_path"]),
            "matches_all_words": bool(words) and r["score"] == len(words),
        })
    return {"match": match, "products": products}


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
                "SELECT product_id, name, price, image_file_path FROM catalogue WHERE product_id = ?",
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
