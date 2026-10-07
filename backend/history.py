"""Saved chat history for logged-in shoppers, stored in the existing `chat_messages` table.

Every function takes the user id that the server got from the session cookie, and every
query filters on it, so a shopper can only ever read or delete their own messages.
Guests are never saved.

Stored per row: user_id, role ('user' | 'assistant'), content, products_json, created_at.
`products_json` holds the chat cards shown with a reply. On reload only the product ids
are used; cards are rebuilt from the current catalogue, so an old price is never shown.
"""

import json
import sqlite3

from db import connect_chat, connect_readonly
from models import MAX_HISTORY_TURN_CHARS, ChatTurn, HistoryMessage, ProductCard
from tools import CARD_COLUMNS, card_from_row


def _product_ids(products_json: str | None) -> list[str]:
    """Product ids from either our format ([{"id": ...}]) or the seed format ([{"product_id": ...}])."""
    if not products_json:
        return []
    try:
        items = json.loads(products_json)
    except ValueError:
        return []
    ids = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict):
            pid = item.get("id") or item.get("product_id")
            if isinstance(pid, str) and pid not in ids:
                ids.append(pid)
    return ids[:4]


def _cards_for(ids: list[str]) -> dict[str, ProductCard]:
    if not ids:
        return {}
    marks = ", ".join("?" * len(ids))
    with connect_readonly() as conn:
        rows = conn.execute(f"SELECT {CARD_COLUMNS} FROM catalogue WHERE product_id IN ({marks})", ids).fetchall()
    return {r["product_id"]: card_from_row(r) for r in rows}


def _recent_rows(user_id: int, limit: int) -> list[sqlite3.Row]:
    """The user's newest `limit` messages, returned oldest first."""
    with connect_chat() as conn:
        rows = conn.execute(
            "SELECT id, role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? AND role IN ('user', 'assistant') ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def load_messages(user_id: int, limit: int) -> list[HistoryMessage]:
    """For the chat panel: the last `limit` messages with their product cards."""
    rows = _recent_rows(user_id, limit)
    ids_per_row = [_product_ids(r["products_json"]) for r in rows]
    try:
        cards = _cards_for(sorted({i for ids in ids_per_row for i in ids}))
    except sqlite3.Error:
        cards = {}
    return [
        HistoryMessage(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            products=[cards[i] for i in ids if i in cards],
            created_at=r["created_at"],
        )
        for r, ids in zip(rows, ids_per_row)
    ]


def model_history(user_id: int, turns: int) -> list[ChatTurn]:
    """For the agent: the last `turns` messages as plain text turns (cut to a safe length)."""
    return [
        ChatTurn(role=r["role"], content=r["content"][:MAX_HISTORY_TURN_CHARS])
        for r in _recent_rows(user_id, turns)
        if r["content"].strip()
    ]


def save_exchange(user_id: int, message: str, reply: str, cards: list[ProductCard]) -> None:
    """Save one shopper message and the assistant's reply (with the ids of its chat cards)."""
    products_json = json.dumps([{"id": c.id} for c in cards]) if cards else None
    with connect_chat() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, products_json),
        )


def clear(user_id: int) -> int:
    """Delete only this user's messages. Returns how many were deleted."""
    with connect_chat() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
