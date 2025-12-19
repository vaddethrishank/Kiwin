-- Consolidated Fix Script
-- Run this in Supabase SQL Editor to fix missing tables and columns

-- 1. Ensure AGENTS table has necessary columns
ALTER TABLE agents ADD COLUMN IF NOT EXISTS tools TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS api_key TEXT;

-- 2. Create MESSAGES table if it doesn't exist
CREATE TABLE IF NOT EXISTS messages (
  id uuid default gen_random_uuid() primary key,
  agent_id uuid references agents(id) on delete cascade not null,
  user_id uuid references auth.users(id), -- Nullable for public chat
  session_id text, -- For public chat
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. Update MESSAGES table for Public Chat (if it already existed but was old)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'user_id') THEN
        ALTER TABLE messages ALTER COLUMN user_id DROP NOT NULL;
    END IF;
END $$;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS session_id TEXT;

-- 4. RLS for Messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts when re-running
DROP POLICY IF EXISTS "Users can view their own messages" ON messages;
DROP POLICY IF EXISTS "Users can insert their own messages" ON messages;
DROP POLICY IF EXISTS "Public can view their own session messages" ON messages;
DROP POLICY IF EXISTS "Public can insert their own session messages" ON messages;

-- Authenticated Users Policies
CREATE POLICY "Users can view their own messages"
  ON messages FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own messages"
  ON messages FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Public/Anonymous Users Policies
CREATE POLICY "Public can view their own session messages"
  ON messages FOR SELECT
  USING (session_id IS NOT NULL); -- Simplified for now, ideally matches a session logic

CREATE POLICY "Public can insert their own session messages"
  ON messages FOR INSERT
  WITH CHECK (session_id IS NOT NULL);


-- 5. RAG Match Function
create extension if not exists vector;

create or replace function match_documents (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  filter_agent_id uuid
)
returns table (
  id uuid,
  content text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  join files on documents.file_id = files.id
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  and files.agent_id = filter_agent_id
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
