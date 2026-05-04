# ─── Risk Management ─────────────────────────────────────────────────────────
TAKE_PROFIT_PCT  = 0.025   # Sell when +2.5% profit
STOP_LOSS_PCT    = 0.030   # Sell when -3.0% loss
MAX_POS_PCT      = 0.25    # Max 25% of tradeable THB per coin
MIN_ORDER_THB    = 200.0   # Minimum single order in THB
RESERVE_PCT      = 0.10    # Always keep 10% of balance in THB (never trade)
MAX_POSITIONS    = 4       # Hold at most 4 coins at once

# ─── Signal Thresholds (RSI-14) ───────────────────────────────────────────────
RSI_BUY_STRONG   = 38      # RSI <= 38 → strong buy regardless of EMA
RSI_BUY_NORMAL   = 50      # RSI <= 50 + uptrend (EMA12 > EMA26) → buy
RSI_SELL_NORMAL  = 52      # RSI >= 52 + downtrend → sell
RSI_SELL_STRONG  = 62      # RSI >= 62 → strong sell regardless of EMA

# ─── OHLCV Settings ───────────────────────────────────────────────────────────
KLINE_TIMEFRAME  = '1h'    # Hourly candles
KLINE_LIMIT      = 72      # 3 days of data (enough for RSI-14 + EMA-26)

# ─── Target Trading Pairs on BinanceTH (THB quote) ───────────────────────────
# Bot scans all pairs every 15 min but holds MAX_POSITIONS (4) at most.
# Pairs ranked by volatility + liquidity — higher chance of hitting signals.
TRADE_PAIRS = [
    # Tier 1 — highest liquidity, most reliable signals
    'BTC/THB',
    'ETH/THB',
    'XRP/THB',
    'SOL/THB',
    'BNB/THB',
    # Tier 2 — high volatility, good for short-term gains
    'DOGE/THB',
    'ADA/THB',
    'AVAX/THB',
    'LINK/THB',
    'DOT/THB',
    # Tier 3 — smaller coins, higher risk/reward
    'LTC/THB',
    'TRX/THB',
    'NEAR/THB',
    'TON/THB',
    'POL/THB',
]
