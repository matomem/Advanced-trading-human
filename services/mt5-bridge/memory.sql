CREATE TABLE IF NOT EXISTS strategy_memories (
 id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 symbol TEXT NOT NULL, timeframe TEXT NOT NULL, category TEXT NOT NULL,
 observation TEXT NOT NULL, tags TEXT[] NOT NULL DEFAULT '{}',
 evidence JSONB NOT NULL DEFAULT '{}'::jsonb, confidence NUMERIC(5,4) NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK(status IN ('UNVERIFIED','SUPPORTED','REJECTED','ARCHIVED')),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_memories_symbol_timeframe ON strategy_memories(symbol,timeframe,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON strategy_memories USING GIN(tags);
CREATE TABLE IF NOT EXISTS model_registry (
 id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 model_name TEXT NOT NULL, version TEXT NOT NULL, artifact_uri TEXT NOT NULL,
 feature_schema JSONB NOT NULL, train_start TIMESTAMPTZ, train_end TIMESTAMPTZ,
 metrics JSONB NOT NULL DEFAULT '{}'::jsonb, status TEXT NOT NULL DEFAULT 'EXPERIMENTAL'
);
