from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from .database import (
    UserSettings,
    ensure_user_settings,
    format_user_settings,
    get_user_popular_pair_selections,
    get_user_settings,
    set_all_user_popular_pair_selections,
    toggle_user_notifications,
    toggle_user_popular_pair_selection,
    update_user_pair_universe,
    update_user_rsi_range,
    update_user_timeframe,
    update_user_volume_change_percent,
)
from .keyboards import (
    NOTIFICATIONS_TOGGLE_CALLBACK,
    PAIR_UNIVERSE_MENU_CALLBACK,
    PAIR_UNIVERSE_VALUE_PREFIX,
    POPULAR_PAIR_CLEAR_ALL_CALLBACK,
    POPULAR_PAIR_SELECTIONS_CALLBACK,
    POPULAR_PAIR_SELECT_ALL_CALLBACK,
    POPULAR_PAIR_VALUE_PREFIX,
    RSI_MENU_CALLBACK,
    RSI_RANGE_OPTIONS,
    RSI_VALUE_PREFIX,
    SETTINGS_MENU_CALLBACK,
    TIMEFRAME_MENU_CALLBACK,
    TIMEFRAME_OPTIONS,
    TIMEFRAME_VALUE_PREFIX,
    VOLUME_MENU_CALLBACK,
    VOLUME_THRESHOLD_OPTIONS,
    VOLUME_VALUE_PREFIX,
    pair_universe_keyboard,
    popular_pair_symbol_from_callback_value,
    popular_pairs_keyboard,
    rsi_keyboard,
    settings_keyboard,
    timeframe_keyboard,
    volume_keyboard,
)
from src.market.universes import PAIR_UNIVERSE_OPTIONS, PAIR_UNIVERSE_POPULAR_30


router = Router()


def _settings_keyboard(settings: UserSettings):
    return settings_keyboard(
        pair_universe=settings.pair_universe,
        timeframe=settings.timeframe,
        rsi_min=settings.rsi_min,
        rsi_max=settings.rsi_max,
        volume_change_percent=settings.volume_change_percent,
        notifications_enabled=settings.notifications_enabled,
    )


async def _show_settings_message(message: Message, settings: UserSettings) -> None:
    await message.answer(
        format_user_settings(settings),
        reply_markup=_settings_keyboard(settings),
    )


async def _edit_settings_message(
    callback: CallbackQuery,
    settings: UserSettings,
    reply_markup,
) -> None:
    if callback.message is None:
        await callback.answer("Настройки обновлены.")
        return

    await callback.message.edit_text(
        format_user_settings(settings),
        reply_markup=reply_markup,
    )
    await callback.answer()


async def _edit_pair_universe_message(
    callback: CallbackQuery,
    database_path: str,
    settings: UserSettings,
) -> None:
    selections = await get_user_popular_pair_selections(
        database_path,
        callback.from_user.id,
    )
    selected_count = sum(selections.values())
    await _edit_settings_message(
        callback,
        settings,
        pair_universe_keyboard(selected_popular_pairs_count=selected_count),
    )


async def _edit_popular_pairs_message(
    callback: CallbackQuery,
    settings: UserSettings,
    selections: dict[str, bool],
) -> None:
    selected_count = sum(selections.values())
    text = (
        f"{format_user_settings(settings)}\n\n"
        f"Популярные пары: выбрано {selected_count}/30\n"
        "Отметьте пары, которые нужно мониторить."
    )

    if callback.message is None:
        await callback.answer("Настройки обновлены.")
        return

    await callback.message.edit_text(
        text,
        reply_markup=popular_pairs_keyboard(selections),
    )
    await callback.answer()


