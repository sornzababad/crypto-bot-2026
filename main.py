"""
Crypto Trading Bot — BinanceTH (USDT pairs)
Runs continuously on VPS, scanning every 15 min.
"""

import json
import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from bot.config import (
    TAKE_PROFIT_PCT, STOP_LOSS_PCT, TRAIL_PCT, COOLDOWN_HOURS,
    MAX_POS_PCT, MAX_POS_PCT_STRONG, MAX_POS_PCT_MEME, MEME_PAIRS,
    MIN_ORDER_USDT, RESERVE_PCT,
    MAX_POSITIONS, TRADE_PAIRS, STALE_HOURS, STALE_BAND_PCT,
)
from bot.exchange import (
    get_candles,
    get_balances,
    get_free_usdt,
    get_coin_balance,
    get_current_price,
    place_market_buy,
    place_market_sell,
)
from bot.strategy import get_signal, calc_rsi, is_btc_bullish
from bot.notifier import (
    notify_buy, notify_sell, notify_summary, notify_error,
)

STATE_FILE    = Path('state.json')
SUMMARY_EVERY = 1800


# ─── State helpers ────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {'positions': {}, 'last_summary_ts': 0, 'initial_usdt': 0, 'cooldowns': {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def reconcile_positions(state: dict):
    """Pull any coins held on exchange but missing from state back into tracking."""
    try:
        balances = get_balances()
    except Exception:
        return

    # Remove corrupted positions with entry_price <= 0
    bad_syms = [s for s, p in state['positions'].items() if float(p.get('entry_price', 1)) <= 0]
    for s in bad_syms:
        del state['positions'][s]
        print(f"  Removed corrupted position: {s}")

    for coin, qty in balances.items():
        if coin in ('THB', 'USDT'):
            continue
        symbol = f"{coin}/USDT"
        if symbol not in TRADE_PAIRS:
            continue
        if symbol in state['positions']:
            continue
        try:
            price = get_current_price(symbol)
            value = qty * price
            if value < MIN_ORDER_USDT * 2:   # ignore dust
                continue
            state['positions'][symbol] = {
                'quantity':      qty,
                'entry_price':   price,
                'highest_price': price,
                'entry_time':    datetime.now(timezone.utc).isoformat(),
                'invested_usdt': value,
                'reconciled':    True,
            }
            print(f"  Reconciled: {symbol} {qty:.6g} @ {price:.4f} (${value:.2f})")
        except Exception:
            traceback.print_exc()


# ─── Main ─────────────────────────────────────────────────────────────────────

