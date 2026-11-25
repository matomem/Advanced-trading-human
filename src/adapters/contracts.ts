import type { Candle, Instrument, Timeframe } from "../brain/types.js";

/** Implement these contracts with a trusted MT5/broker service; never put broker secrets in the browser. */
export interface MarketDataAdapter {
  getCandles(instrument: Instrument, timeframe: Timeframe, count: number): Promise<Candle[]>;
  getQuote(instrument: Instrument): Promise<{ bid: number; ask: number; timestamp: number }>;
}
export interface EconomicEvent {
  id: string; currency: string; impact: "LOW" | "MEDIUM" | "HIGH";
  title: string; scheduledAt: number; actual?: string; forecast?: string; previous?: string;
}
export interface EconomicCalendarAdapter {
  getUpcomingEvents(from: number, to: number): Promise<EconomicEvent[]>;
}
export interface SentimentSnapshot {
  instrument: Instrument; score: number; sources: string[]; observedAt: number;
}
export interface SentimentAdapter {
  getSentiment(instrument: Instrument): Promise<SentimentSnapshot>;
}
export interface TradeExecutionAdapter {
  /** Deliberately not implemented by this repository. Add only behind demo-first safeguards. */
  submitOrder(input: { instrument: Instrument; side: "BUY" | "SELL"; units: number; stopLoss: number; takeProfit: number }): Promise<{ orderId: string; status: string }>;
}
