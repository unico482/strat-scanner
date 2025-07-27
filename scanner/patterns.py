def strat_number(candle, prev_candle):
    if candle.high < prev_candle.high and candle.low > prev_candle.low:
        return 1  # Inside
    elif candle.high > prev_candle.high and candle.low < prev_candle.low:
        return 3  # Outside
    else:
        return 2  # Directional


def is_green(candle):
    return candle.close > candle.open


def is_red(candle):
    return candle.close < candle.open


def wick_ratios(candle):
    body = abs(candle.close - candle.open)
    upper = candle.high - max(candle.close, candle.open)
    lower = min(candle.close, candle.open) - candle.low
    return upper, lower, body


def detect_patterns(symbol, candles, selected_filters):
    if len(candles) < 3:
        return None

    c2 = candles.iloc[-3]
    c1 = candles.iloc[-2]
    cc = candles.iloc[-1]

    sn_cc = strat_number(cc, c1)
    sn_c1 = strat_number(c1, c2)
    sn_c2 = strat_number(c2, candles.iloc[-4]) if len(candles) >= 4 else None

    upper, lower, body = wick_ratios(cc)
    c1_upper, c1_lower, c1_body = wick_ratios(c1)
    candle_range = cc.high - cc.low if cc.high > cc.low else 0

    hammer_body_position = min(cc.close, cc.open) >= cc.high - candle_range * 0.4 if candle_range > 0 else False
    shooter_body_position = max(cc.close, cc.open) <= cc.low + candle_range * 0.4 if candle_range > 0 else False

    matches = []

    if "Hammer" in selected_filters and lower >= 1.5 * body and hammer_body_position:
        matches.append("Hammer")

    if "Shooter" in selected_filters and upper >= 1.5 * body and shooter_body_position:
        matches.append("Shooter")

    if "Inside Bar" in selected_filters and sn_cc == 1:
        matches.append("Inside Bar")

    if "Outside" in selected_filters and sn_cc == 3:
        matches.append("Outside")

    if "2d Green" in selected_filters and sn_cc == 2 and cc.low < c1.low and cc.close > cc.open:
        matches.append("2d Green")

    if "2u Red" in selected_filters and sn_cc == 2 and cc.high > c1.high and cc.close < cc.open:
        matches.append("2u Red")

    # Updated pattern structure-only logic
    if (
        "RevStrat" in selected_filters
        and sn_c1 == 1
        and sn_cc == 2
    ):
        matches.append("RevStrat")

    if (
        "3-2-2" in selected_filters
        and sn_c1 == 3
        and sn_cc == 2
    ):
        matches.append("3-2-2")

    if all(f in matches for f in selected_filters):
        return {
            "symbol": symbol,
            "patterns": matches,
            "cc": sn_cc,
            "c1": sn_c1,
            "c2": sn_c2,
        }

    return None
