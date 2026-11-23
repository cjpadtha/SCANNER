# BTC Live

Live Bitcoin price from Coinbase's public data, refreshed every 15 seconds while this note is open.
Requires the Dataview plugin with **Enable JavaScript Queries** turned on.

```dataviewjs
const box = dv.el("div", "Loading BTC…");
async function update() {
  try {
    const s = await (await fetch("https://api.exchange.coinbase.com/products/BTC-USD/stats")).json();
    const last = +s.last, chg = ((last - +s.open) / +s.open * 100).toFixed(2);
    box.innerHTML = `<b>BTC $${last.toLocaleString()}</b> (${chg}% 24h) · H $${(+s.high).toLocaleString()} · L $${(+s.low).toLocaleString()} · ${new Date().toLocaleTimeString()}`;
  } catch (e) { box.textContent = "BTC price unavailable: " + e; }
}
update();
const t = setInterval(() => box.isConnected ? update() : clearInterval(t), 15000);
```
