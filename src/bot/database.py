from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from src.bot.db_backend import connect_postgres, is_postgres_database_url
from src.market.universes import (
    PAIR_UNIVERSE_TOP_150,
    POPULAR_30_USDT_PAIRS,
    normalize_pair_symbol,
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


CREATE_USER_CUSTOM_PAIRS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_custom_pairs (
    telegram_user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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


CREATE_USER_SETTINGS_TABLE_POSTGRES_SQL = """
CREATE TABLE IF NOT EXISTS user_settings (
    telegram_user_id BIGINT PRIMARY KEY,
    exchange TEXT NOT NULL,
    pair_universe TEXT NOT NULL DEFAULT 'top_150',
    timeframe TEXT NOT NULL,
    volume_change_percent DOUBLE PRECISION NOT NULL,
    rsi_min INTEGER NOT NULL,
    rsi_max INTEGER NOT NULL,
    notifications_enabled BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


CREATE_SIGNAL_COOLDOWNS_TABLE_POSTGRES_SQL = """
CREATE TABLE IF NOT EXISTS signal_cooldowns (
    telegram_user_id BIGINT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    last_sent_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (telegram_user_id, symbol, timeframe)
);
"""


CREATE_USER_POPULAR_PAIR_SELECTIONS_TABLE_POSTGRES_SQL = """
CREATE TABLE IF NOT EXISTS user_popular_pair_selections (
    telegram_user_id BIGINT NOT NULL,
    symbol TEXT NOT NULL,
    selected BOOLEAN NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (telegram_user_id, symbol)
);
"""


CREATE_USER_CUSTOM_PAIRS_TABLE_POSTGRES_SQL = """
CREATE TABLE IF NOT EXISTS user_custom_pairs (
    telegram_user_id BIGINT NOT NULL,
    symbol TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (telegram_user_id, symbol)
);
"""


async def init_db(database_path: str) -> None:
    if is_postgres_database_url(database_path):
        await _init_postgres_db(database_path)
        return

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(database_path) as db:
        await db.execute(CREATE_USER_SETTINGS_TABLE_SQL)
        await _ensure_user_settings_columns(db)
        await db.execute(CREATE_SIGNAL_COOLDOWNS_TABLE_SQL)
        await db.execute(CREATE_USER_POPULAR_PAIR_SELECTIONS_TABLE_SQL)
        await db.execute(CREATE_USER_CUSTOM_PAIRS_TABLE_SQL)
        await db.execute(CREATE_UPDATED_AT_TRIGGER_SQL)
        await db.commit()


async def ensure_user_settings(
    database_path: str,
    telegram_user_id: int,
) -> UserSettings:
    if is_postgres_database_url(database_path):
        return await _ensure_user_settings_postgres(database_path, telegram_user_id)

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
    if is_postgres_database_url(database_path):
        return await _get_user_settings_postgres(database_path, telegram_user_id)

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
    if is_postgres_database_url(database_path):
        return await _get_notification_user_settings_postgres(database_path)

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
    if is_postgres_database_url(database_path):
        return await _get_user_popular_pair_selections_postgres(
            database_path,
            telegram_user_id,
        )

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


async def get_user_custom_pairs(
    database_path: str,
    telegram_user_id: int,
) -> list[str]:
    if is_postgres_database_url(database_path):
        return await _get_user_custom_pairs_postgres(database_path, telegram_user_id)

    await ensure_user_settings(database_path, telegram_user_id)

    async with aiosqlite.connect(database_path) as db:
        cursor = await db.execute(
            """
            SELECT symbol
            FROM user_custom_pairs
            WHERE telegram_user_id = ?
            ORDER BY symbol
            """,
            (telegram_user_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()

    return [str(row[0]) for row in rows]


async def add_user_custom_pair(
    database_path: str,
    telegram_user_id: int,
    symbol: str,
) -> list[str]:
    normalized_symbol = normalize_pair_symbol(symbol)
    if is_postgres_database_url(database_path):
        return await _add_user_custom_pair_postgres(
            database_path,
            telegram_user_id,
            normalized_symbol,
        )

    await ensure_user_settings(database_path, telegram_user_id)

    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO user_custom_pairs (
                telegram_user_id,
                symbol
            )
            VALUES (?, ?)
            """,
            (telegram_user_id, normalized_symbol),
        )
        await db.commit()

    return await get_user_custom_pairs(database_path, telegram_user_id)


async def remove_user_custom_pair(
    database_path: str,
    telegram_user_id: int,
    symbol: str,
) -> list[str]:
    normalized_symbol = normalize_pair_symbol(symbol)
    if is_postgres_database_url(database_path):
        return await _remove_user_custom_pair_postgres(
            database_path,
            telegram_user_id,
            normalized_symbol,
        )

    await ensure_user_settings(database_path, telegram_user_id)

    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """
            DELETE FROM user_custom_pairs
            WHERE telegram_user_id = ?
              AND symbol = ?
            """,
            (telegram_user_id, normalized_symbol),
        )
        await db.commit()

    return await get_user_custom_pairs(database_path, telegram_user_id)


