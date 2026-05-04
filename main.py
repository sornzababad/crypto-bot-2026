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
    TAKE_PROFIT_PCT, STOP_LOSS_PCT,
    MAX_POS_PCT, MIN_ORDER_THB, RESERVE_PCT,
    MAX_POSITIONS, TRADE_PAIRS,
)
from bot.exchange import (
    create_exchange,
    get_closing_prices,
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
SUMMARY_EVERY = 3600  # seconds between portfolio summaries


# ─── State helpers ────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {'positions': {}, 'last_summary_ts': 0, 'initial_thb': 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ─── Main ────────────────────────────────────────────────────────────────────

def run():
    state    = load_state()
    exchange = create_exchange()

    # Snapshot free THB at start of run
    thb_balance = get_free_thb(exchange)
    total_value = thb_balance  # will add coin values below
    pnl_map     = {}           # symbol → {'pnl_pct': float}

    # Remember initial investment for overall P&L calculation
    if state.get('initial_thb', 0) == 0 and thb_balance > 0:
        state['initial_thb'] = thb_balance
        print(f"First run — recording initial balance: {thb_balance:.0f} THB")

    # ── Step 1: Manage open positions (stop-loss / take-profit) ───────────────
    print(f"\n=== Open positions: {list(state['positions'].keys())} ===")

    for symbol, pos in list(state['positions'].items()):
        coin = symbol.split('/')[0]
        try:
            qty          = float(pos['quantity'])
            entry_price  = float(pos['entry_price'])
            current_price = get_current_price(exchange, symbol)
            coin_value   = qty * current_price
            total_value += coin_value
            pnl_pct      = (current_price - entry_price) / entry_price * 100
            pnl_map[symbol] = {'pnl_pct': pnl_pct}

            print(f"  {symbol}: entry={entry_price:.2f} now={current_price:.2f}"
                  f" pnl={pnl_pct:+.2f}%")

            should_sell = False
            reason      = ''

            if pnl_pct >= TAKE_PROFIT_PCT * 100:
                should_sell = True
                reason      = f'Take Profit +{pnl_pct:.2f}%'
            elif pnl_pct <= -(STOP_LOSS_PCT * 100):
                should_sell = True
                reason      = f'Stop Loss {pnl_pct:.2f}%'

            if should_sell:
                actual_qty = get_coin_balance(exchange, coin)
                if actual_qty > 0:
                    order        = place_market_sell(exchange, symbol, actual_qty)
                    filled_price = float(order.get('average') or current_price)
                    thb_returned = actual_qty * filled_price
                    notify_sell(symbol, filled_price, actual_qty,
                                thb_returned, reason, pnl_pct)
                    print(f"  SOLD {symbol}: {reason}")
                else:
                    print(f"  {symbol}: no balance found — removing from state")
                del state['positions'][symbol]
                pnl_map.pop(symbol, None)

            time.sleep(0.5)
        except Exception:
            traceback.print_exc()

    # ── Step 2: Look for new buy opportunities ────────────────────────────────
    open_count    = len(state['positions'])
    thb_balance   = get_free_thb(exchange)  # Refresh after any sells
    tradeable_thb = thb_balance * (1 - RESERVE_PCT)

    print(f"\n=== Scanning for buys | THB available: {tradeable_thb:.0f}"
          f" | positions: {open_count}/{MAX_POSITIONS} ===")

    for symbol in TRADE_PAIRS:
        if open_count >= MAX_POSITIONS:
            print(f"  Max positions ({MAX_POSITIONS}) reached — skipping scan")
            break
        if symbol in state['positions']:
            continue  # Already holding this coin

        try:
            prices = get_closing_prices(exchange, symbol)
            signal = get_signal(prices)
            rsi    = round(calc_rsi(prices), 1)
            print(f"  {symbol}: RSI={rsi} signal={signal}")

            if signal in ('BUY', 'BUY_STRONG'):
                thb_to_use = tradeable_thb * MAX_POS_PCT
                thb_to_use = max(thb_to_use, MIN_ORDER_THB)

                if thb_to_use > tradeable_thb:
                    print(f"  Not enough THB for {symbol} (need {thb_to_use:.0f})")
                    continue

                order       = place_market_buy(exchange, symbol, thb_to_use)
                filled_qty  = float(order.get('filled') or order.get('amount') or 0)
                avg_price   = float(order.get('average') or 0)

                if filled_qty <= 0 or avg_price <= 0:
                    # Fallback: estimate from current price
                    avg_price  = get_current_price(exchange, symbol)
                    filled_qty = thb_to_use / avg_price

                invested_thb = filled_qty * avg_price

                state['positions'][symbol] = {
                    'quantity':    filled_qty,
                    'entry_price': avg_price,
                    'entry_time':  datetime.now(timezone.utc).isoformat(),
                    'invested_thb': invested_thb,
                }

                notify_buy(symbol, avg_price, filled_qty, invested_thb, rsi, signal)
                print(f"  BOUGHT {filled_qty:.6g} {symbol} @ {avg_price:.2f}"
                      f" ({invested_thb:.0f} THB)")

                tradeable_thb -= invested_thb
                open_count    += 1

            time.sleep(1.0)
        except Exception:
            traceback.print_exc()

    # ── Step 3: Hourly portfolio summary ─────────────────────────────────────
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts - state.get('last_summary_ts', 0) >= SUMMARY_EVERY:
        final_thb   = get_free_thb(exchange)
        # Re-add coin values for summary total
        coin_total  = 0.0
        for symbol, pos in state['positions'].items():
            try:
                price      = get_current_price(exchange, symbol)
                coin_total += float(pos['quantity']) * price
            except Exception:
                pass
        total_value = final_thb + coin_total
        notify_summary(final_thb, total_value, pnl_map, state.get('initial_thb', total_value))
        state['last_summary_ts'] = now_ts

    save_state(state)
    print(f"\nDone. THB balance: {get_free_thb(exchange):.0f}"
          f" | Positions: {list(state['positions'].keys())}")


if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        traceback.print_exc()
        notify_error(str(e))
