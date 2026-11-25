"""Provider adapters: credentials are server-side environment variables only."""
import os
from datetime import datetime, timezone
import httpx

class ProviderNotConfigured(RuntimeError): pass

async def economic_news(from_ts: int, to_ts: int):
    """Finnhub economic calendar. Provider plan/coverage may vary by account."""
    token=os.getenv("FINNHUB_API_KEY")
    if not token: raise ProviderNotConfigured("FINNHUB_API_KEY is not configured")
    start=datetime.fromtimestamp(from_ts,timezone.utc).date().isoformat()
    end=datetime.fromtimestamp(to_ts,timezone.utc).date().isoformat()
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.get("https://finnhub.io/api/v1/calendar/economic",params={"from":start,"to":end,"token":token})
        r.raise_for_status(); payload=r.json()
    events=[]
    for e in payload.get("economicCalendar",[]):
        events.append({"currency":e.get("country",""),"title":e.get("event",""),
          "impact":str(e.get("impact","")).upper(),"scheduledAt":e.get("time"),
          "actual":e.get("actual"),"forecast":e.get("estimate"),"previous":e.get("prev")})
    return events

async def market_sentiment(symbol: str):
    """Optional Finnhub news headlines; score is a transparent keyword heuristic, not institutional sentiment."""
    token=os.getenv("FINNHUB_API_KEY")
    if not token: raise ProviderNotConfigured("FINNHUB_API_KEY is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.get("https://finnhub.io/api/v1/news",params={"category":"forex","token":token})
        r.raise_for_status(); articles=r.json()
    terms=symbol.replace("/","").upper()
    selected=[a for a in articles if terms in (a.get("headline","")+a.get("summary","")).replace("/","").upper()]
    positive=("beats","growth","rally","surge","strong","higher","gain","bullish")
    negative=("misses","decline","fall","drop","weak","lower","loss","bearish")
    score=0
    for a in selected:
        text=(a.get("headline","")+" "+a.get("summary","")).lower()
        score += sum(text.count(w) for w in positive)-sum(text.count(w) for w in negative)
    return {"symbol":symbol,"score":max(-1,min(1,score/max(1,len(selected)*3))),
            "articleCount":len(selected),"sources":["Finnhub headlines"],"observedAt":int(datetime.now(timezone.utc).timestamp()*1000),
            "method":"simple-keyword-baseline; not investment-grade sentiment"}
