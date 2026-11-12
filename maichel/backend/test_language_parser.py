import unittest

from language_parser import LanguageParser


class LanguageParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = LanguageParser()

    def test_unknown_text_is_routed_to_chat_not_a_command(self):
        result = self.parser.parse_command("tell me a joke")

        self.assertEqual(result["intent"], "chat")
        self.assertEqual(result["entities"], {})

    def test_known_local_command_still_routes_to_control(self):
        result = self.parser.parse_command("open chrome")

        self.assertEqual(result["intent"], "app_open")
        self.assertEqual(result["entities"]["app"], "chrome")

    def test_thai_wake_word_is_removed(self):
        result = self.parser.parse_command("ลิซ่า tell me a joke")

        self.assertEqual(result["intent"], "chat")
        self.assertEqual(result["original_text"], "tell me a joke")

    def test_control_responses_are_localized_in_thai(self):
        response = self.parser.get_response_message(
            "app_open", {"app": "chrome"}, language="thai"
        )

        self.assertEqual(response, "กำลังเปิดแอปที่เลือกค่ะ")

    def test_thai_app_and_volume_commands_are_recognized(self):
        open_result = self.parser.parse_command("ลิซ่า เปิด โครม")
        mute_result = self.parser.parse_command("ลิซ่า ปิดเสียง")

        self.assertEqual(open_result["intent"], "app_open")
        self.assertEqual(open_result["entities"]["app"], "chrome")
        self.assertEqual(mute_result["intent"], "volume")
        self.assertEqual(mute_result["entities"]["direction"], "mute")

    def test_thai_system_health_commands_are_recognized(self):
        result = self.parser.parse_command("ลิซ่า เช็คสเปกคอม")

        self.assertEqual(result["intent"], "system_check")
        self.assertEqual(result["entities"], {})

    def test_skills_command_routes_to_chat(self):
        result = self.parser.parse_command("/skills")

        self.assertEqual(result["intent"], "chat")


if __name__ == "__main__":
    unittest.main()
