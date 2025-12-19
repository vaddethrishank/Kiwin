-- Migration to support Public Chat (Anonymous Users)

-- 1. Add session_id column to messages table
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS session_id TEXT;

-- 2. Make user_id nullable (since public users are anonymous)
ALTER TABLE messages 
ALTER COLUMN user_id DROP NOT NULL;

-- 3. (Optional) Index on session_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
