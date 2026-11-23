// Kalshi relay for the BTC Live page (Cloudflare Workers, free plan). It only forwards PUBLIC market-data GET requests
// (/trade-api/v2/markets...) and adds the header that lets your phone's browser read the answer. No keys, no orders.
// Setup: dash.cloudflare.com → Workers & Pages → Create → Worker → paste this → Deploy → copy the https://….workers.dev address
// into BTC Live → "Connect Kalshi".
export default {
  async fetch(req) {
    const url = new URL(req.url);
    const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS" };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (req.method !== "GET" || !url.pathname.startsWith("/trade-api/v2/markets")) return new Response("not allowed", { status: 403, headers: cors });
    const r = await fetch("https://api.elections.kalshi.com" + url.pathname + url.search, { headers: { "Accept": "application/json" } });
    return new Response(r.body, { status: r.status, headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" } });
  },
};
