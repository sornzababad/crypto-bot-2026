# ─── Risk Management ─────────────────────────────────────────────────────────
TAKE_PROFIT_PCT  = 0.035   # Sell when +3.5% profit
STOP_LOSS_PCT    = 0.020   # Sell when -2.0% loss (tighter cut)
MAX_POS_PCT      = 0.20    # Max 20% of tradeable THB per coin
MIN_ORDER_THB    = 200.0   # Minimum single order in THB
RESERVE_PCT      = 0.10    # Keep 10% cash reserve
MAX_POSITIONS    = 3       # Hold at most 3 coins (reduce overexposure)

# ─── EMA Settings ─────────────────────────────────────────────────────────────
EMA_FAST         = 9       # Fast EMA — more reactive (was 12)
EMA_SLOW         = 21      # Slow EMA — trend baseline (was 26)

# ─── RSI Settings ───────────────────────────────────────────────────────────
RSI_PERIOD       = 14     # RSI calculation period
RSI_OVERBOUGHT   = 72      # Don't BUY if RSI >= 72 (too hot)
RSI_OVERSOLD     = 28      # Don't SELL if RSI <= 28 (too cold, bounce risk)

# ─── Trend Filters ───────────────────────────────────────────────────────────
TREND_STRENGTH_MIN = 0.005   # Minimum EMA separation (0.5%) for valid trend
CONFIRMATION_BUFFER = 0.001  # Price must close 0.1% beyond EMA for confirmation

# ─── Fees & execution ─────────────────────────────────────────────────────────
FEE_PCT = 0.001              # BinanceTH fee per side (0.1%)
FEE_ROUND_TRIP_PCT = FEE_PCT * 2  # buy + sell

# ─── OHLCV Settings ───────────────────────────────────────────────────────────
KLINE_TIMEFRAME  = '30m'    # More frequent signals than 1h
KLINE_LIMIT      = 72      # 72 candles

# ─── Target Trading Pairs on BinanceTH (THB quote) ───────────────────────────
TRADE_PAIRS = [
    # Tier 1 only — highest liquidity, most reliable signals
    'BTC/THB',
    'ETH/THB',
    'XRP/THB',
    'SOL/THB',
    'BNB/THB',
]
