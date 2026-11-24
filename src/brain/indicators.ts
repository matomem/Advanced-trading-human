import type { Candle, IndicatorSummary } from "./types.js";

export function ema(values: number[], period: number): number {
  if (values.length < period || period < 1) return Number.NaN;
  const alpha = 2 / (period + 1);
  let value = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (const next of values.slice(period)) value = alpha * next + (1 - alpha) * value;
  return value;
}

export function rsi(values: number[], period = 14): number {
  if (values.length <= period) return Number.NaN;
  let gains = 0;
  let losses = 0;
  for (let i = 1; i <= period; i++) {
    const change = values[i]! - values[i - 1]!;
    gains += Math.max(change, 0);
    losses += Math.max(-change, 0);
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  for (let i = period + 1; i < values.length; i++) {
    const change = values[i]! - values[i - 1]!;
    avgGain = (avgGain * (period - 1) + Math.max(change, 0)) / period;
    avgLoss = (avgLoss * (period - 1) + Math.max(-change, 0)) / period;
  }
  if (avgLoss === 0) return 100;
  return 100 - 100 / (1 + avgGain / avgLoss);
}

export function atr(candles: Candle[], period = 14): number {
  if (candles.length <= period) return Number.NaN;
  const ranges: number[] = [];
  for (let i = 1; i < candles.length; i++) {
    const c = candles[i]!;
    const previousClose = candles[i - 1]!.close;
    ranges.push(Math.max(c.high - c.low, Math.abs(c.high - previousClose), Math.abs(c.low - previousClose)));
  }
  return ranges.slice(-period).reduce((a, b) => a + b, 0) / period;
}

export function summarize(candles: Candle[]): IndicatorSummary | null {
  if (candles.length < 30) return null;
  const closes = candles.map(c => c.close);
  const recent = candles.slice(-20);
  const last = candles[candles.length - 1]!;
  const prior = candles[candles.length - 2]!;
  return {
    emaFast: ema(closes, 9),
    emaSlow: ema(closes, 21),
    rsi: rsi(closes, 14),
    atr: atr(candles, 14),
    recentHigh: Math.max(...recent.slice(0, -1).map(c => c.high)),
    recentLow: Math.min(...recent.slice(0, -1).map(c => c.low)),
    momentum: last.close - prior.close
  };
}
