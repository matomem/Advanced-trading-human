"""Minimal OHLC backtester with spread, commission and slippage cost deductions.
Input CSV: time,open,high,low,close. Strategy callback is deliberately explicit.
"""
import argparse, json
import pandas as pd

def run_backtest(df, fast=10, slow=30, spread=0.0001, commission_per_unit=0.0, slippage=0.00002):
    df=df.copy().sort_values("time").reset_index(drop=True)
    if len(df)<slow+2: raise ValueError("Not enough bars")
    df["fast"]=df.close.ewm(span=fast,adjust=False).mean()
    df["slow"]=df.close.ewm(span=slow,adjust=False).mean()
    df["signal"]=0
    df.loc[df.fast>df.slow,"signal"]=1
    df.loc[df.fast<df.slow,"signal"]=-1
    # Signal formed at close; fill at next bar open to avoid look-ahead.
    df["position"]=df.signal.shift(1).fillna(0)
    df["ret"]=df.close.pct_change().fillna(0)*df.position
    turnover=df.position.diff().abs().fillna(df.position.abs())
    cost=turnover*((spread/2)+slippage+commission_per_unit)
    df["net_ret"]=df.ret-cost
    equity=(1+df.net_ret).cumprod()
    peak=equity.cummax(); drawdown=equity/peak-1
    trades=int((turnover>0).sum())
    return {"bars":len(df),"trades":trades,"total_return":float(equity.iloc[-1]-1),
            "max_drawdown":float(drawdown.min()),"win_bar_rate":float((df.loc[df.position!=0,"net_ret"]>0).mean()),
            "cost_assumptions":{"spread":spread,"slippage":slippage,"commission_per_unit":commission_per_unit},
            "warning":"Illustrative moving-average baseline only; add broker-specific contract sizing, swap, financing, margin, stop fills and walk-forward validation."}

def optimize(df, fast_values=(5,10,15,20), slow_values=(25,30,40,50), spread=0.0001, commission_per_unit=0.0, slippage=0.00002):
    """Small transparent parameter sweep; ranks by return penalized by drawdown."""
    rows=[]
    for fast in fast_values:
        for slow in slow_values:
            if fast >= slow: continue
            result=run_backtest(df,fast,slow,spread,commission_per_unit,slippage)
            rows.append({"fast":fast,"slow":slow,**result,
                         "score":result["total_return"] + result["max_drawdown"]})
    return sorted(rows,key=lambda x:x["score"],reverse=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--fast",type=int,default=10); p.add_argument("--slow",type=int,default=30)
    p.add_argument("--spread",type=float,default=0.0001); p.add_argument("--commission",type=float,default=0); p.add_argument("--slippage",type=float,default=0.00002); p.add_argument("--optimize",action="store_true")
    a=p.parse_args(); df=pd.read_csv(a.csv); result=optimize(df,spread=a.spread,commission_per_unit=a.commission,slippage=a.slippage) if a.optimize else run_backtest(df,a.fast,a.slow,a.spread,a.commission,a.slippage); print(json.dumps(result,indent=2))
if __name__=="__main__": main()
