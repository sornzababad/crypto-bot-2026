import os
import pandas as pd
import ta
import requests
from google import genai
from binance.client import Client

# ดึงค่าจาก GitHub Secrets
B_KEY      = os.getenv('BINANCE_KEY')
B_SECRET   = os.getenv('BINANCE_SECRET')
G_KEY      = os.getenv('GEMINI_KEY')
LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

client = Client(B_KEY, B_SECRET, tld='th')
ai_client = genai.Client(api_key=G_KEY)

def send_line(msg):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, json=data, headers=headers)

def ask_ai(prices):
    prompt = f"ราคาปิด 24 ชม. ล่าสุด: {prices}. เทรนด์นี้ควร BUY หรือ WAIT? ตอบสั้นๆ พร้อมเหตุผล 1 ประโยค"
    try:
        response = ai_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text
    except: return "WAIT"

# --- LOGIC การเช็คสัญญาณ (รัน 1 รอบเมื่อถูกเรียก) ---
def run_check():
    SYMBOLS = ['BTCTHB', 'ETHTHB', 'SOLTHB']
    cash = float(client.get_asset_balance(asset='THB')['free'])
    
    for sym in SYMBOLS:
        bars = client.get_historical_klines(sym, Client.KLINE_INTERVAL_1HOUR, "2 days ago UTC")
        df = pd.DataFrame(bars)
        df['close'] = df[4].astype(float)
        
        ema_f = ta.trend.ema_indicator(df['close'], 12).iloc[-1]
        ema_s = ta.trend.ema_indicator(df['close'], 26).iloc[-1]
        
        asset = sym.replace('THB', '')
        held = float(client.get_asset_balance(asset=asset)['free'])
        
        # 🟢 สั่งซื้อ
        if ema_f > ema_s and held < 0.0001 and cash > 500:
            history = df['close'].tail(24).tolist()
            ai_reply = ask_ai(history)
            if "BUY" in ai_reply.upper():
                buy_amt = cash * 0.5
                client.order_market_buy(symbol=sym, quoteOrderQty=round(buy_amt, 1))
                send_line(f"🟢 [GITHUB] ซื้อ {sym}\n🤖 AI: {ai_reply}")
        
        # 🔴 สั่งขาย
        elif ema_f < ema_s and held > 0.0001:
            client.order_market_sell(symbol=sym, quantity=held)
            send_line(f"🔴 [GITHUB] ขาย {sym} แล้วครับ!")

if __name__ == "__main__":
    run_check()
