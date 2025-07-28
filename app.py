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

if watchlist_type == "Crypto":
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
    """Return the most-recent closed higher-TF bar for every symbol."""
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
    """True = green close, False = red close, None = inside/NA."""
    try:
        if pd.isna(bar["open"]) or pd.isna(bar["close"]) or bar["high"] == bar["low"]:
            return None
        return bool(bar["close"] > bar["open"])
    except KeyError:
        return None


def colour_letter(flag: bool | None, label: str) -> str:
    if flag is None or pd.isna(flag):
        return ""
    colour = "#10b981" if flag else "#ef4444"
    return f"{label}"  if colour == "#10b981" else f"{label}"  # placeholder, will stay plain text


def style_pattern(value) -> str:
    """Return plain text for Streamlit-native table (no HTML)."""
    return ", ".join(value) if isinstance(value, list) else str(value)


SPACER = "   "           # three regular spaces for wider gaps


# ────────── main action ──────────
if st.button("Run Scanner"):
    try:
        tickers = load_watchlist(watchlist_type.lower())
        tf_key  = timeframe.lower()

        # fetch raw bars
        bars_df = fetch_bars(tickers, tf_key, watchlist_type.lower())
        st.markdown(f"### Scanning {watchlist_type} watchlist on {timeframe} timeframe…")
        st.write(f"Raw bars fetched: ({bars_df.shape[0]}, {bars_df.shape[1]})")

        # keep four bars per symbol, newest last
        recent_bars = (
            bars_df.sort_values(["symbol", "timestamp"])
                   .groupby("symbol")
                   .tail(4)
                   .reset_index(drop=True)
        )

        # shift window when “Use previous” is active
        if scan_previous:
            mask = recent_bars.groupby("symbol").cumcount(ascending=False) != 0
            recent_bars = recent_bars[mask].reset_index(drop=True)

        # decide higher-TFs needed
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

            # continuity flags
            if "day" in htf_data and symbol in htf_data["day"].index:
                hit["D"] = tfc_flag(htf_data["day"].loc[symbol])
            if "week" in htf_data and symbol in htf_data["week"].index:
                hit["W"] = tfc_flag(htf_data["week"].loc[symbol])
            if "month" in htf_data and symbol in htf_data["month"].index:
                hit["M"] = tfc_flag(htf_data["month"].loc[symbol])

            matches.append(hit)

        if not matches:
            st.warning("No matching patterns found.")
            st.stop()

        df = pd.DataFrame(matches)

        # plain-text continuity letters (Streamlit will colour according to theme)
        for col in ("D", "W", "M"):
            if col in df.columns:
                df[col] = df[col].apply(lambda v, l=col: l if v is not None else "")

        # build TFC column
        df["TFC"] = df.apply(lambda r: SPACER.join([r.get(x, "") for x in ("D","W","M") if r.get(x)]), axis=1)
        df = df.drop(columns=[c for c in ("D", "W", "M") if c in df.columns])

        # rename & prettify
        df = df.rename(
            columns={
                "symbol":  "Symbol",
                "patterns": "Pattern",
                "cc":       "CC",
                "c1":       "C1",
                "c2":       "C2",
            }
        )

        if "Symbol" in df.columns:
            df["Symbol"] = df["Symbol"].str.upper()
        if "Pattern" in df.columns:
            df["Pattern"] = df["Pattern"].apply(style_pattern)

        # column order for native dataframe
        ordered = ["Symbol", "Pattern", "CC", "C1", "C2", "TFC"]
        df = df[[c for c in ordered if c in df.columns]]

        # ─────  convert Pattern to list → Streamlit shows pill chips  ─────
        df["Pattern"] = df["Pattern"].apply(lambda x: [x] if not isinstance(x, list) else x)

        # ─────  split TFC into separate columns (letters)  ─────
        df["D_flag"] = df.pop("D") if "D" in df.columns else None
        df["W_flag"] = df.pop("W") if "W" in df.columns else None
        df["M_flag"] = df.pop("M") if "M" in df.columns else None

        for col, letter in (("D_flag", "D"), ("W_flag", "W"), ("M_flag", "M")):
            if col in df.columns:
                df[letter] = df[col].apply(lambda b: letter if b is not None else "")

        # reorder visible columns
        visible_cols = ["Symbol", "Pattern", "CC", "C1", "C2", "D", "W", "M"]
        df = df[[c for c in visible_cols if c in df.columns]]

        # ─────  Styler: colour text + hide grid + hide index + drop flag cols  ─────
        def colour_text(val):
            # val is 'D','W','M' or ''
            if val in ("D", "W", "M"):
                colour = "#10b981" if val.isupper() else "#ef4444"  # uppercase → green, lowercase (unused) → red
                return f"color: {colour}; font-weight: 700;"
            return ""

        styler = (
            df.style
              .applymap(colour_text, subset=["D", "W", "M"])
              .hide(axis="index")                                # no row numbers
              .set_table_styles(
                  [                                               # remove all borders
                      {"selector": "th, td", "props": [("border", "none")]},
                  ]
              )
        )

        st.dataframe(styler, use_container_width=True)

 except Exception as e:
        st.error(f"Error while running scanner: {e}")
