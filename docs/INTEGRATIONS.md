# Integration and activation guide

## MT5 + XM Global
1. Install the official MetaTrader 5 desktop terminal on a Windows machine. Install the XM Global MT5 version and sign in using the exact XM server shown in your XM account.
2. Create/use an XM demo account first. Confirm symbols in Market Watch; brokers may use suffixes (for example GOLD or XAUUSD.a), so do not assume XAUUSD/ USDJPY names.
3. Run the Python bridge on that same machine. Install `services/mt5-bridge/requirements.txt`, copy `.env.example` to `.env`, fill credentials locally, and set `TRADING_MODE=demo`, `KILL_SWITCH=true`. Never commit .env.
4. Bind the bridge to localhost or a private VPN. Put it behind TLS and a reverse proxy if remote access is unavoidable. Do not expose port 8000 publicly.
5. Test /health, /account, /symbols/{symbol}/tick and /candles with a Bearer token. MetaTrader5 Python package is Windows/terminal-dependent; the phone MT5 app cannot host this bridge.

## News and sentiment
Set FINNHUB_API_KEY on the server to enable the optional economic calendar and headline baseline in providers.py. Verify provider plan, coverage, rate limits, timestamps and terms. Keyword sentiment is explicitly a weak baseline, not a predictive model. Do not treat event impact labels as trade signals.

## Persistent journal and strategy memory
Apply schema.sql and memory.sql to PostgreSQL (docker-compose mounts both on first database initialization). The API exposes /journal, /performance, /memory and POST /memory. The memory table stores observations, tags, confidence and evidence; entries begin UNVERIFIED and are not automatically treated as profitable rules. Add encryption at rest, backups, retention, migrations and per-user authorization before production. Never store broker passwords or API tokens in journal rows.

## ML and inference
Export OHLC CSV from MT5 and run services/ml/features.py to build point-in-time features with a future-return label. Train XGBoost or the optional PyTorch baseline with a chronological holdout. The inference-only services/ml/serve.py exposes /predict behind ML_API_TOKEN; it returns a probability and never places an order. Run it separately with its own token and network boundary. Use walk-forward evaluation, leakage checks, purged overlapping labels, calibration and model registry/version tracking before relying on outputs.

## Backtesting
backtest.py is an illustrative moving-average baseline. It shifts signals to next-bar execution and subtracts configurable spread/slippage/commission, but does not yet model exact MT5 contract sizes, partial fills, stop/limit gaps, swaps, financing, margin or symbol-specific pip values. It is not a validated strategy optimizer.

## Execution safety
The bridge has a kill switch ON by default, demo-account verification, symbol allowlist, broker volume-step/min/max checks, spread and stop-distance limits, order_check preflight, open-position cap, daily loss/order limits and per-trade risk cap. News blackout protection fails closed by default: FINNHUB_API_KEY must be configured and the calendar request must succeed before an order can proceed; high-impact USD/JPY events within NEWS_BLACKOUT_MINUTES block orders. Set exact XM symbol names in ALLOWED_SYMBOLS after checking Market Watch. Do not enable live mode until extensive independent testing, broker rule verification and manual review. Live activation is not performed by this code change.


## Decision API
The TypeScript decision API is a separate Node process. It reads /account, /risk, /symbols/{symbol}/tick, /symbols/{symbol}/candles and /news from the MT5 bridge, evaluates the existing rules engine, and writes the resulting decision to /journal/decisions. It is analysis-only and never submits an order. Configure services/decision-api/.env.example, build with `npm run build`, then start `node --env-file=services/decision-api/.env dist/services/decision-api/server.js`. The dashboard needs the separate DECISION_API_TOKEN. Session classification currently uses approximate UTC hour windows; verify/adjust for daylight-saving changes and your broker's trading sessions.

The /risk endpoint includes today's UTC realized deals plus current floating P/L. Positions without stop-loss values or uncomputable stop risk cause risk_unknown=true; the decision API treats that as 100% open risk to force a no-trade result. This is intentionally conservative, but the daily P/L convention should be reconciled with your broker's day boundary before production use.
