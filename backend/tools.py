"""Agent tools. Read-only and limited to the `catalogue` table."""

import re
from pathlib import Path

from pydantic_ai import RunContext

from db import connect_readonly
from models import ChatDeps, ProductCard

MAX_RESULTS = 8
STOPWORDS = {
    "a", "an", "and", "any", "are", "do", "for", "have", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "show", "some", "the", "to", "want", "with", "you", "your", "yale",
}
HAYSTACK = "lower(name || ' ' || garment_type || ' ' || description || ' ' || colors || ' ' || search_tags)"


def image_url(image_file_path: str) -> str:
    return f"/api/images/{Path(image_file_path).name}"


def _keywords(query: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", query.lower())
    return [w for w in words if w not in STOPWORDS][:8]


def _query(words: list[str], max_price: float | None, limit: int) -> list:
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
    """Search the Campus Customs catalogue.

    Args:
        query: What the shopper wants, e.g. "navy hoodie", "Berkeley college", "gift".
        max_price: Optional highest price in dollars. Pass it whenever the shopper gives a budget.
        limit: How many results to return (1-8).

    Returns `products` (each with `id`, `name`, `price` already formatted like "$68.00", and
    `image_url`) and `match`:
    - "keywords": the products matched the query words.
    - "price_only": no product matched the query words, so these are simply products within
      `max_price`, cheapest first. Present them as options in the budget, not as exact matches.
    - "none": nothing found.
    Does not include sizes or stock.
    """
    limit = max(1, min(int(limit), MAX_RESULTS))
    words = _keywords(query)

    rows = _query(words, max_price, limit)
    match = "keywords" if rows else "none"
    if not rows and words and max_price is not None:
        # Words like "gift" or "present" appear in no product text; fall back to the budget alone.
        rows = _query([], max_price, limit)
        match = "price_only" if rows else "none"

    products = []
    for r in rows:
        card = ProductCard(id=r["product_id"], name=r["name"], price=r["price"], image_url=image_url(r["image_file_path"]))
        ctx.deps.seen_products[card.id] = card
        products.append({**card.model_dump(), "price": f"${card.price:.2f}"})
    return {"match": match, "products": products}
