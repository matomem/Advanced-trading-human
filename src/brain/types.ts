export type Instrument = "USDJPY" | "XAUUSD";
export type Timeframe = "1m" | "5m" | "15m" | "1h";
export type Direction = "LONG" | "SHORT" | "FLAT";
export type SetupType = "TREND_PULLBACK" | "BREAKOUT" | "NO_TRADE";

export interface Candle {
  time: number; // UTC epoch milliseconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface TimeframeData {
  "1m": Candle[];
  "5m": Candle[];
  "15m": Candle[];
  "1h": Candle[];
}

export interface MarketSnapshot {
  instrument: Instrument;
  candles: TimeframeData;
  bid: number;
  ask: number;
  timestamp: number;
  session: "ASIA" | "LONDON" | "NEW_YORK" | "OVERLAP" | "OFF_HOURS";
  newsBlackout: boolean;
  accountEquity: number;
  dailyPnl: number;
  dailyLossLimitPct: number;
  openRiskPct: number;
}

export interface BrainConfig {
  riskPerTradePct: number;
  minScore: number;
  maxSpreadPips: number;
  minAtrPips: number;
  maxAtrPips: number;
  stopAtrMultiple: number;
  rewardRisk: number;
  maxOpenRiskPct: number;
}

export interface IndicatorSummary {
  emaFast: number;
  emaSlow: number;
  rsi: number;
  atr: number;
  recentHigh: number;
  recentLow: number;
  momentum: number;
}

export interface TradeDecision {
  instrument: Instrument;
  direction: Direction;
  setup: SetupType;
  score: number;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  entry: number | null;
  stopLoss: number | null;
  takeProfit: number | null;
  stopDistance: number | null;
  riskAmount: number;
  positionUnits: number;
  reasons: string[];
  warnings: string[];
  createdAt: number;
}
