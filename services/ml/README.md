# ML training service

The XGBoost trainer uses a chronological holdout (not random shuffling) and saves feature names with the model. Prepare labels without look-ahead bias: a row's target must be based only on a clearly defined future outcome, while every feature must be available at decision time. Include spread, commission, swaps and slippage in labels/backtests. Evaluate walk-forward folds, calibration, drawdown and out-of-sample stability before deployment. The training script does not place orders. PyTorch is intentionally not included as a second unvalidated model; add a neural model only after a reproducible baseline and sufficient clean data exist.

Run: `pip install -r requirements.txt && python train_xgboost.py --csv data/features.csv --target target`.
