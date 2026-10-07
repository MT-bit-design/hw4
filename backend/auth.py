"""Create account, log in, log out, and "who am I".

Sessions are a signed, HttpOnly, SameSite=Lax cookie (Starlette's
SessionMiddleware, configured in main.py) holding only the user's id.
No endpoint ever returns a password or a password hash.
"""

import re
import sqlite3
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import connect_users
from passwords import DUMMY_HASH, hash_password, verify_password

ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

INVALID_LOGIN = "Invalid email or password."
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD, MAX_PASSWORD = 8, 128
MAX_NAME = 50
MAX_EMAIL = 254


# ---------- request checks ----------

def require_json_from_allowed_origin(request: Request) -> None:
    """CSRF guard for state-changing requests: JSON only, and from our own front end."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Origin not allowed.")
    if not request.headers.get("content-type", "").startswith("application/json"):
        raise HTTPException(status_code=415, detail="Send JSON.")


router = APIRouter(prefix="/api/auth")
post_guard = [Depends(require_json_from_allowed_origin)]


# ---------- login rate limiting ----------

class LoginRateLimiter:
    """Counts failed logins per email and per client IP in a sliding window.

    In-memory, so it resets when the server restarts; good enough for a single
    dev server. A multi-server deployment would keep these counters in Redis.
    """

    def __init__(self, per_email: int = 5, per_ip: int = 20, window_seconds: int = 15 * 60):
        self.limits = {"email": per_email, "ip": per_ip}
        self.window = window_seconds
        self.failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def _recent(self, key: tuple[str, str], now: float) -> deque[float]:
        q = self.failures[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def retry_after(self, email: str, ip: str) -> int:
        """Seconds until another attempt is allowed (0 = allowed now)."""
        now = time.monotonic()
        wait = 0.0
        with self.lock:
            for kind, value in (("email", email), ("ip", ip)):
                q = self._recent((kind, value), now)
                if len(q) >= self.limits[kind]:
                    wait = max(wait, self.window - (now - q[0]))
        return int(wait) + 1 if wait else 0

    def record_failure(self, email: str, ip: str) -> None:
        now = time.monotonic()
        with self.lock:
            self._recent(("email", email), now).append(now)
            self._recent(("ip", ip), now).append(now)

    def reset(self, email: str) -> None:
        with self.lock:
            self.failures.pop(("email", email), None)


limiter = LoginRateLimiter()


# ---------- helpers ----------

class SignupIn(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginIn(BaseModel):
    email: str
    password: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return len(email) <= MAX_EMAIL and bool(EMAIL_RE.fullmatch(email))


def clean_name(value: str, label: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= MAX_NAME:
        raise HTTPException(status_code=400, detail=f"{label} must be 1 to {MAX_NAME} characters.")
    if not all(c.isalpha() or c in " -'." for c in name) or not any(c.isalpha() for c in name):
        raise HTTPException(status_code=400, detail=f"{label} can only contain letters, spaces, hyphens, apostrophes, and periods.")
    return name


def public_user(row: sqlite3.Row) -> dict:
    """The only user fields that ever leave the server."""
    first = row["first_name"] or (row["name"] or "").split(" ")[0]
    return {"id": row["id"], "first_name": first, "last_name": row["last_name"] or "", "email": row["email"]}


USER_COLUMNS = "id, name, email, first_name, last_name"


def start_session(request: Request, user_id: int) -> None:
    request.session.clear()
    request.session["uid"] = user_id


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ---------- endpoints ----------

@router.post("/signup", status_code=201, dependencies=post_guard)
def signup(body: SignupIn, request: Request) -> dict:
    first = clean_name(body.first_name, "First name")
    last = clean_name(body.last_name, "Last name")
    email = normalize_email(body.email)
    if not valid_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if not MIN_PASSWORD <= len(body.password) <= MAX_PASSWORD:
        raise HTTPException(status_code=400, detail=f"Password must be {MIN_PASSWORD} to {MAX_PASSWORD} characters.")
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords don't match.")

    with connect_users() as conn:
        if conn.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        try:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        row = conn.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()

    start_session(request, row["id"])
    return {"user": public_user(row)}


@router.post("/login", dependencies=post_guard)
def login(body: LoginIn, request: Request) -> dict:
    email = normalize_email(body.email)
    ip = client_ip(request)

    wait = limiter.retry_after(email, ip)
    if wait:
        minutes = max(1, round(wait / 60))
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in about {minutes} minute{'s' if minutes != 1 else ''}.",
            headers={"Retry-After": str(wait)},
        )

    row = None
    if valid_email(email) and len(body.password) <= MAX_PASSWORD:
        with connect_users() as conn:
            row = conn.execute(
                f"SELECT {USER_COLUMNS}, password_hash FROM users WHERE lower(email) = ?", (email,)
            ).fetchone()

    # Always run one hash check so a missing email and a wrong password take the same time.
    ok = verify_password(body.password, row["password_hash"] if row else DUMMY_HASH) and row is not None
    if not ok:
        limiter.record_failure(email, ip)
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)

    limiter.reset(email)
    start_session(request, row["id"])
    return {"user": public_user(row)}


@router.post("/logout", dependencies=post_guard)
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    uid = request.session.get("uid")
    if not isinstance(uid, int):
        raise HTTPException(status_code=401, detail="Not logged in.")
    with connect_users() as conn:
        row = conn.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = ?", (uid,)).fetchone()
    if row is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not logged in.")
    return {"user": public_user(row)}
