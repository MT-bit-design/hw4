"""Database connections.

Two kinds of connection, kept deliberately separate:
- `connect_readonly()` for the products API. Opened with `mode=ro`, so SQLite
  itself refuses every write.
- `connect_users()` for auth. Read-write, but an SQLite authorizer only lets
  statements read or insert rows in the `users` table. Any statement that
  touches another table (including `chat_messages`) fails before it runs.
"""

import sqlite3
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "campus_customs.db"

USERS_TABLE = "users"


def _require_db() -> None:
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Database not found. Unzip data.zip first.")


def connect_readonly() -> sqlite3.Connection:
    """Read-only connection; any write raises an error."""
    _require_db()
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
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
