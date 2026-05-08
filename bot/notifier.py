import os
from datetime import datetime, timedelta, timezone

import requests

from bot.config import TAKE_PROFIT_PCT, STOP_LOSS_PCT

LINE_TOKEN = os.getenv('LINE_TOKEN', '')
USER_ID    = os.getenv('LINE_USER_ID', '')
BKK        = timezone(timedelta(hours=7))


def _now_bkk() -> str:
    return datetime.now(BKK).strftime('%H:%M น. %d/%m/%Y')


def _push(text: str):
    if not LINE_TOKEN or not USER_ID:
        print(f"[LINE] {text}")
        return
    url     = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json',
               'Authorization': f'Bearer {LINE_TOKEN}'}
    res = requests.post(
        url,
        json={"to": USER_ID, "messages": [{"type": "text", "text": text}]},
        headers=headers,
        timeout=10,
    )
    print(f"LINE {res.status_code}: {res.text[:120]}")


def notify_buy(symbol: str, price: float, quantity: float,
               invested_thb: float, rsi: float, signal: str):
    coin = symbol.split('/')[0]
    text = (
        f"🟢 ซื้อ {coin}\n"
        f"ราคา: {price:,.2f} ฿\n"
        f"จำนวน: {quantity:.6g} {coin}\n"
        f"ลงทุน: {invested_thb:,.0f} ฿\n"
        f"สัญญาณ: {signal} (RSI {rsi:.0f})\n"
        f"TP: {price*(1+TAKE_PROFIT_PCT):,.2f} ฿  |  SL: {price*(1-STOP_LOSS_PCT):,.2f} ฿\n"
        f"⏰ {_now_bkk()}"
    )
    _push(text)


def notify_sell(symbol: str, price: float, quantity: float,
                thb_returned: float, reason: str, pnl_pct: float):
    coin = symbol.split('/')[0]
    icon = '🟢' if pnl_pct >= 0 else '🔴'
    sign = '+' if pnl_pct >= 0 else ''
    text = (
        f"{icon} ขาย {coin}\n"
        f"ราคา: {price:,.2f} ฿\n"
        f"จำนวน: {quantity:.6g} {coin}\n"
        f"ได้รับ: {thb_returned:,.0f} ฿\n"
        f"กำไร/ขาดทุน: {sign}{pnl_pct:.2f}%\n"
        f"เหตุผล: {reason}\n"
        f"⏰ {_now_bkk()}"
    )
    _push(text)


def notify_summary(thb_balance: float, total_value: float,
                   positions: dict, realized_pnl_thb: float,
                   scan_results: list = None):
    sign  = '+' if realized_pnl_thb >= 0 else ''
    lines = [
        f"📊 สรุปพอร์ต — {_now_bkk()}",
        f"มูลค่ารวม: {total_value:,.0f} ฿",
        f"THB ว่าง: {thb_balance:,.0f} ฿",
        f"กำไร/ขาดทุนสะสม: {sign}{realized_pnl_thb:,.2f} ฿",
        "",
    ]
    if positions:
        lines.append("📌 ถือครอง:")
        for sym, pos in positions.items():
            p   = pos.get('pnl_pct', 0.0)
            s   = '+' if p >= 0 else ''
            lines.append(f"  • {sym.split('/')[0]}: {s}{p:.2f}%")
        lines.append("")
    else:
        lines.append("(ไม่มีเหรียญในพอร์ต — รอสัญญาณซื้อ)")
        lines.append("")

    if scan_results:
        lines.append("🔍 RSI ล่าสุด:")
        for sym, rsi, sig in scan_results[:8]:
            coin = sym.split('/')[0]
            tag  = f" ← {sig}" if sig not in ('HOLD', 'NEUTRAL') else ''
            lines.append(f"  {coin}: {rsi}{tag}")

    _push("\n".join(lines))


def notify_error(message: str):
    _push(f"⚠️ Bot Error\n{message[:300]}\n{_now_bkk()}")
