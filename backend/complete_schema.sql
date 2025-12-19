-- KIWIN COMPLETE DATABASE SCHEMA
-- Run this script in your Supabase SQL Editor to initialize the entire project.

-- 1. Enable Extensions
create extension if not exists vector;

-- 2. Create AGENTS Table
create table if not exists agents (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users(id) not null,
  name text not null,
  role text not null default 'assistant',
  description text,
  model text not null default 'gemini-1.5-flash', -- Default to Flash
  system_prompt text,
  api_key text, -- For user-provided Gemini keys
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for Agents
alter table agents enable row level security;
create policy "Users can view their own agents" on agents for select using (auth.uid() = user_id);
create policy "Users can insert their own agents" on agents for insert with check (auth.uid() = user_id);
create policy "Users can update their own agents" on agents for update using (auth.uid() = user_id);
create policy "Users can delete their own agents" on agents for delete using (auth.uid() = user_id);


-- 3. Create FILES Table (RAG)
create table if not exists files (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users(id) not null,
  agent_id uuid references agents(id) on delete cascade,
  file_name text not null,
  file_path text not null,
  file_type text,
  file_size bigint,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for Files
alter table files enable row level security;
create policy "Users can view their own files" on files for select using (auth.uid() = user_id);
create policy "Users can upload their own files" on files for insert with check (auth.uid() = user_id);
create policy "Users can delete their own files" on files for delete using (auth.uid() = user_id);


-- 4. Create DOCUMENTS Table (Embeddings)
create table if not exists documents (
  id uuid default gen_random_uuid() primary key,
  file_id uuid references files(id) on delete cascade,
  content text,
  metadata jsonb,
  embedding vector(768) -- Gemini Embedding Dimension
);

-- RLS for Documents
alter table documents enable row level security;
create policy "Users can view own document chunks" on documents for select using (
  exists (
    select 1 from files where files.id = documents.file_id and files.user_id = auth.uid()
  )
);


-- 5. Create MESSAGES Table (Chat History)
create table if not exists messages (
  id uuid default gen_random_uuid() primary key,
  agent_id uuid references agents(id) on delete cascade not null,
  user_id uuid references auth.users(id) not null,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for Messages
alter table messages enable row level security;
create policy "Users can view their own messages" on messages for select using (auth.uid() = user_id);
create policy "Users can insert their own messages" on messages for insert with check (auth.uid() = user_id);


-- 6. Create CONTACT_MESSAGES Table (Public Form)
create table if not exists contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  message text not null,
  status text default 'new',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for Contact Messages
alter table contact_messages enable row level security;
-- Allow anyone (including unauthenticated users) to insert
create policy "Allow public to insert contact messages" on contact_messages for insert to anon, authenticated with check (true);


-- 7. Create Matching Function (Vector Search)
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


-- 8. Storage Bucket Setup
insert into storage.buckets (id, name, public) values ('agent-knowledge', 'agent-knowledge', false)
on conflict (id) do nothing;

-- Storage Policies
-- Note: We drop existing policies first to ideally make this script re-runnable without error
drop policy if exists "Users can upload own files" on storage.objects;
drop policy if exists "Users can view own files" on storage.objects;
drop policy if exists "Users can delete own files" on storage.objects;

create policy "Users can upload own files" on storage.objects for insert with check (bucket_id = 'agent-knowledge' and name like (auth.uid()::text || '/%'));
create policy "Users can view own files" on storage.objects for select using (bucket_id = 'agent-knowledge' and name like (auth.uid()::text || '/%'));
create policy "Users can delete own files" on storage.objects for delete using (bucket_id = 'agent-knowledge' and name like (auth.uid()::text || '/%'));
