# scanner/utils.py
from pathlib import Path
import pandas as pd

# repo root (one level above this file’s folder)
BASE_DIR = Path(__file__).resolve().parents[1]

def save_to_csv(df, filename: str = "scanner_results.csv"):
    df.to_csv(filename, index=False)

def format_strat_match_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    return df.sort_values(["symbol", "timeframe"]).reset_index(drop=True)

def load_watchlist(watchlist_type: str) -> list[str]:
    """
    Return the tickers in stock_watchlist.txt or crypto_watchlist.txt.

    Parameters
    ----------
    watchlist_type : str
        "stock" or "crypto"

    Returns
    -------
    list[str]
        Upper-case tickers
    """
    filename = "stock_watchlist.txt" if watchlist_type == "stock" else "crypto_watchlist.txt"
    path = BASE_DIR / filename
    # final local fallback (helps when someone runs from repo root)
    if not path.exists():
        path = Path(filename)
    with path.open() as f:
        return [line.strip().upper() for line in f if line.strip()]
