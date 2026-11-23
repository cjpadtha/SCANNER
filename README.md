# SCANNER — HVN Breakout Scanner

**📈 [Open the BTC Live app →](kalshi/)** (Kalshi 15-min lean + hourly model, phone-friendly)


Educational study tool for Bitcoin on the 1-minute chart. It runs inside TradingView, simulates trades in the Strategy Tester, and **never places real orders**. Not financial advice.

## The rules

1. **HVN zones** are built from the 2 hours *before* the breakout. High-volume rows of the profile merge into zones; a zone's top/bottom is the highest/lowest **close** inside it.
2. **Breakout:** candle 1 closes outside the zone, candle 2 closes even further out. Confirmed at candle 2's close.
3. **Big breakout** (candle 2's body ≥ 1× ATR) → the trade is taken automatically.
4. **Not big** → no trade, just a grey BUY?/SELL? marker with its score.
5. The **score** starts at 50 and moves with:

   | Factor | Change |
   |---|---|
   | 15m market structure with / against the breakout | +15 / −15 |
   | 1m fair value gap in the breakout direction | +10 |
   | Opposite-side 1m liquidity sweep in the last 30 bars | +10 |
   | Breakout candle swept a level and closed back (trap) | −20 |
   | Big breakout candle | +10 |
   | High volume on the breakout candles (≥ 1.5× the 20-bar average) | 0 (new — measured only) |
   | Breakout on the right side of VWAP | 0 (new — measured only) |
   | Extended: candle 2 closed > 2 ATR past the zone (chasing) | 0 (new — measured only) |

   The score is **points, not a probability**. The real win rate comes from the signal tracking below.
6. **Stop:** candle 1's low/high (or zone midpoint / far edge, in settings).
7. **Target:** midpoint of the next HVN in the trade direction; if there isn't one, 2R.

## Set it up (TradingView)

Script: [`pine/hvn_breakout_scanner.pine`](pine/hvn_breakout_scanner.pine)

1. On a computer at tradingview.com, open **`BINANCE:BTCUSDT`** (or `COINBASE:BTCUSD`, `BYBIT:BTCUSDT.P`) on the **1-minute** chart. Use an exchange symbol, not an index like `CRYPTO:BTCUSD`: the HVN zones need real volume.
2. **Pine Editor** (bottom) → delete the template → paste the script → **Save** → **Add to chart**.
3. Open **Strategy Tester** for the results. The table on the chart shows trades, win rate and total R for the window.

Once added, it shows in the phone app too.

**Settings worth knowing** (gear icon):

- *Simulate the last N hours* — default 24. Raise it (e.g. 72–168) for more trades; free plans load fewer 1m bars.
- *Only signal during* — all hours (default; BTC trades 24/7), NY stock-market hours, or the 09:30–11:00 ET killzone, when BTC volume is usually highest.
- *Only auto-take breakouts that agree with 15m structure* — off by default.
- Sizing is 10% of equity; costs are 0.1% commission per fill (typical taker fee). Set your exchange's fee in **Properties**. On 1m trades fees matter a lot: 0.2% round trip is about $190 per BTC at a $95k price, so a target only a few hundred dollars away loses a big share of it to fees.

**What's on the chart:**

- **Trades taken:** a teal BUY / red SELL label with planned R:R, entry price, score, the score band's measured win rate and the break-even win rate, plus a green target box and red stop box (like TradingView's position tool) that end where the trade exits, with the result in R printed there.
- **Not-taken signals:** small grey triangles — hover one for its score, measured win rate and reasons. Switch to full labels or off under *Display*.
- **HVN zones** (last 2h): green = support below price, red = resistance above, orange = price inside. Dotted line = zone midpoint (the trade target). The label shows the price range and the zone's share of 2h volume.
- **Stats table** bottom right (movable / hideable under *Display*).

**Turn off TradingView's own trade markers** (the purple L / LX / S / SX arrows with `+0.0166` sizes): strategy settings (gear) → **Style** → untick **Trades on chart**. Scripts can't hide these themselves.

**Phone alerts:** Alert (clock icon) → Condition: **HVN Breakout** → **alert() function calls only** → turn on **Notify in app**. You'll get the side, score, measured win rate, entry, stop and target for every trade taken. Turn on *Also alert on not-taken signals* in settings to get the grey ones too.

## Signal tracking (real win rates)

Every signal — taken or not — is followed until price hits its target or its stop (if both happen in the same 1m bar it counts as a stop) or 240 bars pass. The result is recorded in R **after fees** (fee per fill set under *Signal tracking*; keep it equal to the Commission in Properties).

The **"What really happened"** table (bottom left) shows, for the simulation window:

- **All signals** — count, % that made money, average R.
- **By score** (under 50 / 50–64 / 65–79 / 80+) — does a higher score actually win more? If not, the weights are wrong.
- **By check** — for each check, avg R when it was present vs. absent ("avg R without"). A check is worth weight only if the first is clearly higher than the second over ~30+ signals.
- **By session** — Asia / London / NY (ET).

Each trade label now reads e.g. `BUY 2.3R @ 95,120 · score 85 · 31% won (n24) · need 34%`: the score band's measured win rate so far (only from signals that finished before this one) and the win rate this trade needs to break even with its R:R and fees. Shown once a band has at least 10 finished signals.

*Only auto-take if this signal's score band has made money so far* uses this live: it skips a trade unless earlier signals with a similar score averaged above 0R.

**Using it to set the weights:** run 168h (or as long as your plan allows), read the "By check" rows, then raise the weight of checks whose avg R beats "avg R without" and lower or zero the ones that don't. Keep the window the same between changes. More checks ≠ better — with one or two weeks of data, a few strong checks beat many weak ones.

## Reading the results

- Judge it in **R**: avg R per trade above 0 after fees is the bar to clear. The chart table's R is after commission, so it matches the Strategy Tester.
- A handful of trades over a day or two is noise. Look at 50+ trades before trusting it.
- Try the 15m-structure filter on and off, and the session filter, and compare total R.
- 1m stops are tight, so fees can be a full R or more. Test: set commission to 0 in Properties to see the edge before fees, then try *Skip trades whose target is closer than x%* (e.g. 0.5), *Extra stop buffer* (e.g. 0.5 ATR) and *Only auto-take if score ≥* (e.g. 70). Change one at a time over the same window.

## Python (older confluence model)

`nq_scanner.py` and `backtest.py` are the earlier POC / sweep / FVG / opening-range confluence score using Yahoo data. They don't implement the HVN breakout rules above.


```
pip install -r requirements.txt
python nq_scanner.py                    # current read using Yahoo (delayed) data
python backtest.py --out results.csv    # replay last 60 days of 5m bars
python backtest.py --csv bars.csv       # or your own exported bars
```
