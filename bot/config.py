# ─── Risk Management ─────────────────────────────────────────────────────────
TAKE_PROFIT_PCT  = 0.025   # Sell when +2.5% profit
STOP_LOSS_PCT    = 0.030   # Sell when -3.0% loss
MAX_POS_PCT      = 0.25    # Max 25% of tradeable THB per coin
MIN_ORDER_THB    = 200.0   # Minimum single order in THB
RESERVE_PCT      = 0.10    # Always keep 10% of balance in THB (never trade)
MAX_POSITIONS    = 4       # Hold at most 4 coins at once

# ─── Signal Thresholds (RSI-14) ───────────────────────────────────────────────
RSI_BUY_STRONG   = 30      # RSI <= 30 → strong buy regardless of EMA
RSI_BUY_NORMAL   = 42      # RSI <= 42 + uptrend (EMA12 > EMA26) → buy
RSI_SELL_NORMAL  = 58      # RSI >= 58 + downtrend → sell
RSI_SELL_STRONG  = 70      # RSI >= 70 → strong sell regardless of EMA

# ─── OHLCV Settings ───────────────────────────────────────────────────────────
KLINE_TIMEFRAME  = '1h'    # Hourly candles
KLINE_LIMIT      = 72      # 3 days of data (enough for RSI-14 + EMA-26)

# ─── Target Trading Pairs on BinanceTH (THB quote) ───────────────────────────
TRADE_PAIRS = [
    'BTC/THB',
    'ETH/THB',
    'BNB/THB',
    'XRP/THB',
    'SOL/THB',
    'DOGE/THB',
    'ADA/THB',
]
