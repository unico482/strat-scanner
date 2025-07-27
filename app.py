# --- connectivity probe ----------------------------------------------------
import streamlit as st, requests, os

def probe_binance_once():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ping", timeout=5)
        code = r.status_code
        msg  = f"Binance /fapi/v1/ping → {code}   " \
               f"(host = {os.getenv('FLY_REGION', 'streamlit-cloud')})"
    except Exception as e:
        msg  = f"Binance ping failed → {e}"
    # put the result in an unmistakeable place
    st.markdown(f"### {msg}")

probe_binance_once()
# --------------------------------------------------------------------------

import streamlit as st
import pandas as pd
from scanner.utils import load_watchlist
from scanner.data import fetch_bars
from scanner.patterns import detect_patterns

st.set_page_config(page_title="Strat Scanner", layout="wide")
st.title("Strat Pattern Scanner")

watchlist_type = st.selectbox("Watchlist Type", ["Stock", "Crypto"])

if watchlist_type == "Crypto":
    timeframe = st.selectbox("Timeframe", ["4H", "12H", "Previous Day", "Day", "Week", "Month"])
else:
    timeframe = st.selectbox("Timeframe", ["Day", "Week", "Month"])

selected_patterns = st.multiselect(
    "Filter patterns",
    options=[
        {"label": "Hammer", "value": "Hammer"},
        {"label": "Shooter", "value": "Shooter"},
        {"label": "Inside Bar", "value": "Inside Bar"},
        {"label": "2u Red", "value": "2u Red"},
        {"label": "2d Green", "value": "2d Green"},
        {"label": "RevStrat", "value": "RevStrat"},
        {"label": "3-2-2", "value": "3-2-2"},
    ],
    format_func=lambda x: x["label"],
    default=[],
)

if st.button("Run Scanner"):
    try:
        tickers = load_watchlist(watchlist_type.lower())
        tf = timeframe.lower()
        bars_df = fetch_bars(tickers, tf, watchlist_type.lower())
        st.markdown(f"### Scanning {watchlist_type} watchlist on {timeframe} timeframe…")
        st.write(f"Raw bars fetched: ({bars_df.shape[0]}, {bars_df.shape[1]})")

        # Sort by symbol and timestamp to ensure chronological order
        bars_df = bars_df.sort_values(["symbol", "timestamp"])
        recent_bars = bars_df.groupby("symbol").tail(4).reset_index(drop=True)

        selected_pattern_values = [p["value"] for p in selected_patterns]

        matches = []
        for symbol, group in recent_bars.groupby("symbol"):
            if len(group) >= 3:
                result = detect_patterns(symbol, group, selected_pattern_values)
                if result:
                    matches.append(result)

        if not matches:
            st.warning("No matching patterns found.")
        else:
            df = pd.DataFrame(matches)
            st.dataframe(df)

    except Exception as e:
        st.error(f"Error while running scanner: {e}")
