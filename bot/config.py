# ─── Risk Management ─────────────────────────────────────────────────────────
TAKE_PROFIT_PCT  = 0.040   # Sell when +4.0% profit  (was 2.5%)
STOP_LOSS_PCT    = 0.025   # Sell when -2.5% loss    (was 3.0%)
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
