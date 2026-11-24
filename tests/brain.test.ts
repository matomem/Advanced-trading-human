import { describe, expect, it } from "vitest";
import { evaluateMarket } from "../src/brain/brain.js";
import type { Candle, MarketSnapshot } from "../src/brain/types.js";

function candles(base: number, step: number): Candle[] {
  return Array.from({ length: 60 }, (_, i) => {
    const close = base + i * step;
    return { time: 1_700_000_000_000 + i * 60_000, open: close - step * 0.4, high: close + 0.02, low: close - 0.02, close };
  });
}

function snapshot(overrides: Partial<MarketSnapshot> = {}): MarketSnapshot {
  const data = candles(150, 0.01);
  return {
    instrument: "USDJPY",
    candles: { "1m": data, "5m": data, "15m": data, "1h": data },
    bid: 150.5, ask: 150.51, timestamp: Date.now(), session: "LONDON",
    newsBlackout: false, accountEquity: 10_000, dailyPnl: 0,
    dailyLossLimitPct: 2, openRiskPct: 0, ...overrides
  };
}

describe("expert brain safety gates", () => {
  it("refuses to trade during a news blackout", () => {
    const result = evaluateMarket(snapshot({ newsBlackout: true }));
    expect(result.direction).toBe("FLAT");
    expect(result.riskAmount).toBe(0);
  });

  it("locks trading after the daily loss limit", () => {
    const result = evaluateMarket(snapshot({ dailyPnl: -200 }));
    expect(result.direction).toBe("FLAT");
    expect(result.reasons.join(" ")).toContain("Daily loss limit");
  });

  it("rejects invalid market quotes", () => {
    const result = evaluateMarket(snapshot({ bid: 151, ask: 150 }));
    expect(result.direction).toBe("FLAT");
  });

  it("rejects insufficient candle history", () => {
    const result = evaluateMarket(snapshot({ candles: { "1m": [], "5m": [], "15m": [], "1h": [] } }));
    expect(result.direction).toBe("FLAT");
  });
});
