from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from .database import (
    UserSettings,
    add_user_custom_pair,
    clear_user_custom_pairs,
    ensure_user_settings,
    format_user_settings,
    get_user_custom_pairs,
    get_user_popular_pair_selections,
    get_user_settings,
    remove_user_custom_pair,
    set_all_user_popular_pair_selections,
    toggle_user_notifications,
    toggle_user_popular_pair_selection,
    update_user_pair_universe,
    update_user_rsi_range,
    update_user_timeframe,
    update_user_volume_change_percent,
)
from .keyboards import (
    MAIN_MENU_HELP_TEXT,
    MAIN_MENU_SETTINGS_TEXT,
    MAIN_MENU_STATUS_TEXT,
    CUSTOM_PAIR_REMOVE_PREFIX,
    CUSTOM_PAIRS_ACTIVATE_CALLBACK,
    CUSTOM_PAIRS_CALLBACK,
    CUSTOM_PAIRS_CLEAR_CALLBACK,
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
    TIMEFRAME_VALUE_PREFIX,
    VOLUME_MENU_CALLBACK,
    VOLUME_THRESHOLD_OPTIONS,
    VOLUME_VALUE_PREFIX,
    custom_pairs_keyboard,
    default_timeframe_for_pair_universe,
    main_menu_keyboard,
    pair_universe_keyboard,
    popular_pair_symbol_from_callback_value,
    popular_pairs_keyboard,
    rsi_keyboard,
    settings_keyboard,
    timeframe_keyboard,
    timeframe_options_for_pair_universe,
    volume_keyboard,
)
from src.market.universes import (
    PAIR_UNIVERSE_CUSTOM,
    PAIR_UNIVERSE_OPTIONS,
    PAIR_UNIVERSE_POPULAR_30,
    normalize_pair_symbol,
    pair_universe_label,
)


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


async def _show_main_menu(message: Message) -> None:
    await message.answer(
        "Главное меню открыто. Выберите действие кнопками ниже.",
        reply_markup=main_menu_keyboard(),
    )


async def _settings_for_message(message: Message, database_path: str) -> UserSettings | None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return None

    settings = await get_user_settings(database_path, message.from_user.id)
    if settings is None:
        settings = await ensure_user_settings(database_path, message.from_user.id)
    return settings


async def _show_status_message(message: Message, database_path: str) -> None:
    settings = await _settings_for_message(message, database_path)
    if settings is None:
        return

    selected_pairs_count = None
    if settings.pair_universe == PAIR_UNIVERSE_POPULAR_30:
        selections = await get_user_popular_pair_selections(
            database_path,
            settings.telegram_user_id,
        )
        selected_pairs_count = sum(selections.values())
    if settings.pair_universe == PAIR_UNIVERSE_CUSTOM:
        custom_pairs = await get_user_custom_pairs(
            database_path,
            settings.telegram_user_id,
        )
        selected_pairs_count = len(custom_pairs)

    await message.answer(_format_status_message(settings, selected_pairs_count))


