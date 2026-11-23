// Kalshi relay for the BTC Live page (Cloudflare Workers, free plan). Read-only: forwards PUBLIC Kalshi market data and adds the
// header that lets your phone's browser read it. No keys, no account data, no orders.
//  - https://<your-relay>.workers.dev/               → the open BTC 15-minute markets (KXBTC15M), for a quick check
//  - https://<your-relay>.workers.dev/trade-api/v2/… → any public Kalshi market-data GET (what the app uses)
export default {
  async fetch(req) {
    const url = new URL(req.url);
    const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "*" };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (req.method !== "GET") return new Response(JSON.stringify({ error: "read-only relay: GET only" }), { status: 405, headers: { ...cors, "Content-Type": "application/json" } });
    let path = url.pathname.replace(/\/+$/, "");
    let search = url.search;
    if (path === "" || path === "/") { path = "/trade-api/v2/markets"; search = "?series_ticker=KXBTC15M&status=open&limit=5"; }
    if (!path.startsWith("/trade-api/v2/")) return new Response(JSON.stringify({ error: "only /trade-api/v2/ market data is relayed", got: path }), { status: 404, headers: { ...cors, "Content-Type": "application/json" } });
    if (/\/(portfolio|orders|account)/.test(path)) return new Response(JSON.stringify({ error: "account endpoints are not relayed" }), { status: 403, headers: { ...cors, "Content-Type": "application/json" } });
    const r = await fetch("https://api.elections.kalshi.com" + path + search, { headers: { "Accept": "application/json", "User-Agent": "btc-live-relay/1.0" } });
    const body = await r.text();
    return new Response(body, { status: r.status, headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" } });
  },
};
