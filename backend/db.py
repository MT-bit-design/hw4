"""Database connections.

Two kinds of connection, kept deliberately separate:
- `connect_readonly()` for the products API and agent tools. Opened with
  `mode=ro`, so SQLite itself refuses every write, and an authorizer only lets
  it read the `catalogue` and `inventory` tables.
- `connect_users()` for auth. Read-write, but an SQLite authorizer only lets
  statements read or insert rows in the `users` table. Any statement that
  touches another table (including `chat_messages`) fails before it runs.
- `connect_chat()` for saved chat history. Read-write, limited by an
  authorizer to reading, inserting, and deleting rows in `chat_messages`.
"""

import sqlite3
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "campus_customs.db"

USERS_TABLE = "users"
PRODUCT_TABLES = {"catalogue", "inventory"}


def _require_db() -> None:
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Database not found. Unzip data.zip first.")


def _products_only(action: int, arg1: str | None, _arg2, _db, _trigger) -> int:
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if arg1 in PRODUCT_TABLES else sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def connect_readonly() -> sqlite3.Connection:
    """Read-only connection that can only read `catalogue` and `inventory`."""
    _require_db()
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.set_authorizer(_products_only)
    return conn


def _users_only(action: int, arg1: str | None, _arg2, _db, _trigger) -> int:
    if action in (sqlite3.SQLITE_READ, sqlite3.SQLITE_INSERT):
        return sqlite3.SQLITE_OK if arg1 == USERS_TABLE else sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def connect_users() -> sqlite3.Connection:
    """Read-write connection that can only read from / insert into `users`."""
    _require_db()
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    conn.set_authorizer(_users_only)
    return conn


CHAT_TABLE = "chat_messages"


def _chat_only(action: int, arg1: str | None, _arg2, _db, _trigger) -> int:
    if action in (sqlite3.SQLITE_READ, sqlite3.SQLITE_INSERT, sqlite3.SQLITE_DELETE):
        return sqlite3.SQLITE_OK if arg1 == CHAT_TABLE else sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def connect_chat() -> sqlite3.Connection:
    """Read-write connection that can only read, insert, or delete rows in `chat_messages`.
    Callers must always filter by the logged-in user's id (see history.py)."""
    _require_db()
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    conn.set_authorizer(_chat_only)
    return conn
