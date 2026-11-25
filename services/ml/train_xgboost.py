"""Train an auditable XGBoost classifier from labelled historical features.
CSV must contain feature columns plus target (0/1); never train on future-derived columns.
"""
import argparse, json
from pathlib import Path
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier
import joblib

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True); p.add_argument("--target",default="target")
    p.add_argument("--model",default="artifacts/xgb-model.joblib")
    args=p.parse_args()
    df=pd.read_csv(args.csv).dropna().sort_values("timestamp") if "timestamp" in pd.read_csv(args.csv,nrows=0).columns else pd.read_csv(args.csv).dropna()
    if args.target not in df: raise SystemExit("Target column missing")
    y=df.pop(args.target).astype(int); df=df.drop(columns=["timestamp"],errors="ignore")
    if y.nunique()!=2: raise SystemExit("Training target must contain both classes")
    split=int(len(df)*0.8)
    if split<100 or len(df)-split<20: raise SystemExit("Need at least 120 chronological samples")
    model=XGBClassifier(n_estimators=300,max_depth=3,learning_rate=.03,subsample=.8,
                        colsample_bytree=.8,reg_lambda=2,eval_metric="logloss",
                        random_state=42,n_jobs=2)
    model.fit(df.iloc[:split],y.iloc[:split])
    pred=model.predict(df.iloc[split:]); prob=model.predict_proba(df.iloc[split:])[:,1]
    report=classification_report(y.iloc[split:],pred,output_dict=True,zero_division=0)
    Path(args.model).parent.mkdir(parents=True,exist_ok=True); joblib.dump({"model":model,"features":list(df.columns)},args.model)
    print(json.dumps({"holdout_auc":float(roc_auc_score(y.iloc[split:],prob)) if y.iloc[split:].nunique()==2 else None,
                      "holdout":report,"model":args.model},indent=2))
if __name__=="__main__": main()
