from datetime import UTC, datetime

import aiosqlite

from src.bot.db_backend import connect_postgres, is_postgres_database_url


TIMEFRAME_COOLDOWN_SECONDS = {
    "1m": 60,
    "3m": 3 * 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
}


def cooldown_seconds_for_timeframe(timeframe: str) -> int:
    try:
        return TIMEFRAME_COOLDOWN_SECONDS[timeframe]
    except KeyError as exc:
        raise ValueError(f"Unsupported timeframe for cooldown: {timeframe}.") from exc


async def can_send_signal(
    database_path: str,
    telegram_user_id: int,
    symbol: str,
    timeframe: str,
    now: datetime | None = None,
) -> bool:
    now = _utc_now() if now is None else _as_utc(now)
    last_sent_at = await get_last_signal_sent_at(
        database_path,
        telegram_user_id,
        symbol,
        timeframe,
    )
    if last_sent_at is None:
        return True

    cooldown_seconds = cooldown_seconds_for_timeframe(timeframe)
    return (now - last_sent_at).total_seconds() >= cooldown_seconds


async def record_signal_sent(
    database_path: str,
    telegram_user_id: int,
    symbol: str,
    timeframe: str,
    sent_at: datetime | None = None,
) -> None:
    sent_at = _utc_now() if sent_at is None else _as_utc(sent_at)

    if is_postgres_database_url(database_path):
        await _record_signal_sent_postgres(
            database_path,
            telegram_user_id,
            symbol,
            timeframe,
            sent_at,
        )
        return

    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """
            INSERT INTO signal_cooldowns (
                telegram_user_id,
                symbol,
                timeframe,
                last_sent_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_user_id, symbol, timeframe)
            DO UPDATE SET last_sent_at = excluded.last_sent_at
            """,
            (
                telegram_user_id,
                symbol,
                timeframe,
                sent_at.isoformat(timespec="seconds"),
            ),
        )
        await db.commit()


async def get_last_signal_sent_at(
    database_path: str,
    telegram_user_id: int,
    symbol: str,
    timeframe: str,
) -> datetime | None:
    if is_postgres_database_url(database_path):
        return await _get_last_signal_sent_at_postgres(
            database_path,
            telegram_user_id,
            symbol,
            timeframe,
        )

    async with aiosqlite.connect(database_path) as db:
        cursor = await db.execute(
            """
            SELECT last_sent_at
            FROM signal_cooldowns
            WHERE telegram_user_id = ?
              AND symbol = ?
              AND timeframe = ?
            """,
            (telegram_user_id, symbol, timeframe),
        )
        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return None

    return _parse_datetime(str(row[0]))


async def _record_signal_sent_postgres(
    database_url: str,
    telegram_user_id: int,
    symbol: str,
    timeframe: str,
    sent_at: datetime,
) -> None:
    connection = await connect_postgres(database_url)
    try:
        await connection.execute(
            """
            INSERT INTO signal_cooldowns (
                telegram_user_id,
                symbol,
                timeframe,
                last_sent_at
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_user_id, symbol, timeframe)
            DO UPDATE SET last_sent_at = excluded.last_sent_at
            """,
            telegram_user_id,
            symbol,
            timeframe,
            sent_at,
        )
    finally:
        await connection.close()


async def _get_last_signal_sent_at_postgres(
    database_url: str,
    telegram_user_id: int,
    symbol: str,
    timeframe: str,
) -> datetime | None:
    connection = await connect_postgres(database_url)
    try:
        row = await connection.fetchrow(
            """
            SELECT last_sent_at
            FROM signal_cooldowns
            WHERE telegram_user_id = $1
              AND symbol = $2
              AND timeframe = $3
            """,
            telegram_user_id,
            symbol,
            timeframe,
        )
    finally:
        await connection.close()

    if row is None:
        return None

    return _as_utc(row["last_sent_at"])


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)
