from dataclasses import dataclass
from typing import Any

from .indicators import calculate_rsi, calculate_volume_change_percent


CLOSE_INDEX = 4
VOLUME_INDEX = 5
RSI_PERIOD = 14


@dataclass(frozen=True)
class SignalResult:
    matched: bool
    symbol: str
    exchange: str
    timeframe: str
    volume_change_percent: float | None
    rsi: float | None
    price: float | None
    reason: str


def evaluate_signal(
    symbol: str,
    exchange: str,
    timeframe: str,
    candles: list,
    volume_threshold_percent: float,
    rsi_min: float,
    rsi_max: float,
) -> SignalResult:
    if len(candles) < 2:
        return _result(
            matched=False,
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            reason="Not enough candles: at least two closed candles are required.",
        )

    previous_candle = candles[-2]
    current_candle = candles[-1]

    try:
        previous_volume = _candle_value(previous_candle, VOLUME_INDEX)
        current_volume = _candle_value(current_candle, VOLUME_INDEX)
        price = _candle_value(current_candle, CLOSE_INDEX)
        closes = [_candle_value(candle, CLOSE_INDEX) for candle in candles]
    except (TypeError, ValueError, IndexError) as exc:
        return _result(
            matched=False,
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            reason=f"Invalid candle format: {exc}.",
        )

    volume_change = calculate_volume_change_percent(
        current_volume=current_volume,
        previous_volume=previous_volume,
    )
    if volume_change is None:
        return _result(
            matched=False,
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            volume_change_percent=None,
            price=price,
            reason="Previous volume must be greater than zero.",
        )

    rsi = calculate_rsi(closes, period=RSI_PERIOD)
    if rsi is None:
        return _result(
            matched=False,
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            volume_change_percent=volume_change,
            price=price,
            reason=f"Not enough close prices to calculate RSI period {RSI_PERIOD}.",
        )

    volume_matched = volume_change >= volume_threshold_percent
    rsi_matched = rsi_min <= rsi <= rsi_max
    matched = volume_matched and rsi_matched

    if matched:
        reason = "Volume and RSI conditions matched."
    else:
        reasons = []
        if not volume_matched:
            reasons.append(
                "Volume change "
                f"{volume_change:.2f}% is below threshold "
                f"{volume_threshold_percent:.2f}%"
            )
        if not rsi_matched:
            reasons.append(f"RSI {rsi:.2f} is outside range {rsi_min:g}-{rsi_max:g}")
        reason = "; ".join(reasons) + "."

    return _result(
        matched=matched,
        symbol=symbol,
        exchange=exchange,
        timeframe=timeframe,
        volume_change_percent=volume_change,
        rsi=rsi,
        price=price,
        reason=reason,
    )


def format_signal_message(result: SignalResult) -> str:
    quote_asset = result.symbol.split("/")[-1] if "/" in result.symbol else "USDT"

    return (
        f"Сигнал: {result.symbol}\n\n"
        f"Биржа: {result.exchange.capitalize()}\n"
        f"Таймфрейм: {result.timeframe}\n"
        f"Объем: {_format_signed_percent(result.volume_change_percent)}\n"
        f"RSI: {_format_number(result.rsi)}\n"
        f"Цена: {_format_number(result.price)} {quote_asset}"
    )


def _candle_value(candle: Any, index: int) -> float:
    return float(candle[index])


def _result(
    matched: bool,
    symbol: str,
    exchange: str,
    timeframe: str,
    reason: str,
    volume_change_percent: float | None = None,
    rsi: float | None = None,
    price: float | None = None,
) -> SignalResult:
    return SignalResult(
        matched=matched,
        symbol=symbol,
        exchange=exchange,
        timeframe=timeframe,
        volume_change_percent=volume_change_percent,
        rsi=rsi,
        price=price,
        reason=reason,
    )


def _format_signed_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def _format_number(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:g}"
