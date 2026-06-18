import io
import asyncio
import fitz  # PyMuPDF
from typing import List
from supabase import create_client, Client
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from app.core.config import settings

# HuggingFace Inference API - pure HTTP calls, NO local model, zero extra RAM
# Model: BAAI/bge-base-en-v1.5 → 768-dim (matches Supabase vector column)
_embeddings_model = None

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = HuggingFaceInferenceAPIEmbeddings(
            api_key=settings.HF_TOKEN or "",
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
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# ---------------------------------------------------------------------------
# Sync helpers — each runs in asyncio.to_thread to keep the event loop free.
# ---------------------------------------------------------------------------

def _fetch_file_record_sync(db: Client, file_id: str):
    return db.table("files").select("*").eq("id", file_id).execute()

def _fetch_agent_key_sync(db: Client, agent_id: str):
    return db.table("agents").select("api_key").eq("id", agent_id).execute()

def _download_file_sync(db: Client, bucket: str, file_path: str):
    return db.storage.from_(bucket).download(file_path)

def _embed_documents_sync(chunks: List[str]) -> List[List[float]]:
    return get_embeddings_model().embed_documents(chunks)

def _extract_pdf_text_sync(file_content: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF.
    
    PyMuPDF preserves reading order and handles complex layouts
    (multi-column, embedded fonts, rotated text) that pypdf struggles with.
    """
    doc = fitz.open(stream=file_content, filetype="pdf")
    pages_text = []
    for page in doc:
        # get_text("text") respects reading order and handles ligatures
        pages_text.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages_text)

def _insert_documents_batch_sync(db: Client, batch: list):
    return db.table("documents").insert(batch).execute()

# ---------------------------------------------------------------------------

async def process_file(file_id: str, agent_id: str, user_id: str):
    """
    Background task to process an uploaded file for RAG.
    All blocking I/O is offloaded to a thread pool so the event loop stays free.
    """
    print(f"Processing file {file_id} for agent {agent_id}")
    db = get_db()

    try:
        # ── 1. Fetch file metadata ─────────────────────────────────────────
        file_record = await asyncio.to_thread(_fetch_file_record_sync, db, file_id)
        if not file_record.data:
            print(f"Error: File {file_id} not found in DB")
            return

        file_data = file_record.data[0]
        file_path = file_data["file_path"]
        file_type = file_data.get("file_type", "")
        bucket_name = "agent-knowledge"

        # ── 2. Download file + fetch agent key — IN PARALLEL ──────────────
        try:
            download_task = asyncio.to_thread(_download_file_sync, db, bucket_name, file_path)
            agent_key_task = asyncio.to_thread(_fetch_agent_key_sync, db, agent_id)
            file_content, agent_record = await asyncio.gather(download_task, agent_key_task)
        except Exception as e:
            print(f"Error downloading file {file_path}: {e}")
            return

        # Resolve API key
        if not agent_record.data or not agent_record.data[0].get("api_key"):
            api_key = settings.GROQ_API_KEY
            if not api_key:
                print(f"Error: No API Key found for agent {agent_id}")
                return
        else:
            api_key = agent_record.data[0]["api_key"]

        # ── 3. Extract text (CPU-bound — run in thread) ────────────────────
        text = ""
        if "pdf" in file_type or file_path.endswith(".pdf"):
            try:
                text = await asyncio.to_thread(_extract_pdf_text_sync, file_content)
            except Exception as e:
                print(f"Error extracting PDF text: {e}")
                return
        else:
            try:
                text = file_content.decode("utf-8", errors="ignore")
            except Exception as e:
                print(f"Error decoding text file: {e}")
                return

        if not text.strip():
            print("Warning: No text extracted from file.")
            return

        # ── 4. Chunk text (CPU-bound — run in thread) ──────────────────────
        chunks = await asyncio.to_thread(text_splitter.split_text, text)
        print(f"Generated {len(chunks)} chunks")

        # ── 5. Embed all chunks — offload blocking HTTP call ───────────────
        try:
            vectors = await asyncio.to_thread(_embed_documents_sync, chunks)
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return

        if len(vectors) != len(chunks):
            print("Mismatch between chunks and vectors count")
            return

        # ── 6. Store in Supabase 'documents' — batched, each in a thread ──
        documents_data = [
            {
                "file_id": file_id,
                "content": chunk,
                "metadata": {"chunk_index": i},
                "embedding": vectors[i]
            }
            for i, chunk in enumerate(chunks)
        ]

        batch_size = 50
        # Fire all batch inserts concurrently
        insert_tasks = [
            asyncio.to_thread(_insert_documents_batch_sync, db, documents_data[i:i + batch_size])
            for i in range(0, len(documents_data), batch_size)
        ]
        await asyncio.gather(*insert_tasks)

        print(f"Successfully processed file {file_id}")

    except Exception as e:
        print(f"Critical error processing file {file_id}: {e}")
