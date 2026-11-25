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
async def order(req: OrderRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    # Live execution is intentionally locked behind multiple explicit operator settings.
    if KILL_SWITCH: raise HTTPException(423,"Kill switch is ON")
    if MODE != "demo":
        if os.getenv("ALLOW_LIVE_TRADING") != "true" or os.getenv("LIVE_CONFIRMATION") != "I_ACCEPT_LIVE_TRADING_RISK":
            raise HTTPException(403,"Live trading is not armed")
        if req.operator_confirmation != "I_CONFIRM_THIS_LIVE_ORDER":
            raise HTTPException(403,"Per-order live confirmation required")
    # Fail closed around scheduled high-impact events when news protection is required.
    if os.getenv("REQUIRE_NEWS_PROVIDER","true").lower() != "false":
        if not os.getenv("FINNHUB_API_KEY"): raise HTTPException(503,"News blackout protection requires FINNHUB_API_KEY")
        from_ts=int(time.time())-int(os.getenv("NEWS_BLACKOUT_MINUTES","30"))*60
        to_ts=int(time.time())+int(os.getenv("NEWS_BLACKOUT_MINUTES","30"))*60
        try: events=await economic_news(from_ts,to_ts)
        except Exception as e: raise HTTPException(503,f"Unable to verify news blackout; refusing order ({type(e).__name__})")
        relevant={"USD","JPY"} if "JPY" in req.symbol.upper() else {"USD"}
        for event in events:
            if event.get("impact") != "HIGH" or event.get("currency") not in relevant: continue
            raw=event.get("scheduledAt")
            try:
                event_time=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
                if event_time.tzinfo is None: event_time=event_time.replace(tzinfo=timezone.utc)
            except (TypeError,ValueError): continue
            if abs((event_time-datetime.now(timezone.utc)).total_seconds()) <= int(os.getenv("NEWS_BLACKOUT_MINUTES","30"))*60:
                raise HTTPException(423,{"message":"High-impact news blackout active","event":event.get("title"),"currency":event.get("currency")})
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
        allowed={s.strip().upper() for s in os.getenv("ALLOWED_SYMBOLS","XAUUSD,USDJPY").split(",") if s.strip()}
        if req.symbol.upper() not in allowed: raise HTTPException(403,"Symbol is not in ALLOWED_SYMBOLS")
        if req.volume < spec.volume_min or req.volume > spec.volume_max:
            raise HTTPException(400,"Volume outside broker symbol limits")
        step=float(spec.volume_step or 0)
        if step <= 0 or abs(round(req.volume/step)*step-req.volume) > 1e-8:
            raise HTTPException(400,"Volume does not match broker lot step")
        buy=req.side=="BUY"; price=tick.ask if buy else tick.bid
        spread_points=(tick.ask-tick.bid)/spec.point
        if spread_points > float(os.getenv("MAX_SPREAD_POINTS","1000")):
            raise HTTPException(423,"Spread exceeds configured maximum")
        min_stop_distance=float(spec.trade_stops_level)*spec.point
        if min_stop_distance and (abs(price-req.stop_loss)<min_stop_distance or abs(req.take_profit-price)<min_stop_distance):
            raise HTTPException(400,"Stop-loss/take-profit is inside broker minimum stop distance")
        if mt5.positions_total() >= int(os.getenv("MAX_OPEN_POSITIONS","3")):
            raise HTTPException(423,"Maximum open-position count reached")
        if (buy and not req.stop_loss < price < req.take_profit) or (not buy and not req.take_profit < price < req.stop_loss):
            raise HTTPException(400,"Invalid stop-loss/take-profit direction")
        # Broker-side pre-trade controls: realized daily loss, daily order count and stop-risk cap.
        now=datetime.now(timezone.utc); day_start=now.replace(hour=0,minute=0,second=0,microsecond=0)
        deals=mt5.history_deals_get(day_start,now)
        if deals is None: raise HTTPException(503,"Unable to verify daily deal history; refusing order")
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
        check=mt5.order_check(request)
        if check is None or check.retcode not in (0,mt5.TRADE_RETCODE_DONE):
            raise HTTPException(400,{"message":"Broker order_check rejected request","retcode":getattr(check,"retcode",None),"comment":getattr(check,"comment",None)})
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

class MemoryInput(BaseModel):
    symbol: str
    timeframe: str
    category: str
    observation: str = Field(min_length=5,max_length=4000)
    tags: list[str] = Field(default_factory=list,max_length=30)
    evidence: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0,ge=0,le=1)

@app.post("/memory")
def add_memory(item: MemoryInput, authorization: str | None = Header(default=None)):
    auth(authorization)
    import json
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO strategy_memories(symbol,timeframe,category,observation,tags,evidence,confidence)
                           VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (item.symbol,item.timeframe,item.category,item.observation,item.tags,json.dumps(item.evidence),item.confidence))
            memory_id=cur.fetchone()[0]
    return {"id":memory_id,"status":"UNVERIFIED"}

@app.get("/memory")
def search_memory(symbol: str | None=None, timeframe: str | None=None, q: str | None=None,
                  limit: int=50, authorization: str | None=Header(default=None)):
    auth(authorization)
    if not 1 <= limit <= 200: raise HTTPException(400,"limit must be 1..200")
    clauses=[]; params=[]
    if symbol: clauses.append("symbol=%s"); params.append(symbol)
    if timeframe: clauses.append("timeframe=%s"); params.append(timeframe)
    if q: clauses.append("observation ILIKE %s"); params.append("%"+q[:100]+"%")
    where=("WHERE "+" AND ".join(clauses)) if clauses else ""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""SELECT id,created_at,symbol,timeframe,category,observation,tags,evidence,confidence,status
                            FROM strategy_memories {where} ORDER BY created_at DESC LIMIT %s""",(*params,limit))
            rows=cur.fetchall()
    return [{"id":r[0],"created_at":r[1].isoformat(),"symbol":r[2],"timeframe":r[3],"category":r[4],
             "observation":r[5],"tags":r[6],"evidence":r[7],"confidence":float(r[8]),"status":r[9]} for r in rows]

@app.get("/performance")
def performance(authorization: str | None=Header(default=None)):
    auth(authorization)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT COUNT(*), COUNT(*) FILTER(WHERE outcome='WIN'),
                           COUNT(*) FILTER(WHERE outcome='LOSS'),
                           COALESCE(SUM(pnl-costs),0), COALESCE(AVG(pnl-costs),0)
                           FROM trade_outcomes""")
            count,wins,losses,net,avg=cur.fetchone()
    closed=int(count or 0)
    return {"closed_trades":closed,"wins":int(wins or 0),"losses":int(losses or 0),
            "win_rate":float(wins or 0)/closed if closed else 0,"net_pnl_after_costs":float(net),
            "average_net_pnl":float(avg)}

@app.get("/calendar/health")
def calendar_health(authorization: str | None=Header(default=None)):
    auth(authorization)
    return {"provider":"Finnhub","configured":bool(os.getenv("FINNHUB_API_KEY")),
            "note":"Coverage and event-impact semantics depend on provider plan; verify before use."}
