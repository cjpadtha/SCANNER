# SCANNER — HVN Breakout Scanner

Educational study tool for Bitcoin on the 1-minute chart. It runs inside TradingView, simulates trades in the Strategy Tester, and **never places real orders**. Not financial advice.

## The rules

1. **HVN zones** are built from the 2 hours *before* the breakout. High-volume rows of the profile merge into zones; a zone's top/bottom is the highest/lowest **close** inside it.
2. **Breakout:** candle 1 closes outside the zone, candle 2 closes even further out. Confirmed at candle 2's close.
3. **Big breakout** (candle 2's body ≥ 1× ATR) → the trade is taken automatically.
4. **Not big** → no trade, just a grey BUY?/SELL? label with a probability.
5. The probability starts at 50% and moves with:

   | Factor | Change |
   |---|---|
   | 15m market structure with / against the breakout | +15 / −15 |
   | 1m fair value gap in the breakout direction | +10 |
   | Opposite-side 1m liquidity sweep in the last 30 bars | +10 |
   | Breakout candle swept a level and closed back (trap) | −20 |
   | Big breakout candle | +10 |

   It's a heuristic score, not a measured probability. The backtest is how you find out if it means anything.
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
- Sizing is 10% of equity; costs are 0.1% commission per fill (typical taker fee). Set your exchange's fee in **Properties**. On 1m trades fees matter a lot: 0.2% round trip is ~$190 on a $95k BTC move, so a target only a few hundred dollars away loses a big share to fees.

**Phone alerts:** Alert (clock icon) → Condition: **HVN Breakout** → **alert() function calls only** → turn on **Notify in app**. You'll get the side, probability, entry, stop and target for every trade taken. Turn on *Also alert on probability-only signals* in settings to get the grey ones too.

## Reading the results

- Judge it in **R**: avg R per trade above 0 after fees is the bar to clear. The chart table's R uses actual fill prices but not commission, so also check Net profit in the Strategy Tester, which includes fees.
- A handful of trades over a day or two is noise. Look at 50+ trades before trusting it.
- Try the 15m-structure filter on and off, and the session filter, and compare total R.

## Python (older confluence model)

`nq_scanner.py` and `backtest.py` are the earlier POC / sweep / FVG / opening-range confluence score using Yahoo data. They don't implement the HVN breakout rules above.


```
pip install -r requirements.txt
python nq_scanner.py                    # current read using Yahoo (delayed) data
python backtest.py --out results.csv    # replay last 60 days of 5m bars
python backtest.py --csv bars.csv       # or your own exported bars
```
