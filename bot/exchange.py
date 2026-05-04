"""
Direct REST client for BinanceTH (api.binance.th).
Uses only /api/v3/ endpoints — no /sapi/ calls that trigger geo-blocks.
"""

import hmac
import hashlib
import os
import time
from functools import lru_cache
from urllib.parse import urlencode

import requests

_BASE = os.getenv('BINANCE_BASE_URL', 'https://api.binance.th')
_KEY  = os.getenv('BINANCE_API_KEY', '')
_SEC  = os.getenv('BINANCE_API_SECRET', '')

from bot.config import KLINE_TIMEFRAME, KLINE_LIMIT


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def _sign(params: dict) -> str:
    return hmac.new(_SEC.encode(), urlencode(params).encode(), hashlib.sha256).hexdigest()


def _headers() -> dict:
    return {'X-MBX-APIKEY': _KEY}


def _get_public(path: str, params: dict | None = None) -> any:
    r = requests.get(f'{_BASE}{path}', params=params or {}, timeout=10)
    r.raise_for_status()
    return r.json()


def _get_private(path: str, params: dict | None = None) -> any:
    p = {**(params or {}), 'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
    p['signature'] = _sign(p)
    r = requests.get(f'{_BASE}{path}', params=p, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def _post_private(path: str, params: dict | None = None) -> any:
    p = {**(params or {}), 'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
    p['signature'] = _sign(p)
    r = requests.post(f'{_BASE}{path}', params=p, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


# ─── Quantity precision ───────────────────────────────────────────────────────

@lru_cache(maxsize=32)
def _step_size(raw_symbol: str) -> float:
    info = _get_public('/api/v3/exchangeInfo')
    for s in info.get('symbols', []):
        if s['symbol'] == raw_symbol:
            for f in s.get('filters', []):
                if f['filterType'] == 'LOT_SIZE':
                    return float(f['stepSize'])
    return 1e-6


def _round_qty(symbol: str, qty: float) -> float:
    raw  = symbol.replace('/', '')
    step = _step_size(raw)
    precision = max(0, -int(f'{step:.10f}'.rstrip('0').find('.') - len(f'{step:.10f}'.rstrip('0')) + 1))
    # simpler: count decimal places in step
    s = f'{step:.10f}'.rstrip('0')
    decimals = len(s.split('.')[1]) if '.' in s else 0
    return round(int(qty / step) * step, decimals)


# ─── Public endpoints ─────────────────────────────────────────────────────────

def get_closing_prices(symbol: str) -> list[float]:
    interval_map = {'1h': '1h', '15m': '15m', '4h': '4h', '1d': '1d'}
    data = _get_public('/api/v3/klines', {
        'symbol':   symbol.replace('/', ''),
        'interval': interval_map.get(KLINE_TIMEFRAME, '1h'),
        'limit':    KLINE_LIMIT,
    })
    return [float(c[4]) for c in data]


def get_current_price(symbol: str) -> float:
    data = _get_public('/api/v3/ticker/price', {'symbol': symbol.replace('/', '')})
    return float(data['price'])


# ─── Private endpoints ────────────────────────────────────────────────────────

def get_balances() -> dict[str, float]:
    data = _get_private('/api/v3/account')
    return {b['asset']: float(b['free']) for b in data.get('balances', [])
            if float(b['free']) > 0}


def get_free_thb() -> float:
    return get_balances().get('THB', 0.0)


def get_coin_balance(coin: str) -> float:
    return get_balances().get(coin, 0.0)


def place_market_buy(symbol: str, thb_amount: float) -> dict:
    price    = get_current_price(symbol)
    quantity = _round_qty(symbol, thb_amount / price)
    return _post_private('/api/v3/order', {
        'symbol':   symbol.replace('/', ''),
        'side':     'BUY',
        'type':     'MARKET',
        'quantity': quantity,
    })


def place_market_sell(symbol: str, quantity: float) -> dict:
    quantity = _round_qty(symbol, quantity)
    return _post_private('/api/v3/order', {
        'symbol':   symbol.replace('/', ''),
        'side':     'SELL',
        'type':     'MARKET',
        'quantity': quantity,
    })
