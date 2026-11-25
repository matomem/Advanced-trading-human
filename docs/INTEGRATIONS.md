# Integration and activation guide

## MT5 + XM Global
1. Install the official MetaTrader 5 desktop terminal on a Windows machine. Install the XM Global MT5 version and sign in using the exact XM server shown in your XM account.
2. Create/use an XM demo account first. Confirm symbols in Market Watch; brokers may use suffixes (for example GOLD or XAUUSD.a), so do not assume XAUUSD/ USDJPY names.
3. Run the Python bridge on that same machine. Install `services/mt5-bridge/requirements.txt`, copy `.env.example` to `.env`, fill credentials locally, and set `TRADING_MODE=demo`, `KILL_SWITCH=true`. Never commit .env.
4. Bind the bridge to localhost or a private VPN. Put it behind TLS and a reverse proxy if remote access is unavoidable. Do not expose port 8000 publicly.
5. Test /health, /account, /symbols/{symbol}/tick and /candles with a Bearer token. MetaTrader5 Python package is Windows/terminal-dependent; the phone MT5 app cannot host this bridge.

## News and sentiment
Set FINNHUB_API_KEY on the server to enable the optional economic calendar and headline baseline in providers.py. Verify provider plan, coverage, rate limits, timestamps and terms. Keyword sentiment is explicitly a weak baseline, not a predictive model. Do not treat event impact labels as trade signals.

## Persistent journal
Apply schema.sql to PostgreSQL. The schema stores decision snapshots and linked outcomes. Add encryption at rest, backups, retention, user authentication, migrations and repository methods before production. Never store broker passwords or API tokens in journal rows.

## ML
Train XGBoost only on time-ordered, point-in-time features. Use walk-forward evaluation and leakage checks. Keep model artifact version, training window, feature schema and metrics. PyTorch is deferred until data volume and a validated baseline justify it.

## Backtesting
backtest.py is an illustrative moving-average baseline. It shifts signals to next-bar execution and subtracts configurable spread/slippage/commission, but does not yet model exact MT5 contract sizes, partial fills, stop/limit gaps, swaps, financing, margin or symbol-specific pip values. It is not a validated strategy optimizer.

## Execution safety
The bridge has a kill switch ON by default, demo-account verification, symbol and stop checks, volume cap, and separate explicit live-mode environment confirmations. Do not enable live mode until extensive independent testing, broker rule verification and manual review. Live activation is not performed by this code change.
