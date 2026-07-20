PAIR_UNIVERSE_TOP_150 = "top_150"
PAIR_UNIVERSE_POPULAR_30 = "popular_30"

PAIR_UNIVERSE_OPTIONS = (
    PAIR_UNIVERSE_TOP_150,
    PAIR_UNIVERSE_POPULAR_30,
)

PAIR_UNIVERSE_LABELS = {
    PAIR_UNIVERSE_TOP_150: "Топ-150 по объему",
    PAIR_UNIVERSE_POPULAR_30: "Популярные 30",
}

POPULAR_30_USDT_PAIRS = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "TRX/USDT",
    "TON/USDT",
    "SUI/USDT",
    "LTC/USDT",
    "BCH/USDT",
    "DOT/USDT",
    "UNI/USDT",
    "AAVE/USDT",
    "NEAR/USDT",
    "ETC/USDT",
    "FIL/USDT",
    "ATOM/USDT",
    "ARB/USDT",
    "OP/USDT",
    "INJ/USDT",
    "WLD/USDT",
    "PEPE/USDT",
    "SHIB/USDT",
    "BONK/USDT",
    "MNT/USDT",
    "ONDO/USDT",
)


def pair_universe_label(pair_universe: str) -> str:
    return PAIR_UNIVERSE_LABELS.get(pair_universe, pair_universe)


def fixed_symbols_for_pair_universe(pair_universe: str) -> tuple[str, ...] | None:
    if pair_universe == PAIR_UNIVERSE_POPULAR_30:
        return POPULAR_30_USDT_PAIRS
    return None
