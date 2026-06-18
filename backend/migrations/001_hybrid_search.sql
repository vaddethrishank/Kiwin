-- ════════════════════════════════════════════════════════════════
-- Kiwin Hybrid Search Migration
-- Run once in: Supabase Dashboard → SQL Editor → New Query
-- ════════════════════════════════════════════════════════════════

-- ── Step 1: Add generated tsvector column + GIN index ────────────
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS fts tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;

CREATE INDEX IF NOT EXISTS documents_fts_idx ON documents USING GIN (fts);

-- Create HNSW vector index for extremely fast nearest neighbor search
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING hnsw (embedding vector_cosine_ops);

-- ── Step 2: Backfill existing rows (forces tsvector recompute) ───
UPDATE documents SET content = content;

-- ── Step 3: Create hybrid_search function (Vector + BM25 + RRF) ─
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text       text,
  query_embedding  vector(768),
  filter_agent_id  uuid,
  match_count      int     DEFAULT 5,
  rrf_k            int     DEFAULT 60
)
RETURNS TABLE (
  id        uuid,
  content   text,
  metadata  jsonb,
  rrf_score double precision
)
LANGUAGE sql
AS $$
  WITH
  -- Dense vector similarity leg
  vector_results AS (
    SELECT
      d.id,
      d.content,
      d.metadata,
      ROW_NUMBER() OVER (ORDER BY d.embedding <=> query_embedding) AS rank
    FROM documents d
    JOIN files f ON f.id = d.file_id
    WHERE f.agent_id = filter_agent_id
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count * 2
  ),
  -- Sparse BM25 full-text search leg (ts_rank_cd ≈ BM25)
  fts_results AS (
    SELECT
      d.id,
      d.content,
      d.metadata,
      ROW_NUMBER() OVER (ORDER BY ts_rank_cd(d.fts, query) DESC) AS rank
    FROM documents d
    JOIN files f ON f.id = d.file_id,
    plainto_tsquery('english', query_text) query
    WHERE f.agent_id = filter_agent_id
      AND d.fts @@ query
    ORDER BY ts_rank_cd(d.fts, query) DESC
    LIMIT match_count * 2
  ),
  -- Reciprocal Rank Fusion:  score = 1/(k + rank_v) + 1/(k + rank_fts)
  rrf AS (
    SELECT
      COALESCE(v.id,       fts.id)       AS id,
      COALESCE(v.content,  fts.content)  AS content,
      COALESCE(v.metadata, fts.metadata) AS metadata,
      COALESCE(1.0 / (rrf_k + v.rank),   0.0)
      + COALESCE(1.0 / (rrf_k + fts.rank), 0.0) AS rrf_score
    FROM vector_results v
    FULL OUTER JOIN fts_results fts ON fts.id = v.id
  )
  SELECT id, content, metadata, rrf_score
  FROM rrf
  ORDER BY rrf_score DESC
  LIMIT match_count;
$$;
