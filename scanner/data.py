# scanner/data.py

from scanner.alpaca_data import fetch_stock_bars
from scanner.binance_futures_data import fetch_crypto_bars_binance_futures

def fetch_bars(tickers, timeframe: str, watchlist_type: str):
    if watchlist_type == "stock":
        return fetch_stock_bars(tickers, timeframe)
    elif watchlist_type == "crypto":
        return fetch_crypto_bars_binance_futures(tickers, timeframe)
    else:
        raise ValueError("Invalid watchlist type")
