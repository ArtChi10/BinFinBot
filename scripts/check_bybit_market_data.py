from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market.bybit_client import (  # noqa: E402
    BybitMarketDataClient,
    MarketDataError,
    UnsupportedTimeframeError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke check Bybit market data.")
    parser.add_argument("--limit", type=int, default=10, help="Number of USDT pairs.")
    parser.add_argument("--timeframe", default="15m", help="OHLCV timeframe.")
    parser.add_argument(
        "--ohlcv-limit",
        type=int,
        default=50,
        help="Number of OHLCV candles to request.",
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()

    client = BybitMarketDataClient()
    try:
        pairs = await client.get_top_usdt_pairs(limit=args.limit)
        print(f"Top {len(pairs)} Bybit spot USDT pairs by 24h quote volume:")
        for index, symbol in enumerate(pairs, start=1):
            print(f"{index}. {symbol}")

        symbol = pairs[0]
        candles = await client.fetch_ohlcv(
            symbol=symbol,
            timeframe=args.timeframe,
            limit=args.ohlcv_limit,
        )
    except (MarketDataError, UnsupportedTimeframeError, ValueError) as exc:
        print(f"Smoke check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await client.close()

    last_closed_candle = candles[-2] if len(candles) > 1 else candles[-1]
    print()
    print(f"Fetched {len(candles)} candles for {symbol} {args.timeframe}.")
    print(f"Last closed candle: {last_closed_candle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
