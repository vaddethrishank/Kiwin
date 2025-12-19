from supabase import create_client
from app.core.config import settings
from dotenv import load_dotenv

load_dotenv()

# Use Service Key to bypass RLS for checking
url = settings.SUPABASE_URL
key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY

if not key:
    print("Error: No Supabase Key found.")
    exit(1)

supabase = create_client(url, key)

print("Checking 'documents' table...")

try:
    response = supabase.table("documents").select("id", count="exact").execute()
    count = response.count
    print(f"Total Embeddings/Chunks found: {count}")
    
    if count > 0:
        # Show sample
        sample = supabase.table("documents").select("content, file_id").limit(1).execute()
        print(f"Sample Chunk: {sample.data[0]['content'][:50]}...")
        
except Exception as e:
    print(f"Error connecting to DB: {e}")
