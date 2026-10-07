"""Campus Customs backend.

Run from inside backend/:  uvicorn main:app --reload --port 8000

- Products API: read-only; only the `catalogue` and `inventory` tables are queried.
- Auth API (auth.py): create account / log in / log out; may only touch `users`.
- Chat API: PydanticAI agent (agent.py) with one read-only catalogue tool (tools.py).
- `chat_messages` is never read or written, and no user data is sent to the model.
"""

import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import Depends, FastAPI, HTTPException, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

import history  # noqa: E402
import price_check  # noqa: E402
from agent import ChatNotConfigured, rerun_with_correction, run_chat  # noqa: E402
from auth import ALLOWED_ORIGINS, client_ip, require_json_from_allowed_origin, session_user  # noqa: E402
from auth import router as auth_router  # noqa: E402
from db import ROOT, connect_readonly  # noqa: E402
from models import (  # noqa: E402
    MAX_HISTORY_TURN_CHARS,
    MAX_HISTORY_TURNS,
    MAX_MESSAGE_CHARS,
    MAX_PAGE_CARDS,
    MAX_PRODUCT_CARDS,
    MAX_SAVED_MESSAGES_SHOWN,
    ChatDeps,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    Customer,
    PageContextIn,
    PageResults,
    ShopReply,
)
from tools import lookup_product  # noqa: E402

log = logging.getLogger("campus_customs")
if not log.handlers:  # our own INFO lines (e.g. price check) next to uvicorn's; never message contents or keys
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
    log.propagate = False

SESSION_SECRET = os.getenv("SESSION_SECRET", "")
if len(SESSION_SECRET) < 32 or SESSION_SECRET.startswith("change-me"):
    raise RuntimeError(
        "SESSION_SECRET is missing or too short. Copy backend/.env.example to backend/.env "
        "and set it to a long random value."
    )

IMAGES_DIR = (ROOT / "data" / "products").resolve()

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Explicit column list so nothing outside these fields can leak.
PRODUCT_COLUMNS = "product_id, name, garment_type, description, colors, search_tags, image_file_path, price"

app = FastAPI(title="Campus Customs API")

# Signed session cookie: HttpOnly (Starlette always sets it), SameSite=Lax, 7 days.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="cc_session",
    max_age=7 * 24 * 60 * 60,
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "false").lower() == "true",
)

# Credentials (the cookie) are only allowed for the Vite dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes the submitted input back, which could include a password.
    return JSONResponse(status_code=422, content={"detail": "Please fill in every field."})


app.include_router(auth_router)


# ---------- chat ----------

class ReplyRateLimiter:
    """Sliding-window cap on chat replies: per client IP, plus one global cap for the whole server."""

    def __init__(self, per_ip_per_minute: int = 8, global_per_minute: int = 40):
        self.per_ip = per_ip_per_minute
        self.global_cap = global_per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, ip: str) -> int:
        """Record a request; return 0 if allowed, else seconds to wait."""
        now = time.monotonic()
        with self.lock:
            waits = []
            for key, cap in ((f"ip:{ip}", self.per_ip), ("global", self.global_cap)):
                q = self.hits[key]
                while q and now - q[0] > 60:
                    q.popleft()
                if len(q) >= cap:
                    waits.append(60 - (now - q[0]))
            if waits:
                return int(max(waits)) + 1
            self.hits[f"ip:{ip}"].append(now)
            self.hits["global"].append(now)
            return 0


chat_limiter = ReplyRateLimiter()

BLOCKED_REPLY = (
    "I'm just here to help you shop Campus Customs, so I can't help with that one. "
    "Want me to find you a hoodie, crewneck, or tee?"
)


