"""Price check on agent replies: every dollar amount must come from a tool result.

Allowed amounts for one reply:
- the price of every product a tool returned in this run (ChatDeps.seen_products, built from database rows)
- the price of the product page the shopper is on (looked up in the catalogue by the server)
- amounts the shopper typed in this message, so echoing a budget ("under $60") is fine

Anything else (a guessed price, a computed total, an invented discount or shipping fee) is flagged.
main.py then asks the agent once to rewrite, and if that still fails, sends a safe fallback.
"""

import re

from models import ChatDeps

# $68, $68.00, $ 68, $1,250.50
DOLLAR_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?")

FALLBACK_REPLY = (
    "I want to be sure I quote you the right price, so I'll leave the numbers to the product page; "
    "it always shows the current price. Tap a product to see it."
)


def _cents(whole: str, frac: str | None) -> int:
    return int(whole.replace(",", "")) * 100 + int((frac or "0").ljust(2, "0"))


def amounts_in(text: str) -> list[tuple[str, int]]:
    """Every dollar amount in `text` as (as written, cents)."""
    return [(m.group(0), _cents(m.group(1), m.group(2))) for m in DOLLAR_RE.finditer(text)]


def allowed_cents(deps: ChatDeps, user_message: str) -> set[int]:
    allowed = {round(card.price * 100) for card in deps.seen_products.values()}
    if deps.viewed_product:
        allowed |= {c for _, c in amounts_in(deps.viewed_product.price)}
    allowed |= {c for _, c in amounts_in(user_message)}
    return allowed


def unverified_amounts(reply: str, deps: ChatDeps, user_message: str) -> list[str]:
    """Dollar amounts in the reply that no tool result (or the shopper) supplied."""
    allowed = allowed_cents(deps, user_message)
    return [written for written, cents in amounts_in(reply) if cents not in allowed]


def correction_prompt(bad: list[str]) -> str:
    return (
        "[Automatic price check] Your reply mentioned "
        + ", ".join(bad)
        + ", which doesn't match any price returned by a tool in this conversation. "
        "Rewrite the reply using only exact unit prices from tool results. "
        "Don't add totals, discounts, shipping costs, or estimates."
    )
