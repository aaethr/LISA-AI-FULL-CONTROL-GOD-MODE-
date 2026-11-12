# LISA Local Assistant

LISA is a Windows-local, chat-first companion with Thai voice controls and an accessible text fallback. It preserves the existing read-only system-health dashboard.

## Safe local behavior

- AI chat uses only the configured loopback Ollama-compatible endpoint.
- No remote provider fallback, gateway, external channel, or notification service.
- API and browser integration are restricted to `127.0.0.1`/localhost.
- Arbitrary shell and unrestricted file operations are disabled.
- App open/close, settings, file, and memory mutations require a fresh preview and explicit approval.
- Memories are stored in a user-local SQLite database and are never inferred or persisted from chat automatically.
- Chat transcripts and microphone audio are not saved.
- Recent chat context is held in browser memory only and clears when the page is reloaded.

## Configuration

Set Windows environment variables and restart LISA:

```text
LISA_OLLAMA_BASE_URL=http://127.0.0.1:11434
LISA_AI_MODEL=<an Ollama model installed locally>
```

No API key is required for Ollama. The application rejects non-loopback base URLs.

Install Ollama, download a model such as Qwen 3 with `ollama pull qwen3`, and ensure Ollama is running before chatting.

## Run

```bat
cd maichel
install.bat
run_michael.bat
```

Open `http://127.0.0.1:8000/app`.

## Tests

From `maichel/backend`:

```bat
python -m unittest test_assistant_core.py test_action_approval.py test_language_parser.py test_system_monitor.py
```
