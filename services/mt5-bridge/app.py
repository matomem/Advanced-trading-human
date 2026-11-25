"""Authenticated MT5 bridge. Run on the Windows host where the MT5 terminal is installed.
The bridge defaults to read-only + demo mode. Never expose it directly to the public internet.
"""
from __future__ import annotations
import os, hmac, time
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import MetaTrader5 as mt5

TOKEN = os.environ.get("BRIDGE_API_TOKEN", "")
MODE = os.environ.get("TRADING_MODE", "demo").lower()
KILL_SWITCH = os.environ.get("KILL_SWITCH", "true").lower() != "false"
app = FastAPI(title="Human Trader MT5 Bridge", version="0.1.0")
origins = [x.strip() for x in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET","POST"], allow_headers=["Authorization","Content-Type"])

def auth(authorization: str | None):
    if not TOKEN or not authorization or not hmac.compare_digest(authorization.removeprefix("Bearer ").strip(), TOKEN):
        raise HTTPException(401, "Missing or invalid bridge token")

def connect():
    login = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")
    path = os.getenv("MT5_PATH") or None
    if not all([login, password, server]):
        raise HTTPException(503, "Configure MT5_LOGIN, MT5_PASSWORD and MT5_SERVER on the bridge host")
    ok = mt5.initialize(path, login=int(login), password=password, server=server) if path else mt5.initialize(login=int(login), password=password, server=server)
    if not ok:
        raise HTTPException(503, f"MT5 initialize failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        raise HTTPException(503, "MT5 account information unavailable")
    return account

@app.get("/health")
def health():
    return {"service":"mt5-bridge","mode":MODE,"kill_switch":KILL_SWITCH,"utc":datetime.now(timezone.utc).isoformat()}

@app.get("/account")
def account(authorization: str | None = Header(default=None)):
    auth(authorization); info=connect()
    try:
        return {"login":str(info.login),"server":info.server,"company":info.company,"currency":info.currency,
                "balance":info.balance,"equity":info.equity,"margin_free":info.margin_free,
                "trade_allowed":bool(info.trade_allowed),"is_demo":bool(info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)}
    finally: mt5.shutdown()

@app.get("/symbols/{symbol}/tick")
def tick(symbol: str, authorization: str | None = Header(default=None)):
    auth(authorization); connect()
    try:
        if not mt5.symbol_select(symbol, True): raise HTTPException(404, "Symbol unavailable; check broker symbol suffix")
        t=mt5.symbol_info_tick(symbol)
        if t is None: raise HTTPException(404, "No tick received")
        return {"symbol":symbol,"bid":t.bid,"ask":t.ask,"time":t.time,"time_msc":t.time_msc}
    finally: mt5.shutdown()

@app.get("/symbols/{symbol}/candles")
def candles(symbol: str, timeframe: str="M5", count: int=500, authorization: str | None = Header(default=None)):
    auth(authorization); connect()
    frames={"M1":mt5.TIMEFRAME_M1,"M5":mt5.TIMEFRAME_M5,"M15":mt5.TIMEFRAME_M15,"H1":mt5.TIMEFRAME_H1,"H4":mt5.TIMEFRAME_H4,"D1":mt5.TIMEFRAME_D1}
    if timeframe not in frames: mt5.shutdown(); raise HTTPException(400,"Unsupported timeframe")
    try:
        if not mt5.symbol_select(symbol, True): raise HTTPException(404,"Symbol unavailable")
        rates=mt5.copy_rates_from_pos(symbol,frames[timeframe],0,min(max(count,1),5000))
        if rates is None: raise HTTPException(502,f"MT5 rates error: {mt5.last_error()}")
        return [{"time":int(r["time"])*1000,"open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"]),"volume":int(r["tick_volume"])} for r in rates]
    finally: mt5.shutdown()

class OrderRequest(BaseModel):
    symbol: str
    side: Literal["BUY","SELL"]
    volume: float = Field(gt=0, le=float(os.getenv("MAX_LOTS","0.10")))
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    operator_confirmation: str = ""

