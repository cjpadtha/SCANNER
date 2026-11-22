"""
NQ Confluence Scanner  (Nasdaq-100 E-mini / Micro futures)

Educational analysis tool. It does NOT place trades and is not financial advice.

What it checks:
  1. Volume profile  -> POC and High Volume Nodes (HVNs)
  2. ICT concepts    -> previous day high/low, liquidity sweeps, unfilled fair value gaps, killzones
  3. Patterns        -> engulfing, inside bar, opening range breakout
  4. News            -> recent headlines with simple keyword sentiment

Setup:   pip install -r requirements.txt
Run:     python nq_scanner.py

Note: Yahoo data for NQ=F is delayed and has no order-flow detail. Treat output as a study aid.
"""

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------- Settings ----------------

SYMBOL = "NQ=F"          # NQ continuous contract on Yahoo (MNQ tracks the same price)
INTERVAL = "5m"
PERIOD = "5d"
BIN_SIZE = 5.0           # points per volume-profile bucket
TZ = "America/New_York"
MIN_SCORE = 3            # confluence needed before calling a bias
SWEEP_BARS = 6           # a liquidity sweep counts only within this many bars (6 x 5m = 30 min)

BULL_WORDS = ["beat", "beats", "surge", "rally", "record", "gain", "gains", "jump", "rises",
              "upgrade", "strong", "cooling inflation", "rate cut", "soars", "rebound"]
BEAR_WORDS = ["miss", "misses", "plunge", "drop", "falls", "slump", "selloff", "sell-off",
              "downgrade", "weak", "hot inflation", "rate hike", "tumble", "recession", "tariff"]


# ---------------- Data ----------------

