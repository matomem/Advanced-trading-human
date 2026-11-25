import { createServer } from "node:http";
import { timingSafeEqual } from "node:crypto";
import { evaluateMarket } from "../../src/brain/brain.js";
import type { Candle, Instrument, MarketSnapshot, Timeframe } from "../../src/brain/types.js";

const BRIDGE_URL=(process.env.MT5_BRIDGE_URL ?? "http://127.0.0.1:8000").replace(/\/$/,"");
const BRIDGE_TOKEN=process.env.BRIDGE_API_TOKEN ?? "";
const API_TOKEN=process.env.DECISION_API_TOKEN ?? "";
const PORT=Number(process.env.DECISION_API_PORT ?? 8200);
type Quote={bid:number;ask:number};
type Account={equity:number;balance:number};
type Risk={daily_pnl:number;open_risk_pct:number;daily_loss_limit_pct:number;risk_unknown:boolean};
type WireCandle={time:number;open:number;high:number;low:number;close:number;volume?:number};
type Event={currency:string;impact:string;scheduledAt:string;title:string};

function send(res:any,status:number,data:unknown){
  res.statusCode=status;res.setHeader("Content-Type","application/json; charset=utf-8");
  res.end(JSON.stringify(data));
}
function authorized(value:string | undefined, expected:string):boolean{
  if(!expected || !value?.startsWith("Bearer ")) return false;
  const supplied=Buffer.from(value.slice(7)); const target=Buffer.from(expected);
  return supplied.length===target.length && timingSafeEqual(supplied,target);
}
async function bridgeGet<T>(path:string):Promise<T>{
  const r=await fetch(BRIDGE_URL+path,{headers:{Authorization:"Bearer "+BRIDGE_TOKEN}});
  const body=await r.text(); if(!r.ok) throw new Error("MT5 bridge "+r.status+": "+body.slice(0,300));
  return JSON.parse(body) as T;
}
async function bridgePost<T>(path:string,body:unknown):Promise<T>{
  const r=await fetch(BRIDGE_URL+path,{method:"POST",headers:{Authorization:"Bearer "+BRIDGE_TOKEN,"Content-Type":"application/json"},body:JSON.stringify(body)});
  const text=await r.text(); if(!r.ok) throw new Error("MT5 bridge "+r.status+": "+text.slice(0,300));
  return JSON.parse(text) as T;
}
function sessionAt(date:Date):MarketSnapshot["session"]{
  const h=date.getUTCHours();
  if(h>=0 && h<7) return "ASIA";
  if(h>=7 && h<13) return "LONDON";
  if(h>=13 && h<17) return "OVERLAP";
  if(h>=17 && h<21) return "NEW_YORK";
  return "OFF_HOURS";
}
function candles(rows:WireCandle[]):Candle[]{
  return rows.slice().sort((a,b)=>a.time-b.time).map(x=>({time:x.time,open:x.open,high:x.high,low:x.low,close:x.close,volume:x.volume}));
}
async function checkNews(instrument:Instrument,now:number):Promise<{blocked:boolean;warning?:string}>{
  try{
    const from=Math.floor(now/1000)-30*60, to=Math.floor(now/1000)+30*60;
    const events=await bridgeGet<Event[]>("/news?from_ts="+from+"&to_ts="+to);
    const currencies=instrument==="USDJPY"?new Set(["USD","JPY"]):new Set(["USD"]);
    for(const event of events){
      if(event.impact!=="HIGH" || !currencies.has(event.currency)) continue;
      const ts=Date.parse(event.scheduledAt);
      if(!Number.isFinite(ts)) return {blocked:true,warning:"A relevant high-impact event has an unreadable timestamp; analysis is blocked."};
      if(Math.abs(ts-now)<=30*60*1000) return {blocked:true,warning:"High-impact event blackout: "+event.title};
    }
    return {blocked:false};
  }catch(e){
    return {blocked:true,warning:"Calendar unavailable; fail-closed news protection applied: "+(e instanceof Error?e.message:"unknown error")};
  }
}
async function decision(instrument:Instrument){
  const symbol=instrument==="XAUUSD"?(process.env.XAUUSD_SYMBOL??"XAUUSD"):(process.env.USDJPY_SYMBOL??"USDJPY");
  const frames:Record<Timeframe,string>={"1m":"M1","5m":"M5","15m":"M15","1h":"H1"};
  const [quote,account,risk,...histories]=await Promise.all([
    bridgeGet<Quote>("/symbols/"+encodeURIComponent(symbol)+"/tick"),
    bridgeGet<Account>("/account"),
    bridgeGet<Risk>("/risk"),
    ...Object.values(frames).map(tf=>bridgeGet<WireCandle[]>("/symbols/"+encodeURIComponent(symbol)+"/candles?timeframe="+tf+"&count=300"))
  ]);
  const now=Date.now(); const news=await checkNews(instrument,now);
  const frameNames=Object.keys(frames) as Timeframe[];
  const history=Object.fromEntries(frameNames.map((tf,i)=>[tf,candles(histories[i] as WireCandle[])])) as MarketSnapshot["candles"];
  const snapshot:MarketSnapshot={
    instrument,candles:history,bid:quote.bid,ask:quote.ask,timestamp:now,
    session:sessionAt(new Date(now)),newsBlackout:news.blocked,
    accountEquity:account.equity,dailyPnl:risk.daily_pnl,
    dailyLossLimitPct:risk.daily_loss_limit_pct,
    openRiskPct:risk.risk_unknown?100:risk.open_risk_pct
  };
  const result=evaluateMarket(snapshot);
  if(news.warning) result.warnings.push(news.warning);
  let journal:{id:number}|null=null; let journalWarning:string|undefined;
  try{
    journal=await bridgePost<{id:number}>("/journal/decisions",{
      symbol,timeframe:"multi-timeframe",decision:result,model_version:"typescript-rules-v1",
      feature_snapshot:{bid:quote.bid,ask:quote.ask,session:snapshot.session,newsBlackout:news.blocked,
        dailyPnl:risk.daily_pnl,openRiskPct:snapshot.openRiskPct}
    });
  }catch(e){journalWarning=e instanceof Error?e.message:"Journal write failed";}
  return {symbol,snapshot,decision:result,journalId:journal?.id??null,journalWarning,
    execution:"NOT_SENT",note:"This endpoint analyzes and journals only. It never submits an order."};
}

const server=createServer(async(req,res)=>{
  const url=new URL(req.url??"/","http://127.0.0.1");
  if(req.method==="GET" && url.pathname==="/health") return send(res,200,{service:"human-trader-decision-api",executionEnabled:false});
  if(!authorized(req.headers.authorization,API_TOKEN)) return send(res,401,{error:"Missing or invalid decision API token"});
  if(req.method==="GET" && url.pathname.startsWith("/decision/")){
    const key=url.pathname.split("/").pop();
    if(key!=="XAUUSD" && key!=="USDJPY") return send(res,400,{error:"Supported instruments: XAUUSD, USDJPY"});
    try{return send(res,200,await decision(key as Instrument));}
    catch(e){return send(res,503,{error:e instanceof Error?e.message:"Market analysis failed",execution:"NOT_SENT"});}
  }
  return send(res,404,{error:"Not found"});
});
server.listen(PORT,"127.0.0.1",()=>process.stdout.write("Decision API listening on http://127.0.0.1:"+PORT+"\n"));
