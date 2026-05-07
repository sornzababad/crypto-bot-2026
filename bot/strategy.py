from bot.config import EMA_FAST, EMA_SLOW, RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD


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


def calc_rsi(prices: list[float], period: int = RSI_PERIOD) -> float:
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
    EMA Crossover strategy with RSI filters for frequent trading.

    Logic:
      - Detect EMA_FAST crossing above EMA_SLOW → BUY (bullish crossover)
      - Detect EMA_FAST crossing below EMA_SLOW → SELL (bearish crossover)
      - RSI filters prevent entries in extreme conditions (optional for more trades)

    Returns: 'BUY' | 'SELL' | 'HOLD'
    """
    if len(prices) < EMA_SLOW + 1:  # Need extra candle for previous EMA
        return 'HOLD'

    rsi = calc_rsi(prices)
    
    # Current EMAs
    ema_f = calc_ema(prices, EMA_FAST)
    ema_s = calc_ema(prices, EMA_SLOW)
    
    # Previous EMAs (using prices[:-1])
    prev_prices = prices[:-1]
    prev_ema_f = calc_ema(prev_prices, EMA_FAST)
    prev_ema_s = calc_ema(prev_prices, EMA_SLOW)
    
    # Detect crossovers
    prev_uptrend = prev_ema_f > prev_ema_s
    curr_uptrend = ema_f > ema_s
    
    if not prev_uptrend and curr_uptrend:  # Bullish crossover
        if rsi < RSI_OVERBOUGHT:  # Optional filter: not too overbought
            return 'BUY'
    elif prev_uptrend and not curr_uptrend:  # Bearish crossover
        if rsi > RSI_OVERSOLD:  # Optional filter: not too oversold
            return 'SELL'
    
    return 'HOLD'
