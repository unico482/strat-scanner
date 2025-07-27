# scanner/alpaca_data.py

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from datetime import datetime, timedelta
import pandas as pd
import os
import re
from dotenv import load_dotenv

load_dotenv()

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")

client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

TIMEFRAME_MAP = {
    "day": TimeFrame.Day,
    "week": TimeFrame.Week,
    "month": TimeFrame.Month,
}

DURATION_MAP = {
    "day": timedelta(days=10),
    "week": timedelta(weeks=6),
    "month": timedelta(days=120),
}

def fetch_stock_bars(tickers, timeframe: str):
    tf_enum = TIMEFRAME_MAP[timeframe]
    delta = DURATION_MAP[timeframe]
    end = datetime.utcnow()
    start = end - delta

    request = StockBarsRequest(
        symbol_or_symbols=tickers,
        timeframe=tf_enum,
        start=start,
        end=end,
        feed=DataFeed.IEX
    )
    bars = client.get_stock_bars(request).df

    if "trade_count" in bars.columns:
        bars = bars.drop(columns=["trade_count", "vwap"])
    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.reset_index()

    return (
        bars.sort_values(["symbol", "timestamp"])
        .groupby("symbol")
        .tail(4)
        .reset_index(drop=True)
        .assign(timeframe=timeframe)
    )
