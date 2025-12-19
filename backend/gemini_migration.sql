-- Gemini uses 768 dimensions instead of OpenAI's 1536.
-- Run this script to update your existing table.

-- 1. Drop the existing column (WARNING: Deletes existing embeddings)
ALTER TABLE documents DROP COLUMN embedding;

-- 2. Add the new column with 768 dimensions
ALTER TABLE documents ADD COLUMN embedding vector(768);
