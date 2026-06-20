from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from typing import List, Optional, AsyncGenerator
from supabase import create_client, Client
from app.api import deps
from app.core.config import settings
from app.core.job_store import job_store
from app.services.rag import process_file
from app.db.supabase import supabase as admin_supabase
from pydantic import BaseModel
import uuid
import asyncio
from datetime import datetime

router = APIRouter()

def get_db(token: str) -> Client:
    """
    Returns a Supabase client.
    If SUPABASE_SERVICE_ROLE_KEY is set, returns a client with admin privileges (bypassing RLS).
    Otherwise, returns a client authenticated with the user's token (enforcing RLS).
    """
    if settings.SUPABASE_SERVICE_ROLE_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
    # Fallback to user token (Subject to RLS)
    headers = {"Authorization": f"Bearer {token}"}
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    client.postgrest.auth(token)
    
    # Force update storage headers
    if hasattr(client, 'storage'):
        client.storage.session.headers.update(headers)
        
    return client

class FileResponse(BaseModel):
    id: str
    agent_id: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: str

# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD  — returns instantly; RAG processing runs in background
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=FileResponse)
async def upload_file(
    agent_id: str = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Upload a file to the agent's knowledge base.
    Returns immediately after storing the file — RAG processing happens in the background.
    Track progress via GET /progress/{file_id}.
    """
    db = get_db(auth.credentials)

    # 1. Verify Agent ownership
    user_db = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    user_db.postgrest.auth(auth.credentials)
    
    agent_res = user_db.table("agents").select("id").eq("id", agent_id).eq("user_id", current_user.id).execute()
    if not agent_res.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 2. Upload to Supabase Storage
    file_content = await file.read()
    timestamp = int(datetime.utcnow().timestamp())
    file_path = f"{current_user.id}/{agent_id}/{timestamp}_{file.filename}"
    bucket_name = "agent-knowledge"

    try:
        res = db.storage.from_(bucket_name).upload(
            file_path, 
            file_content,
            {"content-type": file.content_type, "upsert": "true"} 
        )
    except Exception as e:
        print(f"Storage Upload Error: {e}")
        if hasattr(e, 'message'):
             print(f"Error Message: {e.message}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # 3. Store Metadata in DB
    file_data = {
        "user_id": current_user.id,
        "agent_id": agent_id,
        "file_name": file.filename,
        "file_path": file_path,
        "file_type": file.content_type,
        "file_size": len(file_content)
    }

    result = db.table("files").insert(file_data).execute()

    if not result.data:
         raise HTTPException(status_code=500, detail="Failed to save file metadata")
         
    # 4. Register job + fire background RAG processing
    file_id = result.data[0]['id']
    job_store.register(file_id)                                          # creates SSE queue
    background_tasks.add_task(process_file, file_id, agent_id, current_user.id)

    # Return immediately — UI updates optimistically, tracks progress via SSE
    return result.data[0]


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[FileResponse])
def list_files(
    agent_id: str,
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    List files for a specific agent.
    """
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    db.postgrest.auth(auth.credentials)
    
    result = db.table("files").select("*").eq("agent_id", agent_id).eq("user_id", current_user.id).execute()
    return result.data


# ─────────────────────────────────────────────────────────────────────────────
# DELETE  — returns instantly; actual deletion runs in background
# ─────────────────────────────────────────────────────────────────────────────

async def _delete_file_background(file_id: str, file_path: str, token: str):
    """Background coroutine that deletes the file from DB + storage."""
    db = get_db(token)
    bucket_name = "agent-knowledge"

    try:
        db.table("files").delete().eq("id", file_id).execute()
    except Exception as e:
        print(f"[DELETE] DB deletion failed for {file_id}: {e}")

    try:
        db.storage.from_(bucket_name).remove([file_path])
    except Exception as e:
        print(f"[DELETE] Storage deletion failed for {file_id}: {e}")


@router.delete("/{file_id}", response_model=dict)
def delete_file(
    file_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Delete a file. Returns instantly — actual DB + storage cleanup runs in background.
    The frontend should remove the file from the UI immediately (optimistic update).
    """
    user_db = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    user_db.postgrest.auth(auth.credentials)

    # Verify ownership synchronously (fast — just a DB read)
    file_record = user_db.table("files").select("file_path").eq("id", file_id).eq("user_id", current_user.id).execute()
    
    if not file_record.data:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = file_record.data[0]["file_path"]

    # Fire-and-forget: actual deletion runs in background
    background_tasks.add_task(_delete_file_background, file_id, file_path, auth.credentials)

    # Respond instantly so the UI can remove the item without waiting
    return {"status": "success", "id": file_id}


# ─────────────────────────────────────────────────────────────────────────────
# STATUS  — quick poll endpoint (optional fallback)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status/{file_id}", response_model=dict)
def get_file_status(
    file_id: str,
    current_user = Depends(deps.get_current_user),
):
    """
    Returns the current RAG processing status for a file.
    Statuses: pending | processing | ready | error
    """
    status = job_store.get_status(file_id)
    if status is None:
        # Not in memory — assume already complete (server restarted or old file)
        return {"file_id": file_id, "status": "ready", "error": None}

    return {
        "file_id": file_id,
        "status": status,
        "error": job_store.get_error(file_id) if status == "error" else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SSE PROGRESS STREAM  — real-time events for the Knowledge Base UI
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/progress/{file_id}")
async def stream_file_progress(
    file_id: str,
    token: str = Query(..., description="Bearer token (EventSource cannot set headers)"),
):
    """
    SSE endpoint — streams RAG processing progress events for a given file.
    Accepts the auth token as a query parameter because the browser's native
    EventSource API does not support custom request headers.

    Events emitted by rag.process_file():
      event: progress  data: downloading | extracting | chunking | embedding | storing
      event: complete  data: ready
      event: error     data: <error message>

    The connection closes automatically once 'complete' or 'error' is received.
    """
    # Validate token manually (EventSource can't send Authorization header)
    try:
        user_response = admin_supabase.auth.get_user(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not validate token: {e}")
    if not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid token")

    async def event_generator() -> AsyncGenerator[str, None]:
        # Yield an initial ping so the browser connection is established
        yield ": ping\n\n"

        queue = job_store.get_queue(file_id)

        if queue is None:
            # Job not found / already done — check final status
            current_status = job_store.get_status(file_id)
            if current_status == "error":
                yield f"event: error\ndata: {job_store.get_error(file_id)}\n\n"
            else:
                # Not in store at all = old file, already processed
                yield "event: complete\ndata: ready\n\n"
            return

        # Stream events until complete or error
        while True:
            try:
                # Poll every 200 ms so we don't block forever if queue is empty
                event_str = await asyncio.wait_for(queue.get(), timeout=0.2)
                yield event_str

                # Stop streaming once a terminal event is received
                if event_str.startswith("event: complete") or event_str.startswith("event: error"):
                    break

            except asyncio.TimeoutError:
                # Keep-alive comment to prevent proxy/browser connection timeout
                yield ": keep-alive\n\n"

                # Edge case: job finished but queue entry was already consumed
                status = job_store.get_status(file_id)
                if status in ("ready", "error"):
                    if status == "ready":
                        yield "event: complete\ndata: ready\n\n"
                    else:
                        yield f"event: error\ndata: {job_store.get_error(file_id)}\n\n"
                    break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # Disable Nginx buffering
            "Connection": "keep-alive",
        },
    )
