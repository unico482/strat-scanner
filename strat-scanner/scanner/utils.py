import pandas as pd

def save_to_csv(df, filename="scanner_results.csv"):
    df.to_csv(filename, index=False)

def format_strat_match_df(df):
    df = df.copy()
    df = df.sort_values(by=["symbol", "timeframe"])
    return df.reset_index(drop=True)
