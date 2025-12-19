-- Storage Bucket Setup for Knowledge Base (Updated)

-- 1. Create the bucket (Safe insert)
insert into storage.buckets (id, name, public)
values ('agent-knowledge', 'agent-knowledge', false)
on conflict (id) do nothing;

-- 2. Drop existing policies to handle re-runs
drop policy if exists "Users can upload own files" on storage.objects;
drop policy if exists "Users can view own files" on storage.objects;
drop policy if exists "Users can update own files" on storage.objects;
drop policy if exists "Users can delete own files" on storage.objects;

-- 3. Simplified Policies using prefix matching

-- Policy: Users can upload to their own folder (user_id/...)
create policy "Users can upload own files"
on storage.objects for insert
with check (
  bucket_id = 'agent-knowledge' 
  and name like (auth.uid()::text || '/%')
);

-- Policy: Users can view their own files
create policy "Users can view own files"
on storage.objects for select
using (
  bucket_id = 'agent-knowledge' 
  and name like (auth.uid()::text || '/%')
);

-- Policy: Users can update their own files
create policy "Users can update own files"
on storage.objects for update
using (
  bucket_id = 'agent-knowledge' 
  and name like (auth.uid()::text || '/%')
);

-- Policy: Users can delete their own files
create policy "Users can delete own files"
on storage.objects for delete
using (
  bucket_id = 'agent-knowledge' 
  and name like (auth.uid()::text || '/%')
);
