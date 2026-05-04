from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from .database import ensure_user_settings, format_user_settings, get_user_settings
from .keyboards import settings_keyboard


router = Router()


@router.message(CommandStart())
async def handle_start(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    settings = await ensure_user_settings(database_path, message.from_user.id)
    await message.answer(
        "Привет! Я помогу подготовить криптовалютный скринер.\n\n"
        f"{format_user_settings(settings)}",
        reply_markup=settings_keyboard(),
    )


@router.message(Command("settings"))
async def handle_settings(message: Message, database_path: str) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    settings = await get_user_settings(database_path, message.from_user.id)
    if settings is None:
        settings = await ensure_user_settings(database_path, message.from_user.id)

    await message.answer(
        format_user_settings(settings),
        reply_markup=settings_keyboard(),
    )


@router.callback_query(F.data.startswith("settings:"))
async def handle_settings_placeholder(callback: CallbackQuery) -> None:
    await callback.answer("Настройка будет добавлена в следующих задачах.")
