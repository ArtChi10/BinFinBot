import unittest

from src.bot.keyboards import (
    MAIN_MENU_HELP_TEXT,
    MAIN_MENU_SETTINGS_TEXT,
    MAIN_MENU_STATUS_TEXT,
    bot_commands,
    main_menu_keyboard,
)


class KeyboardTests(unittest.TestCase):
    def test_main_menu_keyboard_contains_primary_actions(self) -> None:
        keyboard = main_menu_keyboard()
        button_texts = [
            button.text
            for row in keyboard.keyboard
            for button in row
        ]

        self.assertEqual(
            button_texts,
            [
                MAIN_MENU_SETTINGS_TEXT,
                MAIN_MENU_STATUS_TEXT,
                MAIN_MENU_HELP_TEXT,
            ],
        )

    def test_bot_commands_contains_menu_commands(self) -> None:
        commands = [command.command for command in bot_commands()]

        self.assertEqual(commands, ["menu", "settings", "status", "help"])


if __name__ == "__main__":
    unittest.main()
