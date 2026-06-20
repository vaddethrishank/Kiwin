import io
import asyncio
import fitz  # PyMuPDF
import requests
from typing import List
from supabase import create_client, Client
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.job_store import job_store

# ---------------------------------------------------------------------------
# Google Gemini AI Embeddings — 768-dim
# Model: text-embedding-004 → 768-dim (matches Supabase vector column)
# ---------------------------------------------------------------------------

def _gemini_embed_sync(texts: List[str]) -> List[List[float]]:
    """Call Google Gemini embeddings API and return a list of 768-dim vectors."""
    if not texts:
        return []
    
    requests_payload = [
        {
            "model": "models/gemini-embedding-2", 
            "content": {"parts": [{"text": t}]},
            "outputDimensionality": 768
        }
        for t in texts
    ]
    
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={settings.GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={"requests": requests_payload},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return [item["values"] for item in data.get("embeddings", [])]

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
    # Batch the requests to Gemini API to prevent timeouts and payload limits
    batch_size = 20
    all_vectors = []
    print(f"[INGEST] Sending {len(chunks)} chunks to Gemini API in batches of {batch_size}...")
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"[INGEST]  -> Sending Gemini batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
        all_vectors.extend(_gemini_embed_sync(batch))
    print(f"[INGEST] Successfully embedded all {len(chunks)} chunks.")
    return all_vectors

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
    Progress events are emitted via job_store so the SSE endpoint can stream
    them to the browser in real-time.
    """
    print(f"Processing file {file_id} for agent {agent_id}")
    db = get_db()

    async def _fail(msg: str) -> None:
        """Emit error event and mark job failed."""
        print(f"[RAG ERROR] {file_id}: {msg}")
        job_store.set_status(file_id, "error", error=msg)
        await job_store.emit(file_id, "error", msg)

    try:
        job_store.set_status(file_id, "processing")
        await job_store.emit(file_id, "progress", "downloading")

        # ── 1. Fetch file metadata ─────────────────────────────────────────
        file_record = await asyncio.to_thread(_fetch_file_record_sync, db, file_id)
        if not file_record.data:
            await _fail("File not found in DB")
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
            await _fail(f"Download failed: {e}")
            return

        # Resolve API key
        if not agent_record.data or not agent_record.data[0].get("api_key"):
            api_key = settings.GROQ_API_KEY
            if not api_key:
                await _fail(f"No API Key found for agent {agent_id}")
                return
        else:
            api_key = agent_record.data[0]["api_key"]

        # ── 3. Extract text (CPU-bound — run in thread) ────────────────────
        await job_store.emit(file_id, "progress", "extracting")
        text = ""
        if "pdf" in file_type or file_path.endswith(".pdf"):
            try:
                text = await asyncio.to_thread(_extract_pdf_text_sync, file_content)
            except Exception as e:
                await _fail(f"PDF extraction failed: {e}")
                return
        else:
            try:
                text = file_content.decode("utf-8", errors="ignore")
            except Exception as e:
                await _fail(f"Text decode failed: {e}")
                return

        if not text.strip():
            await _fail("No text extracted from file")
            return

        # ── 4. Chunk text (CPU-bound — run in thread) ──────────────────────
        await job_store.emit(file_id, "progress", "chunking")
        chunks = await asyncio.to_thread(text_splitter.split_text, text)
        print(f"Generated {len(chunks)} chunks")

        # ── 5. Embed all chunks — offload blocking HTTP call ───────────────
        await job_store.emit(file_id, "progress", "embedding")
        try:
            vectors = await asyncio.to_thread(_embed_documents_sync, chunks)
        except Exception as e:
            await _fail(f"Embedding failed: {e}")
            return

        if len(vectors) != len(chunks):
            await _fail("Mismatch between chunks and vectors count")
            return

        # ── 6. Store in Supabase 'documents' — batched, each in a thread ──
        await job_store.emit(file_id, "progress", "storing")
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
        print(f"[INGEST] Starting DB insertion of {len(documents_data)} chunks in batches of {batch_size}...")
        for i in range(0, len(documents_data), batch_size):
            batch = documents_data[i:i + batch_size]
            print(f"[INGEST]  -> Inserting DB batch {i//batch_size + 1}/{(len(documents_data)-1)//batch_size + 1}")
            await asyncio.to_thread(_insert_documents_batch_sync, db, batch)

        # ── 7. Done ────────────────────────────────────────────────────────
        job_store.set_status(file_id, "ready")
        await job_store.emit(file_id, "complete", "ready")
        print(f"Successfully processed file {file_id}")

    except Exception as e:
        await _fail(f"Critical error: {e}")
        print(f"Critical error processing file {file_id}: {e}")
