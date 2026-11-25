# Decision API

This Node service connects the existing TypeScript trading brain to the MT5 bridge. It fetches 1m/5m/15m/1h candles, bid/ask, account equity, daily P/L, aggregate open risk and the economic calendar. It evaluates the current rules engine and writes the result to the PostgreSQL journal through the bridge.

From the repository root:
1. Copy `services/decision-api/.env.example` to `services/decision-api/.env`; set a separate DECISION_API_TOKEN and the same BRIDGE_API_TOKEN used by the bridge.
2. Set XAUUSD_SYMBOL and USDJPY_SYMBOL to exact XM Market Watch names.
3. Run `npm install`, then `npm run build`.
4. Start with `node --env-file=services/decision-api/.env dist/services/decision-api/server.js`.
5. Call `GET http://127.0.0.1:8200/decision/XAUUSD` or `/decision/USDJPY` with `Authorization: Bearer <DECISION_API_TOKEN>`.

If news cannot be verified, the analysis is marked as a news blackout. If open positions have no stop loss or risk cannot be computed, open risk is treated as 100% so the decision engine returns no trade. The API is analysis-only and never submits an order. Position units from the research engine are approximate; use broker contract-aware sizing before any automated execution is considered.
