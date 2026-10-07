# AI Prompts Log

A log of the prompts I typed to Claude Code while working on this homework, kept exactly as typed.

---

## Problem 1 - Vibe coder prompts

**Prompt:**

```text
Problem 1: Vibe coder prompts.
Make a file called `AI_prompts.md` in the project root. It's a log of what I type to you while I work on this homework, so keep my prompts exactly as I type them.
The homework has 13 problems. Give each problem its own section with:

* the problem number and title
* the prompt I typed
* a follow-up prompt, only if I needed one, plus one sentence on what was missing after the first try

Add a new section every time I start a new problem, so the file keeps growing.
Log this prompt as "Problem 1 - Vibe coder prompts." Then make a git commit named "Problem 1 - Vibe coder prompts."
```

**Follow-up prompt:** None needed.

---

## Problem 2 - Analyze the database

**Prompt:**

```text
Problem 2: Analyze the database.
Unzip `data.zip` so I have `data/campus_customs.db` and `data/products/`. Then look inside the database in read-only mode. Don't change anything in it.
For every table (at least `catalogue`, `inventory`, and `users`), check:

* the field names and types
* the primary keys and how the tables connect (like which field links inventory to catalogue)
* how many rows each table has
* a few example rows from `catalogue` and `inventory`

Create `output/harness.md`. For each table, write the table name, then each field, then one short line on why that field matters for the shop or the chatbot. Keep it simple. I'll keep adding to this file in later problems (models, tools, safety, specs).
Safety rule: this file goes on a public GitHub repo. In `users`, only describe the fields. Don't copy any real email, name, or password hash into the file or show them to me.
Log this prompt in `AI_prompts.md` as "Problem 2 - Analyze the database." Then make a git commit named "Problem 2 - Analyze the database." Don't commit `data/` or any `.db` file.
```

**Follow-up prompt:** None needed.

---

## Problem 3 - Build the campus customs website

**Prompt:**

```text
Problem 3: Build the Campus Customs website.
Build a React + Vite + TypeScript front end in a `frontend/` folder, plus a small FastAPI app in `backend/main.py`. The backend only serves products and images for now. I'll grow it into the agent backend in Problem 5.
Website

* A nav bar at the top with links to: Home, Products, About Us, Log in, Create account.
* Home and About Us: write them in your own words. The shop sells official Yale merch to students, alumni, and fans. The tone is warm, proud, and punchy, with short headings. Use Yale navy blue as the main color. Don't copy text from any real website.
* Log in and Create account: simple forms that look good. They don't need to work yet.
* Products page: a grid of cards from the catalogue, each with the image, name, price, and a short description. Use the real image paths from the database.
* Clicking a card opens a single-item page. Put the big image on one side and the full text on the other: description, price, and the sizes with stock for each size. Show sold-out sizes as sold out.
* A floating chat button in the bottom right that opens a chat panel. It's a stub for now: the user types, and it shows a placeholder reply from one function. That function will call my backend later.

Backend (read-only)

* `GET /api/products`, `GET /api/products/{id}` (with sizes and stock), and an images endpoint that serves files from `data/products/` only.
* Open the database in read-only mode.
* Don't expose the `users` or `chat_messages` tables anywhere. No password hashes, ever.
* Block path tricks like `../` in the images endpoint.
* Add a `backend/requirements.txt`. Allow requests from the Vite dev server.

Git

* Don't commit `data/`, any `.db` file, or `node_modules/`.
* Log this prompt in `AI_prompts.md` as "Problem 3 - Build the campus customs website."
* Commit it as "Problem 3 - Build the campus customs website."
```

**Follow-up prompt:** None needed.
