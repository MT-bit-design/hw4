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

---

## Authentication

Create account, log in, and log out are handled by `backend/auth.py`. The front end (`frontend/src/auth.tsx`) asks `GET /api/auth/me` on every page load to find out who is logged in.

### Endpoints

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/auth/signup` | Validates input, creates the user, and logs them in. |
| `POST` | `/api/auth/login` | Checks email + password and starts a session. |
| `POST` | `/api/auth/logout` | Clears the session. |
| `GET` | `/api/auth/me` | Returns the logged-in user, or 401. |

The only user fields that ever leave the server are `id`, `first_name`, `last_name`, and `email`. No endpoint returns a password or a password hash.

### What's stored for a user

A new account adds one row to `users`:

| Field | Value |
|---|---|
| `first_name`, `last_name` | As typed (trimmed). |
| `name` | `first_name + " " + last_name` (the table requires it). |
| `email` | Trimmed and lower-cased; unique. |
| `password_hash` | `pbkdf2_sha256$<salt>$<digest>` (see below). The plain password is never stored. |
| `created_at` | Set by the database. |

### How passwords are protected

- **Same method as the existing data:** PBKDF2-HMAC-SHA256, 120,000 iterations, hex digest, stored as `pbkdf2_sha256$<salt>$<digest>`. The seed users and new users use one format, so both can log in.
- **Library:** Python's standard `hashlib.pbkdf2_hmac` (OpenSSL-backed) for hashing and `secrets` for randomness.
- **Unique salt per password:** 8 random bytes (16 hex characters) from `secrets.token_hex`, so two people with the same password get different hashes.
- **Constant-time comparison** with `hmac.compare_digest`.
- **Never stored or logged in plain text.** The server log only shows the method, path, and status code. FastAPI's default validation error (which echoes the request body) is replaced with a generic message so a password can't bounce back.
- **Same work for wrong email and wrong password:** if the email doesn't exist, the server still checks the password against a dummy hash, so response time doesn't reveal which emails have accounts.
- **Known trade-off:** 120,000 iterations is below today's OWASP advice (600,000 for PBKDF2-SHA256). We kept it so seed accounts keep working. A future upgrade could re-hash with more iterations on the next successful login (this needs the iteration count added to the stored format).

### How sessions work

- After a successful login or sign-up, the server puts only the user's `id` into a **signed session cookie** called `cc_session` (Starlette `SessionMiddleware`, signed with `itsdangerous`).
- The cookie is **`HttpOnly`** (JavaScript can't read it) and **`SameSite=Lax`**, and it lasts 7 days. Set `COOKIE_SECURE=true` in production so it's only sent over HTTPS.
- No token is ever put in `localStorage`. Staying logged in after a refresh works because the browser re-sends the cookie and the app calls `/api/auth/me`.
- A tampered cookie fails the signature check and is treated as logged out.
- The signing secret is `SESSION_SECRET` in `backend/.env` (random, never committed). `backend/.env.example` has a placeholder only. The server refuses to start if the secret is missing, too short, or still the placeholder.

### Attack protections

| Threat | Protection |
|---|---|
| Password guessing | Failed logins are limited to **5 per email** and **20 per IP address** in a 15-minute window. Further attempts get `429 Too Many Requests` with a `Retry-After` header, even if the password is right. Counters are in memory and reset when the server restarts. |
| Finding out which emails exist (login) | Wrong email and wrong password both return `401` with the same message: "Invalid email or password." |
| SQL injection | Every query uses `?` placeholders; no SQL is built from user input. |
| Bad input | The server checks everything again, whatever the browser did: a valid email format (max 254 characters), a password of 8–128 characters, the two passwords matching, and first and last names of 1–50 characters using letters, spaces, hyphens, apostrophes, and periods only. |
| Cross-site requests (CSRF) | `SameSite=Lax` cookie; CORS allows credentials only for the Vite dev server (`http://localhost:5173`, `http://127.0.0.1:5173`); every `POST` must be `application/json`, and a request from any other `Origin` is rejected with `403`. |
| Over-reaching database access | Products use a **read-only** connection (`mode=ro`). Auth uses a separate connection with an SQLite authorizer that only allows reading from and inserting into `users`. Any statement touching `chat_messages`, `catalogue`, or `inventory`, and any `UPDATE`, `DELETE`, or `DROP`, is refused before it runs. |
| Leaking secrets | Responses never include `password_hash`. `.env`, `data/`, and `*.db` are in `.gitignore`. |
