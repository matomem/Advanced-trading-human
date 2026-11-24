import type { BrainConfig, Instrument, MarketSnapshot } from "./types.js";

export function pipSize(instrument: Instrument): number {
  return instrument === "USDJPY" ? 0.01 : 0.1;
}

export function spreadInPips(snapshot: MarketSnapshot): number {
  return (snapshot.ask - snapshot.bid) / pipSize(snapshot.instrument);
}

export function riskBudget(snapshot: MarketSnapshot, config: BrainConfig): number {
  const dailyLimit = snapshot.accountEquity * (snapshot.dailyLossLimitPct / 100);
  const remainingDaily = Math.max(0, dailyLimit + snapshot.dailyPnl);
  const perTrade = snapshot.accountEquity * (config.riskPerTradePct / 100);
  const remainingPortfolio = Math.max(
    0,
    snapshot.accountEquity * ((config.maxOpenRiskPct - snapshot.openRiskPct) / 100)
  );
  return Math.max(0, Math.min(perTrade, remainingDaily, remainingPortfolio));
}

/**
 * Approximate units for FX-style instruments when one price unit of movement
 * per unit position equals one account-currency unit. Broker contract sizing,
 * quote-to-account conversion and lot rules must be supplied by the execution
 * adapter before any order is sent.
 */
export function sizePosition(riskAmount: number, stopDistance: number): number {
  if (!Number.isFinite(riskAmount) || !Number.isFinite(stopDistance) || stopDistance <= 0) return 0;
  return riskAmount / stopDistance;
}
