"""
Direct REST client for BinanceTH (api.binance.th).

Confirmed endpoints from official BinanceTH API docs:
  GET  /api/v1/accountV2      — account balances
  GET  /api/v1/klines         — candlestick / price history
  GET  /api/v1/order          — query order status
  POST /api/v1/order          — place new order

Response format (all endpoints):
  {"code": 0, "msg": "", "timestamp": 123, "data": <actual payload>}
"""

import hmac
import hashlib
import os
import time
from functools import lru_cache
from urllib.parse import urlencode

import requests

_BASE = 'https://api.binance.th'
_KEY  = os.getenv('BINANCE_API_KEY', '')
_SEC  = os.getenv('BINANCE_API_SECRET', '')

from bot.config import KLINE_TIMEFRAME, KLINE_LIMIT


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def _sign(params: dict) -> str:
    return hmac.new(_SEC.encode(), urlencode(params).encode(), hashlib.sha256).hexdigest()


def _headers() -> dict:
    return {'X-MBX-APIKEY': _KEY}


def _unwrap(res: requests.Response) -> any:
    """BinanceTH wraps most responses: {"code":0,"data":<payload>}
    but klines returns a raw list directly."""
    res.raise_for_status()
    body = res.json()
    if isinstance(body, list):
        return body
    if isinstance(body, dict) and body.get('code', 0) != 0:
        raise RuntimeError(f"BinanceTH API error {body.get('code')}: {body.get('msg')}")
    return body.get('data', body)


def _get_public(path: str, params: dict | None = None) -> any:
    r = requests.get(f'{_BASE}{path}', params=params or {}, timeout=10)
    return _unwrap(r)


def _get_private(path: str, params: dict | None = None) -> any:
    p = {**(params or {}), 'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
    p['signature'] = _sign(p)
    r = requests.get(f'{_BASE}{path}', params=p, headers=_headers(), timeout=10)
    return _unwrap(r)


def _post_private(path: str, params: dict | None = None) -> any:
    p = {**(params or {}), 'timestamp': int(time.time() * 1000), 'recvWindow': 5000}
    p['signature'] = _sign(p)
    r = requests.post(f'{_BASE}{path}', params=p, headers=_headers(), timeout=10)
    return _unwrap(r)


# ─── Quantity rounding ────────────────────────────────────────────────────────

@lru_cache(maxsize=32)
def _step_size(raw_symbol: str) -> float:
    try:
        info = _get_public('/api/v1/exchangeInfo')
        symbols = info if isinstance(info, list) else info.get('symbols', [])
        for s in symbols:
            if s.get('symbol') == raw_symbol:
                for f in s.get('filters', []):
                    if f.get('filterType') == 'LOT_SIZE':
                        return float(f['stepSize'])
    except Exception:
        pass
    return 1e-6


def _round_qty(symbol: str, qty: float) -> float:
    step = _step_size(symbol.replace('/', ''))
    s    = f'{step:.10f}'.rstrip('0')
    decs = len(s.split('.')[1]) if '.' in s else 0
    return round(int(qty / step) * step, decs)


# ─── Public endpoints ─────────────────────────────────────────────────────────

def get_candles(symbol: str) -> tuple[list[float], list[float]]:
    """Returns (closes, volumes) for the configured timeframe."""
    data = _get_public('/api/v1/klines', {
        'symbol':   symbol.replace('/', ''),
        'interval': KLINE_TIMEFRAME,
        'limit':    KLINE_LIMIT,
    })
    rows = data if isinstance(data, list) else data.get('data', [])
    closes  = [float(c[4]) for c in rows]
    volumes = [float(c[5]) for c in rows]
    return closes, volumes


def get_closing_prices(symbol: str) -> list[float]:
    closes, _ = get_candles(symbol)
    return closes


def get_current_price(symbol: str) -> float:
    # Use last kline close price (limit=1) — avoids needing a separate ticker endpoint
    data = _get_public('/api/v1/klines', {
        'symbol':   symbol.replace('/', ''),
        'interval': '1m',
        'limit':    1,
    })
    rows = data if isinstance(data, list) else data.get('data', [])
    return float(rows[-1][4])


# ─── Private endpoints ────────────────────────────────────────────────────────

def get_balances() -> dict[str, float]:
    data = _get_private('/api/v1/accountV2')
    bals = data if isinstance(data, list) else data.get('balances', [])
    return {b['asset']: float(b['free']) for b in bals if float(b['free']) > 0}


def get_free_thb() -> float:
    return get_balances().get('THB', 0.0)


def get_coin_balance(coin: str) -> float:
    return get_balances().get(coin, 0.0)


def place_market_buy(symbol: str, thb_amount: float) -> dict:
    price    = get_current_price(symbol)
    quantity = _round_qty(symbol, thb_amount / price)
    return _post_private('/api/v1/order', {
        'symbol':   symbol.replace('/', ''),
        'side':     'BUY',
        'type':     'MARKET',
        'quantity': quantity,
    })


def place_market_sell(symbol: str, quantity: float) -> dict:
    quantity = _round_qty(symbol, quantity)
    return _post_private('/api/v1/order', {
        'symbol':   symbol.replace('/', ''),
        'side':     'SELL',
        'type':     'MARKET',
        'quantity': quantity,
    })
