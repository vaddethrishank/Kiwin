-- Chats / Messages History
create table messages (
  id uuid default gen_random_uuid() primary key,
  agent_id uuid references agents(id) on delete cascade not null,
  user_id uuid references auth.users(id) not null,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS
alter table messages enable row level security;

create policy "Users can view their own messages"
  on messages for select
  using (auth.uid() = user_id);

create policy "Users can insert their own messages"
  on messages for insert
  with check (auth.uid() = user_id);
