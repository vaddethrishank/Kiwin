import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or "your-project" in url:
    print("Error: SUPABASE_URL not set correctly.")
    exit(1)

if not key or "your-anon-key" in key:
    print("Error: SUPABASE_KEY not set correctly.")
    exit(1)

try:
    supabase = create_client(url, key)
    print(f"Supabase Client initialized for: {url}")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)
