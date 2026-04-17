import os
import time
import hmac
import hashlib
import requests
import pandas as pd
import ta
from google import genai

# ⚙️ 1. ดึงค่าจาก Secrets
B_KEY      = os.getenv('BINANCE_KEY')
B_SECRET   = os.getenv('BINANCE_SECRET')
G_KEY      = os.getenv('GEMINI_KEY')
LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

BASE_URL = 'https://api.binance.th'

def send_line(msg):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, json=data, headers=headers)

# ฟังก์ชันสำหรับเซ็นชื่อกำกับคำสั่ง (Signature) ตามกฎของ Binance
def get_binance_balance():
    endpoint = '/api/v3/account'
    query_string = f"timestamp={int(time.time() * 1000)}"
    signature = hmac.new(B_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    headers = {'X-MBX-APIKEY': B_KEY}
    res = requests.get(url, headers=headers)
    return res.json()

def run_check():
    # แจ้งเตือนในไลน์ให้รู้ว่าบอท "ตื่นแล้ว"
    send_line("🤖 บอท GitHub กำลังเริ่มตรวจสอบตลาด...")
    
    try:
        # ลองดึงข้อมูลยอดเงิน (ถ้าผ่านจุดนี้ได้คือรอด!)
        account_info = get_binance_balance()
        
        # เช็คว่าโดนบล็อก IP ไหม
        if 'code' in account_info and account_info['code'] == 0:
             print("Success connection!")
        
        # ดึงราคา BTC เพื่อทดสอบ
        price_res = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol=BTCTHB")
        price = price_res.json()['price']
        
        send_line(f"✅ เชื่อมต่อสำเร็จ!\nราคา BTC ตอนนี้: {float(price):,.0f} บาท")

    except Exception as e:
        error_msg = str(e)
        if "Service unavailable" in error_msg or "restricted" in error_msg:
            send_line("❌ GitHub ยังคงโดนบล็อก IP (Restricted Location)")
        else:
            send_line(f"⚠️ Error: {error_msg[:50]}")

if __name__ == "__main__":
    run_check()
