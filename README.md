# BizPilot AI

BizPilot AI is a guest business-advice chat app built with FastAPI. The browser UI is served by FastAPI from `/`; chat, saved ideas, business plans, research, competitors, and opportunity suggestions use backend API routes. Browser preferences and chat history stay in local storage. Provider credentials stay on the server.

## Run locally

From `C:\BizPilot` in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
notepad .env
pip install -r requirements.txt
uvicorn main:app --reload
```

Put provider credentials only in the local `.env` or deployment environment settings. `.env` and local database files are excluded by `.gitignore`; never commit a real key. Restart the backend after changing environment values.

Local app: <http://127.0.0.1:8000/>. Health: <http://127.0.0.1:8000/health>. API docs: <http://127.0.0.1:8000/docs>.

## Deploy on Render

Create a **Web Service** from this repository, choose the Python runtime, and set the root directory to the project root. Use:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

Add the environment variables in the Render service dashboard. Do not commit `.env` or paste credentials into source files. If using a Render PostgreSQL database, set `DATABASE_URL` to its internal database URL. Otherwise, the default SQLite database is local to the service filesystem and may not persist across redeploys.

The frontend uses relative API paths, so it works at the deployed service origin without a hardcoded local address. If the frontend is hosted on a separate domain, set `CORS_ORIGINS` to a comma-separated list of exact allowed origins, for example `https://your-frontend.example`. Same-origin deployment needs no additional CORS origin.

## Environment settings

All settings have defaults except provider credentials needed for those features.

| Variable | Purpose | Default |
| --- | --- | --- |
| `AI_API_KEY` | Backend AI provider credential | unset |
| `AI_API_BASE` | OpenAI-compatible chat completions base URL | `https://api.openai.com/v1` |
| `AI_MODEL` | Model name accepted by the configured API | `gpt-3.5-turbo` |
| `SEARCH_API_KEY` | Search provider credential (`TAVILY_API_KEY` and `SERPAPI_API_KEY` are also recognized) | unset |
| `SEARCH_API_BASE` | Search API base URL | `https://api.tavily.com` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./bizpilot.db` |
| `HOST` | Host used by `python main.py` | `0.0.0.0` |
| `PORT` | Server port; Render provides this value | `8000` locally |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | local loopback origins |
| `CHAT_RATE_LIMIT_PER_MINUTE` | Maximum `/chat` requests per client IP per window | `10` |
| `CHAT_RATE_WINDOW_SECONDS` | Chat rate-limit window length | `60` |

The app also recognizes `OPENAI_API_KEY` and `GEMINI_API_KEY` as AI-key aliases. Configure a provider-compatible base URL and model for those providers. Provider availability and pricing depend on the provider and account.

## Tests

Run the existing test suite from the project folder:

```powershell
python -m unittest discover -s tests
```
