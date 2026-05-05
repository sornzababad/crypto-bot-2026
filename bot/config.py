# ─── Risk Management ─────────────────────────────────────────────────────────
TAKE_PROFIT_PCT  = 0.040   # Sell when +4.0% profit
STOP_LOSS_PCT    = 0.025   # Initial hard stop -2.5% (fallback if no peak yet)
TRAIL_PCT        = 0.020   # Trailing stop: SL trails 2% below highest price since entry
COOLDOWN_HOURS   = 3       # Skip re-buy for 3h after a stop loss on same coin
VOL_RATIO_MIN    = 1.2     # Current candle volume must be >= 1.2x recent avg to confirm buy
MAX_POS_PCT      = 0.30    # Max 30% of tradeable THB per coin (was 25%)
MIN_ORDER_THB    = 200.0   # Minimum single order in THB
RESERVE_PCT      = 0.05    # Keep 5% cash reserve    (was 10%)
MAX_POSITIONS    = 5       # Hold at most 5 coins     (was 4)

# ─── EMA Settings ─────────────────────────────────────────────────────────────
EMA_FAST         = 9       # Fast EMA — more reactive (was 12)
EMA_SLOW         = 21      # Slow EMA — trend baseline (was 26)

# ─── RSI Guards (prevent entry in extreme conditions only) ────────────────────
RSI_OVERBOUGHT   = 72      # Don't BUY if RSI >= 72 (too hot)
RSI_OVERSOLD     = 28      # Don't SELL if RSI <= 28 (too cold, bounce risk)

# ─── OHLCV Settings ───────────────────────────────────────────────────────────
KLINE_TIMEFRAME  = '1h'    # Hourly candles
KLINE_LIMIT      = 72      # 3 days of data

# ─── Target Trading Pairs on BinanceTH (THB quote) ───────────────────────────
TRADE_PAIRS = [
    # Confirmed available on BinanceTH
    'BTC/THB',
    'ETH/THB',
    'XRP/THB',
    'SOL/THB',
    'BNB/THB',
]
