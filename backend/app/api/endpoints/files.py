from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from typing import List, Optional
from supabase import create_client, Client
from app.api import deps
from app.core.config import settings
from app.services.rag import process_file
from pydantic import BaseModel
import uuid
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
    # CRITICAL FIX: Pass token in headers directly so Storage client picks it up
    headers = {"Authorization": f"Bearer {token}"}
    from supabase.lib.client_options import ClientOptions
    
    # Depending on supabase-py version, checking if options is accepted like this
    # If ClientOptions is hard to import, we can pass a dict if the lib allows, 
    # but create_client signature is create_client(url, key, options=None)
    
    # Let's try to set it after creation if import is risky, 
    # but defining headers at init is safest.
    # Safe approach without importing internal class if possible:
    # Most versions allow options={'headers': ...} or similar via ClientOptions
    
    # We will try imports at top level or here if needed.
    # To avoid import errors if ClientOptions moved, let's use a simpler way if possible.
    # Actually, client.storage.session.headers might be accessible.
    
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
    """
    # Use Admin client for upload to ensure we can write to storage regardless of tricky RLS
    db = get_db(auth.credentials)
    
    # 1. Verify Agent ownership (Always verify ownership manually if using Admin client!)
    # We use a user-scoped query or just check manually.
    # Since 'db' might be admin, we must be careful.
    
    # Let's verify using a standard user query first to be safe about permissions
    user_db = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    user_db.postgrest.auth(auth.credentials)
    
    agent_res = user_db.table("agents").select("id").eq("id", agent_id).eq("user_id", current_user.id).execute()
    if not agent_res.data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 2. Upload to Supabase Storage
    file_content = await file.read()
    timestamp = int(datetime.utcnow().timestamp())
    # Path: user_id/agent_id/timestamp_filename
    file_path = f"{current_user.id}/{agent_id}/{timestamp}_{file.filename}"
    bucket_name = "agent-knowledge"

    try:
        # Use 'db' (potentially Admin) for storage operations
        res = db.storage.from_(bucket_name).upload(
            file_path, 
            file_content,
            {"content-type": file.content_type, "upsert": "true"} 
        )
    except Exception as e:
        print(f"Storage Upload Error: {e}")
        # Print detailed traceback or error dict if possible
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

    # Use 'db' (Admin) or 'user_db'? 
    # If we used Admin for storage, we should probably stick to it or consistency, 
    # but 'files' table usually has RLS.
    # If we use Admin, we bypass RLS on 'files' table too.
    result = db.table("files").insert(file_data).execute()

    if not result.data:
         raise HTTPException(status_code=500, detail="Failed to save file metadata")
         
    # 4. Trigger Background RAG Processing
    file_id = result.data[0]['id']
    background_tasks.add_task(process_file, file_id, agent_id, current_user.id)

    return result.data[0]

@router.get("/", response_model=List[FileResponse])
def list_files(
    agent_id: str,
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    List files for a specific agent.
    """
    # For reading, standard RLS is usually fine and safer.
    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    db.postgrest.auth(auth.credentials)
    
    result = db.table("files").select("*").eq("agent_id", agent_id).eq("user_id", current_user.id).execute()
    return result.data

@router.delete("/{file_id}", response_model=dict)
def delete_file(
    file_id: str,
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Delete a file.
    """
    # Use Admin for deletion to ensure cleanup works
    db = get_db(auth.credentials)
    user_db = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    user_db.postgrest.auth(auth.credentials)

    # 1. Get file path (Verify ownership via user_db first)
    file_record = user_db.table("files").select("*").eq("id", file_id).eq("user_id", current_user.id).execute()
    
    if not file_record.data:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = file_record.data[0]["file_path"]
    bucket_name = "agent-knowledge"

    # 2. Delete from DB (Admin)
    del_result = db.table("files").delete().eq("id", file_id).execute()

    # 3. Delete from Storage (Admin)
    try:
        db.storage.from_(bucket_name).remove([file_path])
    except Exception as e:
        print(f"Failed to delete file from storage: {e}")
    
    return {"status": "success", "id": file_id}
