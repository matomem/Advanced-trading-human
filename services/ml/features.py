"""Point-in-time OHLC feature generation and forward-return labels.
Features at row t use only bars <= t. The target is a future outcome and must never
be included among model features. CSV input columns: time,open,high,low,close,volume.
"""
import argparse
import numpy as np
import pandas as pd

def build_features(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.0) -> pd.DataFrame:
    required={"time","open","high","low","close"}
    missing=required-set(df.columns)
    if missing: raise ValueError(f"Missing columns: {sorted(missing)}")
    if horizon < 1: raise ValueError("horizon must be positive")
    d=df.copy().sort_values("time").reset_index(drop=True)
    close=d.close.astype(float); high=d.high.astype(float); low=d.low.astype(float)
    ret=close.pct_change()
    out=pd.DataFrame({"timestamp":d.time})
    for n in (1,2,3,5,10,20):
        out[f"return_{n}"]=close.pct_change(n)
        out[f"ema_gap_{n}"]=close/(close.ewm(span=n,adjust=False).mean())-1
    tr=pd.concat([(high-low),(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
    out["atr_pct"]=tr.rolling(14).mean()/close
    out["range_pct"]=(high-low)/close
    out["body_pct"]=(close-d.open.astype(float))/close
    out["upper_wick_pct"]=(high-np.maximum(d.open,close))/close
    out["lower_wick_pct"]=(np.minimum(d.open,close)-low)/close
    out["volatility_20"]=ret.rolling(20).std()
    if "volume" in d: out["volume_change"]=d.volume.pct_change().replace([np.inf,-np.inf],np.nan)
    future=close.shift(-horizon)/close-1
    out["target"]=(future>threshold).astype("Int64")
    out.loc[future.isna(),"target"]=pd.NA
    return out.replace([np.inf,-np.inf],np.nan).dropna().reset_index(drop=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--out",default="data/features.csv")
    p.add_argument("--horizon",type=int,default=5); p.add_argument("--threshold",type=float,default=0.0)
    a=p.parse_args(); result=build_features(pd.read_csv(a.csv),a.horizon,a.threshold)
    result.to_csv(a.out,index=False); print(f"Wrote {len(result)} labelled rows to {a.out}")
if __name__=="__main__": main()
