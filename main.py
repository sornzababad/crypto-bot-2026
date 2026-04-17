import os
import pandas as pd
import ta
import requests
from google import genai
from binance.client import Client

# ⚙️ Configuration
B_KEY      = os.getenv('BINANCE_KEY')
B_SECRET   = os.getenv('BINANCE_SECRET')
G_KEY      = os.getenv('GEMINI_KEY')
LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

# 🔌 พยายามเชื่อมต่อแบบ bypass การ ping เบื้องต้น
try:
    client = Client(B_KEY, B_SECRET)
    # บังคับ URL เป็นของไทย
    client.API_URL = 'https://api.binance.th/api'
    client.PRIVATE_API_URL = 'https://api.binance.th/api'
except Exception as e:
    print(f"Connection Init Error: {e}")

ai_client = genai.Client(api_key=G_KEY)

def send_line(msg):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, json=data, headers=headers)

def run_check():
    try:
        # ลองดึงราคาดู ถ้าผ่านตรงนี้ได้แสดงว่า IP ไม่โดนบล็อก
        sym = 'BTCTHB'
        bars = client.get_historical_klines(sym, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
        print("Successfully connected to Binance TH!")
        
        # ... (ใส่ Logic การเทรดเดิมต่อจากตรงนี้) ...
        # (เพื่อความกระชับ ผมจะข้ามส่วน Logic ที่เหลือไปนะครับ)
        
    except Exception as e:
        print(f"Critical Error: {e}")
        if "restricted location" in str(e).lower():
            print("❌ ยืนยัน: GitHub IP ถูก Binance บล็อกพื้นที่ครับ")

if __name__ == "__main__":
    run_check()
