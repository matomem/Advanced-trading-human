# Advanced Trading Human

Research and decision-support platform for **XAU/USD (gold)** and **USD/JPY**. The project contains a TypeScript decision engine plus separate Python integration services.

## Platform modules

| Module | What is present | What still needs external setup |
|---|---|---|
| Decision engine | EMA/RSI/ATR, trend-pullback and breakout scoring, candle patterns, liquidity sweeps, risk/session/spread gates | Live XM demo data is connected through the decision API; verify broker-specific data and sessions |
| MT5 / XM | Authenticated FastAPI bridge for account, ticks, OHLC candles and guarded demo-first order route | Windows host, MT5 terminal, XM demo login/server and exact broker symbol names |
| News | Finnhub economic-calendar adapter and high-impact event blackout in order route | FINNHUB_API_KEY, provider plan/coverage validation |
| Sentiment | Finnhub forex headlines with transparent keyword heuristic | A licensed, validated sentiment source and robust NLP model |
| Persistent memory | PostgreSQL decision journal, outcome records, searchable strategy observations and performance API | Database provisioning, backup, encryption and migrations |
| ML | Point-in-time OHLC feature builder, XGBoost and optional PyTorch trainers, authenticated inference-only API | Your historical data, clean labels, walk-forward validation and model deployment |
| Research | Next-bar illustrative OHLC backtest and parameter sweep with spread/commission/slippage inputs | Tick-quality fills, swaps, contract sizing, margin and walk-forward robustness |
| Dashboard | Browser dashboard for account, quotes, calendar, sentiment, journal, stored memories, live decision analysis and a manually confirmed demo-only order ticket | Host it locally/private network and configure CORS |
| Execution safety | Kill switch, demo-account check, symbol allowlist, lot constraints, spread/stops checks, order preflight, daily limits, per-trade risk cap and news blackout | Real broker demo testing and independent security review |

## Quick start

### 1. MT5 bridge (Windows host with desktop terminal)

1. Install the official MT5 desktop terminal and sign in to an **XM demo account**.
2. Confirm the exact broker server and symbol names in Market Watch (XM may use suffixes such as GOLD or XAUUSD.a).
3. From `services/mt5-bridge`, install dependencies and copy `.env.example` to a local `.env`.
4. Set MT5 credentials locally, generate a long random BRIDGE_API_TOKEN, set `TRADING_MODE=demo`, keep `KILL_SWITCH=true`, and set ALLOWED_SYMBOLS to exact broker symbols.
5. Run `uvicorn app:app --host 127.0.0.1 --port 8000` from that directory.

The MetaTrader5 Python package requires the Windows terminal environment; it cannot run inside the MT5 phone app. Do not expose this service directly to the public internet.

### 2. PostgreSQL journal and memory

Set POSTGRES_PASSWORD, then run `docker compose up -d db`. The initial database mounts schema.sql and memory.sql. If your database volume already existed before memory.sql was added, apply that file manually with psql.

### 3. News protection

Set FINNHUB_API_KEY in the bridge environment. News blackout protection is required by default for order requests; if the provider is not configured or cannot be reached, order execution is refused. Confirm that the provider plan returns the events and timestamps you need.

### 4. Dashboard

Serve the `dashboard` folder from localhost (for example, `python -m http.server 5173` from that folder), set CORS_ORIGINS accordingly, then open the local dashboard URL. Enter the bridge token in the page. It is held in page memory and not stored in localStorage.

### 5. ML feature generation, training and inference

Export historical OHLC bars to CSV with columns `time,open,high,low,close` and optional `volume`. From `services/ml`:

```bash
pip install -r requirements.txt
python features.py --csv data/xauusd_m5.csv --out data/features.csv --horizon 5
python train_xgboost.py --csv data/features.csv --target target
```

The optional PyTorch baseline uses `requirements-torch.txt`. The inference API in `serve.py` returns model probabilities only and has no order-execution capability. Run it from services/ml with `uvicorn serve:app --host 127.0.0.1 --port 8100` after setting ML_API_TOKEN and XGB_MODEL_PATH. Protect it with a separate ML_API_TOKEN and keep it on a private network.

### 6. Decision API

Copy `services/decision-api/.env.example` to `services/decision-api/.env`, set a separate `DECISION_API_TOKEN` and the same `BRIDGE_API_TOKEN` as the MT5 bridge. Set the exact XM symbol names, then run `npm run build` and `node --env-file=services/decision-api/.env dist/services/decision-api/server.js`. The dashboard can call `/decision/XAUUSD` and `/decision/USDJPY`. This endpoint only analyzes and journals; it does not place orders.

### 7. Checks

```bash
npm install
npm run typecheck
npm test
python -m compileall -q services
cd services/ml && python -m unittest discover -v -p 'test_*.py'
```

## Safety and current limitations

- No credentials or API keys are committed. Do not paste them into GitHub files or chat.
- The MT5 bridge is a Windows-hosted companion service, not a mobile MT5 plugin.
- The decision engine is not yet wired end-to-end to the live MT5 feed and ML inference service. The dashboard has a manual demo-only order ticket; it is not a finished multi-user production terminal and does not support automatic/live orders.
- The news and sentiment adapters depend on provider access and require validation. The sentiment score is a keyword heuristic, not institutional-grade analysis.
- ML training scripts do not make a model profitable. Use point-in-time features, walk-forward evaluation, realistic costs and out-of-sample demo testing.
- Backtesting is an illustrative baseline, not a broker-accurate simulator.
- The order route defaults to demo mode and kill switch ON. Live mode has additional explicit gates but is not enabled or certified by this repository change. Do not use live funds until all integrations, controls, monitoring and independent review are complete.
- No strategy guarantees profits. This software is for research and technical development, not a promise of returns.

See [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) for setup and operating details.