@app.post("/orders")
def order(req: OrderRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    # Live execution is intentionally locked behind multiple explicit operator settings.
    if KILL_SWITCH: raise HTTPException(423,"Kill switch is ON")
    if MODE != "demo":
        if os.getenv("ALLOW_LIVE_TRADING") != "true" or os.getenv("LIVE_CONFIRMATION") != "I_ACCEPT_LIVE_TRADING_RISK":
            raise HTTPException(403,"Live trading is not armed")
        if req.operator_confirmation != "I_CONFIRM_THIS_LIVE_ORDER":
            raise HTTPException(403,"Per-order live confirmation required")
    info=connect()
    try:
        if MODE == "demo" and info.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise HTTPException(403,"Demo mode requires an MT5 demo account")
        if MODE != "demo" and info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise HTTPException(403,"Configured live mode but MT5 account is demo")
        if not info.trade_allowed: raise HTTPException(403,"Trading disabled by terminal/account")
        if not mt5.symbol_select(req.symbol,True): raise HTTPException(404,"Symbol unavailable")
        tick=mt5.symbol_info_tick(req.symbol); spec=mt5.symbol_info(req.symbol)
        if tick is None or spec is None: raise HTTPException(502,"No quote/specification")
        buy=req.side=="BUY"; price=tick.ask if buy else tick.bid
        if (buy and not req.stop_loss < price < req.take_profit) or (not buy and not req.take_profit < price < req.stop_loss):
            raise HTTPException(400,"Invalid stop-loss/take-profit direction")
        # Broker-side pre-trade controls: realized daily loss, daily order count and stop-risk cap.
        now=datetime.now(timezone.utc); day_start=now.replace(hour=0,minute=0,second=0,microsecond=0)
        deals=mt5.history_deals_get(day_start,now) or []
        daily_pnl=sum(float(d.profit+d.swap+d.commission) for d in deals)
        max_daily_pct=float(os.getenv("MAX_DAILY_LOSS_PCT","1.0"))
        if daily_pnl <= -(float(info.balance)*max_daily_pct/100):
            raise HTTPException(423,"Daily loss limit reached; execution blocked")
        entries=[d for d in deals if getattr(d,"entry",None)==mt5.DEAL_ENTRY_IN]
        if len(entries) >= int(os.getenv("MAX_ORDERS_PER_DAY","5")):
            raise HTTPException(423,"Daily order limit reached")
        order_type=mt5.ORDER_TYPE_BUY if buy else mt5.ORDER_TYPE_SELL
        estimated_loss=mt5.order_calc_profit(order_type,req.symbol,req.volume,price,req.stop_loss)
        risk_limit=float(info.equity)*float(os.getenv("MAX_RISK_PER_TRADE_PCT","0.25"))/100
        if estimated_loss is None or abs(float(estimated_loss)) > risk_limit:
            raise HTTPException(400,{"message":"Trade exceeds configured risk-per-trade cap","estimated_loss":estimated_loss,"risk_limit":risk_limit})
        request={"action":mt5.TRADE_ACTION_DEAL,"symbol":req.symbol,"volume":req.volume,
                 "type":order_type,"price":price,"sl":req.stop_loss,"tp":req.take_profit,
                 "deviation":20,"magic":26001,"comment":"HumanTrader guarded order",
                 "type_time":mt5.ORDER_TIME_GTC,"type_filling":spec.filling_mode}
        result=mt5.order_send(request)
        if result is None: raise HTTPException(502,f"MT5 order_send failed: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise HTTPException(502,{"retcode":result.retcode,"comment":result.comment})
        return {"ticket":result.order,"deal":result.deal,"status":"accepted","mode":MODE}
    finally: mt5.shutdown()

# Optional external data providers. Missing keys fail closed with HTTP 503.
from providers import economic_news, market_sentiment, ProviderNotConfigured
from datetime import timedelta
@app.get("/news")
async def news(from_ts: int, to_ts: int, authorization: str | None = Header(default=None)):
    auth(authorization)
    if to_ts <= from_ts or to_ts-from_ts > 31*86400: raise HTTPException(400,"Invalid date range (maximum 31 days)")
    try: return await economic_news(from_ts,to_ts)
    except ProviderNotConfigured as e: raise HTTPException(503,str(e))
    except Exception as e: raise HTTPException(502,f"Calendar provider error: {type(e).__name__}")

@app.get("/sentiment/{symbol}")
async def sentiment(symbol: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    try: return await market_sentiment(symbol)
    except ProviderNotConfigured as e: raise HTTPException(503,str(e))
    except Exception as e: raise HTTPException(502,f"Sentiment provider error: {type(e).__name__}")

def db_connect():
    import psycopg
    dsn=os.getenv("DATABASE_URL")
    if not dsn: raise HTTPException(503,"DATABASE_URL is not configured")
    try: return psycopg.connect(dsn)
    except Exception as e: raise HTTPException(503,f"Database unavailable: {type(e).__name__}")

class DecisionInput(BaseModel):
    symbol: str
    timeframe: str
    decision: dict
    model_version: str = "rules-v1"
    feature_snapshot: dict = {}

@app.post("/journal/decisions")
def save_decision(item: DecisionInput, authorization: str | None = Header(default=None)):
    auth(authorization)
    import json
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO trade_decisions(symbol,timeframe,decision,model_version,feature_snapshot) VALUES(%s,%s,%s,%s,%s) RETURNING id",
                        (item.symbol,item.timeframe,json.dumps(item.decision),item.model_version,json.dumps(item.feature_snapshot)))
            decision_id=cur.fetchone()[0]
    return {"id":decision_id,"stored":True}

class OutcomeInput(BaseModel):
    decision_id: int = Field(gt=0)
    outcome: Literal["WIN","LOSS","BREAKEVEN"]
    pnl: float
    costs: float = 0
    notes: str = ""

@app.post("/journal/outcomes")
def save_outcome(item: OutcomeInput, authorization: str | None = Header(default=None)):
    auth(authorization)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO trade_outcomes(decision_id,closed_at,outcome,pnl,costs,notes) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",
                        (item.decision_id,datetime.now(timezone.utc),item.outcome,item.pnl,item.costs,item.notes))
            outcome_id=cur.fetchone()[0]
    return {"id":outcome_id,"stored":True}

@app.get("/journal")
def journal(limit: int=100, authorization: str | None = Header(default=None)):
    auth(authorization)
    if not 1 <= limit <= 500: raise HTTPException(400,"limit must be 1..500")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT d.id,d.created_at,d.symbol,d.timeframe,d.decision,d.model_version,
                           o.outcome,o.pnl,o.costs,o.closed_at FROM trade_decisions d
                           LEFT JOIN LATERAL (SELECT * FROM trade_outcomes WHERE decision_id=d.id ORDER BY closed_at DESC LIMIT 1) o ON true
                           ORDER BY d.created_at DESC LIMIT %s""",(limit,))
            rows=cur.fetchall()
    return [{"id":r[0],"created_at":r[1].isoformat(),"symbol":r[2],"timeframe":r[3],"decision":r[4],
             "model_version":r[5],"outcome":r[6],"pnl":float(r[7]) if r[7] is not None else None,
             "costs":float(r[8]) if r[8] is not None else None,"closed_at":r[9].isoformat() if r[9] else None} for r in rows]
