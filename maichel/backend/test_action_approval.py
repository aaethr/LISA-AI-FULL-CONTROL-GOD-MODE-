import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main


class FakeMemory:
    def __init__(self):
        self.saved = []

    def get(self, memory_id):
        return {"id": memory_id, "text": "Existing note"}

    def create(self, text):
        self.saved.append(text)


class ActionApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        main.action_previews.clear()

    async def test_unapproved_action_cannot_execute(self):
        preview = await main.preview_action(
            main.ActionPreview(
                action="memory_create", params={"text": "A private note"}
            )
        )

        with self.assertRaises(HTTPException) as raised:
            await main.execute_action(main.ActionApproval(preview_id=preview["preview_id"]))

        self.assertEqual(raised.exception.status_code, 403)

    async def test_approved_action_executes_once(self):
        memory = FakeMemory()
        with patch.object(main.assistant_router, "memory", memory):
            preview = await main.preview_action(
                main.ActionPreview(
                    action="memory_create", params={"text": "A private note"}
                )
            )
            approval = main.ActionApproval(preview_id=preview["preview_id"])

            await main.approve_action(approval)
            result = await main.execute_action(approval)

            self.assertEqual(result["status"], "success")
            self.assertEqual(memory.saved, ["A private note"])
            with self.assertRaises(HTTPException) as raised:
                await main.execute_action(approval)

        self.assertEqual(raised.exception.status_code, 409)

    async def test_arbitrary_terminal_action_is_not_previewable(self):
        with self.assertRaises(HTTPException) as raised:
            await main.preview_action(
                main.ActionPreview(action="terminal", params={"command": "whoami"})
            )

        self.assertEqual(raised.exception.status_code, 400)

    async def test_boolean_memory_id_is_rejected(self):
        with patch.object(main.assistant_router, "memory", FakeMemory()):
            with self.assertRaises(HTTPException) as raised:
                await main.preview_action(
                    main.ActionPreview(
                        action="memory_delete", params={"id": True}
                    )
                )

        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
