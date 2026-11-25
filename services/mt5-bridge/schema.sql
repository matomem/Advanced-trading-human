CREATE TABLE IF NOT EXISTS trade_decisions (
  id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  symbol TEXT NOT NULL, timeframe TEXT NOT NULL, decision JSONB NOT NULL,
  model_version TEXT, feature_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS trade_outcomes (
  id BIGSERIAL PRIMARY KEY, decision_id BIGINT NOT NULL REFERENCES trade_decisions(id),
  closed_at TIMESTAMPTZ NOT NULL, outcome TEXT NOT NULL CHECK (outcome IN ('WIN','LOSS','BREAKEVEN')),
  pnl NUMERIC(18,6) NOT NULL, costs NUMERIC(18,6) NOT NULL DEFAULT 0,
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON trade_decisions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcomes_closed_at ON trade_outcomes(closed_at DESC);
