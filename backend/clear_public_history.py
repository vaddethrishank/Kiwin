import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not key:
    print("Error: SUPABASE_SERVICE_ROLE_KEY not found in .env")
    exit(1)

supabase = create_client(url, key)

print("Clearing public chat history...")

# Delete messages where session_id is not null (Public chats)
try:
    data = supabase.table("messages").delete().neq("session_id", "null").execute()
    print("Success! Public chat history cleared.")
    print(f"Deleted rows: {len(data.data)}")
except Exception as e:
    print(f"Error: {e}")
