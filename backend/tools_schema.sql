-- 1. Add tools column to agents table (Stores enabled tools like ['calculator', 'web_search'])
ALTER TABLE agents
ADD COLUMN tools TEXT[] NOT NULL DEFAULT '{}';

-- 2. Create agent_tool_configs table for HTTP API capabilities
CREATE TABLE agent_tool_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
  tool_name TEXT NOT NULL,
  config JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- RLS Policies
ALTER TABLE agent_tool_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own agents' tool configs"
  ON agent_tool_configs FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM agents
      WHERE agents.id = agent_tool_configs.agent_id
      AND agents.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert their own agents' tool configs"
  ON agent_tool_configs FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM agents
      WHERE agents.id = agent_tool_configs.agent_id
      AND agents.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update their own agents' tool configs"
  ON agent_tool_configs FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM agents
      WHERE agents.id = agent_tool_configs.agent_id
      AND agents.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete their own agents' tool configs"
  ON agent_tool_configs FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM agents
      WHERE agents.id = agent_tool_configs.agent_id
      AND agents.user_id = auth.uid()
    )
  );
