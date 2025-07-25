from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# Load credentials
ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")

# Initialize Alpaca clients
stock_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
crypto_client = CryptoHistoricalDataClient()

# Map text to Alpaca timeframes
TIMEFRAME_MAP = {
    "Daily": TimeFrame.Day,
    "Weekly": TimeFrame.Week,
    "Monthly": TimeFrame.Month
}

def fetch_bars(symbols, timeframe="Daily", asset_class="stock", lookback=5):
    """
    Fetch OHLCV bars for given symbols and timeframe.
    Returns a combined pandas DataFrame with all bars.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback * 2)

    tf = TIMEFRAME_MAP[timeframe]
    all_data = []

    for symbol in symbols:
        try:
            if asset_class == "stock":
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=tf,
                    start=start_date,
                    end=end_date
                )
                bars = stock_client.get_stock_bars(request).df
            elif asset_class == "crypto":
                request = CryptoBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=tf,
                    start=start_date,
                    end=end_date
                )
                bars = crypto_client.get_crypto_bars(request).df
            else:
                continue

            if bars.empty:
                continue

            df = bars.reset_index()
            df["symbol"] = symbol
            df["timeframe"] = timeframe
            all_data.append(df)

        except Exception as e:
            print(f"Error fetching {symbol} ({timeframe}): {e}")

    if not all_data:
        return pd.DataFrame()

    result = pd.concat(all_data, ignore_index=True)
    return result[["symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]]
