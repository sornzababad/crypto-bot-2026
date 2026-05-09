from bot.config import (
    EMA_FAST, EMA_SLOW, RSI_OVERBOUGHT, RSI_OVERSOLD,
    VOL_RATIO_MIN, RSI_SLOPE_BARS,
    ADX_PERIOD, ADX_THRESHOLD, BB_LENGTH, BB_STD,
)


# ─── Basic indicators ─────────────────────────────────────────────────────────

def calc_ema(prices: list, period: int) -> float:
    if not prices:
        return 0.0
    if len(prices) < period:
        return prices[-1]
    k   = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


def calc_rsi(prices: list, period: int = 14) -> float:
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


def vol_ratio(volumes: list) -> float:
    """Current candle volume vs average of prior 20 candles."""
    if len(volumes) < 2:
        return 1.0
    avg = sum(volumes[-21:-1]) / min(len(volumes) - 1, 20)
    return volumes[-1] / avg if avg > 0 else 1.0


# ─── Regime indicators ────────────────────────────────────────────────────────

def _wilder_smooth(data: list, period: int) -> list:
    """Wilder's Moving Average (RMA). First value = sum of first `period` bars."""
    if len(data) < period:
        return []
    result = [sum(data[:period])]
    for i in range(period, len(data)):
        result.append(result[-1] - result[-1] / period + data[i])
    return result


def calc_adx(closes: list, highs: list, lows: list, period: int = 14) -> float:
    """Average Directional Index (ADX). Returns 0–100; higher = stronger trend."""
    if len(closes) < period * 2 + 1:
        return 0.0

    tr_list, pdm_list, ndm_list = [], [], []
    for i in range(1, len(closes)):
        tr   = max(highs[i] - lows[i],
                   abs(highs[i] - closes[i - 1]),
                   abs(lows[i]  - closes[i - 1]))
        up   = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        tr_list.append(tr)
        pdm_list.append(up   if up   > down and up   > 0 else 0.0)
        ndm_list.append(down if down > up   and down > 0 else 0.0)

    s_tr  = _wilder_smooth(tr_list,  period)
    s_pdm = _wilder_smooth(pdm_list, period)
    s_ndm = _wilder_smooth(ndm_list, period)

    dx_list = []
    for i in range(len(s_tr)):
        if s_tr[i] == 0:
            continue
        pdi   = 100 * s_pdm[i] / s_tr[i]
        ndi   = 100 * s_ndm[i] / s_tr[i]
        total = pdi + ndi
        dx_list.append(100 * abs(pdi - ndi) / total if total > 0 else 0.0)

    if len(dx_list) < period:
        return 0.0

    # ADX = Wilder smooth of DX
    adx = sum(dx_list[:period]) / period
    for i in range(period, len(dx_list)):
        adx = (adx * (period - 1) + dx_list[i]) / period
    return adx


def calc_bollinger_bands(closes: list, length: int = 20, std_mult: float = 2.0) -> tuple:
    """Returns (upper, middle, lower) Bollinger Bands."""
    if len(closes) < length:
        c = closes[-1]
        return c, c, c
    recent = closes[-length:]
    middle = sum(recent) / length
    std    = (sum((p - middle) ** 2 for p in recent) / length) ** 0.5
    return middle + std_mult * std, middle, middle - std_mult * std


# ─── Regime detection ─────────────────────────────────────────────────────────

def get_regime(closes: list, highs: list, lows: list) -> str:
    """Returns 'trend' or 'sideways' based on ADX(14)."""
    adx = calc_adx(closes, highs, lows, ADX_PERIOD)
    return 'trend' if adx >= ADX_THRESHOLD else 'sideways'


# ─── Entry signals per regime ─────────────────────────────────────────────────

def _trend_signal(closes: list, volumes: list) -> str:
    """
    Momentum strategy for trending markets.
    All 4 must pass: EMA9>EMA21, RSI<72, Volume≥1.5x avg, RSI rising.
    """
    if len(closes) < EMA_SLOW:
        return 'HOLD'

    rsi        = calc_rsi(closes)
    ema_f      = calc_ema(closes, EMA_FAST)
    ema_s      = calc_ema(closes, EMA_SLOW)
    uptrend    = ema_f > ema_s
    vr         = vol_ratio(volumes) if volumes else 1.0
    rsi_prev   = calc_rsi(closes[:-RSI_SLOPE_BARS]) if len(closes) > RSI_SLOPE_BARS + 15 else rsi
    rsi_rising = rsi > rsi_prev

    if uptrend:
        if rsi >= RSI_OVERBOUGHT:  return 'HOLD'
        if vr  <  VOL_RATIO_MIN:   return 'HOLD'
        if not rsi_rising:         return 'HOLD'
        return 'BUY_STRONG' if rsi <= 45 else 'BUY'
    else:
        if rsi <= RSI_OVERSOLD: return 'HOLD'
        return 'SELL_STRONG' if rsi >= 65 else 'SELL'


def _sideways_signal(closes: list) -> str:
    """
    Mean reversion strategy for sideways markets.
    BUY: price <= lower BB AND RSI < 40.
    """
    if len(closes) < BB_LENGTH:
        return 'HOLD'

    rsi          = calc_rsi(closes)
    _, _, bb_low = calc_bollinger_bands(closes, BB_LENGTH, BB_STD)

    if closes[-1] <= bb_low and rsi < 40:
        return 'BUY'
    return 'HOLD'


# ─── Main entry point ─────────────────────────────────────────────────────────

def get_signal(closes: list, highs: list, lows: list,
               volumes: list | None = None) -> tuple[str, str]:
    """
    Returns (signal, regime).
    regime: 'trend' | 'sideways'
    signal: 'BUY_STRONG' | 'BUY' | 'HOLD' | 'SELL' | 'SELL_STRONG'
    """
    regime = get_regime(closes, highs, lows)
    if regime == 'trend':
        signal = _trend_signal(closes, volumes)
    else:
        signal = _sideways_signal(closes)
    return signal, regime


# ─── Global market filter ─────────────────────────────────────────────────────

def is_btc_bullish() -> bool:
    """Returns False only when BTC RSI < 40 (real panic selling)."""
    try:
        from bot.exchange import get_candles
        closes, _, _, _ = get_candles('BTC/USDT')
        return calc_rsi(closes) >= 40
    except Exception:
        return True
