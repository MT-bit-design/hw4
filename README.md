# Campus Customs

An online shop for official Yale clothing with a built-in shopping assistant.
React + Vite + TypeScript front end, FastAPI + PydanticAI back end, SQLite data.

## What you need

- Python 3.10 or newer
- Node.js 20.19+ (or 22.12+)
- The course data pack (`data.zip`)
- A Portkey API key (for the chat assistant)

## 1. Add the data pack

Unzip `data.zip` into the project folder, so you have:

```
data/campus_customs.db
data/products/        (product images)
```

`data/` is in `.gitignore` and is never committed.

## 2. Create your settings file

The backend reads its settings from `backend/.env`. Copy the template there and fill it in:

```
copy .env.example backend\.env        (macOS/Linux: cp .env.example backend/.env)
```

In `backend/.env`, set:

- `SESSION_SECRET`: a long random value (at least 32 characters). To generate one:
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `PORTKEY_API_KEY`: your own Portkey key
- `CHAT_MODEL`: the model name (default `gpt-5.6-luna`)

`backend/.env` is in `.gitignore`. Never commit it.

## 3. Run the backend

From inside `backend/`:

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r ..\requirements.txt      (macOS/Linux: .venv/bin/pip install -r ../requirements.txt)
.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```

The API runs at http://localhost:8000.

## 4. Run the front end

In a second terminal, from inside `frontend/`:

```
cd frontend
npm install
npm run dev
```

## 5. Open the site

Go to **http://localhost:5173**. Browse products, create an account, and click the chat button in the bottom right to talk to the assistant.

## Project layout

```
AI_prompts.md       prompts used to build this project
requirements.txt    backend Python packages
.env.example        settings template (placeholders only)
frontend/           React + Vite + TypeScript site
backend/            FastAPI app: main.py, agent.py, models.py, tools.py, prompts/prompt.md, ...
output/             harness.md, design.md, usability.md, app_check.html (+ app_check_images/), audit_trail.json
```

See `output/harness.md` for how the whole system works.
