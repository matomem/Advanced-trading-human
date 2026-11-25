# ML research and inference pipeline

1. Export historical OHLC bars from MT5 to CSV with columns `time,open,high,low,close` and optional `volume`.
2. Build point-in-time features: `python features.py --csv data/xauusd_m5.csv --out data/features.csv --horizon 5`.
3. Train XGBoost: `python train_xgboost.py --csv data/features.csv --target target`. Optional PyTorch: `pip install -r requirements-torch.txt && python train_torch.py --csv data/features.csv --target target`.
4. Set ML_API_TOKEN and XGB_MODEL_PATH in a local .env, then run `uvicorn serve:app --host 127.0.0.1 --port 8100 --env-file .env`.

Features at time t use only current and past bars. The target is a future-return label. The inference API is authenticated and never places orders. Both models are research baselines. Use walk-forward evaluation, leakage checks, purged overlapping labels, calibration and broker-realistic costs before considering any output. Do not auto-deploy a model from a single holdout score.
