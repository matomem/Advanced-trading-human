"""Authenticated, inference-only XGBoost API. It never places trades."""
import os, math, hmac
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
MODEL_PATH=os.getenv("XGB_MODEL_PATH","artifacts/xgb-model.joblib")
TOKEN=os.getenv("ML_API_TOKEN","")
app=FastAPI(title="Human Trader ML Inference",version="0.1.0")
_model=None
def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH): raise HTTPException(503,"Model artifact is not installed")
        try: _model=joblib.load(MODEL_PATH)
        except Exception as e: raise HTTPException(503,f"Model could not be loaded: {type(e).__name__}")
    return _model
def authorize(value):
    if not TOKEN or not value or not hmac.compare_digest(value.removeprefix("Bearer ").strip(),TOKEN):
        raise HTTPException(401,"Missing or invalid ML API token")
class PredictionInput(BaseModel):
    features: dict[str,float]
    model_version: str = "xgb-experimental"
@app.get("/health")
def health():
    return {"service":"ml-inference","model_configured":os.path.exists(MODEL_PATH),"execution_enabled":False}
@app.post("/predict")
def predict(item: PredictionInput, authorization: str | None=Header(default=None)):
    authorize(authorization); bundle=load_model(); names=bundle["features"]
    missing=set(names)-set(item.features); extra=set(item.features)-set(names)
    if missing or extra: raise HTTPException(400,{"missing_features":sorted(missing),"unexpected_features":sorted(extra)})
    values=[item.features[n] for n in names]
    if not all(math.isfinite(float(v)) for v in values): raise HTTPException(400,"Feature values must be finite")
    probability=float(bundle["model"].predict_proba(pd.DataFrame([values],columns=names))[0][1])
    return {"model_version":item.model_version,"probability_up":probability,"class":int(probability>=0.5),
            "features_used":names,"warning":"Experimental model output only; not a trade signal and never connected to order execution."}
