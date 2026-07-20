from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import UTC, datetime

from aiogram import Bot

from src.analysis.signals import evaluate_signal, format_signal_message
from src.bot.database import UserSettings, get_notification_user_settings
from src.market.bybit_client import BybitMarketDataClient, MarketDataError
from src.monitoring.cooldown import can_send_signal, record_signal_sent


logger = logging.getLogger(__name__)

DEFAULT_TOP_PAIRS_LIMIT = 150
DEFAULT_TOP_PAIRS_REFRESH_SECONDS = 60 * 60
DEFAULT_CHECK_INTERVAL_SECONDS = 60
DEFAULT_OHLCV_LIMIT = 100
DEFAULT_REQUEST_CONCURRENCY = 5

TIMEFRAME_SECONDS = {
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
}


async def run_market_monitor(
    bot: Bot,
    database_path: str,
    *,
    top_pairs_limit: int = DEFAULT_TOP_PAIRS_LIMIT,
    top_pairs_refresh_seconds: int = DEFAULT_TOP_PAIRS_REFRESH_SECONDS,
    check_interval_seconds: int = DEFAULT_CHECK_INTERVAL_SECONDS,
    ohlcv_limit: int = DEFAULT_OHLCV_LIMIT,
    request_concurrency: int = DEFAULT_REQUEST_CONCURRENCY,
) -> None:
    logger.info("Starting market monitor.")
    top_pairs: list[str] = []
    top_pairs_loaded_at = 0.0

    async with BybitMarketDataClient() as client:
        while True:
            try:
                settings = await _load_bybit_notification_settings(database_path)
                if settings:
                    now = time.monotonic()
                    if not top_pairs or now - top_pairs_loaded_at >= top_pairs_refresh_seconds:
                        top_pairs = await client.get_top_usdt_pairs(limit=top_pairs_limit)
                        top_pairs_loaded_at = now
                        logger.info("Loaded %s top Bybit /USDT pairs.", len(top_pairs))

                    await _scan_for_signals(
                        bot=bot,
                        database_path=database_path,
                        client=client,
                        top_pairs=top_pairs,
                        settings=settings,
                        ohlcv_limit=ohlcv_limit,
                        request_concurrency=request_concurrency,
                    )
                else:
                    logger.debug("No users with enabled Bybit notifications.")
            except asyncio.CancelledError:
                logger.info("Stopping market monitor.")
                raise
            except Exception:
                logger.exception("Market monitor cycle failed.")

            await asyncio.sleep(check_interval_seconds)


async def _load_bybit_notification_settings(database_path: str) -> list[UserSettings]:
    settings = await get_notification_user_settings(database_path)
    return [item for item in settings if item.exchange.lower() == "bybit"]


async def _scan_for_signals(
    bot: Bot,
    database_path: str,
    client: BybitMarketDataClient,
    top_pairs: list[str],
    settings: list[UserSettings],
    ohlcv_limit: int,
    request_concurrency: int,
) -> None:
    settings_by_timeframe: dict[str, list[UserSettings]] = defaultdict(list)
    for item in settings:
        settings_by_timeframe[item.timeframe].append(item)

    for timeframe, timeframe_settings in settings_by_timeframe.items():
        candles_by_symbol = await _fetch_candles_for_timeframe(
            client=client,
            symbols=top_pairs,
            timeframe=timeframe,
            ohlcv_limit=ohlcv_limit,
            request_concurrency=request_concurrency,
        )

        for symbol, candles in candles_by_symbol.items():
            closed_candles = closed_ohlcv_candles(candles, timeframe)
            if len(closed_candles) < 2:
                logger.debug("Skipping %s %s: not enough closed candles.", symbol, timeframe)
                continue

            for user_settings in timeframe_settings:
                result = evaluate_signal(
                    symbol=symbol,
                    exchange=user_settings.exchange,
                    timeframe=timeframe,
                    candles=closed_candles,
                    volume_threshold_percent=user_settings.volume_change_percent,
                    rsi_min=user_settings.rsi_min,
                    rsi_max=user_settings.rsi_max,
                )
                if not result.matched:
                    continue

                await _send_signal_if_allowed(
                    bot=bot,
                    database_path=database_path,
                    user_settings=user_settings,
                    symbol=symbol,
                    timeframe=timeframe,
                    message=format_signal_message(result),
                )


async def _fetch_candles_for_timeframe(
    client: BybitMarketDataClient,
    symbols: list[str],
    timeframe: str,
    ohlcv_limit: int,
    request_concurrency: int,
) -> dict[str, list[list[float]]]:
    semaphore = asyncio.Semaphore(request_concurrency)

    async def fetch_symbol(symbol: str) -> tuple[str, list[list[float]] | None]:
        async with semaphore:
            try:
                return symbol, await client.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    limit=ohlcv_limit,
                )
            except MarketDataError as exc:
                logger.warning("Failed to load OHLCV for %s %s: %s", symbol, timeframe, exc)
                return symbol, None
            except Exception:
                logger.exception("Unexpected OHLCV error for %s %s.", symbol, timeframe)
                return symbol, None

    results = await asyncio.gather(*(fetch_symbol(symbol) for symbol in symbols))
    return {symbol: candles for symbol, candles in results if candles}


async def _send_signal_if_allowed(
    bot: Bot,
    database_path: str,
    user_settings: UserSettings,
    symbol: str,
    timeframe: str,
    message: str,
) -> None:
    sent_at = datetime.now(UTC)
    allowed = await can_send_signal(
        database_path=database_path,
        telegram_user_id=user_settings.telegram_user_id,
        symbol=symbol,
        timeframe=timeframe,
        now=sent_at,
    )
    if not allowed:
        logger.debug(
            "Skipping %s %s for user %s: cooldown is active.",
            symbol,
            timeframe,
            user_settings.telegram_user_id,
        )
        return

    try:
        await bot.send_message(chat_id=user_settings.telegram_user_id, text=message)
    except Exception:
        logger.exception(
            "Failed to send signal %s %s to user %s.",
            symbol,
            timeframe,
            user_settings.telegram_user_id,
        )
        return

    await record_signal_sent(
        database_path=database_path,
        telegram_user_id=user_settings.telegram_user_id,
        symbol=symbol,
        timeframe=timeframe,
        sent_at=sent_at,
    )
    logger.info(
        "Sent signal %s %s to user %s.",
        symbol,
        timeframe,
        user_settings.telegram_user_id,
    )


def closed_ohlcv_candles(
    candles: list[list[float]],
    timeframe: str,
    now_ms: int | None = None,
) -> list[list[float]]:
    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(f"Unsupported timeframe: {timeframe}.")

    now_ms = int(datetime.now(UTC).timestamp() * 1000) if now_ms is None else now_ms
    timeframe_ms = TIMEFRAME_SECONDS[timeframe] * 1000
    return [candle for candle in candles if int(candle[0]) + timeframe_ms <= now_ms]