async def clear_user_custom_pairs(
    database_path: str,
    telegram_user_id: int,
) -> list[str]:
    if is_postgres_database_url(database_path):
        return await _clear_user_custom_pairs_postgres(database_path, telegram_user_id)

    await ensure_user_settings(database_path, telegram_user_id)

    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """
            DELETE FROM user_custom_pairs
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        )
        await db.commit()

    return []


async def ensure_user_popular_pair_selections(
    database_path: str,
    telegram_user_id: int,
) -> None:
    if is_postgres_database_url(database_path):
        await _ensure_user_popular_pair_selections_postgres(
            database_path,
            telegram_user_id,
        )
        return

    await ensure_user_settings(database_path, telegram_user_id)
    async with aiosqlite.connect(database_path) as db:
        await _ensure_popular_pair_selection_rows(db, telegram_user_id)
        await db.commit()


async def toggle_user_popular_pair_selection(
    database_path: str,
    telegram_user_id: int,
    symbol: str,
) -> dict[str, bool]:
    if is_postgres_database_url(database_path):
        return await _toggle_user_popular_pair_selection_postgres(
            database_path,
            telegram_user_id,
            symbol,
        )

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
    if is_postgres_database_url(database_path):
        return await _set_all_user_popular_pair_selections_postgres(
            database_path,
            telegram_user_id,
            selected,
        )

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
        (not settings.notifications_enabled,),
    )
    return await _get_existing_user_settings(database_path, telegram_user_id)


async def _update_user_settings(
    database_path: str,
    telegram_user_id: int,
    set_clause: str,
    values: tuple[object, ...],
) -> None:
    if is_postgres_database_url(database_path):
        await _update_user_settings_postgres(
            database_path,
            telegram_user_id,
            set_clause,
            values,
        )
        return

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


async def _init_postgres_db(database_url: str) -> None:
    connection = await connect_postgres(database_url)
    try:
        await connection.execute(CREATE_USER_SETTINGS_TABLE_POSTGRES_SQL)
        await _ensure_user_settings_columns_postgres(connection)
        await connection.execute(CREATE_SIGNAL_COOLDOWNS_TABLE_POSTGRES_SQL)
        await connection.execute(CREATE_USER_POPULAR_PAIR_SELECTIONS_TABLE_POSTGRES_SQL)
        await connection.execute(CREATE_USER_CUSTOM_PAIRS_TABLE_POSTGRES_SQL)
    finally:
        await connection.close()


async def _ensure_user_settings_postgres(
    database_url: str,
    telegram_user_id: int,
) -> UserSettings:
    connection = await connect_postgres(database_url)
    try:
        await connection.execute(
            """
            INSERT INTO user_settings (
                telegram_user_id,
                exchange,
                pair_universe,
                timeframe,
                volume_change_percent,
                rsi_min,
                rsi_max,
                notifications_enabled
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (telegram_user_id) DO NOTHING
            """,
            telegram_user_id,
            DEFAULT_SETTINGS["exchange"],
            DEFAULT_SETTINGS["pair_universe"],
            DEFAULT_SETTINGS["timeframe"],
            DEFAULT_SETTINGS["volume_change_percent"],
            DEFAULT_SETTINGS["rsi_min"],
            DEFAULT_SETTINGS["rsi_max"],
            DEFAULT_SETTINGS["notifications_enabled"],
        )
        await _ensure_popular_pair_selection_rows_postgres(connection, telegram_user_id)
    finally:
        await connection.close()

    settings = await _get_user_settings_postgres(database_url, telegram_user_id)
    if settings is None:
        raise RuntimeError("Failed to create default user settings.")
    return settings


async def _get_user_settings_postgres(
    database_url: str,
    telegram_user_id: int,
) -> UserSettings | None:
    connection = await connect_postgres(database_url)
    try:
        row = await connection.fetchrow(
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
            WHERE telegram_user_id = $1
            """,
            telegram_user_id,
        )
    finally:
        await connection.close()

    if row is None:
        return None
    return _settings_from_row(row)


