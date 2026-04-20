import os
import requests
from datetime import datetime, timezone, timedelta

LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

BASE_URL = 'https://api.binance.th'
SYMBOLS  = ['BTCTHB', 'ETHTHB', 'SOLTHB']
COIN_EMOJI = {'BTC': '₿', 'ETH': 'Ξ', 'SOL': '◎'}


def get_ticker(symbol):
    res = requests.get(f"{BASE_URL}/api/v3/ticker/24hr?symbol={symbol}", timeout=10)
    return res.json()


def format_price(price: float) -> str:
    if price >= 10_000:
        return f"{price:,.0f} ฿"
    elif price >= 1:
        return f"{price:,.2f} ฿"
    return f"{price:.6f} ฿"


def coin_row(ticker: dict) -> dict:
    symbol      = ticker['symbol'].replace('THB', '')
    price       = float(ticker['lastPrice'])
    change_pct  = float(ticker['priceChangePercent'])
    high        = float(ticker['highPrice'])
    low         = float(ticker['lowPrice'])

    is_up        = change_pct >= 0
    change_color = '#2ecc71' if is_up else '#e74c3c'
    arrow        = '▲' if is_up else '▼'
    change_str   = f"{arrow} {abs(change_pct):.2f}%"
    emoji        = COIN_EMOJI.get(symbol, '●')

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
                        "text": f"{emoji} {symbol}",
                        "weight": "bold",
                        "size": "md",
                        "color": "#ffffff",
                        "flex": 3
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


def build_flex(tickers: list) -> dict:
    bkk = datetime.now(timezone(timedelta(hours=7)))
    time_str = bkk.strftime('%H:%M น.  %d/%m/%Y')

    rows = []
    for i, t in enumerate(tickers):
        rows.append(coin_row(t))
        if i < len(tickers) - 1:
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
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📊 Crypto Alert",
                                "weight": "bold",
                                "color": "#ffffff",
                                "size": "xl",
                                "flex": 1
                            }
                        ]
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
                        "text": "ข้อมูลจาก Binance TH  ·  อัปเดตทุก 1 ชั่วโมง",
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
    data = {"to": USER_ID, "messages": [flex_msg]}
    res = requests.post(url, json=data, headers=headers, timeout=10)
    print(f"LINE push status: {res.status_code}  body: {res.text[:200]}")


def send_text(msg: str):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, json=data, headers=headers, timeout=10)


def run_check():
    try:
        tickers = []
        for symbol in SYMBOLS:
            ticker = get_ticker(symbol)
            if 'lastPrice' in ticker:
                tickers.append(ticker)

        if tickers:
            send_flex(build_flex(tickers))
        else:
            send_text("⚠️ ไม่สามารถดึงข้อมูลราคาคริปโตได้")

    except Exception as e:
        send_text(f"⚠️ Error: {str(e)[:100]}")


if __name__ == "__main__":
    run_check()
