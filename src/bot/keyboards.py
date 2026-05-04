from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Timeframe",
                    callback_data="settings:timeframe",
                ),
                InlineKeyboardButton(
                    text="RSI",
                    callback_data="settings:rsi",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Volume",
                    callback_data="settings:volume",
                ),
                InlineKeyboardButton(
                    text="Notifications",
                    callback_data="settings:notifications",
                ),
            ],
        ],
    )
