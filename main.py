import os
import pandas as pd
import ta
import requests
from google import genai
from binance.client import Client

# ดึงค่าจาก Secrets
B_KEY      = os.getenv('BINANCE_KEY')
B_SECRET   = os.getenv('BINANCE_SECRET')
G_KEY      = os.getenv('GEMINI_KEY')
LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

client = Client(B_KEY, B_SECRET)
client.API_URL = 'https://api.binance.th/api'
client.PRIVATE_API_URL = 'https://api.binance.th/api'

ai_client = genai.Client(api_key=G_KEY)

def send_line(msg):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'}
    data = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, json=data, headers=headers)

def run_check():
    # 1. ส่งแจ้งเตือนทันทีที่เริ่ม (เพื่อให้รู้ว่าบอทไม่ตาย)
    send_line("🔍 บอทเริ่มตรวจสอบตลาดประจำชั่วโมง...")
    
    try:
        balance = client.get_asset_balance(asset='THB')
        cash = float(balance['free'])
        print(f"เชื่อมต่อสำเร็จ! เงินสด: {cash} THB")

        # ... (ส่วนเช็คสัญญาณซื้อขายเดิม) ...
        # (ถ้าไม่มีสัญญาณซื้อขาย บอทจะจบการทำงานตรงนี้)

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        # ถ้าโดนบล็อก IP ให้ส่งแจ้งเตือนบอกในไลน์ด้วย
        if "restricted location" in error_msg.lower():
            send_line("❌ GitHub IP โดนบล็อก (Restricted Location) ค่อยมาแก้พรุ่งนี้ครับ")
        else:
            send_line(f"⚠️ เกิดข้อผิดพลาด: {error_msg[:50]}")

if __name__ == "__main__":
    run_check()
