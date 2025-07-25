import pandas as pd
import numpy as np

def detect_strat_patterns(df):
    """
    Add Strat pattern flags to the given dataframe.
    Expects OHLC dataframe with sorted rows per symbol + timeframe.
    """
    df = df.sort_values(by=["symbol", "timeframe", "timestamp"]).copy()

    # === Bar Structure ===
    df["prev_high"] = df.groupby(["symbol", "timeframe"])["high"].shift(1)
    df["prev_low"] = df.groupby(["symbol", "timeframe"])["low"].shift(1)

    df["is_inside"] = (df["high"] < df["prev_high"]) & (df["low"] > df["prev_low"])
    df["is_outside"] = (df["high"] > df["prev_high"]) & (df["low"] < df["prev_low"])
    df["is_2u"] = (df["high"] > df["prev_high"]) & (df["low"] > df["prev_low"])
    df["is_2d"] = (df["high"] < df["prev_high"]) & (df["low"] < df["prev_low"])

    # === Candle Color ===
    df["is_green"] = df["close"] >= df["open"]
    df["is_red"] = df["close"] < df["open"]

    # === Wick & Body Logic ===
    df["range"] = df["high"] - df["low"]
    df["body"] = abs(df["close"] - df["open"])
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    df["is_shooter"] = (
        (df["range"] > 0) &
        (df["body"] > 0) &
        (df[["open", "close"]].max(axis=1) <= df["low"] + df["range"] * 0.4) &
        (df["upper_wick"] >= df["body"] * 1.5)
    )

    df["is_hammer"] = (
        (df["range"] > 0) &
        (df["body"] > 0) &
        (df[["open", "close"]].min(axis=1) >= df["high"] - df["range"] * 0.4) &
        (df["lower_wick"] >= df["body"] * 1.5)
    )

    # === Pattern Labels ===
    patterns = []

    for i, row in df.iterrows():
        label = None

        if row["is_inside"]:
            label = "Inside Bar"
        elif row["is_outside"]:
            label = "Outside Bar"
        elif row["is_2u"] and row["is_red"] and row["is_shooter"]:
            label = "2u Red Shooter"
        elif row["is_2d"] and row["is_green"] and row["is_hammer"]:
            label = "2d Green Hammer"
        elif row["is_shooter"]:
            label = "Shooter"
        elif row["is_hammer"]:
            label = "Hammer"

        # Combo patterns
        elif row["is_2u"]:
            prev_inside = df.at[i - 1, "is_inside"] if i > 0 else False
            prev_3 = df.at[i - 1, "is_outside"] if i > 0 else False
            if prev_inside:
                label = "1-2-2 Rev Strat"
            elif prev_3:
                label = "3-2-2"
            else:
                label = "2u"
        elif row["is_2d"]:
            prev_inside = df.at[i - 1, "is_inside"] if i > 0 else False
            prev_3 = df.at[i - 1, "is_outside"] if i > 0 else False
            if prev_inside:
                label = "1-2-2 Rev Strat"
            elif prev_3:
                label = "3-2-2"
            else:
                label = "2d"

        elif row["is_outside"]:
            prev_inside = df.at[i - 1, "is_inside"] if i > 0 else False
            if prev_inside:
                label = "x-1 Setup"
            else:
                label = "3"

        if label:
            patterns.append((row["symbol"], row["timeframe"], row["timestamp"], label))

    result = pd.DataFrame(patterns, columns=["symbol", "timeframe", "timestamp", "pattern"])
    return result
