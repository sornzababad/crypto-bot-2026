# Crypto Trading Bot — BinanceTH

## What this project is
An automated crypto trading bot for **BinanceTH** (api.binance.th), trading THB pairs.
- Strategy: EMA crossover (9/21) + RSI guards
- Sends buy/sell/summary alerts to **LINE Notify**
- State (open positions) stored in `state.json` and committed back to repo each run

## How the bot runs — TWO options

### Option A: GitHub Actions (already set up)
- Workflow: `.github/workflows/main.yml`
- Runs every 30 min automatically (free)
- Secrets set in GitHub repo settings: `BINANCE_KEY`, `BINANCE_SECRET`, `LINE_TOKEN`, `LINE_USER_ID`

### Option B: VPS on DigitalOcean (in progress)
- Server: `ubuntu-s-1vcpu-1gb-sgp1` (DigitalOcean)
- Bot user: `botuser`
- Repo path: `/home/botuser/crypto-bot-2026`
- Branch: `claude/setup-trading-bot-vps-lrMBl`
- Python venv: `/home/botuser/crypto-bot-2026/venv`

#### VPS setup status
- [x] Repo cloned to `/home/botuser/crypto-bot-2026`
- [x] Branch `claude/setup-trading-bot-vps-lrMBl` checked out
- [x] `python3 -m venv venv` done
- [x] `venv/bin/pip install -r requirements.txt` done
- [ ] Create `.env` file with API keys (see below)
- [ ] Test run manually: `cd /home/botuser/crypto-bot-2026 && set -a && source .env && set +a && venv/bin/python main.py`
- [ ] Set up cron job (every 30 min)
- [ ] Set up git credentials so bot can push `state.json`

#### .env file needed at `/home/botuser/crypto-bot-2026/.env`
```
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
LINE_TOKEN=...
LINE_USER_ID=...
```
Create with: `sudo -u botuser nano /home/botuser/crypto-bot-2026/.env`
Then: `chmod 600 /home/botuser/crypto-bot-2026/.env`

#### Cron job (add with `sudo -u botuser crontab -e`)
```
*/30 * * * * cd /home/botuser/crypto-bot-2026 && set -a && source .env && set +a && venv/bin/python main.py >> /home/botuser/bot.log 2>&1
```

## Key files
| File | Purpose |
|------|---------|
| `main.py` | Main entry point — orchestrates buy/sell/summary |
| `bot/exchange.py` | BinanceTH REST API client (auth, klines, orders) |
| `bot/strategy.py` | EMA + RSI signal logic |
| `bot/config.py` | Risk params (TP=4%, SL=2.5%, max 5 positions) |
| `bot/notifier.py` | LINE push notifications |
| `state.json` | Persisted open positions + last summary timestamp |

## API notes
- BinanceTH base URL: `https://api.binance.th`
- All responses wrapped: `{"code": 0, "data": <payload>}`
- Auth: HMAC-SHA256 signature on query params + `X-MBX-APIKEY` header
- Private endpoints: `/api/v1/accountV2` (balances), `/api/v1/order` (place/query)
- Public endpoints: `/api/v1/klines` (candles)

## Git branches
- `main` — stable base
- `claude/setup-crypto-bot-repo-EjtEx` — main development branch (THIS SESSION)
- `claude/setup-trading-bot-vps-lrMBl` — VPS deployment branch (checked out on VPS)

## Current task for new Claude sessions
**Continue VPS setup.** The user is on the DigitalOcean web console as root.
Next step: create `.env` file then test run the bot manually.
