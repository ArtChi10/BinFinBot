import unittest

from src.bot.keyboards import (
    MAIN_MENU_HELP_TEXT,
    MAIN_MENU_SETTINGS_TEXT,
    MAIN_MENU_STATUS_TEXT,
    bot_commands,
    custom_pairs_keyboard,
    main_menu_keyboard,
    pair_universe_keyboard,
    timeframe_keyboard,
    timeframe_options_for_pair_universe,
)
from src.market.universes import (
    PAIR_UNIVERSE_CUSTOM,
    PAIR_UNIVERSE_POPULAR_30,
    PAIR_UNIVERSE_TOP_150,
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

        self.assertEqual(
            commands,
            ["menu", "settings", "status", "pairs", "addpair", "removepair", "help"],
        )

    def test_pair_universe_keyboard_marks_current_selection(self) -> None:
        keyboard = pair_universe_keyboard(
            selected_popular_pairs_count=12,
            custom_pairs_count=3,
            current_pair_universe=PAIR_UNIVERSE_POPULAR_30,
        )
        button_texts = [
            button.text
            for row in keyboard.inline_keyboard
            for button in row
        ]

        self.assertIn("Активно: Популярные 30", button_texts)
        self.assertIn("Выбрать: Топ-150 по объему", button_texts)
        self.assertIn("Выбрать: Мои пары", button_texts)
        self.assertIn("Настроить мои пары (3)", button_texts)

    def test_custom_pairs_keyboard_shows_active_state_and_remove_buttons(self) -> None:
        keyboard = custom_pairs_keyboard(
            ["BTC/USDC", "ETH/BTC"],
            active=True,
        )
        button_texts = [
            button.text
            for row in keyboard.inline_keyboard
            for button in row
        ]

        self.assertIn("Активно: Мои пары", button_texts)
        self.assertIn("Удалить BTC/USDC", button_texts)
        self.assertIn("Удалить ETH/BTC", button_texts)

    def test_timeframe_options_depend_on_pair_universe(self) -> None:
        self.assertEqual(
            timeframe_options_for_pair_universe(PAIR_UNIVERSE_TOP_150),
            ("5m", "15m", "30m"),
        )
        self.assertEqual(
            timeframe_options_for_pair_universe(PAIR_UNIVERSE_POPULAR_30),
            ("1m", "3m", "5m", "15m", "30m"),
        )
        self.assertEqual(
            timeframe_options_for_pair_universe(PAIR_UNIVERSE_CUSTOM),
            ("1m", "3m", "5m", "15m", "30m"),
        )

    def test_top_150_timeframe_keyboard_hides_fast_options(self) -> None:
        keyboard = timeframe_keyboard(PAIR_UNIVERSE_TOP_150)
        button_texts = [
            button.text
            for row in keyboard.inline_keyboard
            for button in row
        ]

        self.assertNotIn("1m", button_texts)
        self.assertNotIn("3m", button_texts)
        self.assertIn("5m", button_texts)


if __name__ == "__main__":
    unittest.main()
