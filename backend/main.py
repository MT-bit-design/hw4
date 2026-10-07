"""Campus Customs backend.

- Products API: read-only; only the `catalogue` and `inventory` tables are queried.
- Auth API (auth.py): create account / log in / log out; may only touch `users`.
- `chat_messages` is never read or written.
"""

import json
import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .auth import ALLOWED_ORIGINS
from .auth import router as auth_router
from .db import ROOT, connect_readonly

load_dotenv(Path(__file__).resolve().parent / ".env")

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
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes the submitted input back, which could include a password.
    return JSONResponse(status_code=422, content={"detail": "Please fill in every field."})


app.include_router(auth_router)


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