async def _show_custom_pairs_message(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    settings = await _activate_custom_pair_universe(database_path, message.from_user.id)
    custom_pairs = await get_user_custom_pairs(database_path, message.from_user.id)
    await message.answer(
        _format_custom_pairs_menu_text(settings, custom_pairs),
        reply_markup=custom_pairs_keyboard(custom_pairs, active=True),
    )


async def _show_help_message(message: Message) -> None:
    await message.answer(
        "Как пользоваться\n\n"
        "Настройки — открыть параметры скринера и выбрать пары, таймфрейм, RSI, "
        "порог объема и уведомления.\n\n"
        "Статус — быстро посмотреть текущий режим мониторинга.\n\n"
        "Мои пары — список произвольных spot-пар Bybit, например ETH/BTC "
        "или BTC/USDC. Добавить: /addpair ETH/BTC. Удалить: /removepair ETH/BTC.\n\n"
        "Для проверки уведомлений можно временно выбрать Мои пары, 1m, объем 0.1% "
        "и широкий RSI-диапазон. Низкие пороги шумные и нужны только для теста.",
        reply_markup=main_menu_keyboard(),
    )


def _command_argument(message: Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


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
    custom_pairs = await get_user_custom_pairs(database_path, callback.from_user.id)
    selected_count = sum(selections.values())

    if callback.message is None:
        await callback.answer("Настройки обновлены.")
        return

    await callback.message.edit_text(
        _format_pair_universe_menu_text(
            settings,
            selected_popular_pairs_count=selected_count,
            custom_pairs_count=len(custom_pairs),
        ),
        reply_markup=pair_universe_keyboard(
            selected_popular_pairs_count=selected_count,
            custom_pairs_count=len(custom_pairs),
            current_pair_universe=settings.pair_universe,
        ),
    )
    await callback.answer()


async def _activate_popular_30_universe(
    database_path: str,
    telegram_user_id: int,
) -> UserSettings:
    settings = await ensure_user_settings(database_path, telegram_user_id)
    if settings.pair_universe == PAIR_UNIVERSE_POPULAR_30:
        return settings

    return await update_user_pair_universe(
        database_path,
        telegram_user_id,
        PAIR_UNIVERSE_POPULAR_30,
    )


async def _activate_custom_pair_universe(
    database_path: str,
    telegram_user_id: int,
) -> UserSettings:
    settings = await ensure_user_settings(database_path, telegram_user_id)
    if settings.pair_universe == PAIR_UNIVERSE_CUSTOM:
        return settings

    return await update_user_pair_universe(
        database_path,
        telegram_user_id,
        PAIR_UNIVERSE_CUSTOM,
    )


async def _update_pair_universe_with_safe_timeframe(
    database_path: str,
    telegram_user_id: int,
    pair_universe: str,
) -> UserSettings:
    settings = await update_user_pair_universe(
        database_path,
        telegram_user_id,
        pair_universe,
    )
    if settings.timeframe in timeframe_options_for_pair_universe(pair_universe):
        return settings

    return await update_user_timeframe(
        database_path,
        telegram_user_id,
        default_timeframe_for_pair_universe(pair_universe),
    )


async def _edit_popular_pairs_message(
    callback: CallbackQuery,
    settings: UserSettings,
    selections: dict[str, bool],
) -> None:
    selected_count = sum(selections.values())
    text = (
        f"{format_user_settings(settings)}\n\n"
        f"Список пар закреплен: {pair_universe_label(settings.pair_universe)}\n"
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


async def _edit_custom_pairs_message(
    callback: CallbackQuery,
    settings: UserSettings,
    custom_pairs: list[str],
) -> None:
    if callback.message is None:
        await callback.answer("Настройки обновлены.")
        return

    await callback.message.edit_text(
        _format_custom_pairs_menu_text(settings, custom_pairs),
        reply_markup=custom_pairs_keyboard(
            custom_pairs,
            active=settings.pair_universe == PAIR_UNIVERSE_CUSTOM,
        ),
    )
    await callback.answer()


def _format_pair_universe_menu_text(
    settings: UserSettings,
    selected_popular_pairs_count: int,
    custom_pairs_count: int,
) -> str:
    return (
        "Выбор списка пар\n\n"
        f"Сейчас закреплено: {pair_universe_label(settings.pair_universe)}\n"
        f"Популярные 30: выбрано {selected_popular_pairs_count}/30\n\n"
        f"Мои пары: добавлено {custom_pairs_count}\n\n"
        "Таймфреймы:\n"
        "- Топ-150: 5m, 15m, 30m\n"
        "- Популярные 30 и Мои пары: 1m, 3m, 5m, 15m, 30m\n\n"
        f"{format_user_settings(settings)}"
    )


def _format_custom_pairs_menu_text(
    settings: UserSettings,
    custom_pairs: list[str],
) -> str:
    pairs_text = "\n".join(f"- {symbol}" for symbol in custom_pairs)
    if not pairs_text:
        pairs_text = "Пока список пуст."

    return (
        "Мои пары\n\n"
        f"Список пар закреплен: {pair_universe_label(settings.pair_universe)}\n"
        f"Добавлено пар: {len(custom_pairs)}\n\n"
        f"{pairs_text}\n\n"
        "Чтобы добавить пару, отправьте команду:\n"
        "/addpair ETH/BTC\n\n"
        "Поддерживаются пары с явным разделителем: BTC/USDC, ETH-BTC, SOL BTC."
    )


@router.message(CommandStart())
async def handle_start(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    settings = await ensure_user_settings(database_path, message.from_user.id)
    await message.answer(
        "Привет! Я помогу следить за криптовалютными парами.",
        reply_markup=main_menu_keyboard(),
    )
    await message.answer(
        format_user_settings(settings),
        reply_markup=_settings_keyboard(settings),
    )


@router.message(Command("menu"))
async def handle_menu(message: Message) -> None:
    await _show_main_menu(message)


@router.message(Command("settings"))
async def handle_settings(message: Message, database_path: str) -> None:
    settings = await _settings_for_message(message, database_path)
    if settings is None:
        return

    await _show_settings_message(message, settings)


@router.message(Command("status"))
async def handle_status(message: Message, database_path: str) -> None:
    await _show_status_message(message, database_path)


@router.message(Command("pairs"))
async def handle_pairs(message: Message, database_path: str) -> None:
    await _show_custom_pairs_message(message, database_path)


@router.message(Command("addpair"))
async def handle_add_pair(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    raw_symbol = _command_argument(message)
    if not raw_symbol:
        await message.answer("Укажите пару, например: /addpair ETH/BTC")
        return

    try:
        symbol = normalize_pair_symbol(raw_symbol)
    except ValueError:
        await message.answer(
            "Не понял пару. Используйте формат с разделителем, например: /addpair ETH/BTC"
        )
        return

    settings = await _activate_custom_pair_universe(database_path, message.from_user.id)
    custom_pairs = await add_user_custom_pair(
        database_path,
        message.from_user.id,
        symbol,
    )
    await message.answer(
        f"Пара добавлена: {symbol}\n\n"
        f"{_format_custom_pairs_menu_text(settings, custom_pairs)}",
        reply_markup=custom_pairs_keyboard(custom_pairs, active=True),
    )


@router.message(Command("removepair"))
async def handle_remove_pair(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    raw_symbol = _command_argument(message)
    if not raw_symbol:
        await message.answer("Укажите пару, например: /removepair ETH/BTC")
        return

    try:
        symbol = normalize_pair_symbol(raw_symbol)
    except ValueError:
        await message.answer(
            "Не понял пару. Используйте формат с разделителем, например: /removepair ETH/BTC"
        )
        return

    settings = await ensure_user_settings(database_path, message.from_user.id)
    custom_pairs = await remove_user_custom_pair(
        database_path,
        message.from_user.id,
        symbol,
    )
    await message.answer(
        f"Пара удалена: {symbol}\n\n"
        f"{_format_custom_pairs_menu_text(settings, custom_pairs)}",
        reply_markup=custom_pairs_keyboard(
            custom_pairs,
            active=settings.pair_universe == PAIR_UNIVERSE_CUSTOM,
        ),
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await _show_help_message(message)


@router.message(F.text == MAIN_MENU_SETTINGS_TEXT)
async def handle_settings_button(message: Message, database_path: str) -> None:
    settings = await _settings_for_message(message, database_path)
    if settings is None:
        return

    await _show_settings_message(message, settings)


@router.message(F.text == MAIN_MENU_STATUS_TEXT)
async def handle_status_button(message: Message, database_path: str) -> None:
    await _show_status_message(message, database_path)


@router.message(F.text == MAIN_MENU_HELP_TEXT)
async def handle_help_button(message: Message) -> None:
    await _show_help_message(message)


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

    settings = await _update_pair_universe_with_safe_timeframe(
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

    if pair_universe == PAIR_UNIVERSE_CUSTOM:
        custom_pairs = await get_user_custom_pairs(database_path, callback.from_user.id)
        await _edit_custom_pairs_message(callback, settings, custom_pairs)
        return

    await _edit_settings_message(callback, settings, _settings_keyboard(settings))


@router.callback_query(F.data == POPULAR_PAIR_SELECTIONS_CALLBACK)
async def handle_popular_pair_selections(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await _activate_popular_30_universe(database_path, callback.from_user.id)
    selections = await get_user_popular_pair_selections(
        database_path,
        callback.from_user.id,
    )
    await _edit_popular_pairs_message(callback, settings, selections)


@router.callback_query(F.data == CUSTOM_PAIRS_CALLBACK)
async def handle_custom_pairs(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await _activate_custom_pair_universe(database_path, callback.from_user.id)
    custom_pairs = await get_user_custom_pairs(database_path, callback.from_user.id)
    await _edit_custom_pairs_message(callback, settings, custom_pairs)


@router.callback_query(F.data == CUSTOM_PAIRS_ACTIVATE_CALLBACK)
async def handle_custom_pairs_activate(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await _activate_custom_pair_universe(database_path, callback.from_user.id)
    custom_pairs = await get_user_custom_pairs(database_path, callback.from_user.id)
    await _edit_custom_pairs_message(callback, settings, custom_pairs)


@router.callback_query(F.data.startswith(CUSTOM_PAIR_REMOVE_PREFIX))
async def handle_custom_pair_remove(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    raw_symbol = callback.data.removeprefix(CUSTOM_PAIR_REMOVE_PREFIX)
    try:
        symbol = normalize_pair_symbol(raw_symbol)
    except ValueError:
        await callback.answer("Неизвестная пара.", show_alert=True)
        return

    settings = await _activate_custom_pair_universe(database_path, callback.from_user.id)
    custom_pairs = await remove_user_custom_pair(
        database_path,
        callback.from_user.id,
        symbol,
    )
    await _edit_custom_pairs_message(callback, settings, custom_pairs)


@router.callback_query(F.data == CUSTOM_PAIRS_CLEAR_CALLBACK)
async def handle_custom_pairs_clear(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    settings = await _activate_custom_pair_universe(database_path, callback.from_user.id)
    custom_pairs = await clear_user_custom_pairs(database_path, callback.from_user.id)
    await _edit_custom_pairs_message(callback, settings, custom_pairs)


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

    settings = await _activate_popular_30_universe(database_path, callback.from_user.id)
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
    settings = await _activate_popular_30_universe(database_path, callback.from_user.id)
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
    settings = await _activate_popular_30_universe(database_path, callback.from_user.id)
    selections = await set_all_user_popular_pair_selections(
        database_path,
        callback.from_user.id,
        selected=False,
    )
    await _edit_popular_pairs_message(callback, settings, selections)


@router.callback_query(F.data == TIMEFRAME_MENU_CALLBACK)
async def handle_timeframe_menu(callback: CallbackQuery, database_path: str) -> None:
    settings = await ensure_user_settings(database_path, callback.from_user.id)
    await _edit_settings_message(
        callback,
        settings,
        timeframe_keyboard(settings.pair_universe),
    )


@router.callback_query(F.data.startswith(TIMEFRAME_VALUE_PREFIX))
async def handle_timeframe_selection(
    callback: CallbackQuery,
    database_path: str,
) -> None:
    timeframe = callback.data.removeprefix(TIMEFRAME_VALUE_PREFIX)
    current_settings = await ensure_user_settings(database_path, callback.from_user.id)
    if timeframe not in timeframe_options_for_pair_universe(current_settings.pair_universe):
        await callback.answer(
            "Этот таймфрейм недоступен для выбранного списка пар.",
            show_alert=True,
        )
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


def _format_status_message(
    settings: UserSettings,
    selected_pairs_count: int | None,
) -> str:
    notifications = "включены" if settings.notifications_enabled else "выключены"
    pair_details = ""
    if selected_pairs_count is not None:
        if settings.pair_universe == PAIR_UNIVERSE_POPULAR_30:
            pair_details = f"\nВыбрано популярных пар: {selected_pairs_count}/30"
        elif settings.pair_universe == PAIR_UNIVERSE_CUSTOM:
            pair_details = f"\nВыбрано моих пар: {selected_pairs_count}"

    return (
        "Статус мониторинга\n\n"
        f"Биржа: {settings.exchange.capitalize()}\n"
        f"Список пар: {pair_universe_label(settings.pair_universe)}"
        f"{pair_details}\n"
        f"Таймфрейм: {settings.timeframe}\n"
        f"Минимальный рост объема: {settings.volume_change_percent:g}%\n"
        f"RSI: {settings.rsi_min}–{settings.rsi_max}\n"
        f"Уведомления: {notifications}"
    )
