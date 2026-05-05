"""Run this once to discover all available THB pairs on BinanceTH."""
import requests

r = requests.get('https://api.binance.th/api/v1/exchangeInfo', timeout=10)
body = r.json()

# unwrap BinanceTH envelope
if isinstance(body, dict):
    data = body.get('data', body)
    symbols = data.get('symbols', data) if isinstance(data, dict) else data
else:
    symbols = body

thb_pairs = sorted(
    s['symbol'] for s in symbols
    if isinstance(s, dict)
    and s.get('symbol', '').endswith('THB')
    and s.get('status', 'TRADING') == 'TRADING'
)

print(f"Found {len(thb_pairs)} tradeable THB pairs on BinanceTH:\n")
for p in thb_pairs:
    print(f"  {p}")
