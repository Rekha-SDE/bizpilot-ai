# BizPilot AI

BizPilot AI is a guest business-advice chat app built with FastAPI and a browser-based interface. Conversations and preferences are stored locally in the browser. Existing saved ideas and plans remain in the SQLite database and are imported into a read-only chat on first load.

## Run on Windows PowerShell

From the project folder (`C:\BizPilot`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
notepad .env
pip install -r requirements.txt
uvicorn main:app --reload
```

In `.env`, replace the example key with your provider's key. Do not put the key in frontend files, chat messages, screenshots, or Git. `.env` is excluded by `.gitignore`. Restart the server after changing `.env`.

Open <http://127.0.0.1:8000/>. The health endpoint is <http://127.0.0.1:8000/health>; API documentation is at <http://127.0.0.1:8000/docs>.

## AI provider configuration

The backend calls an OpenAI-compatible Chat Completions endpoint. The template uses these settings:

| Variable | Purpose | Default |
| --- | --- | --- |
| `AI_API_KEY` | Secret used by the backend for chat completions | Required for AI replies |
| `AI_API_BASE` | Base URL for the compatible API | `https://api.openai.com/v1` |
| `AI_MODEL` | Model identifier supported by that provider | `gpt-3.5-turbo` |

The backend also recognizes `OPENAI_API_KEY` and `GEMINI_API_KEY` as key aliases. A provider alias does not select its URL or guarantee endpoint compatibility; set `AI_API_BASE` and `AI_MODEL` to values supported by your provider. Provider access and pricing depend on that provider and account; this project does not promise a free tier.

## Existing functionality and data

- `/ideas`, `/plans`, `/market-research`, `/competitor-analysis`, and `/opportunity-suggestions` remain available.
- The chat's **Save idea** action uses the existing saved-ideas API.
- Existing database ideas and plans are copied into a local “Saved work · ideas & plans” chat for convenient reference; the original database records are retained.
- Guest preferences (`displayName`, `location`, `currency`, and `language`) use the existing `bizpilot-guest-preferences-v1` browser storage key and are sent with each chat request.
- Chat history uses `bizpilot-chat-history-v1` in browser local storage. It is guest-local and is not sent to the server as stored history; the current conversation is sent to the AI backend for each reply.

## Tests

Run the existing test suite from the project folder:

```powershell
python -m unittest discover -s tests
```
