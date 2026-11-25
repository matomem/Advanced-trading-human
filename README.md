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