async def _get_notification_user_settings_postgres(
    database_url: str,
) -> list[UserSettings]:
    connection = await connect_postgres(database_url)
    try:
        rows = await connection.fetch(
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
            WHERE notifications_enabled = TRUE
            ORDER BY telegram_user_id
            """
        )
    finally:
        await connection.close()

    return [_settings_from_row(row) for row in rows]


async def _get_user_popular_pair_selections_postgres(
    database_url: str,
    telegram_user_id: int,
) -> dict[str, bool]:
    await _ensure_user_settings_postgres(database_url, telegram_user_id)

    connection = await connect_postgres(database_url)
    try:
        rows = await connection.fetch(
            """
            SELECT symbol, selected
            FROM user_popular_pair_selections
            WHERE telegram_user_id = $1
            """,
            telegram_user_id,
        )
    finally:
        await connection.close()

    selections = {str(row["symbol"]): bool(row["selected"]) for row in rows}
    return {
        symbol: selections.get(symbol, True)
        for symbol in POPULAR_30_USDT_PAIRS
    }


async def _ensure_user_popular_pair_selections_postgres(
    database_url: str,
    telegram_user_id: int,
) -> None:
    await _ensure_user_settings_postgres(database_url, telegram_user_id)


async def _toggle_user_popular_pair_selection_postgres(
    database_url: str,
    telegram_user_id: int,
    symbol: str,
) -> dict[str, bool]:
    if symbol not in POPULAR_30_USDT_PAIRS:
        raise ValueError(f"Unknown popular pair: {symbol}.")

    selections = await _get_user_popular_pair_selections_postgres(
        database_url,
        telegram_user_id,
    )
    next_selected = not selections[symbol]

    connection = await connect_postgres(database_url)
    try:
        await connection.execute(
            """
            UPDATE user_popular_pair_selections
            SET selected = $1, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_user_id = $2
              AND symbol = $3
            """,
            next_selected,
            telegram_user_id,
            symbol,
        )
    finally:
        await connection.close()

    selections[symbol] = next_selected
    return selections


async def _set_all_user_popular_pair_selections_postgres(
    database_url: str,
    telegram_user_id: int,
    selected: bool,
) -> dict[str, bool]:
    await _ensure_user_settings_postgres(database_url, telegram_user_id)

    connection = await connect_postgres(database_url)
    try:
        await connection.executemany(
            """
            UPDATE user_popular_pair_selections
            SET selected = $1, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_user_id = $2
              AND symbol = $3
            """,
            [
                (selected, telegram_user_id, symbol)
                for symbol in POPULAR_30_USDT_PAIRS
            ],
        )
    finally:
        await connection.close()

    return {symbol: selected for symbol in POPULAR_30_USDT_PAIRS}


async def _get_user_custom_pairs_postgres(
    database_url: str,
    telegram_user_id: int,
) -> list[str]:
    await _ensure_user_settings_postgres(database_url, telegram_user_id)

    connection = await connect_postgres(database_url)
    try:
        rows = await connection.fetch(
            """
            SELECT symbol
            FROM user_custom_pairs
            WHERE telegram_user_id = $1
            ORDER BY symbol
            """,
            telegram_user_id,
        )
    finally:
        await connection.close()

    return [str(row["symbol"]) for row in rows]


async def _add_user_custom_pair_postgres(
    database_url: str,
    telegram_user_id: int,
    symbol: str,
) -> list[str]:
    await _ensure_user_settings_postgres(database_url, telegram_user_id)

    connection = await connect_postgres(database_url)
    try:
        await connection.execute(
            """
            INSERT INTO user_custom_pairs (
                telegram_user_id,
                symbol
            )
            VALUES ($1, $2)
            ON CONFLICT (telegram_user_id, symbol) DO NOTHING
            """,
            telegram_user_id,
            symbol,
        )
    finally:
        await connection.close()

    return await _get_user_custom_pairs_postgres(database_url, telegram_user_id)


async def _remove_user_custom_pair_postgres(
    database_url: str,
    telegram_user_id: int,
    symbol: str,
) -> list[str]:
    await _ensure_user_settings_postgres(database_url, telegram_user_id)

    connection = await connect_postgres(database_url)
    try:
        await connection.execute(
            """
            DELETE FROM user_custom_pairs
            WHERE telegram_user_id = $1
              AND symbol = $2
            """,
            telegram_user_id,
            symbol,
        )
    finally:
        await connection.close()

    return await _get_user_custom_pairs_postgres(database_url, telegram_user_id)


async def _clear_user_custom_pairs_postgres(
    database_url: str,
    telegram_user_id: int,
) -> list[str]:
    await _ensure_user_settings_postgres(database_url, telegram_user_id)

    connection = await connect_postgres(database_url)
    try:
        await connection.execute(
            """
            DELETE FROM user_custom_pairs
            WHERE telegram_user_id = $1
            """,
            telegram_user_id,
        )
    finally:
        await connection.close()

    return []


async def _update_user_settings_postgres(
    database_url: str,
    telegram_user_id: int,
    set_clause: str,
    values: tuple[object, ...],
) -> None:
    postgres_set_clause = _postgres_placeholders(set_clause)
    user_id_placeholder = f"${len(values) + 1}"

    connection = await connect_postgres(database_url)
    try:
        await connection.execute(
            (
                f"UPDATE user_settings "
                f"SET {postgres_set_clause}, updated_at = CURRENT_TIMESTAMP "
                f"WHERE telegram_user_id = {user_id_placeholder}"
            ),
            *values,
            telegram_user_id,
        )
    finally:
        await connection.close()


async def _ensure_user_settings_columns_postgres(connection) -> None:
    rows = await connection.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_settings'
        """
    )
    columns = {str(row["column_name"]) for row in rows}
    if "pair_universe" not in columns:
        await connection.execute(
            """
            ALTER TABLE user_settings
            ADD COLUMN pair_universe TEXT NOT NULL DEFAULT 'top_150'
            """
        )


async def _ensure_popular_pair_selection_rows_postgres(
    connection,
    telegram_user_id: int,
) -> None:
    await connection.executemany(
        """
        INSERT INTO user_popular_pair_selections (
            telegram_user_id,
            symbol,
            selected
        )
        VALUES ($1, $2, TRUE)
        ON CONFLICT (telegram_user_id, symbol) DO NOTHING
        """,
        [
            (telegram_user_id, symbol)
            for symbol in POPULAR_30_USDT_PAIRS
        ],
    )


def _postgres_placeholders(sqlite_sql: str) -> str:
    result = []
    placeholder_index = 1
    for char in sqlite_sql:
        if char == "?":
            result.append(f"${placeholder_index}")
            placeholder_index += 1
        else:
            result.append(char)
    return "".join(result)


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
