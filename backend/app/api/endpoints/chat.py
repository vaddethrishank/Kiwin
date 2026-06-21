from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from app.api import deps
from app.services.chat_service import generate_response
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    agent_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("/")
async def chat_with_agent(
    request: ChatRequest,
    current_user = Depends(deps.get_current_user)
):
    """
    Chat with an agent securely (Streaming).
    """
    from app.core.rate_limit import check_rate_limit
    
    # 1. Apply Rate Limiting based on authenticated user_id
    # Limits to 20 requests burst, refills 1 request every 2 seconds
    await check_rate_limit(f"ratelimit:user:{current_user.id}", capacity=20, refill_rate=0.5)

    return StreamingResponse(
        generate_response(
            agent_id=request.agent_id,
            message=request.message,
            user_id=current_user.id
        ),
        media_type="text/plain",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        }
    )

@router.get("/{agent_id}")
async def get_history(
    agent_id: str,
    current_user = Depends(deps.get_current_user)
):
    """
    Get chat history for an agent.
    """
    from app.services.chat_service import get_chat_history
    return await get_chat_history(agent_id, current_user.id)
