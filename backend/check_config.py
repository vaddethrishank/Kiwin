from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
url = os.getenv("SUPABASE_URL")

print(f"SUPABASE_URL: {url}")
if key:
    print(f"SUPABASE_SERVICE_ROLE_KEY: Loaded (Starts with {key[:5]}...)")
else:
    print("SUPABASE_SERVICE_ROLE_KEY: MISSING")
