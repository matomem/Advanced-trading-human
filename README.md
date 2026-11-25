# Advanced Trading Human

Research and decision-support engine for **USD/JPY intraday trading** and **XAU/USD gold scalping**.

## Implemented
- Closed OHLC analysis on 1m, 5m, 15m and 1h candles.
- EMA, RSI, ATR, momentum and recent swing levels.
- Trend-pullback and breakout scoring with explicit reasons.
- Basic engulfing/pin-bar recognition and liquidity-sweep detection.
- Symbol-specific spread/volatility/session filters and risk-based sizing.
- Daily loss, aggregate open-risk and news-blackout rejection gates.
- Typed adapter contracts for broker market data, economic calendars and sentiment.
- Trade journal interface, in-memory development implementation and performance summaries.
- TypeScript and unit-test CI workflow.

## Important status and safety boundary
This is **not yet a live trading bot**. It does not currently connect to MetaTrader 5, XM Global, a market-data feed, an economic-calendar provider or a sentiment provider. Adapter contracts define integration points; they do not fetch real data. The journal currently stores data in memory and loses it when the process stops. There is no live order execution, web dashboard, trained AI model or persistent AI memory.

No strategy can guarantee profits. Validate with historical data and demo/paper trading before considering live use. Never commit API keys, broker passwords, account identifiers or tokens.

## Next integration stages
1. Build a secured MT5 companion service on a machine running the MT5 terminal; expose authenticated market-data endpoints to a backend, not browser code.
2. Add historical data ingestion and walk-forward backtesting including spread, commission, swaps and slippage.
3. Connect a trusted economic-calendar provider and documented sentiment sources; retain timestamps and source provenance.
4. Replace the in-memory journal with encrypted durable storage and add model evaluation/versioning before adaptive strategies are used.
5. Add a dashboard, monitoring, alerts, kill switch and demo-only execution adapter. Live execution must remain separately gated and require explicit operator enablement.

## Development
Requires Node.js 20+.

```bash
npm install
npm run typecheck
npm test
```

## Input contract
Feed normalized candles (oldest first) for each timeframe, current bid/ask, account equity, current daily P&L and a news-blackout flag from a trusted calendar source. Candle timestamps are UTC milliseconds. The decision engine does not fetch market data itself.


## Platform integration foundation

A separate platform layer now lives alongside the TypeScript decision engine:

- `services/mt5-bridge`: authenticated FastAPI bridge for MT5 account, quotes and OHLC data; optional Finnhub economic calendar/headline sentiment; PostgreSQL-backed decision/outcome journal endpoints; demo-first order route with kill switch, account-mode check, daily loss/order limits and per-trade stop-risk cap.
- `services/ml`: chronological XGBoost training baseline with saved feature schema. An optional PyTorch MLP baseline is included separately; compare it against XGBoost and simple baselines before any deployment.
- `services/mt5-bridge/backtest.py`: next-bar moving-average baseline, explicit spread/commission/slippage assumptions and parameter sweep.
- `dashboard/index.html`: read-only browser monitor for bridge status, account and quotes.
- `services/mt5-bridge/schema.sql`: PostgreSQL journal schema.
- `docs/INTEGRATIONS.md`: XM/MT5 setup and safety instructions.

### What still requires your environment

This repository does not contain broker credentials, Finnhub keys or a running MT5 terminal. The MT5 Python package runs on a Windows host with the terminal installed; the bridge cannot run inside a phone MT5 app. Confirm the exact XM server and symbol names in Market Watch. The optional Finnhub calendar/news endpoints require a valid API key and provider-plan coverage. Dashboard is a local read-only starter, not a hosted multi-user production app.

The order endpoint is not production-certified. It defaults to `TRADING_MODE=demo` and `KILL_SWITCH=true`; live mode requires multiple separate environment confirmations and a per-order confirmation. Keep live trading disabled until demo tests, independent code review, broker rule checks and monitoring are complete. The backtest/optimizer is a research baseline, not evidence of profitability.
