"""
VPS Live Runner — Crypto Trading Bot
Runs continuously, executing the trading logic every 30 minutes.
State is saved locally to state.json (no git commits needed on VPS).

Usage:
    python run_live.py

Environment variables (set in .env or export before running):
    BINANCE_API_KEY, BINANCE_API_SECRET, LINE_TOKEN, LINE_USER_ID
"""

import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Load .env file if present (no external library needed)
_env_file = Path(__file__).parent / '.env'
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())

from main import run
from bot.notifier import notify_error

INTERVAL_SECONDS = 30 * 60  # 30 minutes between each scan


def main():
    print("=" * 60)
    print("  Crypto Trading Bot — VPS Live Mode")
    print(f"  Scan interval : {INTERVAL_SECONDS // 60} minutes")
    print(f"  Started at    : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    while True:
        start = time.monotonic()
        now   = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        print(f"\n{'─' * 60}")
        print(f"  Cycle start: {now}")
        print(f"{'─' * 60}")

        try:
            run()
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            traceback.print_exc()
            try:
                notify_error(str(e))
            except Exception:
                pass

        elapsed  = time.monotonic() - start
        sleep_for = max(0, INTERVAL_SECONDS - elapsed)

        next_run = datetime.now(timezone.utc)
        next_ts  = int(next_run.timestamp()) + int(sleep_for)
        next_str = datetime.fromtimestamp(next_ts, tz=timezone.utc).strftime('%H:%M UTC')

        print(f"\n  Cycle done in {elapsed:.1f}s — next run at {next_str} "
              f"(sleeping {sleep_for / 60:.1f} min)")

        try:
            time.sleep(sleep_for)
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break


if __name__ == '__main__':
    main()
