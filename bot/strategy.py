from bot.config import EMA_FAST, EMA_SLOW, RSI_OVERBOUGHT, RSI_OVERSOLD


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
    EMA State-primary strategy with RSI guards.

    Logic:
      - EMA_FAST > EMA_SLOW  →  uptrend  →  BUY  (unless RSI overbought)
      - EMA_FAST < EMA_SLOW  →  downtrend →  SELL (unless RSI oversold)
      - RSI guards only block entries in extreme conditions to avoid chasing

    Returns: 'BUY_STRONG' | 'BUY' | 'HOLD' | 'SELL' | 'SELL_STRONG'
    """
    if len(prices) < EMA_SLOW:
        return 'HOLD'

    rsi     = calc_rsi(prices)
    ema_f   = calc_ema(prices, EMA_FAST)
    ema_s   = calc_ema(prices, EMA_SLOW)
    uptrend = ema_f > ema_s

    if uptrend:
        if rsi >= RSI_OVERBOUGHT:
            return 'HOLD'          # trending up but too hot — wait for cooldown
        if rsi <= 40:
            return 'BUY_STRONG'    # uptrend + deeply oversold = strong entry
        return 'BUY'               # uptrend — standard entry

    else:  # downtrend
        if rsi <= RSI_OVERSOLD:
            return 'HOLD'          # trending down but too cold — bounce risk
        if rsi >= 65:
            return 'SELL_STRONG'   # downtrend + overbought = strong exit
        return 'SELL'              # downtrend — standard exit
