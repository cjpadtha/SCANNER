# SCANNER — NQ Confluence Scanner

Educational study tool for Nasdaq-100 futures (NQ / MNQ). It does **not** place trades and is not financial advice.

It scores five things and calls a bias when the total reaches +3 or -3:

| Factor | +1 (bullish) | -1 (bearish) |
|---|---|---|
| POC (5-day volume profile) | price above POC | price below POC |
| Liquidity sweep (last 30 min) | swept previous day low, closed back above | swept previous day high, closed back below |
| Unfilled fair value gaps | more bullish FVGs below price | more bearish FVGs above price |
| Engulfing candle | bullish engulfing | bearish engulfing |
| Opening range (09:30–10:00 ET) | above the high | below the low |

The Python scanner also scores headline sentiment; TradingView can't read news, so the Pine version doesn't.

## TradingView (recommended — live data, phone alerts)

Files in `pine/`:

- `nq_confluence_indicator.pine` — draws POC, PDH/PDL, opening range, unfilled FVG boxes, nearest HVNs, L/S signal arrows and a score table. Has alerts.
- `nq_confluence_strategy.pine` — same scoring as a strategy, for TradingView's **Strategy Tester** (the backtest).

**Add a script** (needs a computer, at tradingview.com — once added, it also shows in the phone app):

1. Open a chart of `MNQ1!` or `NQ1!` on the **5-minute** timeframe.
2. Open **Pine Editor** at the bottom, delete the template, paste the contents of a `.pine` file.
3. Click **Save**, then **Add to chart**.

**Phone alerts:** on the chart with the indicator added, click **Alert** → Condition: **NQ Confluence** → pick *NQ confluence LONG*, *SHORT* or *ANY signal* → "Once per bar close" → turn on **Notify in app**. Alerts fire on TradingView's servers, so you get them on your phone even with the app closed.

**Backtest:** add the strategy script, then open **Strategy Tester** at the bottom. Look at Net profit, Percent profitable, Profit factor and the List of trades. By default it enters when the score first reaches ±3, exits after 12 bars (60 min) or at 15:55 ET, and charges 1 point round trip in slippage. Change those in the script's settings (gear icon) and **Properties** tab.

**Reading the results**

- Percent profitable near 50% with a small average trade ≈ no edge.
- Turn off longs or shorts in settings to see if one side carries everything — often that's just the trend of the period.
- Free plans load fewer bars, so the test covers a shorter history. A few hundred trades is still a small sample.

## Python (optional)

```
pip install -r requirements.txt
python nq_scanner.py                    # current read using Yahoo (delayed) data
python backtest.py --out results.csv    # replay last 60 days of 5m bars
python backtest.py --csv bars.csv       # or your own exported bars
```