def get_data():
    df = yf.download(SYMBOL, interval=INTERVAL, period=PERIOD, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(TZ)
    return df


def session_dates(index):
    """Futures trading day: a new session starts at 18:00 ET, so shift forward 6 hours."""
    return (index + pd.Timedelta(hours=6)).date


# ---------------- 1. Volume profile ----------------

def volume_profile(df):
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    buckets = (typical / BIN_SIZE).round() * BIN_SIZE
    prof = df["Volume"].groupby(buckets).sum().sort_index()
    poc = float(prof.idxmax())
    cutoff = prof.quantile(0.70)
    v, px = prof.values, prof.index
    hvns = [float(px[i]) for i in range(1, len(v) - 1)
            if v[i] >= cutoff and v[i] >= v[i - 1] and v[i] >= v[i + 1]]
    return poc, hvns


# ---------------- 2. ICT concepts ----------------

def key_levels(df):
    sess = session_dates(df.index)
    days = sorted(set(sess))
    today = df[sess == days[-1]]
    prev = df[sess == days[-2]] if len(days) > 1 else today
    opening = today.between_time("09:30", "09:59")
    return {
        "PDH": float(prev["High"].max()),
        "PDL": float(prev["Low"].min()),
        "ORH": float(opening["High"].max()) if len(opening) else None,
        "ORL": float(opening["Low"].min()) if len(opening) else None,
    }, today


def liquidity_sweeps(today, lv):
    sweeps = []
    for ts, r in today.iterrows():
        if r["High"] > lv["PDH"] and r["Close"] < lv["PDH"]:
            sweeps.append((ts, "bearish", "swept PDH and closed back below"))
        if r["Low"] < lv["PDL"] and r["Close"] > lv["PDL"]:
            sweeps.append((ts, "bullish", "swept PDL and closed back above"))
    return sweeps


def fair_value_gaps(df, keep=5):
    h, l, idx = df["High"].values, df["Low"].values, df.index
    n = len(df)
    if n < 3:
        return []
    # min low / max high of all bars AFTER bar i (inf / -inf when none)
    fut_min = np.append(np.minimum.accumulate(l[::-1])[::-1][1:], np.inf)
    fut_max = np.append(np.maximum.accumulate(h[::-1])[::-1][1:], -np.inf)
    unfilled = []
    for i in range(2, n):
        if l[i] > h[i - 2]:
            if fut_min[i] > h[i - 2]:
                unfilled.append((idx[i], "bullish", float(h[i - 2]), float(l[i])))
        elif h[i] < l[i - 2]:
            if fut_max[i] < l[i - 2]:
                unfilled.append((idx[i], "bearish", float(h[i]), float(l[i - 2])))
    return unfilled[-keep:]


def in_killzone(ts):
    t = ts.time()
    if pd.Timestamp("09:30").time() <= t <= pd.Timestamp("11:00").time():
        return "NY AM killzone"
    if pd.Timestamp("13:30").time() <= t <= pd.Timestamp("16:00").time():
        return "NY PM session"
    return None


# ---------------- 3. Patterns ----------------

def candle_patterns(df):
    a, b = df.iloc[-2], df.iloc[-1]
    found = []
    if b["Close"] > b["Open"] and a["Close"] < a["Open"] and b["Close"] >= a["Open"] and b["Open"] <= a["Close"]:
        found.append(("bullish", "bullish engulfing"))
    if b["Close"] < b["Open"] and a["Close"] > a["Open"] and b["Close"] <= a["Open"] and b["Open"] >= a["Close"]:
        found.append(("bearish", "bearish engulfing"))
    if b["High"] < a["High"] and b["Low"] > a["Low"]:
        found.append(("neutral", "inside bar (compression)"))
    return found


# ---------------- 4. News ----------------

def get_news():
    headlines = []
    for tkr in ["NQ=F", "QQQ", "^NDX"]:
        try:
            items = yf.Ticker(tkr).news or []
        except Exception:
            items = []
        for it in items:
            title = it.get("title") or (it.get("content") or {}).get("title")
            if title and title not in headlines:
                headlines.append(title)
    scored = []
    for h in headlines[:12]:
        low = h.lower()
        s = sum(w in low for w in BULL_WORDS) - sum(w in low for w in BEAR_WORDS)
        scored.append((s, h))
    return scored


# ---------------- Scoring ----------------

def score_window(df, news=None):
    """Score the LAST bar of df using only data up to and including it.

    Returns a dict with the score, a list of (key, points, reason) factors and the
    intermediate results the report prints. The backtest calls this bar by bar.
    """
    price = float(df["Close"].iloc[-1])
    poc, hvns = volume_profile(df)
    lv, today = key_levels(df)
    sweeps = liquidity_sweeps(today, lv)
    fvgs = fair_value_gaps(df)
    pats = candle_patterns(df)
    news = news or []

    factors = []

    def add(key, points, why):
        factors.append((key, points, why))

    add("poc", 1 if price > poc else -1, f"price {'above' if price > poc else 'below'} POC {poc:.2f}")

    # Only a recent sweep counts; one from hours ago no longer says much.
    cutoff = df.index[-1] - pd.Timedelta(INTERVAL) * (SWEEP_BARS - 1)
    recent_sweeps = [sw for sw in sweeps if sw[0] >= cutoff]
    if recent_sweeps:
        s = recent_sweeps[-1]
        add("sweep", 1 if s[1] == "bullish" else -1, f"liquidity sweep at {s[0]:%H:%M}: {s[2]}")

    bull_fvg = [g for g in fvgs if g[1] == "bullish" and g[3] < price]
    bear_fvg = [g for g in fvgs if g[1] == "bearish" and g[2] > price]
    if len(bull_fvg) > len(bear_fvg):
        add("fvg", 1, f"{len(bull_fvg)} unfilled bullish FVG(s) below price")
    elif len(bear_fvg) > len(bull_fvg):
        add("fvg", -1, f"{len(bear_fvg)} unfilled bearish FVG(s) above price")

    for side, name in pats:
        if side != "neutral":
            add("engulfing", 1 if side == "bullish" else -1, name)

    if lv["ORH"] is not None:
        if price > lv["ORH"]:
            add("opening_range", 1, f"above opening range high {lv['ORH']:.2f}")
        elif price < lv["ORL"]:
            add("opening_range", -1, f"below opening range low {lv['ORL']:.2f}")

    news_total = sum(s for s, _ in news)
    if news_total:
        add("news", 1 if news_total > 0 else -1, f"news sentiment {news_total:+d}")

    return {
        "price": price, "poc": poc, "hvns": hvns, "levels": lv, "fvgs": fvgs,
        "factors": factors, "score": sum(p for _, p, _ in factors),
    }


def verdict(score):
    if score >= MIN_SCORE:
        return "LONG bias - look for entries at nearest HVN / bullish FVG below"
    if score <= -MIN_SCORE:
        return "SHORT bias - look for entries at nearest HVN / bearish FVG above"
    return "NO CLEAR EDGE - stand aside"


# ---------------- Report ----------------

def main():
    df = get_data()
    if len(df) < 30:
        print("Not enough data returned. Market may be closed or Yahoo is rate limiting.")
        return

    news = get_news()
    r = score_window(df, news)
    price, poc, hvns, lv, fvgs = r["price"], r["poc"], r["hvns"], r["levels"], r["fvgs"]
    last_ts = df.index[-1]

    print(f"\n=== {SYMBOL} @ {price:.2f}   ({last_ts:%Y-%m-%d %H:%M} ET) ===")
    kz = in_killzone(last_ts)
    print(f"Session: {kz or 'outside main NY windows (lower quality)'}")

    print("\nKey levels")
    for k, v in lv.items():
        if v is not None:
            print(f"  {k}: {v:.2f}")
    print(f"  POC: {poc:.2f}")
    above = sorted(h for h in hvns if h > price)[:3]
    below = sorted((h for h in hvns if h < price), reverse=True)[:3]
    print(f"  HVNs above: {', '.join(f'{h:.2f}' for h in above) or 'none'}")
    print(f"  HVNs below: {', '.join(f'{h:.2f}' for h in below) or 'none'}")

    print("\nUnfilled FVGs (latest)")
    for ts, kind, lo, hi in fvgs:
        print(f"  {kind:8} {lo:.2f} - {hi:.2f}   formed {ts:%m-%d %H:%M}")
    if not fvgs:
        print("  none")

    print("\nHeadlines")
    for s, h in news[:6]:
        print(f"  [{s:+d}] {h}")
    if not news:
        print("  none returned")

    print("\nConfluence")
    for _, p, why in r["factors"]:
        print(f"  {'+' if p > 0 else ''}{p}  {why}")
    print(f"  TOTAL: {r['score']:+d}")
    print(f"\n>>> {verdict(r['score'])}\n")


if __name__ == "__main__":
    main()
