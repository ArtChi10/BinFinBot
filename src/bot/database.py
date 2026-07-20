from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from src.market.universes import (
    PAIR_UNIVERSE_TOP_150,
    POPULAR_30_USDT_PAIRS,
    pair_universe_label,
)


@dataclass(frozen=True)
class UserSettings:
    telegram_user_id: int
    exchange: str
    pair_universe: str
    timeframe: str
    volume_change_percent: float
    rsi_min: int
    rsi_max: int
    notifications_enabled: bool
    created_at: str
    updated_at: str


DEFAULT_SETTINGS = {
    "exchange": "bybit",
    "pair_universe": PAIR_UNIVERSE_TOP_150,
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
    pair_universe TEXT NOT NULL DEFAULT 'top_150',
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


CREATE_USER_POPULAR_PAIR_SELECTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_popular_pair_selections (
    telegram_user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    selected INTEGER NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (telegram_user_id, symbol)
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
        await _ensure_user_settings_columns(db)
        await db.execute(CREATE_SIGNAL_COOLDOWNS_TABLE_SQL)
        await db.execute(CREATE_USER_POPULAR_PAIR_SELECTIONS_TABLE_SQL)
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
                pair_universe,
                timeframe,
                volume_change_percent,
                rsi_min,
                rsi_max,
                notifications_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_user_id,
                DEFAULT_SETTINGS["exchange"],
                DEFAULT_SETTINGS["pair_universe"],
                DEFAULT_SETTINGS["timeframe"],
                DEFAULT_SETTINGS["volume_change_percent"],
                DEFAULT_SETTINGS["rsi_min"],
                DEFAULT_SETTINGS["rsi_max"],
                int(DEFAULT_SETTINGS["notifications_enabled"]),
            ),
        )
        await _ensure_popular_pair_selection_rows(db, telegram_user_id)
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
                pair_universe,
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
                pair_universe,
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


async def get_user_popular_pair_selections(
    database_path: str,
    telegram_user_id: int,
) -> dict[str, bool]:
    await ensure_user_popular_pair_selections(database_path, telegram_user_id)

    async with aiosqlite.connect(database_path) as db:
        cursor = await db.execute(
            """
            SELECT symbol, selected
            FROM user_popular_pair_selections
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()

    selections = {str(symbol): bool(selected) for symbol, selected in rows}
    return {
        symbol: selections.get(symbol, True)
        for symbol in POPULAR_30_USDT_PAIRS
    }


async def get_selected_popular_pairs(
    database_path: str,
    telegram_user_id: int,
) -> list[str]:
    selections = await get_user_popular_pair_selections(database_path, telegram_user_id)
    return [
        symbol
        for symbol in POPULAR_30_USDT_PAIRS
        if selections.get(symbol, False)
    ]


async def ensure_user_popular_pair_selections(
    database_path: str,
    telegram_user_id: int,
) -> None:
    await ensure_user_settings(database_path, telegram_user_id)
    async with aiosqlite.connect(database_path) as db:
        await _ensure_popular_pair_selection_rows(db, telegram_user_id)
        await db.commit()


async def toggle_user_popular_pair_selection(
    database_path: str,
    telegram_user_id: int,
    symbol: str,
) -> dict[str, bool]:
    if symbol not in POPULAR_30_USDT_PAIRS:
        raise ValueError(f"Unknown popular pair: {symbol}.")

    selections = await get_user_popular_pair_selections(database_path, telegram_user_id)
    next_selected = not selections[symbol]

    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """
            UPDATE user_popular_pair_selections
            SET selected = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_user_id = ?
              AND symbol = ?
            """,
            (int(next_selected), telegram_user_id, symbol),
        )
        await db.commit()

    selections[symbol] = next_selected
    return selections


async def set_all_user_popular_pair_selections(
    database_path: str,
    telegram_user_id: int,
    selected: bool,
) -> dict[str, bool]:
    await ensure_user_popular_pair_selections(database_path, telegram_user_id)

    async with aiosqlite.connect(database_path) as db:
        await db.executemany(
            """
            UPDATE user_popular_pair_selections
            SET selected = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_user_id = ?
              AND symbol = ?
            """,
            [
                (int(selected), telegram_user_id, symbol)
                for symbol in POPULAR_30_USDT_PAIRS
            ],
        )
        await db.commit()

    return {symbol: selected for symbol in POPULAR_30_USDT_PAIRS}


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


async def update_user_pair_universe(
    database_path: str,
    telegram_user_id: int,
    pair_universe: str,
) -> UserSettings:
    await ensure_user_settings(database_path, telegram_user_id)
    await _update_user_settings(
        database_path,
        telegram_user_id,
        "pair_universe = ?",
        (pair_universe,),
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


async def _ensure_user_settings_columns(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(user_settings)")
    rows = await cursor.fetchall()
    await cursor.close()

    columns = {str(row[1]) for row in rows}
    if "pair_universe" not in columns:
        await db.execute(
            """
            ALTER TABLE user_settings
            ADD COLUMN pair_universe TEXT NOT NULL DEFAULT 'top_150'
            """
        )


async def _ensure_popular_pair_selection_rows(
    db: aiosqlite.Connection,
    telegram_user_id: int,
) -> None:
    await db.executemany(
        """
        INSERT OR IGNORE INTO user_popular_pair_selections (
            telegram_user_id,
            symbol,
            selected
        )
        VALUES (?, ?, 1)
        """,
        [
            (telegram_user_id, symbol)
            for symbol in POPULAR_30_USDT_PAIRS
        ],
    )


def _settings_from_row(row: aiosqlite.Row) -> UserSettings:
    return UserSettings(
        telegram_user_id=int(row["telegram_user_id"]),
        exchange=str(row["exchange"]),
        pair_universe=str(row["pair_universe"]),
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
        f"Список пар: {pair_universe_label(settings.pair_universe)}\n"
        f"Таймфрейм: {settings.timeframe}\n"
        f"Минимальный рост объема: {settings.volume_change_percent:g}%\n"
        f"RSI: {settings.rsi_min}–{settings.rsi_max}\n"
        f"Уведомления: {notifications}"
    )
