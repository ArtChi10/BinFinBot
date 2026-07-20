from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from collections.abc import Mapping

from src.market.universes import (
    PAIR_UNIVERSE_LABELS,
    POPULAR_30_USDT_PAIRS,
    pair_universe_label,
)


SETTINGS_MENU_CALLBACK = "settings:menu"
PAIR_UNIVERSE_MENU_CALLBACK = "settings:pairs"
POPULAR_PAIR_SELECTIONS_CALLBACK = "settings:popular_pairs"
POPULAR_PAIR_SELECT_ALL_CALLBACK = "settings:popular_pairs:all"
POPULAR_PAIR_CLEAR_ALL_CALLBACK = "settings:popular_pairs:none"
TIMEFRAME_MENU_CALLBACK = "settings:timeframe"
RSI_MENU_CALLBACK = "settings:rsi"
VOLUME_MENU_CALLBACK = "settings:volume"
NOTIFICATIONS_TOGGLE_CALLBACK = "settings:notifications"

PAIR_UNIVERSE_VALUE_PREFIX = "settings:pairs:"
POPULAR_PAIR_VALUE_PREFIX = "settings:popular_pair:"
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


def pair_universe_keyboard(selected_popular_pairs_count: int) -> InlineKeyboardMarkup:
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
        + [
            [
                InlineKeyboardButton(
                    text=f"Настроить популярные 30 ({selected_popular_pairs_count}/30)",
                    callback_data=POPULAR_PAIR_SELECTIONS_CALLBACK,
                )
            ]
        ]
        + [_back_row()],
    )


def popular_pairs_keyboard(
    selections: Mapping[str, bool],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pairs = list(POPULAR_30_USDT_PAIRS)

    for index in range(0, len(pairs), 2):
        row = []
        for symbol in pairs[index : index + 2]:
            base_asset = symbol.split("/", maxsplit=1)[0]
            marker = "[x]" if selections.get(symbol, False) else "[ ]"
            row.append(
                InlineKeyboardButton(
                    text=f"{marker} {base_asset}",
                    callback_data=f"{POPULAR_PAIR_VALUE_PREFIX}{base_asset}",
                )
            )
        rows.append(row)

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="Выбрать все",
                    callback_data=POPULAR_PAIR_SELECT_ALL_CALLBACK,
                ),
                InlineKeyboardButton(
                    text="Снять все",
                    callback_data=POPULAR_PAIR_CLEAR_ALL_CALLBACK,
                ),
            ],
            _back_row(callback_data=PAIR_UNIVERSE_MENU_CALLBACK),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def popular_pair_symbol_from_callback_value(value: str) -> str:
    symbol = f"{value}/USDT"
    if symbol not in POPULAR_30_USDT_PAIRS:
        raise ValueError(f"Unknown popular pair callback value: {value}.")
    return symbol


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


def _back_row(
    callback_data: str = SETTINGS_MENU_CALLBACK,
) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text="Назад",
            callback_data=callback_data,
        )
    ]
