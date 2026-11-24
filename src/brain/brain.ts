import { summarize } from "./indicators.js";
import { pipSize, riskBudget, sizePosition, spreadInPips } from "./risk.js";
import type { BrainConfig, MarketSnapshot, TradeDecision } from "./types.js";

export const DEFAULT_CONFIG: Record<MarketSnapshot["instrument"], BrainConfig> = {
  USDJPY: {
    riskPerTradePct: 0.25, minScore: 72, maxSpreadPips: 1.8,
    minAtrPips: 2, maxAtrPips: 30, stopAtrMultiple: 1.5,
    rewardRisk: 1.8, maxOpenRiskPct: 1
  },
  XAUUSD: {
    riskPerTradePct: 0.2, minScore: 78, maxSpreadPips: 35,
    minAtrPips: 8, maxAtrPips: 250, stopAtrMultiple: 1.25,
    rewardRisk: 1.5, maxOpenRiskPct: 0.8
  }
};

function flat(snapshot: MarketSnapshot, reasons: string[], warnings: string[] = []): TradeDecision {
  return {
    instrument: snapshot.instrument, direction: "FLAT", setup: "NO_TRADE",
    score: 0, confidence: "LOW", entry: null, stopLoss: null, takeProfit: null,
    stopDistance: null, riskAmount: 0, positionUnits: 0, reasons, warnings,
    createdAt: snapshot.timestamp
  };
}

function validCandles(snapshot: MarketSnapshot): boolean {
  return (["1m", "5m", "15m", "1h"] as const).every(tf => {
    const candles = snapshot.candles[tf];
    return candles.length >= 30 && candles.every(c =>
      Number.isFinite(c.time) && [c.open, c.high, c.low, c.close].every(Number.isFinite) &&
      c.high >= Math.max(c.open, c.close) && c.low <= Math.min(c.open, c.close) && c.high >= c.low
    );
  });
}

export function evaluateMarket(
  snapshot: MarketSnapshot,
  config: BrainConfig = DEFAULT_CONFIG[snapshot.instrument]
): TradeDecision {
  const warnings: string[] = [];
  if (!validCandles(snapshot)) return flat(snapshot, ["Insufficient or invalid candle history; at least 30 valid candles per timeframe are required."]);
  if (!(snapshot.ask >= snapshot.bid) || snapshot.bid <= 0) return flat(snapshot, ["Invalid bid/ask quote."]);
  if (snapshot.newsBlackout) return flat(snapshot, ["High-impact news blackout is active."], ["Wait until the configured post-news cooldown expires."]);
  if (snapshot.session === "OFF_HOURS") return flat(snapshot, ["Outside the configured active trading sessions."]);
  if (snapshot.dailyPnl <= -(snapshot.accountEquity * snapshot.dailyLossLimitPct / 100)) {
    return flat(snapshot, ["Daily loss limit reached; trading is locked for the day."]);
  }
  if (snapshot.openRiskPct >= config.maxOpenRiskPct) return flat(snapshot, ["Maximum aggregate open risk reached."]);

  const spread = spreadInPips(snapshot);
  if (spread > config.maxSpreadPips) return flat(snapshot, ["Spread exceeds the instrument's configured maximum."], [`Observed spread: ${spread.toFixed(2)} pips.`]);

  const h1 = summarize(snapshot.candles["1h"])!;
  const m15 = summarize(snapshot.candles["15m"])!;
  const m5 = summarize(snapshot.candles["5m"])!;
  const m1 = summarize(snapshot.candles["1m"])!;
  const pip = pipSize(snapshot.instrument);
  const atrPips = m5.atr / pip;
  if (!Number.isFinite(atrPips) || atrPips < config.minAtrPips || atrPips > config.maxAtrPips) {
    return flat(snapshot, ["Volatility is outside the configured tradable range."], [`5m ATR: ${atrPips.toFixed(1)} pips.`]);
  }

  const longBias = h1.emaFast > h1.emaSlow && m15.emaFast > m15.emaSlow;
  const shortBias = h1.emaFast < h1.emaSlow && m15.emaFast < m15.emaSlow;
  const last5 = snapshot.candles["5m"].at(-1)!;
  const previous5 = snapshot.candles["5m"].at(-2)!;
  const bullishBreakout = last5.close > m5.recentHigh && previous5.close <= m5.recentHigh;
  const bearishBreakout = last5.close < m5.recentLow && previous5.close >= m5.recentLow;
  const bullishPullback = longBias && m5.emaFast > m5.emaSlow && m1.rsi >= 42 && m1.rsi <= 68 && m1.momentum > 0;
  const bearishPullback = shortBias && m5.emaFast < m5.emaSlow && m1.rsi >= 32 && m1.rsi <= 58 && m1.momentum < 0;

  let direction: "LONG" | "SHORT" | "FLAT" = "FLAT";
  let setup: TradeDecision["setup"] = "NO_TRADE";
  let score = 0;
  const reasons: string[] = [];

  if (longBias) { score += 25; reasons.push("1h and 15m trend alignment is bullish."); }
  if (shortBias) { score += 25; reasons.push("1h and 15m trend alignment is bearish."); }
  if (bullishPullback) { direction = "LONG"; setup = "TREND_PULLBACK"; score += 30; reasons.push("Lower-timeframe bullish pullback confirmation."); }
  if (bearishPullback) { direction = "SHORT"; setup = "TREND_PULLBACK"; score += 30; reasons.push("Lower-timeframe bearish pullback confirmation."); }
  if (bullishBreakout && longBias) { direction = "LONG"; setup = "BREAKOUT"; score += 25; reasons.push("5m close broke above the recent swing high in trend direction."); }
  if (bearishBreakout && shortBias) { direction = "SHORT"; setup = "BREAKOUT"; score += 25; reasons.push("5m close broke below the recent swing low in trend direction."); }
  if (direction === "LONG" && m1.rsi > 72) { score -= 15; warnings.push("1m RSI is overbought; entry may be extended."); }
  if (direction === "SHORT" && m1.rsi < 28) { score -= 15; warnings.push("1m RSI is oversold; entry may be extended."); }
  if (spread > config.maxSpreadPips * 0.7) { score -= 8; warnings.push("Spread is elevated relative to the allowed maximum."); }
  if (snapshot.instrument === "XAUUSD" && snapshot.session === "ASIA") { score -= 5; warnings.push("Gold liquidity may be thinner during this session."); }

  score = Math.max(0, Math.min(100, score));
  if (direction === "FLAT" || score < config.minScore) {
    return { ...flat(snapshot, reasons.length ? reasons : ["No qualified strategy setup is present."], warnings), score };
  }

  const entry = direction === "LONG" ? snapshot.ask : snapshot.bid;
  const stopDistance = Math.max(m5.atr * config.stopAtrMultiple, spread * pip * 1.5);
  const stopLoss = direction === "LONG" ? entry - stopDistance : entry + stopDistance;
  const takeProfit = direction === "LONG"
    ? entry + stopDistance * config.rewardRisk
    : entry - stopDistance * config.rewardRisk;
  const riskAmount = riskBudget(snapshot, config);
  const positionUnits = sizePosition(riskAmount, stopDistance);
  if (positionUnits <= 0) return flat(snapshot, ["Risk budget is exhausted or position sizing is invalid."], warnings);

  return {
    instrument: snapshot.instrument, direction, setup, score,
    confidence: score >= 88 ? "HIGH" : score >= 78 ? "MEDIUM" : "LOW",
    entry, stopLoss, takeProfit, stopDistance, riskAmount, positionUnits,
    reasons, warnings, createdAt: snapshot.timestamp
  };
}
