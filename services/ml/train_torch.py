"""Small PyTorch MLP baseline; chronological split, CPU/GPU auto selection.
CSV rows must be point-in-time features plus a binary target column.
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib

class TradingMLP(nn.Module):
    def __init__(self,n_features):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(n_features,64),nn.ReLU(),nn.Dropout(.2),
                               nn.Linear(64,32),nn.ReLU(),nn.Linear(32,1))
    def forward(self,x): return self.net(x).squeeze(-1)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--target",default="target")
    p.add_argument("--out",default="artifacts/torch-model.pt"); p.add_argument("--epochs",type=int,default=30)
    a=p.parse_args(); df=pd.read_csv(a.csv).dropna()
    if a.target not in df: raise SystemExit("Target column missing")
    y=df.pop(a.target).astype("float32").to_numpy()
    x=df.drop(columns=["timestamp"],errors="ignore").astype("float32").to_numpy()
    cut=int(len(x)*.8)
    if cut<100 or len(x)-cut<20 or len(np.unique(y))!=2: raise SystemExit("Need >=120 rows and both classes")
    scaler=StandardScaler(); x_train=scaler.fit_transform(x[:cut]); x_test=scaler.transform(x[cut:])
    device="cuda" if torch.cuda.is_available() else "cpu"
    model=TradingMLP(x.shape[1]).to(device); opt=torch.optim.AdamW(model.parameters(),lr=1e-3,weight_decay=1e-4)
    loss_fn=nn.BCEWithLogitsLoss(); xt=torch.tensor(x_train,device=device); yt=torch.tensor(y[:cut],device=device)
    for _ in range(a.epochs):
        model.train(); opt.zero_grad(); loss=loss_fn(model(xt),yt); loss.backward(); opt.step()
    model.eval()
    with torch.no_grad(): probs=torch.sigmoid(model(torch.tensor(x_test,device=device))).cpu().numpy()
    pred=(probs>=.5).astype(int)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    torch.save({"state_dict":model.cpu().state_dict(),"n_features":x.shape[1],"feature_names":list(df.drop(columns=["timestamp"],errors="ignore").columns)},a.out)
    joblib.dump(scaler,str(Path(a.out).with_suffix(".scaler.joblib")))
    print(json.dumps({"accuracy":float(accuracy_score(y[cut:],pred)),
        "auc":float(roc_auc_score(y[cut:],probs)) if len(np.unique(y[cut:]))==2 else None,
        "test_rows":len(y)-cut,"device":device,"model":a.out},indent=2))
if __name__=="__main__": main()
