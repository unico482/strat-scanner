import streamlit as st
import pandas as pd

from scanner.utils import load_watchlist
from scanner.data import fetch_bars
from scanner.patterns import detect_patterns


# ────────── page setup ──────────
st.set_page_config(page_title="Strat Scanner", layout="wide")
st.title("Strat Pattern Scanner")


# ────────── sidebar widgets ──────────
watchlist_type = st.selectbox("Watchlist Type", ["Stock", "Crypto"])

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
    """True = green close, False = red close, None = inside / NA."""
    try:
        if pd.isna(bar["open"]) or pd.isna(bar["close"]) or bar["high"] == bar["low"]:
            return None
        return bool(bar["close"] > bar["open"])
    except KeyError:
        return None


def colour_letter(flag: bool | None, label: str) -> str:
    if flag is None or pd.isna(flag):
        return ""
    colour = "#10b981" if flag else "#ef4444"            # green / red
    return f'<span style="color:{colour}; font-weight:700">{label}</span>'


def style_pattern(value) -> str:
    txt = ", ".join(value) if isinstance(value, list) else str(value).strip("[]'\" ")
    return (
        '<span style="background-color:#3a3a3a; color:#e5e5e5; '
        'border-radius:4px; padding:2px 6px;">'
        f'{txt.capitalize()}'
        '</span>'
    )


SPACER = "&nbsp;&nbsp;&nbsp;"        # three NBSP for wider gaps


# ────────── main action ──────────
if st.button("Run Scanner"):
    try:
        tickers = load_watchlist(watchlist_type.lower())
        tf_key  = timeframe.lower()

        # raw bars
        bars_df = fetch_bars(tickers, tf_key, watchlist_type.lower())
        st.markdown(f"### Scanning {watchlist_type} watchlist on {timeframe} timeframe…")
        st.write(f"Raw bars fetched: ({bars_df.shape[0]}, {bars_df.shape[1]})")

        # keep four bars per symbol, newest last
        bars_df = bars_df.sort_values(["symbol", "timestamp"])
        recent_bars = (
            bars_df
            .groupby("symbol")
            .tail(4)
            .reset_index(drop=True)
        )

        # shift window when “Use previous” is active
        if scan_previous:
            recent_bars = (
                recent_bars
                .iloc[recent_bars.groupby("symbol").cumcount(ascending=False) != 0]
                .reset_index(drop=True)
            )

        # ─── decide which higher-TF bars we need ───
        if tf_key in ("4h", "12h"):
            htf_list = ["day", "week", "month"]
        elif tf_key in ("day", "previous day", "3 day"):
            htf_list = ["week", "month"]
        elif tf_key == "week":
            htf_list = ["month"]
        else:                                    # month scan → no higher TF
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

        # colour-coded letters
        for col, letter in (("D", "D"), ("W", "W"), ("M", "M")):
            if col in df.columns:
                df[col] = df[col].apply(lambda v, L=letter: colour_letter(v, L))

        # build TFC column with wider gaps
        def tfc_string(row):
            parts = [row.get("D", ""), row.get("W", ""), row.get("M", "")]
            parts = [p for p in parts if p]            # drop empties
            return SPACER.join(parts)

        df["TFC"] = df.apply(tfc_string, axis=1)
        df = df.drop(columns=[c for c in ("D", "W", "M") if c in df.columns])

        # rename & capitalise headers
        df = df.rename(
            columns={
                "symbol":  "Symbol",
                "patterns": "Pattern",
                "cc":       "CC",
                "c1":       "C1",
                "c2":       "C2",
            }
        )

        # prettify values
        if "Symbol" in df.columns:
            df["Symbol"] = df["Symbol"].str.upper()
        if "Pattern" in df.columns:
            df["Pattern"] = df["Pattern"].apply(style_pattern)

        # full-width, equal column widths
        table_html = (
            df.to_html(escape=False, index=False, border=0)
              .replace(
                  '<table class="dataframe">',
                  '<table class="dataframe" style="width:100%; table-layout:fixed;">'
              )
              .replace("<th>", '<th style="text-align:left; width:16%;">')
              .replace("<td>", '<td style="text-align:left; width:16%;">')
        )
        st.markdown(table_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error while running scanner: {e}")
