import streamlit as st
import pandas as pd

from scanner.utils import load_watchlist
from scanner.data import fetch_bars
from scanner.patterns import detect_patterns


# ────────── page setup ──────────
st.set_page_config(page_title="Strat Scanner", layout="wide")
st.title("Strat Pattern Scanner")


# ────────── sidebar widgets ──────────
watchlist_label = st.selectbox("Watchlist Type", ["Stocks", "Crypto"])
watchlist_type  = "stock" if watchlist_label == "Stocks" else "crypto"

if watchlist_type == "crypto":
    timeframe = st.selectbox(
        "Timeframe",
        ["4H", "12H", "Day", "3 Day", "Week", "Month"],
    )
else:
    timeframe = st.selectbox("Timeframe", ["Day", "Week", "Month"])

scan_previous = st.checkbox(
    "Use previous",
    value=False,
    help="When checked, patterns are evaluated on the bar that closed one period ago.",
)

selected_patterns = st.multiselect(
    "Filter patterns",
    options=[
        {"label": "Hammer",      "value": "Hammer"},
        {"label": "Shooter",     "value": "Shooter"},
        {"label": "Inside Bar",  "value": "Inside Bar"},
        {"label": "2u",          "value": "2u"},      
        {"label": "2d",          "value": "2d"},   
        {"label": "2u Red",      "value": "2u Red"},
        {"label": "2d Green",    "value": "2d Green"},
        {"label": "RevStrat",    "value": "RevStrat"},
        {"label": "3-2-2",       "value": "3-2-2"},
        {"label": "Outside Bar", "value": "Outside Bar"},
    ],
    format_func=lambda x: x["label"],
    default=[],
)


# ────────── helpers ──────────
@st.cache_data(ttl=3600)
def get_htf_bars(symbols: list[str], tf: str, src: str) -> pd.DataFrame:
    df = fetch_bars(symbols, tf, src)
    if df.empty:
        return pd.DataFrame(columns=["symbol"]).set_index("symbol")
    return (
        df.sort_values(["symbol", "timestamp"])
          .groupby("symbol")
          .tail(1)
          .set_index("symbol")
    )


def tfc_flag(bar: pd.Series) -> bool | None:
    try:
        if pd.isna(bar["open"]) or pd.isna(bar["close"]) or bar["high"] == bar["low"]:
            return None
        return bool(bar["close"] > bar["open"])
    except KeyError:
        return None


# ────────── main action ──────────
if st.button("Run Scanner"):
    try:
        tickers = load_watchlist(watchlist_type.lower())
        tf_key = timeframe.lower()

        bars_df = fetch_bars(tickers, tf_key, watchlist_type.lower())
        st.markdown(f"### Scanning {watchlist_type} watchlist on {timeframe} timeframe…")
        st.write(f"Raw bars fetched: ({bars_df.shape[0]}, {bars_df.shape[1]})")

        bars_df = bars_df.sort_values(["symbol", "timestamp"])
        recent_bars = (
            bars_df.groupby("symbol")
            .tail(4)
            .reset_index(drop=True)
        )

        if scan_previous:
            mask = recent_bars.groupby("symbol").cumcount(ascending=False) != 0
            recent_bars = recent_bars[mask].reset_index(drop=True)

        # decide higher timeframes
        if tf_key in ("4h", "12h"):
            htf_list = ["day", "week", "month"]
        elif tf_key in ("day", "previous day", "3 day"):
            htf_list = ["week", "month"]
        elif tf_key == "week":
            htf_list = ["month"]
        else:
            htf_list = []

        htf_data = {
            tf: get_htf_bars(tickers, tf, watchlist_type.lower())
            for tf in htf_list
        }

        selected_values = [p["value"] for p in selected_patterns]
        matches = []

        for symbol, group in recent_bars.groupby("symbol"):
            if len(group) < 3:
                continue

            hit = detect_patterns(symbol, group, selected_values)
            if not hit:
                continue

            if "day" in htf_data and symbol in htf_data["day"].index:
                hit["D_flag"] = tfc_flag(htf_data["day"].loc[symbol])
            if "week" in htf_data and symbol in htf_data["week"].index:
                hit["W_flag"] = tfc_flag(htf_data["week"].loc[symbol])
            if "month" in htf_data and symbol in htf_data["month"].index:
                hit["M_flag"] = tfc_flag(htf_data["month"].loc[symbol])

            matches.append(hit)

        if not matches:
            st.warning("No matching patterns found.")
            st.stop()

        df = pd.DataFrame(matches)

        # ───── standardise column names ─────
        df = df.rename(columns={
            "symbol": "Symbol",
            "patterns": "Pattern"
        })
        if "Symbol" in df.columns:
            df["Symbol"] = df["Symbol"].str.upper()

        # ───── pill-style pattern column ─────
        df["Pattern"] = df["Pattern"].apply(lambda x: [x] if not isinstance(x, list) else x)

        # ───── TFC logic: uppercase = green, lowercase = red ─────
        def tfc_letter(flag, label):
            if pd.isna(flag) or flag is None:
                return ""
            return label.upper() if flag else label.lower()

        include_d = tf_key in ("4h", "12h") and watchlist_type.lower() == "crypto"

        df["TFC"] = df.apply(
            lambda row: " ".join(filter(None, [
                tfc_letter(row["D_flag"], "D") if include_d and "D_flag" in row else "",
                tfc_letter(row["W_flag"], "W") if "W_flag" in row else "",
                tfc_letter(row["M_flag"], "M") if "M_flag" in row else ""
            ])),
            axis=1
        )

        # drop temp flag columns
        for col in ("D_flag", "W_flag", "M_flag"):
            if col in df.columns:
                df.drop(columns=col, inplace=True)

        # final output
        df = df[["Symbol", "Pattern", "TFC"]]
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Error while running scanner: {e}")
