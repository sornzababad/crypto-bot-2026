"""
Crypto Trading Bot — BinanceTH (USDT pairs)
Runs continuously on VPS, scanning every 15 min.

Strategy: Market Regime Detection (ADX-based)
  - ADX >= 25 → Trend → EMA9/21 + RSI + Volume momentum
  - ADX <  25 → Sideways → Bollinger Band mean reversion

Trend exits:   Trailing stop (2.5% from peak) + Hard SL (-3%)
Sideways exits: Price hits SMA20 (TP) + Hard SL (-2%)
Global:        BTC RSI filter + Stale exit (6h ±1%) + Cooldown after SL
"""

import json
import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from bot.config import (
    STOP_LOSS_PCT, SL_SIDEWAYS, TRAIL_PCT, COOLDOWN_HOURS,
    MAX_POS_PCT, MAX_POS_PCT_STRONG, MAX_POS_PCT_MEME, MEME_PAIRS,
    MIN_ORDER_USDT, RESERVE_PCT, MAX_POSITIONS, TRADE_PAIRS,
    STALE_HOURS, STALE_BAND_PCT, BB_LENGTH, BB_STD,
)
from bot.exchange import (
    get_candles, get_balances, get_free_usdt, get_coin_balance,
    get_current_price, place_market_buy, place_market_sell,
)
from bot.strategy import (
    get_signal, calc_rsi, calc_adx, is_btc_bullish, calc_bollinger_bands,
)
from bot.notifier import (
    notify_buy, notify_sell, notify_summary, notify_error, notify_startup,
)

STATE_FILE    = Path('state.json')
SUMMARY_EVERY = 1800  # 30 minutes


# ─── State helpers ────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {'positions': {}, 'last_summary_ts': 0, 'cooldowns': {}, 'realized_pnl_usdt': 0.0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def reconcile_positions(state: dict):
    """Pull coins held on exchange but missing from state into tracking."""
    try:
        balances = get_balances()
    except Exception:
        return

    bad = [s for s, p in state['positions'].items() if float(p.get('entry_price', 1)) <= 0]
    for s in bad:
        del state['positions'][s]
        print(f"  Removed corrupted position: {s}")

    for coin, qty in balances.items():
        if coin in ('THB', 'USDT'):
            continue
        symbol = f"{coin}/USDT"
        if symbol not in TRADE_PAIRS or symbol in state['positions']:
            continue
        try:
            price = get_current_price(symbol)
            value = qty * price
            if value < MIN_ORDER_USDT * 2:
                continue
            state['positions'][symbol] = {
                'quantity':      qty,
                'entry_price':   price,
                'highest_price': price,
                'entry_time':    datetime.now(timezone.utc).isoformat(),
                'invested_usdt': value,
                'top_up_count':  0,
                'regime':        'trend',   # default reconciled positions to trend logic
                'reconciled':    True,
            }
            print(f"  Reconciled: {symbol} {qty:.6g} @ ${price:.4f} (${value:.2f})")
        except Exception:
            traceback.print_exc()


# ─── Exit helpers ─────────────────────────────────────────────────────────────

def _check_trend_exit(pos: dict, current_price: float, pnl_pct: float, hours_held: float):
    """Trailing stop + hard SL for trend positions. Returns (should_sell, reason, is_stop_loss)."""
    entry_price = float(pos['entry_price'])
    highest     = float(pos.get('highest_price', entry_price))
    trail_sl    = highest * (1 - TRAIL_PCT)
    hard_sl     = entry_price * (1 - STOP_LOSS_PCT)
    active_sl   = max(trail_sl, hard_sl)

    if current_price <= active_sl:
        is_sl = pnl_pct < 0
        if current_price <= hard_sl:
            reason = f'Trend Hard SL {pnl_pct:.2f}%'
        else:
            reason = f'Trend Trail Stop {pnl_pct:.2f}% (peak ${highest:.4f})'
        return True, reason, is_sl

    if hours_held >= STALE_HOURS and abs(pnl_pct) <= STALE_BAND_PCT:
        return True, f'Stale {hours_held:.1f}h ({pnl_pct:+.2f}%)', False

    return False, '', False


