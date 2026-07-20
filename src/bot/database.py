from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(frozen=True)
class UserSettings:
    telegram_user_id: int
    exchange: str
    timeframe: str
    volume_change_percent: float
    rsi_min: int
    rsi_max: int
    notifications_enabled: bool
    created_at: str
    updated_at: str


DEFAULT_SETTINGS = {
    "exchange": "bybit",
    "timeframe": "15m",
    "volume_change_percent": 0.5,
    "rsi_min": 60,
    "rsi_max": 80,
    "notifications_enabled": True,
}


CREATE_USER_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_settings (
    telegram_user_id INTEGER PRIMARY KEY,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    volume_change_percent REAL NOT NULL,
    rsi_min INTEGER NOT NULL,
    rsi_max INTEGER NOT NULL,
    notifications_enabled INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


CREATE_SIGNAL_COOLDOWNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS signal_cooldowns (
    telegram_user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    last_sent_at TEXT NOT NULL,
    PRIMARY KEY (telegram_user_id, symbol, timeframe)
);
"""


CREATE_UPDATED_AT_TRIGGER_SQL = """
CREATE TRIGGER IF NOT EXISTS user_settings_updated_at
AFTER UPDATE ON user_settings
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE user_settings
    SET updated_at = CURRENT_TIMESTAMP
    WHERE telegram_user_id = OLD.telegram_user_id;
END;
"""


async def init_db(database_path: str) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(database_path) as db:
        await db.execute(CREATE_USER_SETTINGS_TABLE_SQL)
        await db.execute(CREATE_SIGNAL_COOLDOWNS_TABLE_SQL)
        await db.execute(CREATE_UPDATED_AT_TRIGGER_SQL)
        await db.commit()


async def ensure_user_settings(
    database_path: str,
    telegram_user_id: int,
) -> UserSettings:
    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO user_settings (
                telegram_user_id,
                exchange,
                timeframe,
                volume_change_percent,
                rsi_min,
                rsi_max,
                notifications_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_user_id,
                DEFAULT_SETTINGS["exchange"],
                DEFAULT_SETTINGS["timeframe"],
                DEFAULT_SETTINGS["volume_change_percent"],
                DEFAULT_SETTINGS["rsi_min"],
                DEFAULT_SETTINGS["rsi_max"],
                int(DEFAULT_SETTINGS["notifications_enabled"]),
            ),
        )
        await db.commit()

    settings = await get_user_settings(database_path, telegram_user_id)
    if settings is None:
        raise RuntimeError("Failed to create default user settings.")
    return settings


async def get_user_settings(
    database_path: str,
    telegram_user_id: int,
) -> UserSettings | None:
    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                telegram_user_id,
                exchange,
                timeframe,
                volume_change_percent,
                rsi_min,
                rsi_max,
                notifications_enabled,
                created_at,
                updated_at
            FROM user_settings
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return None

    return _settings_from_row(row)


async def get_notification_user_settings(database_path: str) -> list[UserSettings]:
    async with aiosqlite.connect(database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                telegram_user_id,
                exchange,
                timeframe,
                volume_change_percent,
                rsi_min,
                rsi_max,
                notifications_enabled,
                created_at,
                updated_at
            FROM user_settings
            WHERE notifications_enabled = 1
            ORDER BY telegram_user_id
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()

    return [_settings_from_row(row) for row in rows]


async def update_user_timeframe(
    database_path: str,
    telegram_user_id: int,
    timeframe: str,
) -> UserSettings:
    await ensure_user_settings(database_path, telegram_user_id)
    await _update_user_settings(
        database_path,
        telegram_user_id,
        "timeframe = ?",
        (timeframe,),
    )
    return await _get_existing_user_settings(database_path, telegram_user_id)


async def update_user_rsi_range(
    database_path: str,
    telegram_user_id: int,
    rsi_min: int,
    rsi_max: int,
) -> UserSettings:
    await ensure_user_settings(database_path, telegram_user_id)
    await _update_user_settings(
        database_path,
        telegram_user_id,
        "rsi_min = ?, rsi_max = ?",
        (rsi_min, rsi_max),
    )
    return await _get_existing_user_settings(database_path, telegram_user_id)


async def update_user_volume_change_percent(
    database_path: str,
    telegram_user_id: int,
    volume_change_percent: float,
) -> UserSettings:
    await ensure_user_settings(database_path, telegram_user_id)
    await _update_user_settings(
        database_path,
        telegram_user_id,
        "volume_change_percent = ?",
        (volume_change_percent,),
    )
    return await _get_existing_user_settings(database_path, telegram_user_id)


async def toggle_user_notifications(
    database_path: str,
    telegram_user_id: int,
) -> UserSettings:
    settings = await ensure_user_settings(database_path, telegram_user_id)
    await _update_user_settings(
        database_path,
        telegram_user_id,
        "notifications_enabled = ?",
        (int(not settings.notifications_enabled),),
    )
    return await _get_existing_user_settings(database_path, telegram_user_id)


async def _update_user_settings(
    database_path: str,
    telegram_user_id: int,
    set_clause: str,
    values: tuple[object, ...],
) -> None:
    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            f"UPDATE user_settings SET {set_clause} WHERE telegram_user_id = ?",
            (*values, telegram_user_id),
        )
        await db.commit()


async def _get_existing_user_settings(
    database_path: str,
    telegram_user_id: int,
) -> UserSettings:
    settings = await get_user_settings(database_path, telegram_user_id)
    if settings is None:
        raise RuntimeError("User settings were not found after update.")
    return settings


def _settings_from_row(row: aiosqlite.Row) -> UserSettings:
    return UserSettings(
        telegram_user_id=int(row["telegram_user_id"]),
        exchange=str(row["exchange"]),
        timeframe=str(row["timeframe"]),
        volume_change_percent=float(row["volume_change_percent"]),
        rsi_min=int(row["rsi_min"]),
        rsi_max=int(row["rsi_max"]),
        notifications_enabled=bool(row["notifications_enabled"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def format_user_settings(settings: UserSettings) -> str:
    notifications = "включены" if settings.notifications_enabled else "выключены"
    exchange = settings.exchange.capitalize()

    return (
        "Текущие настройки\n\n"
        f"Биржа: {exchange}\n"
        f"Таймфрейм: {settings.timeframe}\n"
        f"Минимальный рост объема: {settings.volume_change_percent:g}%\n"
        f"RSI: {settings.rsi_min}–{settings.rsi_max}\n"
        f"Уведомления: {notifications}"
    )
