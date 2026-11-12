import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


SYSTEM_PROMPT = (
    "You are LISA, a helpful local personal assistant. Reply in the user's language. "
    "You cannot control the computer or claim to have performed actions. "
    "Memory is only supplied by the user. Do not invent saved information."
)


class AssistantConfigurationError(RuntimeError):
    pass


class AssistantProviderError(RuntimeError):
    pass


class Brain:
    def __init__(self, opener=urlopen):
        self._opener = opener

    @staticmethod
    def configured_base_url() -> str:
        base = os.environ.get("LISA_OLLAMA_BASE_URL", "").strip()
        if not base:
            raise AssistantConfigurationError(
                "ตั้งค่า LISA_OLLAMA_BASE_URL เป็น local Ollama endpoint เช่น http://127.0.0.1:11434"
            )
        try:
            parsed = urlparse(base)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as error:
            raise AssistantConfigurationError(
                "LISA_OLLAMA_BASE_URL must be a valid local HTTP URL."
            ) from error
        if (
            parsed.scheme != "http"
            or hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise AssistantConfigurationError(
                "Only loopback local endpoints are allowed. Remote Ollama endpoints are disabled."
            )
        return base.rstrip("/")

    def respond(
        self,
        message: str,
        memory_context: Optional[List[str]] = None,
        history: Optional[List[dict]] = None,
    ) -> str:
        content = message.strip()
        if not content:
            raise ValueError("Message cannot be empty.")
        if len(content) > 8000:
            raise ValueError("Message is too long; limit it to 8000 characters.")
        model = os.environ.get("LISA_AI_MODEL", "").strip()
        if not model:
            raise AssistantConfigurationError(
                "Set LISA_AI_MODEL to a model installed in the local Ollama instance."
            )
        base = self.configured_base_url()
        system = SYSTEM_PROMPT
        if memory_context:
            system += "\n\nUser-approved memory only:\n" + "\n".join(memory_context)

        messages = [{"role": "system", "content": system}]
        for turn in (history or [])[-10:]:
            if (
                isinstance(turn, dict)
                and turn.get("role") in {"user", "assistant"}
                and isinstance(turn.get("content"), str)
            ):
                messages.append(
                    {"role": turn["role"], "content": turn["content"][:8000]}
                )
        messages.append({"role": "user", "content": content})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        request = Request(
            base + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            raise AssistantProviderError(
                f"Local Ollama returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise AssistantProviderError(
                f"Could not reach the configured local Ollama endpoint: {error.reason}"
            ) from error
        except TimeoutError as error:
            raise AssistantProviderError("The local Ollama request timed out.") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise AssistantProviderError("Local Ollama returned an invalid response.") from error

        message_result = result.get("message") if isinstance(result, dict) else None
        answer = message_result.get("content") if isinstance(message_result, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise AssistantProviderError("Local Ollama returned no text response.")
        return answer.strip()


class SQLiteMemory:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            appdata = (
                os.environ.get("LOCALAPPDATA")
                or os.environ.get("APPDATA")
                or os.path.join(os.path.expanduser("~"), "AppData", "Local")
            )
            directory = os.path.join(appdata, "LISA")
            os.makedirs(directory, exist_ok=True)
            self.db_path = os.path.join(directory, "lisa-memory.sqlite3")
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS memories ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "text TEXT NOT NULL UNIQUE, "
                "created_at TEXT NOT NULL, "
                "updated_at TEXT NOT NULL)"
            )

    def list(self, limit: int = 100):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, text, created_at, updated_at FROM memories "
                "ORDER BY updated_at DESC LIMIT ?", (max(1, min(limit, 500)),)
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, limit: int = 5):
        term = query.strip().casefold()
        if not term:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT text FROM memories WHERE lower(text) LIKE ? "
                "ORDER BY updated_at DESC LIMIT ?",
                ("%" + term + "%", max(1, min(limit, 20))),
            ).fetchall()
        return [row["text"] for row in rows]

    def create(self, text: str):
        note = text.strip()
        if not note:
            raise ValueError("A memory cannot be empty.")
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO memories(text, created_at, updated_at) "
                "VALUES (?, ?, ?)",
                (note, timestamp, timestamp),
            )
        if cursor.rowcount == 0:
            raise ValueError("That memory already exists.")
        return self.get(cursor.lastrowid)

    def get(self, memory_id: int):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, text, created_at, updated_at FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return dict(row) if row else None

    def update(self, memory_id: int, text: str):
        note = text.strip()
        if not note:
            raise ValueError("A memory cannot be empty.")
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE memories SET text=?, updated_at=? WHERE id=?",
                (note, timestamp, memory_id),
            )
        if cursor.rowcount == 0:
            raise KeyError("Memory not found.")

    def delete(self, memory_id: int):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT text FROM memories WHERE id=?", (memory_id,)
            ).fetchone()
            if not row:
                raise KeyError("Memory not found.")
            connection.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        return row["text"]


class AssistantRouter:
    def __init__(self, brain: Optional[Brain] = None, memory: Optional[SQLiteMemory] = None):
        self.brain = brain or Brain()
        self.memory = memory or SQLiteMemory()

    def respond(self, message: str, history: Optional[List[dict]] = None) -> str:
        content = message.strip()
        if not content:
            raise ValueError("Message cannot be empty.")
        if content.casefold() == "/skills":
            return "LISA lists reviewed Skills/Tools in the workspace panel."
        context = self.memory.search(content, limit=3)
        return self.brain.respond(content, context, history)


assistant_router = AssistantRouter()
