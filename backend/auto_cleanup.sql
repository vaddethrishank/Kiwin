-- Function: Keep only the last 50 messages for a given Agent + User pair
create or replace function keep_latest_messages() returns trigger as $$
begin
  delete from messages
  where id in (
    select id from messages
    where agent_id = NEW.agent_id 
    and user_id = NEW.user_id
    order by created_at desc
    offset 50 -- The Limit: Keep top 50, delete the rest
  );
  return NEW;
end;
$$ language plpgsql;

-- Trigger: Run this every time a new message is inserted
drop trigger if exists trigger_keep_latest_messages on messages;
create trigger trigger_keep_latest_messages
  after insert on messages
  for each row
  execute function keep_latest_messages();
