# ML research pipeline

## 1. Create point-in-time features
Export historical OHLC bars from MT5 (CSV columns: time, open, high, low, close, optional volume), then run:
`python features.py --csv data/xauusd_m5.csv --out data/features.csv --horizon 5`

Every feature is computed using current/past bars only. The target labels whether the close after N bars is above the current close by the configured threshold. This is a simple research label, not a trade recommendation. Add spread, commission, swaps, slippage and instrument contract rules before interpreting results.

## 2. Train
`python train_xgboost.py --csv data/features.csv --target target`
Optional PyTorch:
`pip install -r requirements-torch.txt && python train_torch.py --csv data/features.csv --target target`

Both scripts use chronological holdouts. For real evaluation, implement rolling walk-forward folds, purge/embargo overlapping labels, calibrate probabilities, record model versions, and compare against a no-skill baseline. Never train on future-derived features. Do not auto-deploy a model from a single holdout score.

## 3. Backtest
The bridge backtest is a transparent moving-average example. It is not a broker-accurate fill simulator. Validate with tick or sufficiently granular data, realistic spreads by session, commissions, swaps, gaps, stop slippage, margin and contract size before relying on results.
