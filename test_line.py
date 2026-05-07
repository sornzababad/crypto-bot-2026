"""Send a test LINE notification to verify the connection."""
import os, sys
sys.path.insert(0, '/home/botuser/crypto-bot-2026')
from bot.notifier import _push

_push("🤖 ทดสอบ LINE Notify\nบอทเชื่อมต่อสำเร็จ ✅\nพร้อมแจ้งเตือนซื้อ/ขายแล้วครับ")
print("Sent!")
