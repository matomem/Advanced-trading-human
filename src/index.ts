export { evaluateMarket, DEFAULT_CONFIG } from "./brain/brain.js";
export { ema, rsi, atr, summarize } from "./brain/indicators.js";
export { pipSize, spreadInPips, riskBudget, sizePosition } from "./brain/risk.js";
export { detectCandlePattern, detectLiquiditySweep, analyzeAdvancedContext } from "./brain/advanced.js";
export type { CandlePattern, LiquiditySweep, AdvancedMarketContext } from "./brain/advanced.js";
export type * from "./brain/types.js";
export type { MarketDataAdapter, EconomicCalendarAdapter, EconomicEvent, SentimentAdapter, SentimentSnapshot, TradeExecutionAdapter } from "./adapters/contracts.js";
export { MemoryJournal, summarizePerformance } from "./learning/journal.js";
export type { JournalStore, JournalRecord, TradeOutcome } from "./learning/journal.js";
