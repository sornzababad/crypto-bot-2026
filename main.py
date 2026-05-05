"""
Crypto Trading Bot — BinanceTH
Runs every 15 min via GitHub Actions (free).

Flow each run:
  1. Load state (open positions) from state.json
  2. Check each open position → sell if stop-loss or take-profit hit
  3. Scan all target pairs for buy signals → open new positions
  4. Send hourly portfolio summary to LINE
  5. Save updated state back to state.json (committed by workflow)
"""

import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from bot.config import (
    TAKE_PROFIT_PCT, STOP_LOSS_PCT, TRAIL_PCT, COOLDOWN_HOURS,
    MAX_POS_PCT, MIN_ORDER_THB, RESERVE_PCT,
    MAX_POSITIONS, TRADE_PAIRS,
)
from bot.exchange import (
    get_candles,
    get_free_thb,
    get_coin_balance,
    get_current_price,
    place_market_buy,
    place_market_sell,
)
from bot.strategy import get_signal, calc_rsi
from bot.notifier import (
    notify_buy, notify_sell, notify_summary, notify_error,
)

STATE_FILE    = Path('state.json')
SUMMARY_EVERY = 1800  # seconds between portfolio summaries (every 30-min run)


# ─── State helpers ────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {'positions': {}, 'last_summary_ts': 0, 'initial_thb': 0, 'cooldowns': {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ─── Main ─────────────────────────────────────────────────────────────────────

