import os
import time
import requests
from datetime import datetime, timezone, timedelta

LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

COINS = [
    {'id': 'bitcoin',       'symbol': 'BTC',  'emoji': '₿'},
    {'id': 'ethereum',      'symbol': 'ETH',  'emoji': 'Ξ'},
    {'id': 'binancecoin',   'symbol': 'BNB',  'emoji': '◆'},
    {'id': 'solana',        'symbol': 'SOL',  'emoji': '◎'},
    {'id': 'ripple',        'symbol': 'XRP',  'emoji': '✕'},
    {'id': 'dogecoin',      'symbol': 'DOGE', 'emoji': 'Ð'},
    {'id': 'cardano',       'symbol': 'ADA',  'emoji': '₳'},
    {'id': 'avalanche-2',   'symbol': 'AVAX', 'emoji': '△'},
    {'id': 'the-open-network', 'symbol': 'TON',  'emoji': '◈'},
    {'id': 'tron',          'symbol': 'TRX',  'emoji': '◉'},
    {'id': 'chainlink',     'symbol': 'LINK', 'emoji': '⬡'},
    {'id': 'polkadot',      'symbol': 'DOT',  'emoji': '●'},
    {'id': 'matic-network', 'symbol': 'POL',  'emoji': '⬟'},
    {'id': 'litecoin',      'symbol': 'LTC',  'emoji': 'Ł'},
    {'id': 'near',          'symbol': 'NEAR', 'emoji': '◇'},
]

CHUNK_SIZE = 5   # coins per bubble in the carousel


# ─── Data fetching ────────────────────────────────────────────────────────────

def get_market_data() -> list:
    ids = ','.join(c['id'] for c in COINS)
    url = (
        'https://api.coingecko.com/api/v3/coins/markets'
        f'?vs_currency=thb&ids={ids}&order=market_cap_desc'
        '&sparkline=false&price_change_percentage=24h'
    )
    res = requests.get(url, timeout=15)
    res.raise_for_status()
    return res.json()


def get_hourly_prices(coin_id: str) -> list:
    url = (
        f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
        '?vs_currency=thb&days=3'
    )
    res = requests.get(url, timeout=15)
    res.raise_for_status()
    return [p[1] for p in res.json()['prices']]


# ─── Indicators ──────────────────────────────────────────────────────────────

def calc_ema(prices: list, period: int) -> float:
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


