import type { TradeDecision } from "../brain/types.js";

export interface TradeOutcome {
  decisionId: string; closedAt: number; outcome: "WIN" | "LOSS" | "BREAKEVEN";
  pnl: number; notes?: string;
}
export interface JournalRecord { id: string; decision: TradeDecision; outcome?: TradeOutcome }
export interface JournalStore {
  appendDecision(decision: TradeDecision): Promise<void>;
  appendOutcome(outcome: TradeOutcome): Promise<void>;
  list(limit?: number): Promise<JournalRecord[]>;
}

/** In-memory development store. Replace with encrypted durable storage for production. */
export class MemoryJournal implements JournalStore {
  private records: JournalRecord[] = [];
  async appendDecision(decision: TradeDecision): Promise<void> {
    this.records.push({ id: `${decision.createdAt}-${this.records.length}`, decision });
  }
  async appendOutcome(outcome: TradeOutcome): Promise<void> {
    const index = this.records.findIndex(r => r.id === outcome.decisionId || String(r.decision.createdAt) === outcome.decisionId);
    if (index < 0) throw new Error("Decision not found in journal");
    this.records[index] = { ...this.records[index]!, outcome };
  }
  async list(limit = 100): Promise<JournalRecord[]> {
    if (!Number.isInteger(limit) || limit < 0) throw new Error("Limit must be a non-negative integer");
    return this.records.slice(-limit).reverse();
  }
}

export function summarizePerformance(records: JournalRecord[]): { trades: number; wins: number; losses: number; winRate: number; netPnl: number } {
  const closed = records.filter(r => r.outcome);
  const wins = closed.filter(r => r.outcome!.outcome === "WIN").length;
  const losses = closed.filter(r => r.outcome!.outcome === "LOSS").length;
  return { trades: closed.length, wins, losses, winRate: closed.length ? wins / closed.length : 0,
    netPnl: closed.reduce((sum, r) => sum + r.outcome!.pnl, 0) };
}
