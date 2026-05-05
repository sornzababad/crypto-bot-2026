"""
US Stock scanner — notify only, no auto-trade.

Scans STOCK_WATCHLIST every cycle during NYSE market hours.
Sends LINE alert only when signal CHANGES (no spam).
"""

from datetime import datetime, timezone

import yfinance as yf

from bot.config import STOCK_WATCHLIST
from bot.strategy import get_signal, calc_rsi


def is_market_open() -> bool:
    """NYSE open: Mon-Fri 13:30-20:00 UTC (EDT) / 14:30-21:00 UTC (EST)."""
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:   # Saturday / Sunday
        return False
    return 13 <= now.hour < 21


def scan_stocks(state: dict) -> list[dict]:
    """
    Fetch all stock candles in one batch call, run EMA+RSI signal,
    return list of stocks whose signal changed to BUY/SELL.
    Updates state['stock_signals'] in place.
    """
    if not is_market_open():
        return []

    print("\n=== Scanning US stocks ===")

    try:
        raw = yf.download(
            STOCK_WATCHLIST,
            period='5d',
            interval='15m',
            group_by='ticker',
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"  yfinance download error: {e}")
        return []

    alerts = []
    state.setdefault('stock_signals', {})

    for symbol in STOCK_WATCHLIST:
        try:
            df = raw[symbol] if len(STOCK_WATCHLIST) > 1 else raw
            closes  = df['Close'].dropna().tolist()
            volumes = df['Volume'].dropna().tolist()

            if len(closes) < 25:
                continue

            signal = get_signal(closes, volumes)
            rsi    = round(calc_rsi(closes), 1)
            price  = closes[-1]

            print(f"  {symbol}: ${price:,.2f} RSI={rsi} signal={signal}")

            prev_signal = state['stock_signals'].get(symbol, 'HOLD')
            state['stock_signals'][symbol] = signal

            # notify only on meaningful signal change
            if signal in ('BUY', 'BUY_STRONG') and prev_signal not in ('BUY', 'BUY_STRONG'):
                alerts.append({'symbol': symbol, 'price': price, 'signal': signal, 'rsi': rsi})
            elif signal in ('SELL', 'SELL_STRONG') and prev_signal not in ('SELL', 'SELL_STRONG'):
                alerts.append({'symbol': symbol, 'price': price, 'signal': signal, 'rsi': rsi})

        except Exception as e:
            print(f"  {symbol}: {e}")

    return alerts
