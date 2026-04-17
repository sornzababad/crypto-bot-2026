import os
import pandas as pd
import ta
import requests
from google import genai
from binance.client import Client

# ============================================================
# ⚙️ 1. ดึงค่าจาก GitHub Secrets
# ============================================================
B_KEY      = os.getenv('BINANCE_KEY')
B_SECRET   = os.getenv('BINANCE_SECRET')
G_KEY      = os.getenv('GEMINI_KEY')
LINE_TOKEN = os.getenv('LINE_TOKEN')
USER_ID    = os.getenv('LINE_USER_ID')

# ============================================================
# 🔌 2. การตั้งค่าการเชื่อมต่อ (Fix URL สำหรับ Binance TH)
# ============================================================
# สร้าง Client โดยระบุ URL ของไทยโดยตรงเพื่อแก้ปัญหา Resource Not Found
client = Client(B_KEY, B_SECRET)
client.API_URL = 'https://api.binance.th/api'
client.PRIVATE_API_URL = 'https://api.binance.th/api'

# เชื่อมต่อ AI Gemini
ai_client = genai.Client(api_key=G_KEY)

# ============================================================
# 💬 3. ฟังก์ชันส่งข้อความ LINE OA
# ============================================================
def send_line(msg):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_TOKEN}'
    }
    data = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            print(f"LINE Error: {response.text}")
    except Exception as e:
        print(f"Send Line Error: {e}")

# ============================================================
# 🧠 4. ฟังก์ชันถาม AI Gemini (ชั้นกรองสัญญาณ)
# ============================================================
def ask_ai(symbol, prices):
    prompt = f"""
    คุณคือผู้เชี่ยวชาญด้านการเทรดคริปโต วิเคราะห์เหรียญ {symbol} 
    จากราคาปิด 24 ชั่วโมงล่าสุดนี้: {prices}
    ภาพรวมเทรนด์เป็นอย่างไร? ควรเข้าซื้อตอนนี้เลยไหม? 
    ตอบสั้นๆ ว่า 'BUY' หรือ 'WAIT' พร้อมเหตุผลสั้นๆ 1 ประโยค
    """
    try:
        response = ai_client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "WAIT (AI Error)"

# ============================================================
# 📈 5. ฟังก์ชันหลัก (Check Signal & Trade)
# ============================================================
def run_check():
    # รายชื่อเหรียญที่เราจะเล่นใน Binance TH
    SYMBOLS = ['BTCTHB', 'ETHTHB', 'SOLTHB']
    
    try:
        # เช็คเงินสดบาทที่มีในกระเป๋า
        balance = client.get_asset_balance(asset='THB')
        cash = float(balance['free'])
        print(f"Current THB Balance: {cash}")

        for sym in SYMBOLS:
            # ดึงราคาย้อนหลัง 48 ชม. (เพื่อคำนวณ EMA)
            bars = client.get_historical_klines(sym, Client.KLINE_INTERVAL_1HOUR, "2 days ago UTC")
            df = pd.DataFrame(bars)
            df = df.iloc[:, :6]
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            df['close'] = df['close'].astype(float)
            
            # คำนวณอินดิเคเตอร์ EMA 12 และ 26
            ema_f = ta.trend.ema_indicator(df['close'], window=12).iloc[-1]
            ema_s = ta.trend.ema_indicator(df['close'], window=26).iloc[-1]
            
            # เช็คว่าถือเหรียญนี้อยู่เท่าไหร่
            asset_name = sym.replace('THB', '')
            asset_balance = client.get_asset_balance(asset=asset_name)
            held_qty = float(asset_balance['free'])
            
            current_price = df['close'].iloc[-1]

            # 🟢 เงื่อนไขการซื้อ: EMA ตัดขึ้น + ยังไม่มีของ + มีเงินพอ (ขั้นต่ำ 500 บาท)
            if ema_f > ema_s and held_qty < 0.0001 and cash > 500:
                history = df['close'].tail(24).tolist()
                ai_reply = ask_ai(sym, history)
                
                if "BUY" in ai_reply.upper():
                    # คำนวณเงินซื้อ (ใช้ 50% ของที่มีเพื่อทบต้น)
                    buy_amt = cash * 0.5
                    print(f"Executing BUY for {sym} with {buy_amt} THB")
                    client.order_market_buy(symbol=sym, quoteOrderQty=round(buy_amt, 1))
                    send_line(f"🟢 [GITHUB BOT]\nซื้อเหรียญ: {sym}\nราคา: {current_price:,.2f} THB\n🤖 AI วิเคราะห์: {ai_reply}")
            
            # 🔴 เงื่อนไขการขาย: EMA ตัดลง + มีของอยู่ในมือ
            elif ema_f < ema_s and held_qty > 0.0001:
                print(f"Executing SELL for {sym}")
                client.order_market_sell(symbol=sym, quantity=held_qty)
                # เช็คยอดหลังขายเพื่อรายงาน
                new_cash = float(client.get_asset_balance(asset='THB')['free'])
                send_line(f"🔴 [GITHUB BOT]\nขายเหรียญ: {sym}\nราคา: {current_price:,.2f} THB\n💹 ยอดเงินคงเหลือปัจจุบัน: {new_cash:,.2f} THB")

    except Exception as e:
        print(f"Execution Error: {e}")
        # ถ้า Error หนักๆ ให้ส่งแจ้งเตือนเข้า LINE
        # send_line(f"⚠️ Bot Error: {str(e)}")

if __name__ == "__main__":
    run_check()
