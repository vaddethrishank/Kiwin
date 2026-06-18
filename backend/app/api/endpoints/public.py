from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from app.services.chat_service import generate_response
from pydantic import BaseModel
import uuid

router = APIRouter()

class PublicChatRequest(BaseModel):
    agent_id: str
    message: str
    session_id: str

@router.post("/chat")
async def public_chat(request: PublicChatRequest):
    """
    Public chat endpoint for the widget.
    Uses session_id as the user_id for history tracking.
    """
    # Verify agent exists (optional, generate_response handles it)
    
    return StreamingResponse(
        generate_response(
            agent_id=request.agent_id,
            message=request.message,
            user_id=request.session_id,
            is_public=True
        ),
        media_type="text/plain",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        }
    )
@router.get("/agents/{agent_id}")
async def get_public_agent_details(agent_id: str):
    """
    Fetch public details of an agent for the widget.
    """
    from app.services.chat_service import get_db
    try:
        db = get_db()
        # Only select public-facing fields
        res = db.table("agents").select("name, role, description").eq("id", agent_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Agent not found")
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
