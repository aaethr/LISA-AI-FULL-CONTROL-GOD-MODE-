# LISA Incremental Integration Plan

- Backend: `maichel/backend/main.py`; run `python main.py` or `uvicorn main:app --host 127.0.0.1 --port 8000`; health `GET /api/v1/status`.
- Frontend: `maichel`; static files served by FastAPI. Build: no build step. API seam: `maichel/app.js` uses `/api/v1`; mutation calls use preview/approve/execute.
- API: status, assistant, skills, memory GET/search, action preview/approve/execute, read-only system report/history, legacy control blocked.
- Database: SQLite in `%LOCALAPPDATA%\LISA\lisa-memory.sqlite3`; stdlib sqlite3; no migrations/seed data.
- Environment: `LISA_OLLAMA_BASE_URL` loopback only and `LISA_AI_MODEL`.
- Preserve: existing read-only health dashboard and voice UI; no mock-state switcher or mock data files.
- No unrelated deploy, commit, seed, or remote provider configuration.
