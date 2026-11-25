import type { Candle } from "./types.js";

export type CandlePattern = "BULLISH_ENGULFING" | "BEARISH_ENGULFING" | "PIN_BAR_BULLISH" | "PIN_BAR_BEARISH" | "NONE";
export interface LiquiditySweep { direction: "BULLISH" | "BEARISH"; level: number; reclaimedAt: number; strength: number }
export interface AdvancedMarketContext {
  pattern: CandlePattern;
  sweep: LiquiditySweep | null;
  rangeHigh: number;
  rangeLow: number;
  momentum: number;
}

/** Detects simple, closed-candle patterns. Input must be oldest-first. */
export function detectCandlePattern(candles: Candle[]): CandlePattern {
  if (candles.length < 2) return "NONE";
  const a = candles[candles.length - 2]!;
  const b = candles[candles.length - 1]!;
  const body = Math.abs(b.close - b.open);
  const range = b.high - b.low;
  if (range <= 0) return "NONE";
  const lowerWick = Math.min(b.open, b.close) - b.low;
  const upperWick = b.high - Math.max(b.open, b.close);
  if (a.close < a.open && b.close > b.open && b.open <= a.close && b.close >= a.open) return "BULLISH_ENGULFING";
  if (a.close > a.open && b.close < b.open && b.open >= a.close && b.close <= a.open) return "BEARISH_ENGULFING";
  if (lowerWick >= Math.max(body * 2, range * 0.55) && upperWick <= range * 0.2) return "PIN_BAR_BULLISH";
  if (upperWick >= Math.max(body * 2, range * 0.55) && lowerWick <= range * 0.2) return "PIN_BAR_BEARISH";
  return "NONE";
}

/** Finds a wick through a prior range followed by a close back inside it. */
export function detectLiquiditySweep(candles: Candle[], lookback = 20): LiquiditySweep | null {
  if (!Number.isInteger(lookback) || lookback < 3 || candles.length <= lookback) return null;
  const current = candles[candles.length - 1]!;
  const prior = candles.slice(-(lookback + 1), -1);
  const high = Math.max(...prior.map(c => c.high));
  const low = Math.min(...prior.map(c => c.low));
  if (current.high > high && current.close < high) {
    return { direction: "BEARISH", level: high, reclaimedAt: current.time, strength: (current.high - high) / Math.max(current.high - current.low, Number.EPSILON) };
  }
  if (current.low < low && current.close > low) {
    return { direction: "BULLISH", level: low, reclaimedAt: current.time, strength: (low - current.low) / Math.max(current.high - current.low, Number.EPSILON) };
  }
  return null;
}

export function analyzeAdvancedContext(candles: Candle[], lookback = 20): AdvancedMarketContext | null {
  if (candles.length < Math.max(lookback + 1, 3)) return null;
  const prior = candles.slice(-lookback - 1, -1);
  return {
    pattern: detectCandlePattern(candles),
    sweep: detectLiquiditySweep(candles, lookback),
    rangeHigh: Math.max(...prior.map(c => c.high)),
    rangeLow: Math.min(...prior.map(c => c.low)),
    momentum: candles[candles.length - 1]!.close - candles[candles.length - 2]!.close
  };
}