@router.message(CommandStart())
async def handle_start(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    settings = await ensure_user_settings(database_path, message.from_user.id)
    await message.answer(
        "Привет! Я помогу подготовить криптовалютный скринер.\n\n"
        f"{format_user_settings(settings)}",
        reply_markup=_settings_keyboard(settings),
    )


@router.message(Command("settings"))
async def handle_settings(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    settings = await get_user_settings(database_path, message.from_user.id)
    if settings is None:
        settings = await ensure_user_settings(database_path, message.from_user.id)

    await _show_settings_message(message, settings)


@router.callback_query(F.data == SETTINGS_MENU_CALLBACK)
async def handle_settings_menu(callback: CallbackQuery, database_path: str) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    await _edit_settings_message(callback, settings, _settings_keyboard(settings))


@router.callback_query(F.data == PAIR_UNIVERSE_MENU_CALLBACK)
async def handle_pair_universe_menu(callback: CallbackQuery, database_path: str) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    await _edit_pair_universe_message(callback, database_path, settings)


@router.callback_query(F.data.startswith(PAIR_UNIVERSE_VALUE_PREFIX))
async def handle_pair_universe_selection(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    pair_universe = callback.data.removeprefix(PAIR_UNIVERSE_VALUE_PREFIX)
    if pair_universe not in PAIR_UNIVERSE_OPTIONS:
        await callback.answer("Неизвестный список пар.", show_alert=True)
        return

    settings = await update_user_pair_universe(
        database_path,
        callback.from_user.id,
        pair_universe,
    )

    if pair_universe == PAIR_UNIVERSE_POPULAR_30:
        selections = await get_user_popular_pair_selections(
            database_path,
            callback.from_user.id,
        )
        await _edit_popular_pairs_message(callback, settings, selections)
        return

    await _edit_settings_message(callback, settings, _settings_keyboard(settings))


@router.callback_query(F.data == POPULAR_PAIR_SELECTIONS_CALLBACK)
async def handle_popular_pair_selections(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    selections = await get_user_popular_pair_selections(
        database_path,
        callback.from_user.id,
    )
    await _edit_popular_pairs_message(callback, settings, selections)


@router.callback_query(F.data.startswith(POPULAR_PAIR_VALUE_PREFIX))
async def handle_popular_pair_toggle(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    pair_value = callback.data.removeprefix(POPULAR_PAIR_VALUE_PREFIX)
    try:
        symbol = popular_pair_symbol_from_callback_value(pair_value)
    except ValueError:
        await callback.answer("Неизвестная пара.", show_alert=True)
        return

    settings = await ensure_user_settings(database_path, callback.from_user.id)
    selections = await toggle_user_popular_pair_selection(
        database_path,
        callback.from_user.id,
        symbol,
    )
    await _edit_popular_pairs_message(callback, settings, selections)


@router.callback_query(F.data == POPULAR_PAIR_SELECT_ALL_CALLBACK)
async def handle_popular_pair_select_all(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    selections = await set_all_user_popular_pair_selections(
        database_path,
        callback.from_user.id,
        selected=True,
    )
    await _edit_popular_pairs_message(callback, settings, selections)


@router.callback_query(F.data == POPULAR_PAIR_CLEAR_ALL_CALLBACK)
async def handle_popular_pair_clear_all(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    selections = await set_all_user_popular_pair_selections(
        database_path,
        callback.from_user.id,
        selected=False,
    )
    await _edit_popular_pairs_message(callback, settings, selections)


@router.callback_query(F.data == TIMEFRAME_MENU_CALLBACK)
async def handle_timeframe_menu(callback: CallbackQuery, database_path: str) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    await _edit_settings_message(callback, settings, timeframe_keyboard())


@router.callback_query(F.data.startswith(TIMEFRAME_VALUE_PREFIX))
async def handle_timeframe_selection(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    timeframe = callback.data.removeprefix(TIMEFRAME_VALUE_PREFIX)
    if timeframe not in TIMEFRAME_OPTIONS:
        await callback.answer("Неизвестный таймфрейм.", show_alert=True)
        return

    settings = await update_user_timeframe(
        database_path,
        callback.from_user.id,
        timeframe,
    )
    await _edit_settings_message(callback, settings, _settings_keyboard(settings))


@router.callback_query(F.data == RSI_MENU_CALLBACK)
async def handle_rsi_menu(callback: CallbackQuery, database_path: str) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    await _edit_settings_message(callback, settings, rsi_keyboard())


@router.callback_query(F.data.startswith(RSI_VALUE_PREFIX))
async def handle_rsi_selection(callback: CallbackQuery, database_path: str) -> None:
    rsi_value = callback.data.removeprefix(RSI_VALUE_PREFIX)
    try:
        rsi_min_text, rsi_max_text = rsi_value.split(":", maxsplit=1)
        rsi_min = int(rsi_min_text)
        rsi_max = int(rsi_max_text)
    except ValueError:
        await callback.answer("Неизвестный диапазон RSI.", show_alert=True)
        return

    if (rsi_min, rsi_max) not in RSI_RANGE_OPTIONS:
        await callback.answer("Неизвестный диапазон RSI.", show_alert=True)
        return

    settings = await update_user_rsi_range(
        database_path,
        callback.from_user.id,
        rsi_min,
        rsi_max,
    )
    await _edit_settings_message(callback, settings, _settings_keyboard(settings))


@router.callback_query(F.data == VOLUME_MENU_CALLBACK)
async def handle_volume_menu(callback: CallbackQuery, database_path: str) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    await _edit_settings_message(callback, settings, volume_keyboard())


@router.callback_query(F.data.startswith(VOLUME_VALUE_PREFIX))
async def handle_volume_selection(callback: CallbackQuery, database_path: str) -> None:
    volume_value = callback.data.removeprefix(VOLUME_VALUE_PREFIX)
    try:
        volume_change_percent = float(volume_value)
    except ValueError:
        await callback.answer("Неизвестный порог объема.", show_alert=True)
        return

    if volume_change_percent not in VOLUME_THRESHOLD_OPTIONS:
        await callback.answer("Неизвестный порог объема.", show_alert=True)
        return

    settings = await update_user_volume_change_percent(
        database_path,
        callback.from_user.id,
        volume_change_percent,
    )
    await _edit_settings_message(callback, settings, _settings_keyboard(settings))


@router.callback_query(F.data == NOTIFICATIONS_TOGGLE_CALLBACK)
async def handle_notifications_toggle(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await toggle_user_notifications(database_path, callback.from_user.id)
    await _edit_settings_message(callback, settings, _settings_keyboard(settings))


@router.callback_query()
async def handle_unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer("Неизвестное действие.", show_alert=True)