@app.post("/api/chat", dependencies=[Depends(require_json_from_allowed_origin)])
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Type a message first.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise HTTPException(status_code=400, detail=f"Please keep messages under {MAX_MESSAGE_CHARS} characters.")
    if len(body.history) > MAX_HISTORY_TURNS * 4:
        raise HTTPException(status_code=400, detail="Conversation history is too long.")

    wait = chat_limiter.check(client_ip(request))
    if wait:
        raise HTTPException(
            status_code=429,
            detail="You're chatting fast! Give me a moment and try again.",
            headers={"Retry-After": str(wait)},
        )

    # Who's chatting comes only from the signed session cookie, never from the request body.
    user = session_user(request)
    deps = ChatDeps(customer=Customer(user["id"], user["first_name"], user["email"]) if user else None)
    deps.page_path, deps.viewed_product = page_context(body.page)

    if user:
        # Logged in: history is the shopper's own saved messages (the browser's copy is ignored).
        turns = history.model_history(user["id"], MAX_HISTORY_TURNS)
    else:
        # Guest: the browser's copy, trimmed; nothing is saved.
        turns = [
            turn.model_copy(update={"content": turn.content[:MAX_HISTORY_TURN_CHARS]})
            for turn in body.history[-MAX_HISTORY_TURNS:]
            if turn.content.strip()
        ]

    try:
        output, deps, run_messages = await run_chat(message, turns, deps)
        output = await enforce_price_check(output, deps, message, run_messages)
    except ChatNotConfigured:
        raise HTTPException(status_code=503, detail="The shop assistant isn't set up yet. Please try again later.")
    except UsageLimitExceeded:
        raise HTTPException(status_code=502, detail="That one was too tricky for me. Could you ask a simpler way?")
    except ModelHTTPError as exc:
        # The provider's safety filter (e.g. Azure content filter / jailbreak shield) blocked the message.
        if exc.status_code == 400 and "content_filter" in str(exc.body):
            log.info("chat blocked by provider content filter")
            return finish_chat(user, message, ChatResponse(reply=BLOCKED_REPLY))
        log.warning("chat failed: ModelHTTPError %s", exc.status_code)
        raise HTTPException(status_code=502, detail="The shop assistant is having trouble right now. Please try again.")
    except Exception as exc:  # model/network errors: log the type only, never request contents or keys
        log.warning("chat failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="The shop assistant is having trouble right now. Please try again.")

    # Cards only for real products the tool returned in this run (no invented items or prices).
    cards = []
    for pid in output.product_ids:
        card = deps.seen_products.get(pid)
        if card and card not in cards:
            cards.append(card)
        if len(cards) == MAX_PRODUCT_CARDS:
            break
    response = ChatResponse(reply=output.reply.strip(), products=cards, page_results=page_results_for(output, deps))
    return finish_chat(user, message, response)


async def enforce_price_check(output: ShopReply, deps: ChatDeps, message: str, run_messages) -> ShopReply:
    """Every dollar amount in the reply must come from a tool result (see price_check.py).
    If one doesn't: ask the agent once to rewrite; if it still doesn't, send the safe fallback."""
    bad = price_check.unverified_amounts(output.reply, deps, message)
    if not bad:
        return output
    log.info("price check: %d unverified amount(s); asking the agent to rewrite", len(bad))
    try:
        fixed = await rerun_with_correction(price_check.correction_prompt(bad), run_messages, deps)
    except Exception as exc:  # the rewrite is best-effort; the fallback is always safe
        log.warning("price check rewrite failed: %s", type(exc).__name__)
        fixed = None
    if fixed is not None and not price_check.unverified_amounts(fixed.reply, deps, message):
        log.info("price check: rewrite passed")
        return fixed
    log.info("price check: rewrite still unverified; sending fallback")
    return output.model_copy(update={"reply": price_check.FALLBACK_REPLY})


def finish_chat(user: dict | None, message: str, response: ChatResponse) -> ChatResponse:
    """Save the exchange for logged-in shoppers. A save failure never loses the reply."""
    if user:
        try:
            history.save_exchange(user["id"], message, response.reply, response.products)
            response.saved = True
        except sqlite3.Error as exc:
            log.warning("saving chat history failed: %s", type(exc).__name__)
    return response


SAFE_PATH = re.compile(r"^/[A-Za-z0-9/_\-]{0,100}$")


def page_context(page: PageContextIn | None):
    """Validate the page the browser says it's on. The path must look like one of our routes, and
    the product id is only trusted after looking up the real product in the catalogue."""
    if page is None:
        return None, None
    path = page.path if SAFE_PATH.fullmatch(page.path or "") else None
    product = None
    if page.product_id:
        found = lookup_product(page.product_id)
        if found:
            product = found[0]
    return path, product


@app.get("/api/chat/history")
def get_chat_history(request: Request) -> ChatHistoryResponse:
    """The logged-in shopper's last 30 messages. Guests get an empty list."""
    user = session_user(request)
    if user is None:
        return ChatHistoryResponse(logged_in=False)
    return ChatHistoryResponse(logged_in=True, messages=history.load_messages(user["id"], MAX_SAVED_MESSAGES_SHOWN))


@app.delete("/api/chat/history", dependencies=[Depends(require_json_from_allowed_origin)])
def clear_chat_history(request: Request) -> dict:
    """Delete the logged-in shopper's own messages (and nobody else's)."""
    user = session_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Log in to clear saved chats.")
    return {"deleted": history.clear(user["id"])}


def page_results_for(output: ShopReply, deps: ChatDeps) -> PageResults | None:
    """What the Products page should do, decided only from recorded search_products results:

    - off-topic message, or no search this turn  -> None (page unchanged)
    - last search found nothing                  -> empty results (page clears old cards)
    - agent marked it a browse (show_on_page)    -> that search's cards, up to MAX_PAGE_CARDS
    - otherwise (one-product question)           -> None
    """
    if output.off_topic or not deps.searches:
        return None
    last = deps.searches[-1]
    if not last.cards:
        return PageResults(query=last.query, total=0, products=[])
    if output.show_on_page:
        return PageResults(query=last.query, total=last.total, products=last.cards[:MAX_PAGE_CARDS])
    return None


def image_url(image_file_path: str) -> str:
    return f"/api/images/{Path(image_file_path).name}"


def product_summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "tags": json.loads(row["search_tags"]),
        "price": row["price"],
        "image_url": image_url(row["image_file_path"]),
    }


