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
