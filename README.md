# Advanced Trading Human

An expert decision-support brain for **USD/JPY intraday trading** and **XAU/USD gold scalping**.

## What this first engine does
- Analyses closed OHLC candles across 1m, 5m, 15m and 1h timeframes.
- Calculates EMA trend, RSI, ATR, candle momentum and recent swing levels.
- Scores trend-pullback and breakout conditions with explicit reasons.
- Applies symbol-specific spread, volatility and session filters.
- Calculates risk-based position size from account equity and stop distance.
- Rejects trades when data is insufficient, market conditions are poor, a news blackout is active, or daily risk limits are reached.
- Produces structured decisions that can be logged, backtested and reviewed.

## Important safety boundary
This repository currently contains the **research and decision engine only**. It does not connect to a broker, place orders, or guarantee profitable trades. Start with historical backtests and paper trading. Live execution must be a separate, explicitly enabled adapter with broker-side protective stops, limits and monitoring. Never commit broker credentials or API keys.

## Instruments and profiles
- `USDJPY`: intraday trend/pullback and breakout analysis.
- `XAUUSD`: faster scalping profile with stricter spread and volatility checks.

## Development
Requires Node.js 20+.

```bash
npm install
npm test
npm run typecheck
```

## Input contract
Feed the brain normalized candles (oldest first) for each timeframe, current bid/ask, account equity, current daily P&L, and a news-blackout flag from a trusted calendar source. Candle timestamps must be UTC milliseconds. The engine does not fetch market data itself.

## Next engineering stages
1. Broker/data adapter (MT5 or another supported broker) with demo-account support.
2. Historical data ingestion and walk-forward backtesting with spread, commission and slippage.
3. Paper-trading execution simulator and durable trade journal.
4. Monitoring, alerts, kill switch and guarded live execution after validation.
