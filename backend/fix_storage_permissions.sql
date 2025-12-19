-- EMERGENCY FIX: Make Bucket Public and Permissive
-- This disables strict security checks to get uploads working for now.

-- 1. Make bucket public
update storage.buckets
set public = true
where id = 'agent-knowledge';

-- 2. Drop all restrictive policies
drop policy if exists "Users can upload own files" on storage.objects;
drop policy if exists "Users can view own files" on storage.objects;
drop policy if exists "Users can update own files" on storage.objects;
drop policy if exists "Users can delete own files" on storage.objects;

-- 3. Create a "Allow All" policy for authenticated users
-- This allows any logged-in user to do anything with files in this bucket
create policy "Allow all authenticated operations"
on storage.objects
for all
using (
  bucket_id = 'agent-knowledge' 
  and auth.role() = 'authenticated'
)
with check (
  bucket_id = 'agent-knowledge' 
  and auth.role() = 'authenticated'
);
