from bot.config import RSI_BUY_STRONG, RSI_BUY_NORMAL, RSI_SELL_NORMAL, RSI_SELL_STRONG


def calc_ema(prices: list[float], period: int) -> float:
    if not prices:
        return 0.0
    if len(prices) < period:
        return prices[-1]
    k   = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


def calc_rsi(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains   = [max(c, 0.0) for c in changes]
    losses  = [abs(min(c, 0.0)) for c in changes]
    ag = sum(gains[:period])  / period
    al = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        ag = (ag * (period - 1) + gains[i])  / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + ag / al))


def get_signal(prices: list[float]) -> str:
    """
    Returns one of: 'BUY_STRONG', 'BUY', 'HOLD', 'SELL', 'SELL_STRONG'
    Requires at least 26 prices for EMA-26 to be meaningful.
    """
    if len(prices) < 26:
        return 'HOLD'

    rsi     = calc_rsi(prices)
    ema12   = calc_ema(prices, 12)
    ema26   = calc_ema(prices, 26)
    uptrend = ema12 > ema26

    if rsi <= RSI_BUY_STRONG:
        return 'BUY_STRONG'
    if rsi <= RSI_BUY_NORMAL and uptrend:
        return 'BUY'
    if rsi >= RSI_SELL_STRONG:
        return 'SELL_STRONG'
    if rsi >= RSI_SELL_NORMAL and not uptrend:
        return 'SELL'
    return 'HOLD'
