from bot.config import EMA_FAST, EMA_SLOW, RSI_OVERBOUGHT, RSI_OVERSOLD, VOL_RATIO_MIN, RSI_SLOPE_BARS


def is_btc_bullish() -> bool:
    """Returns True if BTC EMA9 > EMA21. If check fails, assume bullish to not block trading."""
    try:
        from bot.exchange import get_candles
        prices, _ = get_candles('BTC/USDT')
        return calc_ema(prices, EMA_FAST) > calc_ema(prices, EMA_SLOW)
    except Exception:
        return True


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


def vol_ratio(volumes: list[float]) -> float:
    """Current candle volume vs average of prior 20 candles."""
    if len(volumes) < 2:
        return 1.0
    avg = sum(volumes[-21:-1]) / min(len(volumes) - 1, 20)
    return volumes[-1] / avg if avg > 0 else 1.0


def get_signal(prices: list[float], volumes: list[float] | None = None) -> str:
    """
    EMA crossover strategy with RSI guards and volume confirmation.

    Returns: 'BUY_STRONG' | 'BUY' | 'HOLD' | 'SELL' | 'SELL_STRONG'
    """
    if len(prices) < EMA_SLOW:
        return 'HOLD'

    rsi     = calc_rsi(prices)
    ema_f   = calc_ema(prices, EMA_FAST)
    ema_s   = calc_ema(prices, EMA_SLOW)
    uptrend = ema_f > ema_s
    vr      = vol_ratio(volumes) if volumes else 1.0

    rsi_prev    = calc_rsi(prices[:-RSI_SLOPE_BARS]) if len(prices) > RSI_SLOPE_BARS + 15 else rsi
    rsi_rising  = rsi > rsi_prev

    if uptrend:
        if rsi >= RSI_OVERBOUGHT:
            return 'HOLD'
        if vr < VOL_RATIO_MIN:
            return 'HOLD'          # signal not confirmed by volume
        if not rsi_rising:
            return 'HOLD'          # momentum fading — skip entry
        if rsi <= 45:
            return 'BUY_STRONG'
        return 'BUY'

    else:
        if rsi <= RSI_OVERSOLD:
            return 'HOLD'
        if rsi >= 65:
            return 'SELL_STRONG'
        return 'SELL'