def run():
    state = load_state()
    reconcile_positions(state)

    usdt_balance = get_free_usdt()
    total_value  = usdt_balance
    pnl_map      = {}

    # ── Step 1: Manage open positions ─────────────────────────────────────────
    print(f"\n=== Open positions: {list(state['positions'].keys())} ===")

    for symbol, pos in list(state['positions'].items()):
        coin = symbol.split('/')[0]
        try:
            qty           = float(pos['quantity'])
            entry_price   = float(pos['entry_price'])

            # Skip corrupted positions (entry_price = 0 from old bugs)
            if entry_price <= 0:
                print(f"  {symbol}: corrupted (entry_price={entry_price}) — removing")
                del state['positions'][symbol]
                pnl_map.pop(symbol, None)
                continue

            current_price = get_current_price(symbol)
            coin_value    = qty * current_price
            total_value  += coin_value
            pnl_pct       = (current_price - entry_price) / entry_price * 100
            pnl_map[symbol] = {'pnl_pct': pnl_pct}

            highest   = max(current_price, float(pos.get('highest_price', entry_price)))
            pos['highest_price'] = highest
            trail_sl  = highest * (1 - TRAIL_PCT)
            hard_sl   = entry_price * (1 - STOP_LOSS_PCT)
            active_sl = max(trail_sl, hard_sl)

            print(f"  {symbol}: entry={entry_price:.4f} now={current_price:.4f}"
                  f" peak={highest:.4f} sl={active_sl:.4f} pnl={pnl_pct:+.2f}%")

            should_sell  = False
            reason       = ''
            is_stop_loss = False

            try:
                entry_time = datetime.fromisoformat(pos.get('entry_time', datetime.now(timezone.utc).isoformat()))
                hours_held = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
            except Exception:
                hours_held = 0

            if pnl_pct >= TAKE_PROFIT_PCT * 100:
                should_sell = True
                reason      = f'Take Profit +{pnl_pct:.2f}%'
            elif current_price <= active_sl:
                should_sell  = True
                is_stop_loss = True
                if current_price <= hard_sl:
                    reason = f'Hard Stop Loss {pnl_pct:.2f}%'
                else:
                    reason = f'Trailing Stop {pnl_pct:.2f}% (peak ${highest:.4f})'
            elif hours_held >= STALE_HOURS and abs(pnl_pct) <= STALE_BAND_PCT:
                should_sell = True
                reason      = f'Stale {hours_held:.1f}h ({pnl_pct:+.2f}%) — freeing capital'

            if should_sell:
                actual_qty = get_coin_balance(coin)
                if actual_qty > 0:
                    order      = place_market_sell(symbol, actual_qty)
                    fills      = order.get('fills', [])
                    cum_quote  = float(order.get('cummulativeQuoteQty', 0))
                    filled_qty = float(order.get('executedQty') or sum(float(f['qty']) for f in fills) or actual_qty)
                    if cum_quote > 0:
                        usdt_returned = cum_quote
                        filled_price  = cum_quote / filled_qty if filled_qty > 0 else current_price
                    else:
                        filled_price  = current_price
                        usdt_returned = filled_qty * filled_price
                    invested_usdt  = float(pos.get('invested_usdt', usdt_returned))
                    realized_usdt  = usdt_returned - invested_usdt
                    state['realized_pnl_usdt'] = state.get('realized_pnl_usdt', 0) + realized_usdt
                    notify_sell(symbol, filled_price, filled_qty, usdt_returned, reason, pnl_pct)
                    print(f"  SOLD {symbol}: {reason}")
                    if is_stop_loss:
                        state.setdefault('cooldowns', {})[symbol] = int(datetime.now(timezone.utc).timestamp())
                else:
                    print(f"  {symbol}: no balance — removing from state")
                del state['positions'][symbol]
                pnl_map.pop(symbol, None)

            time.sleep(0.5)
        except Exception:
            traceback.print_exc()

    # ── Step 2: Look for new buy opportunities ────────────────────────────────
    open_count         = len(state['positions'])
    usdt_balance       = get_free_usdt()
    tradeable_usdt     = usdt_balance * (1 - RESERVE_PCT)
    original_tradeable = tradeable_usdt  # snapshot for position sizing (prevents geometric decay)

    print(f"\n=== Scanning for buys | USDT: ${tradeable_usdt:.2f}"
          f" | positions: {open_count}/{MAX_POSITIONS} ===")

    scan_results = []

    btc_bullish = is_btc_bullish()
    if not btc_bullish:
        print("  ⚠️  BTC downtrend — pausing all altcoin buys this cycle")

    for symbol in TRADE_PAIRS:
        if open_count >= MAX_POSITIONS:
            print(f"  Max positions ({MAX_POSITIONS}) reached")
            break
        if symbol in state['positions']:
            continue

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
                if not btc_bullish and symbol != 'BTC/USDT':
                    print(f"  {symbol}: skipped — BTC downtrend")
                    continue

                if symbol in MEME_PAIRS:
                    pos_pct = MAX_POS_PCT_MEME
                elif signal == 'BUY_STRONG':
                    pos_pct = MAX_POS_PCT_STRONG
                else:
                    pos_pct = MAX_POS_PCT
                # Size from ORIGINAL budget (not remaining) — avoids geometric decay
                usdt_to_use = max(original_tradeable * pos_pct, MIN_ORDER_USDT)
                # But cap at actually-available cash so we don't oversize
                usdt_to_use = min(usdt_to_use, tradeable_usdt)

                if usdt_to_use < MIN_ORDER_USDT:
                    print(f"  Not enough USDT for {symbol} (${tradeable_usdt:.2f} left)")
                    continue

                order      = place_market_buy(symbol, usdt_to_use)
                fills      = order.get('fills', [])
                filled_qty = float(order.get('executedQty') or sum(float(f['qty']) for f in fills) or 0)
                cum_quote  = float(order.get('cummulativeQuoteQty', 0))
                if filled_qty > 0 and cum_quote > 0:
                    avg_price = cum_quote / filled_qty
                else:
                    avg_price = get_current_price(symbol)
                if filled_qty <= 0:
                    filled_qty = usdt_to_use / avg_price

                invested_usdt = filled_qty * avg_price

                state['positions'][symbol] = {
                    'quantity':      filled_qty,
                    'entry_price':   avg_price,
                    'highest_price': avg_price,
                    'entry_time':    datetime.now(timezone.utc).isoformat(),
                    'invested_usdt': invested_usdt,
                }

                notify_buy(symbol, avg_price, filled_qty, invested_usdt, rsi, signal)
                print(f"  BOUGHT {filled_qty:.6g} {symbol} @ {avg_price:.4f} (${invested_usdt:.2f})")

                tradeable_usdt -= invested_usdt
                open_count     += 1

            time.sleep(1.0)
        except Exception:
            traceback.print_exc()

    # ── Step 3: Portfolio summary ─────────────────────────────────────────────
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts - state.get('last_summary_ts', 0) >= SUMMARY_EVERY:
        final_usdt = get_free_usdt()
        coin_total = 0.0
        for symbol, pos in state['positions'].items():
            try:
                entry_price = float(pos.get('entry_price', 0))
                if entry_price > 0:
                    coin_total += float(pos['quantity']) * get_current_price(symbol)
            except Exception:
                pass
        total_value = final_usdt + coin_total
        notify_summary(final_usdt, total_value, pnl_map,
                       state.get('realized_pnl_usdt', 0.0), scan_results)
        state['last_summary_ts'] = now_ts

    save_state(state)
    print(f"\nDone. USDT: ${get_free_usdt():.2f} | Positions: {list(state['positions'].keys())}")


SCAN_INTERVAL = 900  # 15 minutes

if __name__ == '__main__':
    if os.getenv('GITHUB_ACTIONS'):
        try:
            run()
        except Exception as e:
            traceback.print_exc()
            notify_error(str(e))
    else:
        print("Bot starting — USDT mode, scanning every 15 min")
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
