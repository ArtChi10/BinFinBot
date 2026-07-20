from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.market.universes import PAIR_UNIVERSE_LABELS, pair_universe_label


SETTINGS_MENU_CALLBACK = "settings:menu"
PAIR_UNIVERSE_MENU_CALLBACK = "settings:pairs"
TIMEFRAME_MENU_CALLBACK = "settings:timeframe"
RSI_MENU_CALLBACK = "settings:rsi"
VOLUME_MENU_CALLBACK = "settings:volume"
NOTIFICATIONS_TOGGLE_CALLBACK = "settings:notifications"

PAIR_UNIVERSE_VALUE_PREFIX = "settings:pairs:"
TIMEFRAME_VALUE_PREFIX = "settings:timeframe:"
RSI_VALUE_PREFIX = "settings:rsi:"
VOLUME_VALUE_PREFIX = "settings:volume:"

TIMEFRAME_OPTIONS = ("5m", "15m", "30m")
RSI_RANGE_OPTIONS = (
    (30, 50),
    (40, 60),
    (50, 70),
    (60, 80),
    (70, 90),
)
VOLUME_THRESHOLD_OPTIONS = (0.1, 0.25, 0.5, 1, 3, 5, 10)


def settings_keyboard(
    pair_universe: str,
    timeframe: str,
    rsi_min: int,
    rsi_max: int,
    volume_change_percent: float,
    notifications_enabled: bool,
) -> InlineKeyboardMarkup:
    notifications = "ON" if notifications_enabled else "OFF"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Пары: {pair_universe_label(pair_universe)}",
                    callback_data=PAIR_UNIVERSE_MENU_CALLBACK,
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"Таймфрейм: {timeframe}",
                    callback_data="settings:timeframe",
                ),
                InlineKeyboardButton(
                    text=f"RSI: {rsi_min}–{rsi_max}",
                    callback_data="settings:rsi",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"Объем: {volume_change_percent:g}%",
                    callback_data="settings:volume",
                ),
                InlineKeyboardButton(
                    text=f"Уведомления: {notifications}",
                    callback_data="settings:notifications",
                ),
            ],
        ],
    )


def pair_universe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{PAIR_UNIVERSE_VALUE_PREFIX}{pair_universe}",
                )
            ]
            for pair_universe, label in PAIR_UNIVERSE_LABELS.items()
        ]
        + [_back_row()],
    )


def timeframe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=timeframe,
                    callback_data=f"{TIMEFRAME_VALUE_PREFIX}{timeframe}",
                )
            ]
            for timeframe in TIMEFRAME_OPTIONS
        ]
        + [_back_row()],
    )


def rsi_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{rsi_min}–{rsi_max}",
                    callback_data=f"{RSI_VALUE_PREFIX}{rsi_min}:{rsi_max}",
                )
            ]
            for rsi_min, rsi_max in RSI_RANGE_OPTIONS
        ]
        + [_back_row()],
    )


def volume_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{threshold:g}%",
                    callback_data=f"{VOLUME_VALUE_PREFIX}{threshold:g}",
                )
            ]
            for threshold in VOLUME_THRESHOLD_OPTIONS
        ]
        + [_back_row()],
    )


def _back_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text="Назад",
            callback_data=SETTINGS_MENU_CALLBACK,
        )
    ]