def calc_rsi(prices: list, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains   = [max(c, 0) for c in changes]
    losses  = [abs(min(c, 0)) for c in changes]
    ag = sum(gains[:period])  / period
    al = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        ag = (ag * (period - 1) + gains[i])  / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return 100 - (100 / (1 + ag / al))


def get_signal(prices: list) -> dict:
    rsi   = calc_rsi(prices)
    ema12 = calc_ema(prices, 12)
    ema26 = calc_ema(prices, 26)
    up    = ema12 > ema26

    if rsi <= 30:
        return {'text': '🟢 ซื้อได้เลย!', 'detail': f'RSI {rsi:.0f} — Oversold มาก',      'color': '#27ae60'}
    if rsi <= 42 and up:
        return {'text': '🟢 น่าซื้อ',      'detail': f'RSI {rsi:.0f} — EMA กำลังขึ้น',      'color': '#2ecc71'}
    if rsi >= 70:
        return {'text': '🔴 ขายได้เลย!',  'detail': f'RSI {rsi:.0f} — Overbought มาก',      'color': '#c0392b'}
    if rsi >= 58 and not up:
        return {'text': '🔴 น่าขาย',       'detail': f'RSI {rsi:.0f} — EMA กำลังลง',         'color': '#e74c3c'}
    return     {'text': '🟡 รอดูก่อน',    'detail': f'RSI {rsi:.0f} — ยังไม่มีสัญญาณชัด',  'color': '#f39c12'}


# ─── Flex builder ─────────────────────────────────────────────────────────────

def format_price(price: float) -> str:
    if price >= 10_000:
        return f"{price:,.0f} ฿"
    elif price >= 1:
        return f"{price:,.2f} ฿"
    elif price >= 0.0001:
        return f"{price:.6f} ฿"
    return f"{price:.8f} ฿"


def coin_section(market: dict, meta: dict, signal: dict) -> list:
    price      = market['current_price']
    change_pct = market.get('price_change_percentage_24h') or 0.0
    high       = market.get('high_24h') or price
    low        = market.get('low_24h') or price
    is_up      = change_pct >= 0

    return [
        {
            "type": "box",
            "layout": "horizontal",
            "paddingTop": "10px",
            "contents": [
                {
                    "type": "text",
                    "text": f"{meta['emoji']} {meta['symbol']}",
                    "weight": "bold",
                    "size": "md",
                    "color": "#ffffff",
                    "flex": 2
                },
                {
                    "type": "text",
                    "text": format_price(price),
                    "size": "sm",
                    "color": "#ffffff",
                    "align": "end",
                    "flex": 4
                },
                {
                    "type": "text",
                    "text": f"{'▲' if is_up else '▼'} {abs(change_pct):.2f}%",
                    "size": "sm",
                    "color": '#2ecc71' if is_up else '#e74c3c',
                    "align": "end",
                    "weight": "bold",
                    "flex": 3
                }
            ]
        },
        {
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "contents": [
                {"type": "text", "text": f"H: {format_price(high)}", "size": "xxs", "color": "#888899", "flex": 1},
                {"type": "text", "text": f"L: {format_price(low)}",  "size": "xxs", "color": "#888899", "align": "end", "flex": 1}
            ]
        },
        {
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "paddingAll": "5px",
            "backgroundColor": "#1e1e3a",
            "cornerRadius": "6px",
            "contents": [
                {"type": "text", "text": signal['text'],   "size": "sm",  "weight": "bold", "color": signal['color'], "flex": 0},
                {"type": "text", "text": signal['detail'], "size": "xxs", "color": "#888899", "align": "end", "flex": 1, "gravity": "center"}
            ]
        },
        {"type": "box", "layout": "vertical", "height": "8px", "contents": []}
    ]


def make_bubble(chunk: list, markets_by_id: dict, signals: dict,
                time_str: str, page: int, total_pages: int) -> dict:
    body_contents = []
    for i, meta in enumerate(chunk):
        market = markets_by_id.get(meta['id'])
        if not market:
            continue
        signal = signals.get(meta['id'], {'text': '🟡 รอดูก่อน', 'detail': 'ไม่มีข้อมูล', 'color': '#f39c12'})
        body_contents.extend(coin_section(market, meta, signal))
        if i < len(chunk) - 1:
            body_contents.append({"type": "separator", "color": "#2a2a4a", "margin": "none"})

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#12122a",
            "paddingAll": "14px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "📊 Crypto Alert", "weight": "bold", "color": "#ffffff", "size": "lg", "flex": 1},
                        {"type": "text", "text": f"{page}/{total_pages}", "size": "xs", "color": "#8888aa", "align": "end", "gravity": "bottom", "flex": 0}
                    ]
                },
                {"type": "text", "text": f"อัปเดต: {time_str}", "color": "#8888aa", "size": "xxs", "margin": "sm"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0d0d1f",
            "paddingAll": "14px",
            "contents": body_contents
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#12122a",
            "paddingAll": "8px",
            "contents": [
                {"type": "text", "text": "RSI-14 + EMA-12/26  ·  ใช้ประกอบการตัดสินใจเท่านั้น",
                 "color": "#555577", "size": "xxs", "align": "center"}
            ]
        }
    }


def build_carousel(markets: list, signals: dict) -> dict:
    bkk      = datetime.now(timezone(timedelta(hours=7)))
    time_str = bkk.strftime('%H:%M น. %d/%m/%Y')

    markets_by_id = {m['id']: m for m in markets}

    chunks      = [COINS[i:i + CHUNK_SIZE] for i in range(0, len(COINS), CHUNK_SIZE)]
    total_pages = len(chunks)
    bubbles     = [
        make_bubble(chunk, markets_by_id, signals, time_str, i + 1, total_pages)
        for i, chunk in enumerate(chunks)
    ]

    return {
        "type": "flex",
        "altText": f"📊 Crypto Alert {len(COINS)} เหรียญ — {time_str}",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }


# ─── LINE push ────────────────────────────────────────────────────────────────

def send_flex(flex_msg: dict):
    url     = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    res     = requests.post(url, json={"to": USER_ID, "messages": [flex_msg]},
                            headers=headers, timeout=10)
    print(f"LINE status: {res.status_code}  {res.text[:200]}")


def send_text(msg: str):
    url     = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    requests.post(url, json={"to": USER_ID, "messages": [{"type": "text", "text": msg}]},
                  headers=headers, timeout=10)


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_check():
    try:
        markets = get_market_data()
        if not markets:
            send_text("⚠️ ไม่สามารถดึงข้อมูลราคาคริปโตได้")
            return

        signals = {}
        for coin in COINS:
            try:
                prices = get_hourly_prices(coin['id'])
                signals[coin['id']] = get_signal(prices)
            except Exception:
                signals[coin['id']] = {'text': '🟡 รอดูก่อน', 'detail': 'ดึงข้อมูลไม่ได้', 'color': '#f39c12'}
            time.sleep(0.5)   # avoid CoinGecko rate limit

        send_flex(build_carousel(markets, signals))

    except Exception as e:
        send_text(f"⚠️ Error: {str(e)[:100]}")


if __name__ == "__main__":
    run_check()
