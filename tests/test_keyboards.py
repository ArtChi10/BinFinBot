import unittest

from src.bot.keyboards import (
    MAIN_MENU_HELP_TEXT,
    MAIN_MENU_SETTINGS_TEXT,
    MAIN_MENU_STATUS_TEXT,
    bot_commands,
    main_menu_keyboard,
    pair_universe_keyboard,
)
from src.market.universes import PAIR_UNIVERSE_POPULAR_30


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

    def test_pair_universe_keyboard_marks_current_selection(self) -> None:
        keyboard = pair_universe_keyboard(
            selected_popular_pairs_count=12,
            current_pair_universe=PAIR_UNIVERSE_POPULAR_30,
        )
        button_texts = [
            button.text
            for row in keyboard.inline_keyboard
            for button in row
        ]

        self.assertIn("Активно: Популярные 30", button_texts)
        self.assertIn("Выбрать: Топ-150 по объему", button_texts)


if __name__ == "__main__":
    unittest.main()