def run():
    state = load_state()

    thb_balance = get_free_thb()
    total_value = thb_balance
    pnl_map     = {}

    # ── Step 1: Manage open positions (stop-loss / take-profit) ───────────────
    print(f"\n=== Open positions: {list(state['positions'].keys())} ===")

    for symbol, pos in list(state['positions'].items()):
        coin = symbol.split('/')[0]
        try:
            qty           = float(pos['quantity'])
            entry_price   = float(pos['entry_price'])
            current_price = get_current_price(symbol)
            coin_value    = qty * current_price
            total_value  += coin_value
            pnl_pct       = (current_price - entry_price) / entry_price * 100
            pnl_map[symbol] = {'pnl_pct': pnl_pct}

            print(f"  {symbol}: entry={entry_price:.2f} now={current_price:.2f}"
                  f" pnl={pnl_pct:+.2f}%")

            # update trailing high
            highest = max(current_price, float(pos.get('highest_price', entry_price)))
            pos['highest_price'] = highest
            trail_sl  = highest * (1 - TRAIL_PCT)
            hard_sl   = entry_price * (1 - STOP_LOSS_PCT)
            active_sl = max(trail_sl, hard_sl)  # whichever is higher protects more

            should_sell = False
            reason      = ''
            is_stop_loss = False

            if pnl_pct >= TAKE_PROFIT_PCT * 100:
                should_sell = True
                reason      = f'Take Profit +{pnl_pct:.2f}%'
            elif current_price <= active_sl:
                should_sell  = True
                is_stop_loss = True
                if current_price <= hard_sl:
                    reason = f'Hard Stop Loss {pnl_pct:.2f}%'
                else:
                    reason = f'Trailing Stop {pnl_pct:.2f}% (peak {highest:,.0f})'

            print(f"  {symbol}: entry={entry_price:.2f} now={current_price:.2f}"
                  f" peak={highest:.2f} sl={active_sl:.2f} pnl={pnl_pct:+.2f}%")

            if should_sell:
                actual_qty = get_coin_balance(coin)
                if actual_qty > 0:
                    order        = place_market_sell(symbol, actual_qty)
                    filled_price = float(order.get('fills', [{}])[0].get('price', 0) or current_price)
                    thb_returned = actual_qty * filled_price
                    invested_thb = float(pos.get('invested_thb', thb_returned))
                    realized_thb = thb_returned - invested_thb
                    state['realized_pnl_thb'] = state.get('realized_pnl_thb', 0) + realized_thb
                    notify_sell(symbol, filled_price, actual_qty,
                                thb_returned, reason, pnl_pct)
                    print(f"  SOLD {symbol}: {reason}")
                    if is_stop_loss:
                        state.setdefault('cooldowns', {})[symbol] = int(datetime.now(timezone.utc).timestamp())
                else:
                    print(f"  {symbol}: no balance found — removing from state")
                del state['positions'][symbol]
                pnl_map.pop(symbol, None)

            time.sleep(0.5)
        except Exception:
            traceback.print_exc()

    # ── Step 2: Look for new buy opportunities ────────────────────────────────
    open_count    = len(state['positions'])
    thb_balance   = get_free_thb()
    tradeable_thb = thb_balance * (1 - RESERVE_PCT)

    print(f"\n=== Scanning for buys | THB: {tradeable_thb:.0f}"
          f" | positions: {open_count}/{MAX_POSITIONS} ===")

    scan_results = []  # collect RSI snapshot for summary

    for symbol in TRADE_PAIRS:
        if open_count >= MAX_POSITIONS:
            print(f"  Max positions ({MAX_POSITIONS}) reached")
            break
        if symbol in state['positions']:
            continue

        # skip cooldown period after a stop loss
        now_ts    = int(datetime.now(timezone.utc).timestamp())
        cooled_at = state.get('cooldowns', {}).get(symbol, 0)
        if now_ts - cooled_at < COOLDOWN_HOURS * 3600:
            remaining = int((COOLDOWN_HOURS * 3600 - (now_ts - cooled_at)) / 60)
            print(f"  {symbol}: cooldown {remaining}min remaining")
            continue

        try:
            prices, volumes = get_candles(symbol)
            signal = get_signal(prices, volumes)
            rsi    = round(calc_rsi(prices), 1)
            print(f"  {symbol}: RSI={rsi} signal={signal}")
            scan_results.append((symbol, rsi, signal))

            if signal in ('BUY', 'BUY_STRONG'):
                thb_to_use = max(tradeable_thb * MAX_POS_PCT, MIN_ORDER_THB)

                if thb_to_use > tradeable_thb:
                    print(f"  Not enough THB for {symbol}")
                    continue

                order      = place_market_buy(symbol, thb_to_use)
                fills      = order.get('fills', [])
                filled_qty = float(order.get('executedQty') or sum(float(f['qty']) for f in fills) or 0)
                avg_price  = (
                    float(order.get('cummulativeQuoteQty', 0)) / filled_qty
                    if filled_qty > 0 else get_current_price(symbol)
                )

                if filled_qty <= 0:
                    filled_qty = thb_to_use / avg_price

                invested_thb = filled_qty * avg_price

                state['positions'][symbol] = {
                    'quantity':      filled_qty,
                    'entry_price':   avg_price,
                    'highest_price': avg_price,
                    'entry_time':    datetime.now(timezone.utc).isoformat(),
                    'invested_thb':  invested_thb,
                }

                notify_buy(symbol, avg_price, filled_qty, invested_thb, rsi, signal)
                print(f"  BOUGHT {filled_qty:.6g} {symbol} @ {avg_price:.2f} ({invested_thb:.0f} THB)")

                tradeable_thb -= invested_thb
                open_count    += 1

            time.sleep(1.0)
        except Exception:
            traceback.print_exc()

    # ── Step 3: Hourly portfolio summary ──────────────────────────────────────
    now_ts = int(datetime.now(timezone.utc).timestamp())  # noqa: F841 (reuse ok)
    if now_ts - state.get('last_summary_ts', 0) >= SUMMARY_EVERY:
        final_thb  = get_free_thb()
        coin_total = 0.0
        for symbol, pos in state['positions'].items():
            try:
                coin_total += float(pos['quantity']) * get_current_price(symbol)
            except Exception:
                pass
        total_value = final_thb + coin_total
        notify_summary(final_thb, total_value, pnl_map,
                       state.get('realized_pnl_thb', 0.0), scan_results)
        state['last_summary_ts'] = now_ts

    save_state(state)
    print(f"\nDone. THB: {get_free_thb():.0f} | Positions: {list(state['positions'].keys())}")


SCAN_INTERVAL = 1800  # 30 minutes between scans

if __name__ == '__main__':
    print("Bot starting — continuous mode (scan every 30 min)")
    while True:
        start = time.time()
        try:
            run()
        except Exception as e:
            traceback.print_exc()
            notify_error(str(e))
        elapsed = time.time() - start
        sleep_for = max(0, SCAN_INTERVAL - elapsed)
        print(f"Sleeping {sleep_for:.0f}s until next scan...")
        time.sleep(sleep_for)
