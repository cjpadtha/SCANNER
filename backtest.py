"""
Backtest for the NQ confluence score.

Replays historical 5-minute bars, scores every regular-hours bar with exactly the
same logic as nq_scanner.py (using only data available at that bar), and measures
what price did over the next N bars. Answers: does a +3 / -3 actually predict
direction, and which individual factors carry any signal?

News is NOT included: there is no historical headline feed, so the news factor
always scores 0 here.

Run:
    python backtest.py                      # last 60 days from Yahoo (5m max history)
    python backtest.py --csv bars.csv       # your own data: Datetime,Open,High,Low,Close,Volume
    python backtest.py --horizons 6 12 --cost 1.0 --out results.csv

Educational only. Past results on 60 days of data prove very little.
"""

import argparse
import sys
import time

import numpy as np
import pandas as pd
import yfinance as yf

import nq_scanner as s

LOOKBACK_SESSIONS = 5          # same 5 days of context the live scanner sees
RTH_START, RTH_END = "09:35", "15:55"


def load(args):
    if args.csv:
        df = pd.read_csv(args.csv, index_col=0, parse_dates=True)
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        if df.index.tz is None:
            df.index = df.index.tz_localize(args.csv_tz)
        df.index = df.index.tz_convert(s.TZ)
        return df.sort_index()
    df = yf.download(s.SYMBOL, interval=s.INTERVAL, period=args.period,
                     progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(s.TZ)
    return df


def run(df, horizons, step=1):
    sess = np.asarray(s.session_dates(df.index))
    uniq = sorted(set(sess))
    first_pos = {d: int(np.argmax(sess == d)) for d in uniq}
    sess_rank = {d: k for k, d in enumerate(uniq)}

    times = df.index.time
    t0, t1 = pd.Timestamp(RTH_START).time(), pd.Timestamp(RTH_END).time()
    close = df["Close"].values
    bar = pd.Timedelta(s.INTERVAL)
    max_h = max(horizons)

    candidates = [i for i in range(len(df))
                  if t0 <= times[i] <= t1 and sess_rank[sess[i]] >= LOOKBACK_SESSIONS - 1][::step]

    rows, started = [], time.time()
    for n, i in enumerate(candidates):
        start = first_pos[uniq[sess_rank[sess[i]] - (LOOKBACK_SESSIONS - 1)]]
        window = df.iloc[start:i + 1]
        if len(window) < 30:
            continue
        r = s.score_window(window)
        row = {"time": df.index[i], "price": close[i], "score": r["score"]}
        for key, pts, _ in r["factors"]:
            row[f"f_{key}"] = pts
        for h in horizons:
            j = i + h
            # only count a forward return if bar j exists, is the same session and has no gap
            ok = j < len(df) and sess[j] == sess[i] and df.index[j] - df.index[i] <= bar * h * 1.5
            row[f"fwd_{h}"] = close[j] - close[i] if ok else np.nan
        rows.append(row)
        if n % 250 == 0:
            el = time.time() - started
            print(f"\r  scored {n}/{len(candidates)} bars  ({el:.0f}s)", end="", file=sys.stderr)
    print(file=sys.stderr)
    res = pd.DataFrame(rows).set_index("time")
    for c in [c for c in res.columns if c.startswith("f_")]:
        res[c] = res[c].fillna(0).astype(int)
    return res, max_h


def hit_rate(direction, fwd):
    m = (direction != 0) & fwd.notna() & (fwd != 0)
    if not m.any():
        return np.nan, 0
    return float((np.sign(fwd[m]) == np.sign(direction[m])).mean()), int(m.sum())


def report(res, horizons, cost):
    print(f"\nBars scored: {len(res)}   from {res.index[0]:%Y-%m-%d} to {res.index[-1]:%Y-%m-%d}")
    print(f"Sessions: {len(set(res.index.date))}")

    for h in horizons:
        col = f"fwd_{h}"
        d = res.dropna(subset=[col])
        mins = h * int(pd.Timedelta(s.INTERVAL).total_seconds() // 60)
        base = d[col].mean()
        print(f"\n================ Horizon: {h} bars ({mins} min) ================")
        print(f"Baseline: avg move of ALL bars {base:+.2f} pts, up {100 * (d[col] > 0).mean():.1f}% of the time")

        print("\nBy score   bars   avg fwd pts   % up    signed avg (score direction)")
        for sc, g in d.groupby("score"):
            signed = (np.sign(sc) * g[col]).mean() if sc else np.nan
            print(f"  {sc:+3d}   {len(g):6d}   {g[col].mean():+10.2f}   {100 * (g[col] > 0).mean():5.1f}%"
                  f"   {'' if np.isnan(signed) else f'{signed:+.2f}'}")

        print("\nEach factor alone        bars   hit rate   avg pts in factor's direction")
        for c in sorted(c for c in d.columns if c.startswith("f_")):
            hr, n = hit_rate(d[c], d[col])
            m = d[c] != 0
            avg = (np.sign(d.loc[m, c]) * d.loc[m, col]).mean() if m.any() else np.nan
            if n:
                print(f"  {c[2:]:20} {n:7d}   {100 * hr:6.1f}%   {avg:+.2f}")

        # Signals: only the bar where |score| first crosses MIN_SCORE, so one
        # long-lasting condition is counted once instead of every 5 minutes.
        side = np.where(d["score"] >= s.MIN_SCORE, 1, np.where(d["score"] <= -s.MIN_SCORE, -1, 0))
        side = pd.Series(side, index=d.index)
        prev = side.groupby(d.index.date).shift(1).fillna(0)
        entries = d[(side != 0) & (side != prev)].copy()
        entries["side"] = side[entries.index]
        entries["pnl"] = entries["side"] * entries[col] - cost
        print(f"\nSignals (|score| >= {s.MIN_SCORE}, new crossings only, {cost:.2f} pt cost per trade)")
        if entries.empty:
            print("  none")
            continue
        for name, g in [("LONG", entries[entries.side == 1]), ("SHORT", entries[entries.side == -1]),
                        ("ALL", entries)]:
            if g.empty:
                print(f"  {name:5}  0 trades")
                continue
            wins = (g["pnl"] > 0).mean()
            print(f"  {name:5} {len(g):4d} trades   win {100 * wins:5.1f}%   avg {g['pnl'].mean():+6.2f} pts"
                  f"   total {g['pnl'].sum():+8.2f} pts   (${g['pnl'].sum() * 2:,.0f} per MNQ)")

    print("\nHow to read this:")
    print("  - A factor/score with a hit rate near 50% and avg near 0 has no edge.")
    print("  - Compare signal avg pts to the baseline drift: a trending period makes LONG look good by itself.")
    print("  - A few hundred bars over ~2 months is a small sample; treat any edge as a hypothesis, not proof.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="load bars from CSV instead of Yahoo")
    ap.add_argument("--csv-tz", default="UTC", help="timezone of naive CSV timestamps (default UTC)")
    ap.add_argument("--period", default="60d", help="Yahoo period (5m data is capped at 60d)")
    ap.add_argument("--horizons", type=int, nargs="+", default=[6, 12], help="forward bars to measure")
    ap.add_argument("--cost", type=float, default=1.0, help="points deducted per signal trade (slippage+fees)")
    ap.add_argument("--step", type=int, default=1, help="score every Nth bar (faster, rougher)")
    ap.add_argument("--out", help="save per-bar results to this CSV")
    args = ap.parse_args()

    df = load(args)
    if len(df) < 500:
        print("Not enough data. Yahoo may be blocked/rate limiting; try --csv.")
        return
    print(f"Loaded {len(df)} bars of {s.SYMBOL}. Scoring...", file=sys.stderr)
    res, _ = run(df, args.horizons, args.step)
    if res.empty:
        print("No bars could be scored (need at least 5 sessions of data).")
        return
    report(res, args.horizons, args.cost)
    if args.out:
        res.to_csv(args.out)
        print(f"\nPer-bar results saved to {args.out}")


if __name__ == "__main__":
    main()
