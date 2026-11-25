import { describe, expect, it } from "vitest";
import { detectCandlePattern, detectLiquiditySweep, analyzeAdvancedContext } from "../src/brain/advanced.js";
import type { Candle } from "../src/brain/types.js";

const candle = (open: number, high: number, low: number, close: number, time = 1): Candle => ({ time, open, high, low, close });

describe("advanced market context", () => {
  it("detects bullish engulfing", () => {
    expect(detectCandlePattern([candle(10, 10.2, 9.7, 9.8), candle(9.7, 10.3, 9.6, 10.1)])).toBe("BULLISH_ENGULFING");
  });
  it("detects a bearish liquidity sweep", () => {
    const prior = Array.from({ length: 20 }, (_, i) => candle(10, 11, 9, 10, i));
    prior.push(candle(10, 11.5, 9.5, 10.5, 21));
    expect(detectLiquiditySweep(prior)?.direction).toBe("BEARISH");
  });
  it("returns null when history is insufficient", () => {
    expect(analyzeAdvancedContext([candle(1, 2, 0, 1)], 20)).toBeNull();
  });
});
