import streamlit as st
import pandas as pd
from scanner.data import fetch_bars
from scanner.patterns import detect_strat_patterns
from scanner.utils import format_strat_match_df, save_to_csv

# === Load secrets into env vars (for deployment) ===
os.environ["APCA_API_KEY_ID"] = st.secrets["APCA_API_KEY_ID"]
os.environ["APCA_API_SECRET_KEY"] = st.secrets["APCA_API_SECRET_KEY"]

# === Load Watchlist ===
def load_watchlist(name):
    path = f"{name}_watchlist.txt"
    with open(path, "r") as f:
        return [line.strip().upper() for line in f if line.strip()]

# === Sidebar Controls ===
st.sidebar.title("Strat Scanner")

watchlist_type = st.sidebar.radio("Watchlist", ["Stock", "Crypto"])
selected_timeframes = st.sidebar.multiselect("Timeframes", ["Daily", "Weekly", "Monthly"], default=["Daily"])

tickers = load_watchlist("stock" if watchlist_type == "Stock" else "crypto")
st.sidebar.write(f"{len(tickers)} tickers loaded")

# === Main Header ===
st.title("Strat Pattern Scanner")

# === Run Scanner Button ===
if st.button("Run Scanner"):
    with st.spinner("Fetching data and scanning for patterns..."):
        all_results = []

        for tf in selected_timeframes:
            bars_df = fetch_bars(tickers, timeframe=tf, asset_class="stock" if watchlist_type == "Stock" else "crypto", lookback=30)
            if not bars_df.empty:
                pattern_df = detect_strat_patterns(bars_df)
                all_results.append(pattern_df)

        if all_results:
            final_df = pd.concat(all_results, ignore_index=True)
            final_df = format_strat_match_df(final_df)
            st.success(f"Scan complete. {len(final_df)} pattern(s) found.")
            st.dataframe(final_df, use_container_width=True)

            if st.button("Export to CSV"):
                save_to_csv(final_df)
                st.success("Results saved to scanner_results.csv.")
        else:
            st.warning("No data returned. Check your watchlist or try a different timeframe.")
