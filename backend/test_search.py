import os
import sys

# Parse .env manually to avoid dotenv dependency
env_vars = {}
with open('c:/Users/thris/Kiwin/backend/.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env_vars[k.strip()] = v.strip()

from supabase import create_client

url = env_vars.get("SUPABASE_URL")
key = env_vars.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing DB credentials")
    sys.exit(1)

db = create_client(url, key)

print("Fetching agents to test with...")
agents_res = db.table("agents").select("id, name").execute()
if not agents_res.data:
    print("No agents found in DB")
    sys.exit(0)

print(f"Agents: {agents_res.data}")

# For each agent, see if they have files
for agent in agents_res.data:
    agent_id = agent["id"]
    files_res = db.table("files").select("id").eq("agent_id", agent_id).execute()
    print(f"Agent {agent_id} ({agent['name']}) has {len(files_res.data)} files.")
    
    # Try testing hybrid search with a dummy 768-dim vector (zero vector)
    dummy_vector = [0.0] * 768
    params = {
        "query_text": "hello",
        "query_embedding": dummy_vector,
        "filter_agent_id": agent_id,
        "match_count": 5,
        "rrf_k": 60
    }
    print(f"Calling hybrid_search for agent {agent_id}...")
    try:
        res = db.rpc("hybrid_search", params).execute()
        print(f"hybrid_search results for {agent['name']}: {len(res.data)} matches")
        if res.data:
            print("Sample result content preview:")
            print(res.data[0]['content'][:100])
    except Exception as e:
        print(f"RPC ERROR: {e}")