@app.get("/api/products")
def list_products() -> list[dict]:
    with connect_readonly() as conn:
        rows = conn.execute(
            f"""
            SELECT {PRODUCT_COLUMNS},
                   (SELECT COALESCE(SUM(quantity), 0) FROM inventory i
                    WHERE i.product_id = c.product_id) AS total_stock
            FROM catalogue c
            ORDER BY name
            """
        ).fetchall()
    return [{**product_summary(r), "in_stock": r["total_stock"] > 0} for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with connect_readonly() as conn:
        row = conn.execute(
            f"SELECT {PRODUCT_COLUMNS} FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    def size_rank(size: str) -> int:
        return SIZE_ORDER.index(size) if size in SIZE_ORDER else len(SIZE_ORDER)

    sizes = [
        {"size": s["size"], "quantity": s["quantity"], "in_stock": s["quantity"] > 0}
        for s in sorted(stock, key=lambda s: size_rank(s["size"]))
    ]
    return {**product_summary(row), "sizes": sizes, "in_stock": any(s["in_stock"] for s in sizes)}


@app.get("/api/images/{filename}")
def get_image(filename: str) -> FileResponse:
    # Only plain file names: no slashes, no "..", no hidden files.
    if not SAFE_FILENAME.fullmatch(filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid image name")
    suffix = Path(filename).suffix.lower()
    if suffix not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    path = (IMAGES_DIR / filename).resolve()
    # Belt and braces: the resolved path must still sit directly inside data/products/.
    if path.parent != IMAGES_DIR or not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type=IMAGE_TYPES[suffix])
