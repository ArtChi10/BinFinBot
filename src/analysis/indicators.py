from collections.abc import Sequence


def calculate_volume_change_percent(
    current_volume: float,
    previous_volume: float,
) -> float | None:
    if previous_volume <= 0:
        return None

    return ((current_volume - previous_volume) / previous_volume) * 100


def calculate_price_change_percent(
    current_price: float,
    previous_price: float,
) -> float | None:
    if previous_price <= 0:
        return None

    return ((current_price - previous_price) / previous_price) * 100


def calculate_rsi(closes: Sequence[float], period: int = 14) -> float | None:
    if period <= 0:
        raise ValueError("period must be greater than zero.")
    if len(closes) < period + 1:
        return None

    deltas = [
        float(closes[index]) - float(closes[index - 1])
        for index in range(1, len(closes))
    ]
    gains = [max(delta, 0.0) for delta in deltas]
    losses = [abs(min(delta, 0.0)) for delta in deltas]

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    for index in range(period, len(deltas)):
        average_gain = ((average_gain * (period - 1)) + gains[index]) / period
        average_loss = ((average_loss * (period - 1)) + losses[index]) / period

    if average_loss == 0:
        if average_gain == 0:
            return 50.0
        return 100.0

    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))
