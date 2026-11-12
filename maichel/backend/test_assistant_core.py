import json
import os
import tempfile
import unittest
from unittest.mock import patch

from assistant_core import (
    AssistantConfigurationError,
    AssistantRouter,
    Brain,
    SQLiteMemory,
)


class FakeBrain:
    def __init__(self):
        self.message = None
        self.memory_context = None
        self.history = None

    def respond(self, message, memory_context=None, history=None):
        self.message = message
        self.memory_context = memory_context
        self.history = history
        return "test response"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class AssistantTests(unittest.TestCase):
    def test_memory_is_explicit_and_stored_in_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = SQLiteMemory(os.path.join(directory, "memory.sqlite3"))
            saved = memory.create("Mouse model is Attack Shark X11")

            self.assertEqual(saved["text"], "Mouse model is Attack Shark X11")
            self.assertIn("Mouse", memory.search("mouse")[0])
            memory.update(saved["id"], "Preferred mouse is Attack Shark X11")
            self.assertEqual(memory.get(saved["id"])["text"], "Preferred mouse is Attack Shark X11")
            deleted = memory.delete(saved["id"])
            self.assertEqual(deleted, "Preferred mouse is Attack Shark X11")
            self.assertEqual(memory.list(), [])

    def test_chat_can_use_reviewed_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = SQLiteMemory(os.path.join(directory, "memory.sqlite3"))
            memory.create("Preferred language is Thai")
            brain = FakeBrain()
            router = AssistantRouter(brain=brain, memory=memory)

            router.respond("What language do I prefer?")

            self.assertIn("Preferred language", "\n".join(brain.memory_context))

    def test_chat_can_use_recent_session_context_without_persisting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            brain = FakeBrain()
            memory = SQLiteMemory(os.path.join(directory, "memory.sqlite3"))
            router = AssistantRouter(brain=brain, memory=memory)

            router.respond("What was my previous question?", [
                {"role": "user", "content": "Remember the blue notebook"},
                {"role": "assistant", "content": "I will keep that in mind for this chat."},
            ])

            self.assertEqual(len(brain.history), 2)
            self.assertEqual(brain.history[0]["role"], "user")

    def test_missing_local_model_fails_before_network_request(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AssistantConfigurationError):
                Brain(opener=lambda *args, **kwargs: self.fail("unexpected network call")).respond(
                    "hello"
                )

    def test_remote_ollama_endpoint_is_rejected(self):
        environment = {
            "LISA_AI_MODEL": "test-model",
            "LISA_OLLAMA_BASE_URL": "https://example.com",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(AssistantConfigurationError):
                Brain(opener=lambda *args, **kwargs: self.fail("unexpected network call")).respond(
                    "hello"
                )

    def test_invalid_local_ollama_url_is_reported_as_configuration_error(self):
        environment = {
            "LISA_AI_MODEL": "test-model",
            "LISA_OLLAMA_BASE_URL": "http://[invalid",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(AssistantConfigurationError):
                Brain(opener=lambda *args, **kwargs: self.fail("unexpected network call")).respond(
                    "hello"
                )

    def test_ollama_chat_uses_loopback_config_and_local_format(self):
        calls = []

        def fake_opener(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(
                b'{"message":{"role":"assistant","content":"Hello locally"}}'
            )

        environment = {
            "LISA_AI_MODEL": "qwen:test",
            "LISA_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        }
        with patch.dict(os.environ, environment, clear=True):
            answer = Brain(opener=fake_opener).respond("hello")

        request, timeout = calls[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(answer, "Hello locally")
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(payload["model"], "qwen:test")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"][-1], {"role": "user", "content": "hello"})
        self.assertEqual(timeout, 30)

    def test_ollama_chat_includes_only_recent_valid_history(self):
        calls = []

        def fake_opener(request, timeout):
            calls.append(request)
            return FakeResponse(b'{"message":{"content":"Local response"}}')

        environment = {
            "LISA_AI_MODEL": "qwen:test",
            "LISA_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        }
        history = [
            {"role": "user", "content": f"message {index}"}
            for index in range(12)
        ]
        with patch.dict(os.environ, environment, clear=True):
            Brain(opener=fake_opener).respond("current", history=history)

        payload = json.loads(calls[0].data.decode("utf-8"))
        self.assertEqual(len(payload["messages"]), 12)
        self.assertEqual(payload["messages"][1]["content"], "message 2")
        self.assertEqual(payload["messages"][-1]["content"], "current")


if __name__ == "__main__":
    unittest.main()
