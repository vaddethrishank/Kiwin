-- Create a function to search for documents
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
