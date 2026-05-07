# Crypto Trading Bot — BinanceTH

## What this project is
An automated crypto trading bot for **BinanceTH** (api.binance.th), trading USDT pairs.
- Strategy: EMA crossover (9/21) + RSI guards + volume + RSI slope
- Sends buy/sell/summary alerts via **LINE Messaging API**
- State (open positions) stored in `state.json`
- Scans every **15 minutes**, up to **10 positions**, with **top-up** on winners

## VPS Setup — COMPLETE ✅
- Server: DigitalOcean `ubuntu-s-1vcpu-1gb-sgp1`
- Bot user: `botuser`
- Repo path: `/home/botuser/crypto-bot-2026`
- Branch on VPS: `claude/setup-crypto-bot-repo-EjtEx`
- Python venv: `/home/botuser/crypto-bot-2026/venv`
- systemd service: `crypto-bot` (auto-restarts, runs 24/7)
- `.env` file: `/home/botuser/crypto-bot-2026/.env` (API keys, not in git)

### Useful VPS commands
```bash
# Status
sudo systemctl status crypto-bot

# Logs
sudo journalctl -u crypto-bot -n 50 --no-pager

# Pull latest code + restart
sudo -u botuser bash -c "cd /home/botuser/crypto-bot-2026 && git pull" && sudo systemctl restart crypto-bot

# Live portfolio check
sudo -u botuser bash -c "cd /home/botuser/crypto-bot-2026 && set -a && source .env && set +a && venv/bin/python -c \"
import json; from pathlib import Path; from bot.exchange import get_free_usdt, get_current_price
state = json.loads(Path('state.json').read_text())
usdt = get_free_usdt(); total = usdt
print(f'Free USDT: \${usdt:.2f}')
for sym, pos in state['positions'].items():
    price = get_current_price(sym); qty = float(pos['quantity']); entry = float(pos['entry_price'])
    val = qty * price; pnl = (price - entry) / entry * 100 if entry > 0 else 0; total += val
    print(f'  {sym}: {qty:.6g} @ \${entry:.4f} now \${price:.4f} ({pnl:+.2f}%) = \${val:.2f}')
print(f'Total: \${total:.2f}')
\""

# Check all signals
sudo -u botuser bash -c "cd /home/botuser/crypto-bot-2026 && set -a && source .env && set +a && venv/bin/python -c \"
from bot.exchange import get_candles
from bot.strategy import get_signal, calc_rsi, is_btc_bullish
from bot.config import TRADE_PAIRS
btc_ok = is_btc_bullish()
print(f'BTC: {\"✅ Bullish\" if btc_ok else \"❌ Bearish — buys paused\"}')
for sym in TRADE_PAIRS:
    prices, volumes = get_candles(sym)
    signal = get_signal(prices, volumes); rsi = round(calc_rsi(prices), 1)
    icon = {'BUY_STRONG':'🟢🟢','BUY':'🟢','HOLD':'⚪','SELL':'🔴','SELL_STRONG':'🔴🔴'}.get(signal,'⚪')
    print(f'  {icon} {sym:<12} RSI={rsi:<5} {signal}')
\""
```

## Key files
| File | Purpose |
|------|---------|
| `main.py` | Main loop — positions, buys, top-ups, summary |
| `bot/exchange.py` | BinanceTH REST API (auth, klines, orders) |
| `bot/strategy.py` | EMA + RSI signal + BTC market filter |
| `bot/config.py` | All risk params and trading pairs |
| `bot/notifier.py` | LINE push notifications (USDT formatting) |
| `state.json` | Open positions, cooldowns, realized P&L |

## Current strategy (as of 2026-05-06)

### Entry — ALL 4 must pass
1. EMA9 > EMA21 (uptrend)
2. RSI < 72 (not overbought)
3. Volume ≥ 1.5× 20-candle average
4. RSI rising vs 5 bars ago (momentum)
- RSI ≤ 45 → BUY_STRONG | RSI 46–71 → BUY

### BTC Market Filter
- BTC RSI < 40 → pause ALL altcoin buys (real crash only)
- BTC RSI ≥ 40 → buy normally (mild dips are fine)

### Position sizing (from ORIGINAL budget, not remaining)
| Signal | Coins | Size |
|--------|-------|------|
| BUY_STRONG | non-meme | 25% |
| BUY | non-meme | 12% |
| Any | PEPE/SHIB/DOGE | 10% |
| Top-up | any | 50% of above |

### Exit conditions
| Trigger | Value |
|---------|-------|
| Take Profit | +5% |
| Hard Stop Loss | -3% |
| Trailing Stop | 2.5% below peak price |
| Stale exit | 6h held + P&L ±1% |

### Top-up (adding to winners)
- Max 1 top-up per coin
- Only if P&L > +1% AND signal still BUY/BUY_STRONG
- Size = 50% of normal position
- Weighted average entry recalculated

### After stop loss
- 3-hour cooldown before re-buying same coin

## Risk settings
- Max positions: 10
- Reserve: 5% USDT never traded
- Min order: $5 USDT
- Meme coins (PEPE/SHIB/DOGE): capped at 10%

## 16 Trading pairs
BTC ETH SOL BNB XRP | DOGE ADA AVAX LINK DOT | TON SUI NEAR APT | PEPE SHIB

## API notes
- Base URL: `https://api.binance.th`
- Response format: `{"code": 0, "data": <payload>}` (klines returns raw list)
- Auth: HMAC-SHA256 on query params + `X-MBX-APIKEY` header
- Private: `/api/v1/accountV2` (balances), `/api/v1/order` (orders)
- Public: `/api/v1/klines` (candles)

## Git branches
- `main` — stable base
- `claude/setup-crypto-bot-repo-EjtEx` — **active dev branch** (always develop here)

## For new Claude sessions
Bot is **fully running on VPS**. The typical tasks are:
1. Improve strategy logic
2. Fix bugs from LINE notifications
3. Check signals / portfolio
4. Always develop on branch `claude/setup-crypto-bot-repo-EjtEx`
5. After pushing: tell user to run `git pull + systemctl restart crypto-bot` on VPS