def _check_sideways_exit(pos: dict, symbol: str, current_price: float,
                         pnl_pct: float, hours_held: float):
    """BB mid TP + hard SL for sideways (mean reversion) positions."""
    entry_price = float(pos['entry_price'])
    hard_sl     = entry_price * (1 - SL_SIDEWAYS)

    # Need current BB middle band as TP target
    try:
        closes, _, _, _ = get_candles(symbol)
        _, bb_mid, _    = calc_bollinger_bands(closes, BB_LENGTH, BB_STD)
    except Exception:
        bb_mid = entry_price * 1.02   # fallback: +2% if candle fetch fails

    if current_price >= bb_mid:
        return True, f'Mean Rev TP: hit SMA20 ${bb_mid:.4f} ({pnl_pct:+.2f}%)', False

    if current_price <= hard_sl:
        return True, f'Mean Rev Hard SL {pnl_pct:.2f}%', True

    if hours_held >= STALE_HOURS and abs(pnl_pct) <= STALE_BAND_PCT:
        return True, f'Stale {hours_held:.1f}h ({pnl_pct:+.2f}%)', False

    return False, '', False


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(is_startup: bool = False):
    state = load_state()
    reconcile_positions(state)

    # ── Step 1: Manage open positions ─────────────────────────────────────────
    usdt_balance = get_free_usdt()
    total_value  = usdt_balance
    pnl_map      = {}

    print(f"\n=== Open positions: {list(state['positions'].keys())} ===")

    for symbol, pos in list(state['positions'].items()):
        coin = symbol.split('/')[0]
        try:
            qty         = float(pos['quantity'])
            entry_price = float(pos['entry_price'])

            if entry_price <= 0:
                print(f"  {symbol}: bad entry_price — removing")
                del state['positions'][symbol]
                continue

            current_price = get_current_price(symbol)
            coin_value    = qty * current_price
            total_value  += coin_value
            pnl_pct       = (current_price - entry_price) / entry_price * 100
            regime        = pos.get('regime', 'trend')
            pnl_map[symbol] = {
                'pnl_pct':     pnl_pct,
                'top_up_count': pos.get('top_up_count', 0),
                'regime':      regime,
            }

            # Update peak price (only meaningful for trend positions)
            highest = max(current_price, float(pos.get('highest_price', entry_price)))
            pos['highest_price'] = highest

            print(f"  {symbol} [{regime}]: entry=${entry_price:.4f} now=${current_price:.4f}"
                  f" peak=${highest:.4f} pnl={pnl_pct:+.2f}%")

            try:
                entry_time = datetime.fromisoformat(
                    pos.get('entry_time', datetime.now(timezone.utc).isoformat()))
                hours_held = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
            except Exception:
                hours_held = 0

            # Regime-specific exit logic
            if regime == 'sideways':
                should_sell, reason, is_stop_loss = _check_sideways_exit(
                    pos, symbol, current_price, pnl_pct, hours_held)
            else:
                should_sell, reason, is_stop_loss = _check_trend_exit(
                    pos, current_price, pnl_pct, hours_held)

            if should_sell:
                actual_qty = get_coin_balance(coin)
                if actual_qty > 0:
                    order      = place_market_sell(symbol, actual_qty)
                    fills      = order.get('fills', [])
                    cum_quote  = float(order.get('cummulativeQuoteQty', 0))
                    filled_qty = float(order.get('executedQty') or
                                       sum(float(f['qty']) for f in fills) or actual_qty)
                    if cum_quote > 0:
                        usdt_returned = cum_quote
                        filled_price  = cum_quote / filled_qty if filled_qty > 0 else current_price
                    else:
                        filled_price  = current_price
                        usdt_returned = filled_qty * filled_price
                    invested      = float(pos.get('invested_usdt', usdt_returned))
                    realized      = usdt_returned - invested
                    state['realized_pnl_usdt'] = state.get('realized_pnl_usdt', 0) + realized
                    notify_sell(symbol, filled_price, filled_qty, usdt_returned, reason, pnl_pct)
                    print(f"  SOLD {symbol}: {reason} | realized={realized:+.2f} USDT")
                    if is_stop_loss:
                        state.setdefault('cooldowns', {})[symbol] = int(
                            datetime.now(timezone.utc).timestamp())
                else:
                    print(f"  {symbol}: no balance on exchange — removing")
                del state['positions'][symbol]
                pnl_map.pop(symbol, None)

            time.sleep(0.5)
        except Exception:
            traceback.print_exc()

    if is_startup:
        notify_startup(total_value, len(state['positions']))

    # ── Step 2: Look for new buys + top-ups ──────────────────────────────────
    open_count     = len(state['positions'])
    usdt_balance   = get_free_usdt()
    tradeable_usdt = usdt_balance * (1 - RESERVE_PCT)
    portfolio_base = total_value * (1 - RESERVE_PCT)   # consistent sizing from total value

    print(f"\n=== Scanning | free=${usdt_balance:.2f} portfolio=${total_value:.2f}"
          f" | positions={open_count}/{MAX_POSITIONS} ===")

    scan_results = []
    btc_bullish  = is_btc_bullish()
    if not btc_bullish:
        print("  ⚠️  BTC RSI < 40 — pausing all new buys")

    for symbol in TRADE_PAIRS:
        is_existing = symbol in state['positions']

        if not is_existing and open_count >= MAX_POSITIONS:
            continue

        # Top-up eligibility (trend only, max 1)
        if is_existing:
            pos     = state['positions'][symbol]
            regime  = pos.get('regime', 'trend')
            pnl_now = pnl_map.get(symbol, {}).get('pnl_pct', 0)
            if regime != 'trend':
                continue   # no pyramiding in sideways mode
            if pos.get('top_up_count', 0) >= 2:
                continue
            if pnl_now < 1.0:
                continue   # only add to confirmed winners

        # Cooldown check
        now_ts    = int(datetime.now(timezone.utc).timestamp())
        cooled_at = state.get('cooldowns', {}).get(symbol, 0)
        if now_ts - cooled_at < COOLDOWN_HOURS * 3600:
            remaining = int((COOLDOWN_HOURS * 3600 - (now_ts - cooled_at)) / 60)
            if not is_existing:
                print(f"  {symbol}: cooldown {remaining}min remaining")
            continue

        try:
            closes, highs, lows, volumes = get_candles(symbol)
            signal, regime = get_signal(closes, highs, lows, volumes)
            rsi = round(calc_rsi(closes), 1)

            if is_existing:
                print(f"  {symbol}: top-up? [{regime}] RSI={rsi} signal={signal}"
                      f" pnl={pnl_now:+.2f}%")
            else:
                adx_val = round(calc_adx(closes, highs, lows), 1)
                print(f"  {symbol}: [{regime} ADX={adx_val}] RSI={rsi} signal={signal}")
                scan_results.append((symbol, rsi, signal))

            if signal not in ('BUY', 'BUY_STRONG'):
                time.sleep(0.3)
                continue

            if not btc_bullish and symbol != 'BTC/USDT':
                print(f"  {symbol}: skipped — BTC downtrend")
                continue

            # Position sizing
            if symbol in MEME_PAIRS:
                pos_pct = MAX_POS_PCT_MEME
            elif signal == 'BUY_STRONG':
                pos_pct = MAX_POS_PCT_STRONG
            else:
                pos_pct = MAX_POS_PCT

            if is_existing:
                pos_pct *= 0.5   # top-up = 50% of normal

            usdt_to_use = max(portfolio_base * pos_pct, MIN_ORDER_USDT)
            usdt_to_use = min(usdt_to_use, tradeable_usdt)

            if usdt_to_use < MIN_ORDER_USDT:
                print(f"  {symbol}: not enough USDT (${tradeable_usdt:.2f} available)")
                continue

            # Execute buy
            order      = place_market_buy(symbol, usdt_to_use)
            fills      = order.get('fills', [])
            filled_qty = float(order.get('executedQty') or
                               sum(float(f['qty']) for f in fills) or 0)
            cum_quote  = float(order.get('cummulativeQuoteQty', 0))
            if filled_qty > 0 and cum_quote > 0:
                avg_price = cum_quote / filled_qty
            else:
                avg_price = get_current_price(symbol)
            if filled_qty <= 0:
                filled_qty = usdt_to_use / avg_price

            invested_usdt = filled_qty * avg_price
            label = f'TOP-UP/{signal} [{regime}]' if is_existing else f'{signal} [{regime}]'

            if is_existing:
                pos          = state['positions'][symbol]
                old_qty      = float(pos['quantity'])
                old_invested = float(pos['invested_usdt'])
                new_qty      = old_qty + filled_qty
                new_invested = old_invested + invested_usdt
                new_entry    = new_invested / new_qty
                state['positions'][symbol].update({
                    'quantity':      new_qty,
                    'entry_price':   new_entry,
                    'highest_price': max(avg_price, float(pos.get('highest_price', avg_price))),
                    'invested_usdt': new_invested,
                    'top_up_count':  pos.get('top_up_count', 0) + 1,
                })
                print(f"  TOP-UP {filled_qty:.6g} {symbol} @ ${avg_price:.4f}"
                      f" (${invested_usdt:.2f}) new_avg=${new_entry:.4f}")
            else:
                state['positions'][symbol] = {
                    'quantity':      filled_qty,
                    'entry_price':   avg_price,
                    'highest_price': avg_price,
                    'entry_time':    datetime.now(timezone.utc).isoformat(),
                    'invested_usdt': invested_usdt,
                    'top_up_count':  0,
                    'regime':        regime,
                }
                print(f"  BOUGHT {filled_qty:.6g} {symbol} @ ${avg_price:.4f}"
                      f" (${invested_usdt:.2f}) [{regime}]")
                open_count += 1

            notify_buy(symbol, avg_price, filled_qty, invested_usdt, rsi, label)
            tradeable_usdt -= invested_usdt
            time.sleep(1.0)

        except Exception:
            traceback.print_exc()

    # ── Step 3: Summary every 30 min ─────────────────────────────────────────
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts - state.get('last_summary_ts', 0) >= SUMMARY_EVERY:
        final_usdt = get_free_usdt()
        coin_total = sum(
            float(p['quantity']) * get_current_price(sym)
            for sym, p in state['positions'].items()
            if float(p.get('entry_price', 0)) > 0
        )
        total_value = final_usdt + coin_total
        notify_summary(final_usdt, total_value, pnl_map,
                       state.get('realized_pnl_usdt', 0.0), scan_results)
        state['last_summary_ts'] = now_ts

    save_state(state)
    print(f"\nDone. USDT=${get_free_usdt():.2f} | Positions={list(state['positions'].keys())}")


SCAN_INTERVAL = 900  # 15 minutes

if __name__ == '__main__':
    if os.getenv('GITHUB_ACTIONS'):
        try:
            run(is_startup=True)
        except Exception as e:
            traceback.print_exc()
            notify_error(str(e))
    else:
        print("Bot starting — regime-aware mode, scanning every 15 min")
        first_run = True
        while True:
            start = time.time()
            try:
                run(is_startup=first_run)
                first_run = False
            except Exception as e:
                traceback.print_exc()
                notify_error(str(e))
            elapsed   = time.time() - start
            sleep_for = max(0, SCAN_INTERVAL - elapsed)
            print(f"Sleeping {sleep_for:.0f}s until next scan...")
            time.sleep(sleep_for)
