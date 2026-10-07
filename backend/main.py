"""Campus Customs backend.

Read-only API for the storefront: product list, product detail with stock per
size, and product images. Only the `catalogue` and `inventory` tables are ever
queried; `users` and `chat_messages` are never touched.
"""

import json
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "campus_customs.db"
IMAGES_DIR = (ROOT / "data" / "products").resolve()

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Explicit column list so nothing outside these fields can leak.
PRODUCT_COLUMNS = "product_id, name, garment_type, description, colors, search_tags, image_file_path, price"

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def connect() -> sqlite3.Connection:
    """Open the database in read-only mode; any write raises an error."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Database not found. Unzip data.zip first.")
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


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
    with connect() as conn:
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
    with connect() as conn:
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
