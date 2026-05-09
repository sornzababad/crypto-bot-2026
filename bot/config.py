# ─── Risk Management ─────────────────────────────────────────────────────────
# NO fixed Take Profit — trailing stop handles trend exits, BB mid handles sideways
STOP_LOSS_PCT    = 0.030   # Trend hard stop -3% from avg entry
TRAIL_PCT        = 0.025   # Trend trailing stop 2.5% below peak price
SL_SIDEWAYS      = 0.020   # Sideways hard stop -2% (tighter, expect quick bounce)

# ─── Market Regime Detection ──────────────────────────────────────────────────
ADX_PERIOD       = 14      # ADX smoothing period
ADX_THRESHOLD    = 25      # ADX < 25 = sideways (mean reversion), >= 25 = trend (momentum)
BB_LENGTH        = 20      # Bollinger Bands period
BB_STD           = 2.0     # Bollinger Bands standard deviation multiplier
COOLDOWN_HOURS   = 3       # Skip re-buy for 3h after a stop loss on same coin
VOL_RATIO_MIN    = 1.5     # Volume must be 1.5x average to confirm buy
RSI_SLOPE_BARS   = 5       # RSI must be rising vs N bars ago to confirm momentum
MAX_POS_PCT        = 0.12  # Max 12% per coin (BUY signal) — ~8 BUYs = full deploy
MAX_POS_PCT_STRONG = 0.25  # Max 25% per coin (BUY_STRONG signal)
MAX_POS_PCT_MEME   = 0.10  # Max 10% for meme coins (PEPE/SHIB/DOGE)
MEME_PAIRS         = {'PEPE/USDT', 'SHIB/USDT', 'DOGE/USDT'}
MIN_ORDER_USDT     = 5.0   # Minimum single order in USDT
RESERVE_PCT        = 0.05  # Keep 5% USDT reserve
MAX_POSITIONS      = 10    # Hold at most 10 coins
STALE_HOURS        = 6     # Exit flat positions after 6 hours
STALE_BAND_PCT     = 1.0   # "Flat" = P&L between -1% and +1%

# ─── EMA Settings ─────────────────────────────────────────────────────────────
EMA_FAST         = 9       # Fast EMA
EMA_SLOW         = 21      # Slow EMA

# ─── RSI Guards ───────────────────────────────────────────────────────────────
RSI_OVERBOUGHT   = 72      # Don't BUY if RSI >= 72
RSI_OVERSOLD     = 28      # Don't SELL if RSI <= 28

# ─── OHLCV Settings ───────────────────────────────────────────────────────────
KLINE_TIMEFRAME  = '15m'   # 15-minute candles
KLINE_LIMIT      = 200     # ~50 hours of data for reliable EMA/RSI

# ─── Target Trading Pairs on BinanceTH (USDT quote) ──────────────────────────
TRADE_PAIRS = [
    # Big cap — reliable signals, high volume
    'BTC/USDT',
    'ETH/USDT',
    'SOL/USDT',
    'BNB/USDT',
    'XRP/USDT',
    # High volatility — good for daily trading
    'DOGE/USDT',
    'ADA/USDT',
    'AVAX/USDT',
    'LINK/USDT',
    'DOT/USDT',
    # Trending — high momentum
    'TON/USDT',
    'SUI/USDT',
    'NEAR/USDT',
    'APT/USDT',
    # High risk/reward — volatile meme coins
    'PEPE/USDT',
    'SHIB/USDT',
]
