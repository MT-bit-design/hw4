# Campus Customs Harness

## Database

Source: `data/campus_customs.db` (SQLite). Product images live in `data/products/`.

### How the tables connect

```
catalogue.product_id  1 ──< many  inventory.product_id   (one row per product per size)
users.id              1 ──< many  chat_messages.user_id  (one row per chat message)
```

| Table | Rows | Primary key |
|---|---|---|
| `catalogue` | 102 | `product_id` |
| `inventory` | 612 | `id` (also unique on `product_id` + `size`) |
| `users` | 3 | `id` (also unique on `email`) |
| `chat_messages` | 22 | `id` |

---

### `catalogue`

One row per product (102 products, 22 garment types, priced $32–$98).

| Field | Type | Why it matters |
|---|---|---|
| `product_id` | TEXT, PK | Unique slug for each product; the key that links to `inventory`. |
| `name` | TEXT | Display name the chatbot shows to shoppers. |
| `garment_type` | TEXT | Lets the chatbot filter by kind (hoodie, crewneck, T-shirt, etc.). |
| `description` | TEXT | Plain-language details the chatbot uses to describe and match products. |
| `colors` | TEXT (JSON list) | Lets shoppers search or filter by color. |
| `search_tags` | TEXT (JSON list) | Extra keywords that help the chatbot find the right product. |
| `image_file_path` | TEXT | Path to the product photo, relative to `data/` (e.g. `products/x.jpg`). |
| `price` | REAL | Price in dollars; needed for budget questions and checkout. |

Example rows:

| product_id | name | garment_type | price |
|---|---|---|---|
| `2025-yale-vs-harvard-t-shirt` | 2025 Yale Vs Harvard T Shirt | short-sleeve T-shirt | 32.00 |
| `baseball-left-chest-crewneck` | Baseball Left Chest Crewneck | crewneck sweatshirt | 58.00 |
| `basic-hoodie-big-yale` | Basic Hoodie Big Yale | pullover hoodie | 68.00 |

---

### `inventory`

Stock count for each product in each size. Every product has all 6 sizes (XS, S, M, L, XL, XXL), so 102 × 6 = 612 rows. Quantities range from 0 to 25, and 145 product/size combinations are sold out (quantity 0).

| Field | Type | Why it matters |
|---|---|---|
| `id` | INTEGER, PK | Internal row ID. |
| `product_id` | TEXT, FK → `catalogue.product_id` | Says which product this stock row belongs to. |
| `size` | TEXT | The size (XS–XXL); shoppers ask for products in their size. |
| `quantity` | INTEGER | Units in stock; the chatbot should only offer sizes with quantity > 0. |

Example rows:

| id | product_id | size | quantity |
|---|---|---|---|
| 1 | `2025-yale-vs-harvard-t-shirt` | XS | 25 |
| 3 | `2025-yale-vs-harvard-t-shirt` | M | 20 |
| 4 | `2025-yale-vs-harvard-t-shirt` | L | 2 |

---

### `users`

Shop accounts. Contains personal data, so only the fields are described here; no values are copied.

| Field | Type | Why it matters |
|---|---|---|
| `id` | INTEGER, PK | Unique user ID; links a user to their chat messages. |
| `name` | TEXT | Full name for greeting the user. Personal data. |
| `email` | TEXT, unique | Login identifier. Personal data; never show it to other users. |
| `password_hash` | TEXT | Hashed password for login. Secret; never expose it, not even to the chatbot. |
| `created_at` | TEXT (datetime) | When the account was created. |
| `first_name` | TEXT, optional | First name for friendly greetings. Personal data. |
| `last_name` | TEXT, optional | Last name. Personal data. |

---

### `chat_messages`

Saved chatbot conversation history (11 user messages, 11 assistant replies). Message content is private, so only the fields are described here.

| Field | Type | Why it matters |
|---|---|---|
| `id` | INTEGER, PK | Unique message ID; also keeps messages in order. |
| `user_id` | INTEGER, FK → `users.id` | Which user the conversation belongs to. |
| `role` | TEXT | `user` or `assistant`; who sent the message. |
| `content` | TEXT | The message text; gives the chatbot memory of the conversation. |
| `products_json` | TEXT (JSON), optional | Products the assistant recommended in that reply, so the UI can show them. |
| `created_at` | TEXT (datetime) | When the message was sent. |
