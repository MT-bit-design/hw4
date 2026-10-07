"""Append-only audit trail for chat runs: output/audit_trail.json.

Format: JSON Lines, one AuditEntry object per line. Lines are only ever appended (the file is
opened in append mode), so a restart never wipes or rewrites earlier entries; a missing file
is created on the first write.

Safe for concurrent requests: a thread lock serializes writers inside the process, and an OS
file lock on a side file (audit_trail.json.lock) serializes writers across processes. Each run's
entries are written in one write() call while both locks are held, so runs never interleave.

Privacy: no keys, passwords, hashes, emails, or full chat text. Users are recorded by id (or
"guest"), every text field is redacted and cut to ~100 characters.
"""

import functools
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from models import AUDIT_TEXT_CHARS, AuditEntry, ChatDeps, StopReason

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_LOCK_PATH = AUDIT_PATH.with_name(AUDIT_PATH.name + ".lock")
_thread_lock = threading.Lock()

# ---------- redaction ----------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_HASH = re.compile(r"pbkdf2_sha256\$\S+|\b[0-9a-fA-F]{32,}\b")
_KEY = re.compile(r"\b(?=[A-Za-z0-9_]*\d)(?=[A-Za-z0-9_]*[A-Za-z])[A-Za-z0-9_]{24,}\b|\bsk-[A-Za-z0-9_-]{8,}")


def redact(text: object, limit: int = AUDIT_TEXT_CHARS) -> str:
    """One line, emails/hashes/key-like tokens replaced, cut to `limit` characters."""
    s = " ".join(str(text).split())
    s = _EMAIL.sub("[email]", s)
    s = _HASH.sub("[hash]", s)
    s = _KEY.sub("[key]", s)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id() -> str:
    return uuid.uuid4().hex[:10]


# ---------- tool wrapper ----------

def _summarize(tool: str, result: object) -> str:
    """A short, safe description of a tool result (never the raw email from get_my_account)."""
    if isinstance(result, BaseModel):
        result = result.model_dump()
    if not isinstance(result, dict):
        return redact(result)
    if "error" in result:
        return f"error={result['error']}"
    if tool == "get_my_account":
        return "returned the session user's own account (contents not logged)"
    if "products" in result:
        ids = [p.get("id") for p in result["products"][:3]]
        extra = f", size={result['size']}" if "size" in result else ""
        return redact(f"match={result.get('match')}, total={result.get('total_found')}{extra}, first={ids}")
    if "sizes" in result:
        sizes = ", ".join(f"{s['size']}:{s['quantity']}" for s in result["sizes"])
        return redact(f"{result.get('id')}: {sizes}")
    if "price" in result:
        return redact(f"{result.get('id')}: {result.get('price')}")
    return redact(result)


def audited(tool_fn):
    """Wrap an agent tool so each call is recorded in ctx.deps.audit_steps (signature unchanged)."""

    @functools.wraps(tool_fn)
    def wrapper(ctx, *args, **kwargs):
        shown = ", ".join([repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()])
        try:
            result = tool_fn(ctx, *args, **kwargs)
        except Exception as exc:
            ctx.deps.audit_steps.append((now(), tool_fn.__name__, redact(shown), f"exception {type(exc).__name__}"))
            raise
        ctx.deps.audit_steps.append((now(), tool_fn.__name__, redact(shown), _summarize(tool_fn.__name__, result)))
        return result

    return wrapper


# ---------- writing ----------

def _lock_file(f) -> None:
    if os.name == "nt":
        import msvcrt

        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)  # blocks (retries) until the lock is free
    else:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_EX)


def _unlock_file(f) -> None:
    if os.name == "nt":
        import msvcrt

        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def append(entries: list[AuditEntry]) -> None:
    """Append entries as JSON lines. Never truncates; creates the file if it's missing."""
    if not entries:
        return
    data = "".join(json.dumps(e.model_dump(), ensure_ascii=False) + "\n" for e in entries)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock:
        with open(_LOCK_PATH, "a+b") as lock:
            _lock_file(lock)
            try:
                with open(AUDIT_PATH, "a", encoding="utf-8") as f:  # "a" = append only, never truncate
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
            finally:
                _unlock_file(lock)


def record_run(
    run_id: str,
    user_id: int | None,
    deps: ChatDeps | None,
    stop_reason: StopReason,
    message: str,
    outcome: str,
    extra_steps: list[tuple[str, str, str]] = (),
) -> None:
    """Write one chat run: its tool calls, any extra steps (e.g. price check), and a closing reply entry."""
    user: int | str = user_id if user_id is not None else "guest"
    steps = list(deps.audit_steps) if deps else []
    steps += [(now(), tool, redact(args), redact(result)) for tool, args, result in extra_steps]
    steps.append((now(), "reply", redact(f"message: {message}"), redact(outcome)))
    entries = [
        AuditEntry(time=t, run_id=run_id, user=user, tool=tool, args=args, result=result, stop_reason=stop_reason)
        for t, tool, args, result in steps
    ]
    try:
        append(entries)
    except OSError:
        # Auditing must never break the shop; the server log shows that the write failed (no contents).
        import logging

        logging.getLogger("campus_customs").warning("audit trail write failed")
