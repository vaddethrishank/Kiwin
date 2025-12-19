-- Create contact_messages table
create table public.contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  message text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  status text default 'new' -- new, read, replied
);

-- Enable RLS
alter table public.contact_messages enable row level security;

-- Policy: Allow anyone (anon) to insert messages
create policy "Allow public to insert contact messages"
on public.contact_messages
for insert
to anon, authenticated
with check (true);

-- Policy: Only allow service role (backend) to select/read (effectively admin only)
-- We don't add a SELECT policy for anon/authenticated, so by default they cannot read.
