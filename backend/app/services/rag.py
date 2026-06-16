import io
import pypdf
from typing import List
from supabase import create_client, Client
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from app.core.config import settings

# FastEmbed model (ONNX-based, ~150MB — fits Render free tier, 768-dim matches Supabase)
_embeddings_model = None

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = FastEmbedEmbeddings(
            model_name="BAAI/bge-base-en-v1.5"
        )
    return _embeddings_model

# Initialize Text Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

def get_db() -> Client:
    """
    Returns Supabase client with Service Role Key for background processing.
    """
    if settings.SUPABASE_SERVICE_ROLE_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    # Fallback/Error if not configured - background tasks generally need admin rights 
    # or we need to pass the user token through (but that expires).
    # For now, we assume Service Key is present as per recent fixes.
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def process_file(file_id: str, agent_id: str, user_id: str):
    """
    Background task to process an uploaded file for RAG.
    """
    print(f"Processing file {file_id} for agent {agent_id}")
    db = get_db()
    
    try:
        # 1. Fetch File Metadata
        # We use the Service Key client so RLS doesn't block us from selecting by ID freely
        file_record = db.table("files").select("*").eq("id", file_id).execute()
        if not file_record.data:
            print(f"Error: File {file_id} not found in DB")
            return
        
        file_data = file_record.data[0]
        file_path = file_data["file_path"]
        file_type = file_data.get("file_type", "")
        
        # 2. Download File Content from Storage
        bucket_name = "agent-knowledge"
        try:
             # Download returns bytes directly in recent supabase-py or response object
            res = db.storage.from_(bucket_name).download(file_path)
            # res is usually bytes
            file_content = res
        except Exception as e:
            print(f"Error downloading file {file_path}: {e}")
            return

        # 3. Extract Text
        text = ""
        if "pdf" in file_type or file_path.endswith(".pdf"):
            try:
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as e:
                print(f"Error extracting PDF text: {e}")
                return
        else:
            # Assume text/plain or similar
            try:
                text = file_content.decode("utf-8", errors="ignore")
            except Exception as e:
                print(f"Error decoding text file: {e}")
                return

        if not text.strip():
            print("Warning: No text extracted from file.")
            return

        # 4. Chunk Text
        chunks = text_splitter.split_text(text)
        print(f"Generated {len(chunks)} chunks")

        # 5. Generate Embeddings & Prepare for DB
        try:
            # 5a. Fetch Agent's API Key
            agent_record = db.table("agents").select("api_key").eq("id", agent_id).execute()
            if not agent_record.data or not agent_record.data[0].get("api_key"):
                # Fallback to global Groq key, else error
                api_key = settings.GROQ_API_KEY
                if not api_key:
                    print(f"Error: No Groq API Key found for agent {agent_id} and no global key set")
                    return
            else:
                api_key = agent_record.data[0]["api_key"]

            # Use FastEmbed (ONNX, ~150MB, no PyTorch needed)
            embeddings_model = get_embeddings_model()
            
            vectors = embeddings_model.embed_documents(chunks)
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return

        if len(vectors) != len(chunks):
            print("Mismatch between chunks and vectors count")
            return

        # 6. Store in Supabase 'documents' table
        documents_data = []
        for i, chunk in enumerate(chunks):
            documents_data.append({
                "file_id": file_id,
                "content": chunk,
                "metadata": {"chunk_index": i},
                "embedding": vectors[i]
            })
            
        # Insert in batches to avoid payload limits
        batch_size = 50
        for i in range(0, len(documents_data), batch_size):
            batch = documents_data[i:i + batch_size]
            insert_res = db.table("documents").insert(batch).execute()
            if not insert_res.data and not getattr(insert_res, 'count', 0): # Check specific to lib ver
                 # Some versions return empty data on success if representation not requested, but usually returns list
                 pass
                 
        print(f"Successfully processed file {file_id}")

    except Exception as e:
        print(f"Critical error processing file {file_id}: {e}")
