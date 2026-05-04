import os
import ccxt

from bot.config import KLINE_TIMEFRAME, KLINE_LIMIT


def create_exchange() -> ccxt.Exchange:
    api_key    = os.getenv('BINANCE_API_KEY', '')
    api_secret = os.getenv('BINANCE_API_SECRET', '')

    # Try BinanceTH first; fall back to Binance global with TH URL if not in ccxt build
    try:
        exchange = ccxt.binanceth({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {'defaultType': 'spot'},
            'enableRateLimit': True,
        })
    except AttributeError:
        base_url = os.getenv('BINANCE_BASE_URL', 'https://api.binance.th')
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {'defaultType': 'spot'},
            'enableRateLimit': True,
            'urls': {
                'api': {
                    'public':  base_url,
                    'private': base_url,
                }
            },
        })

    return exchange


def get_closing_prices(exchange: ccxt.Exchange, symbol: str) -> list[float]:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=KLINE_TIMEFRAME, limit=KLINE_LIMIT)
    return [float(c[4]) for c in ohlcv]


def get_free_thb(exchange: ccxt.Exchange) -> float:
    bal = exchange.fetch_balance()
    return float(bal.get('free', {}).get('THB', 0.0))


def get_coin_balance(exchange: ccxt.Exchange, coin: str) -> float:
    bal = exchange.fetch_balance()
    return float(bal.get('free', {}).get(coin, 0.0))


def get_current_price(exchange: ccxt.Exchange, symbol: str) -> float:
    ticker = exchange.fetch_ticker(symbol)
    return float(ticker['last'])


def place_market_buy(exchange: ccxt.Exchange, symbol: str, thb_amount: float) -> dict:
    """Buy coin using a THB cost amount."""
    price    = get_current_price(exchange, symbol)
    quantity = thb_amount / price
    quantity = float(exchange.amount_to_precision(symbol, quantity))
    return exchange.create_market_buy_order(symbol, quantity)


def place_market_sell(exchange: ccxt.Exchange, symbol: str, quantity: float) -> dict:
    quantity = float(exchange.amount_to_precision(symbol, quantity))
    return exchange.create_market_sell_order(symbol, quantity)
