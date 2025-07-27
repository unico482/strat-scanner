import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import time

BASE_URL = "https://data-api.binance.vision/api/v3/klines"

INTERVAL_MAP = {
    "4h": "4h",
    "12h": "12h",
    "day": "1d",
    "previous day": "1d",
    "week": "1w",
    "month": "1M",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_WORKERS = 5
RETRIES     = 4
TIMEOUT     = 10


def convert_symbol_to_binance(symbol: str) -> str:
    """Convert 'BTC/USD' → 'BTCUSDT'."""
    base, _ = symbol.split("/")
    return base + "USDT"


def fetch_symbol(symbol: str, timeframe: str) -> pd.DataFrame | None:
    binance_symbol = convert_symbol_to_binance(symbol)
    interval       = INTERVAL_MAP[timeframe.lower()]
    url = f"{BASE_URL}?symbol={binance_symbol}&interval={interval}&limit=4"

    for attempt in range(RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            klines = r.json()
            if not klines:
                return None

            df = pd.DataFrame(
                klines,
                columns=[
                    "open_time", "open", "high", "low", "close",
                    "volume", "close_time", "quote_asset_vol",
                    "num_trades", "taker_buy_base_vol",
                    "taker_buy_quote_vol", "ignore",
                ],
            )
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
            df = df.rename(columns={"open_time": "timestamp"})
            df["symbol"] = symbol

            # return the unified schema expected downstream
            return df[["symbol", "timestamp", "open", "high", "low", "close", "volume"]]

        except Exception as e:
            if attempt < RETRIES - 1:
                time.sleep(0.3)
            else:
                print(f"[ERROR] {symbol} {timeframe}: {e}")
                return None


def fetch_bars(symbols: list[str], timeframe: str) -> pd.DataFrame:
    """Fetch last 4 bars for every symbol, return concatenated DataFrame."""
    all_bars = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_symbol, s, timeframe): s for s in symbols}
        for fut in as_completed(futures):
            df = fut.result()
            if df is not None:
                all_bars.append(df)

    if not all_bars:
        return pd.DataFrame(
            columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"]
        )

    df = pd.concat(all_bars, ignore_index=True)
    df = df.loc[:, ~df.columns.duplicated()]  # drop duplicate columns

    return df
