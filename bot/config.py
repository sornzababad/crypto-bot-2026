# ─── Risk Management ─────────────────────────────────────────────────────────
TAKE_PROFIT_PCT  = 0.060   # Sell when +6.0% profit (was 4%)
STOP_LOSS_PCT    = 0.030   # Initial hard stop -3.0% (was 2.5% — more room to breathe)
TRAIL_PCT        = 0.018   # Trailing stop 1.8% below peak (tighter to lock gains)
COOLDOWN_HOURS   = 3       # Skip re-buy for 3h after a stop loss on same coin
VOL_RATIO_MIN    = 1.5     # Volume must be 1.5x average — stricter confirmation (was 1.2x)
RSI_SLOPE_BARS   = 5       # RSI must be rising vs N bars ago to confirm momentum
MAX_POS_PCT      = 0.40    # Max 40% of tradeable THB per coin (was 30%)
MIN_ORDER_THB    = 350.0   # Minimum single order in THB (BinanceTH requires >300)
RESERVE_PCT      = 0.05    # Keep 5% cash reserve    (was 10%)
MAX_POSITIONS    = 5       # Hold at most 5 coins     (was 4)

# ─── EMA Settings ─────────────────────────────────────────────────────────────
EMA_FAST         = 9       # Fast EMA — more reactive (was 12)
EMA_SLOW         = 21      # Slow EMA — trend baseline (was 26)

# ─── RSI Guards (prevent entry in extreme conditions only) ────────────────────
RSI_OVERBOUGHT   = 72      # Don't BUY if RSI >= 72 (too hot)
RSI_OVERSOLD     = 28      # Don't SELL if RSI <= 28 (too cold, bounce risk)

# ─── OHLCV Settings ───────────────────────────────────────────────────────────
KLINE_TIMEFRAME  = '15m'   # 15-minute candles (was 1h — faster signals)
KLINE_LIMIT      = 200     # ~50 hours of data for reliable EMA/RSI

# ─── Target Trading Pairs on BinanceTH (THB quote) ───────────────────────────
TRADE_PAIRS = [
    # Confirmed available on BinanceTH
    'BTC/THB',
    'ETH/THB',
    'XRP/THB',
    'SOL/THB',
    'BNB/THB',
]
