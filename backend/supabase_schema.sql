-- Enable pgvector extension for embeddings
create extension if not exists vector;

-- AGENTS TABLE
create table agents (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users(id) not null,
  name text not null,
  role text not null default 'assistant',
  description text,
  model text not null default 'gpt-4-turbo',
  system_prompt text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for Agents
alter table agents enable row level security;

create policy "Users can view their own agents"
  on agents for select
  using (auth.uid() = user_id);

create policy "Users can insert their own agents"
  on agents for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own agents"
  on agents for update
  using (auth.uid() = user_id);

create policy "Users can delete their own agents"
  on agents for delete
  using (auth.uid() = user_id);


-- FILES TABLE (For RAG)
create table files (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users(id) not null,
  agent_id uuid references agents(id) on delete cascade,
  file_name text not null,
  file_path text not null, -- Path in storage bucket
  file_type text,
  file_size bigint,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS for Files
alter table files enable row level security;

create policy "Users can view their own files"
  on files for select
  using (auth.uid() = user_id);

create policy "Users can upload their own files"
  on files for insert
  with check (auth.uid() = user_id);

create policy "Users can delete their own files"
  on files for delete
  using (auth.uid() = user_id);


-- DOCUMENTS TABLE (For Chunks & Embeddings)
create table documents (
  id uuid default gen_random_uuid() primary key,
  file_id uuid references files(id) on delete cascade,
  content text,
  metadata jsonb,
  embedding vector(768) -- Matching Gemini text-embedding-004 dimension
);

-- RLS for Documents (Indirectly accessible via files/agents usually, but good to secure)
alter table documents enable row level security;

-- Simple policy: if you own the file, you own the chunks
create policy "Users can view own document chunks"
  on documents for select
  using (
    exists (
      select 1 from files
      where files.id = documents.file_id
      and files.user_id = auth.uid()
    )
  );
