-- TEMPLATE: Configure HTTP API for an Agent
-- Replace 'YOUR_AGENT_ID_HERE' with your actual Agent UUID (check 'agents' table)

insert into agent_tool_configs (agent_id, tool_name, config)
values (
  'YOUR_AGENT_ID_HERE', -- <--- PASTE AGENT ID HERE
  'http_api',
  '{
    "base_url": "https://jsonplaceholder.typicode.com",
    "headers": {
      "Content-Type": "application/json"
    },
    "endpoints": [
      {
        "method": "GET",
        "path": "/users/{id}",
        "description": "Get user details by ID"
      },
      {
        "method": "GET",
        "path": "/posts",
        "description": "List all posts"
      }
    ]
  }'::jsonb
);
