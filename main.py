import os
import requests
from datetime import datetime, timezone, timedelta

LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

COINS = [
    {'id': 'bitcoin',  'symbol': 'BTC', 'emoji': '₿'},
    {'id': 'ethereum', 'symbol': 'ETH', 'emoji': 'Ξ'},
    {'id': 'solana',   'symbol': 'SOL', 'emoji': '◎'},
]
COIN_IDS = ','.join(c['id'] for c in COINS)


def get_market_data() -> list:
    url = (
        'https://api.coingecko.com/api/v3/coins/markets'
        f'?vs_currency=thb&ids={COIN_IDS}&order=market_cap_desc'
        '&sparkline=false&price_change_percentage=24h'
    )
    res = requests.get(url, timeout=15)
    res.raise_for_status()
    return res.json()


def format_price(price: float) -> str:
    if price >= 10_000:
        return f"{price:,.0f} ฿"
    elif price >= 1:
        return f"{price:,.2f} ฿"
    return f"{price:.6f} ฿"


def coin_row(market: dict, coin_meta: dict) -> dict:
    price      = market['current_price']
    change_pct = market.get('price_change_percentage_24h') or 0.0
    high       = market.get('high_24h') or price
    low        = market.get('low_24h') or price

    is_up        = change_pct >= 0
    change_color = '#2ecc71' if is_up else '#e74c3c'
    arrow        = '▲' if is_up else '▼'
    change_str   = f"{arrow} {abs(change_pct):.2f}%"

    return {
        "type": "box",
        "layout": "vertical",
        "paddingTop": "10px",
        "paddingBottom": "10px",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{coin_meta['emoji']} {coin_meta['symbol']}",
                        "weight": "bold",
                        "size": "md",
                        "color": "#ffffff",
                        "flex": 2
                    },
                    {
                        "type": "text",
                        "text": format_price(price),
                        "size": "md",
                        "color": "#ffffff",
                        "align": "end",
                        "flex": 4
                    },
                    {
                        "type": "text",
                        "text": change_str,
                        "size": "sm",
                        "color": change_color,
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
                    {
                        "type": "text",
                        "text": f"H: {format_price(high)}",
                        "size": "xxs",
                        "color": "#888899",
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": f"L: {format_price(low)}",
                        "size": "xxs",
                        "color": "#888899",
                        "align": "end",
                        "flex": 1
                    }
                ]
            }
        ]
    }


def build_flex(markets: list) -> dict:
    bkk      = datetime.now(timezone(timedelta(hours=7)))
    time_str = bkk.strftime('%H:%M น.  %d/%m/%Y')

    # Map coingecko id → coin meta
    meta_by_id = {c['id']: c for c in COINS}

    rows = []
    for i, market in enumerate(markets):
        meta = meta_by_id.get(market['id'], {'symbol': market['symbol'].upper(), 'emoji': '●'})
        rows.append(coin_row(market, meta))
        if i < len(markets) - 1:
            rows.append({"type": "separator", "color": "#2a2a4a", "margin": "none"})

    return {
        "type": "flex",
        "altText": f"📊 Crypto Alert — {time_str}",
        "contents": {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#12122a",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "text",
                        "text": "📊 Crypto Alert",
                        "weight": "bold",
                        "color": "#ffffff",
                        "size": "xl"
                    },
                    {
                        "type": "text",
                        "text": f"อัปเดตล่าสุด: {time_str}",
                        "color": "#8888aa",
                        "size": "xs",
                        "margin": "sm"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#0d0d1f",
                "paddingAll": "14px",
                "contents": rows
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#12122a",
                "paddingAll": "10px",
                "contents": [
                    {
                        "type": "text",
                        "text": "ข้อมูลจาก CoinGecko  ·  อัปเดตทุก 1 ชั่วโมง",
                        "color": "#555577",
                        "size": "xxs",
                        "align": "center"
                    }
                ]
            }
        }
    }


def send_flex(flex_msg: dict):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_TOKEN}'
    }
    res = requests.post(url, json={"to": USER_ID, "messages": [flex_msg]},
                        headers=headers, timeout=10)
    print(f"LINE status: {res.status_code}  {res.text[:200]}")


def send_text(msg: str):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    requests.post(url, json={"to": USER_ID, "messages": [{"type": "text", "text": msg}]},
                  headers=headers, timeout=10)


def run_check():
    try:
        markets = get_market_data()
        if markets:
            send_flex(build_flex(markets))
        else:
            send_text("⚠️ ไม่สามารถดึงข้อมูลราคาคริปโตได้")
    except Exception as e:
        send_text(f"⚠️ Error: {str(e)[:100]}")


if __name__ == "__main__":
    run_check()
