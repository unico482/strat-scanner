import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def _probe_binance():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ping", timeout=5)
        status_message = f"[probe] Binance ping → {r.status_code} (host region = {os.getenv('FLY_REGION', 'streamlit-cloud')})"
        st.sidebar.write(status_message)  # Show in the Streamlit sidebar
        print(status_message)  # Will show up in the app's logs
    except Exception as e:
        status_message = f"[probe] Binance ping failed → {e}"
        st.sidebar.write(status_message)  # Show in the sidebar
        print(status_message)  # Will show up in the app's logs
        
_probe_binance()

import time

INTERVAL_MAP = {
    "day": "1d",
    "previous day": "1d",
    "week": "1w",
    "month": "1M",
    "4h": "4h",
    "12h": "12h"
}

def convert_symbol_to_binance(symbol):
    """Convert 'BTC/USD' → 'BTCUSDT'."""
    base, quote = symbol.split("/")
    return base + "USDT"

def fetch_symbol(symbol, timeframe, max_retries=3):
    try:
        binance_symbol = convert_symbol_to_binance(symbol)
        interval = INTERVAL_MAP[timeframe.lower()]
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={binance_symbol}&interval={interval}&limit=4"

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    raise e

        data = response.json()
        if not data:
            print(f"[NO DATA] {symbol}")
            return None

        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "_1", "_2", "_3", "_4", "_5", "_6"
        ])[
            ["timestamp", "open", "high", "low", "close", "volume"]
        ]

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[
            ["open", "high", "low", "close", "volume"]
        ].astype(float)

        df["symbol"] = symbol
        df["timeframe"] = timeframe

        # If 'Previous Day', drop today's partial candle
        if timeframe.lower() == "previous day":
            df = df.iloc[:-1]

        return df

    except Exception as e:
        print(f"[ERROR] Failed to fetch {symbol} → {e}")
        return None

def fetch_crypto_bars_binance_futures(tickers, timeframe: str):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_symbol, symbol, timeframe) for symbol in tickers]
        results = [f.result() for f in as_completed(futures)]

    all_bars = [df for df in results if df is not None]

    if all_bars:
        bars = (
            pd.concat(all_bars, ignore_index=True)
            .sort_values(["symbol", "timestamp"])
            .groupby("symbol")
            .tail(4)
            .reset_index(drop=True)
        )
        return bars
    else:
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume", "timeframe"])
