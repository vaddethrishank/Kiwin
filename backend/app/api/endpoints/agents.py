from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from typing import List
from supabase import create_client
from app.api import deps
from app.schemas.agent import Agent, AgentCreate, AgentUpdate
from app.core.config import settings

router = APIRouter()

def get_db(token: str):
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    client.postgrest.auth(token)
    return client

@router.post("/", response_model=Agent)
def create_agent(
    agent_in: AgentCreate,
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Create a new agent.
    """
    db = get_db(auth.credentials)
    agent_data = agent_in.model_dump()
    agent_data["user_id"] = current_user.id
    
    result = db.table("agents").insert(agent_data).execute()
    
    if not result.data:
        raise HTTPException(status_code=400, detail="Error creating agent")
    
    return result.data[0]

@router.get("/", response_model=List[Agent])
def read_agents(
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Retrieve agents belonging to the current user.
    """
    db = get_db(auth.credentials)
    result = db.table("agents").select("*").eq("user_id", current_user.id).execute()
    return result.data

@router.get("/{agent_id}", response_model=Agent)
def read_agent(
    agent_id: str,
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Get a specific agent by ID.
    """
    db = get_db(auth.credentials)
    result = db.table("agents").select("*").eq("id", agent_id).eq("user_id", current_user.id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    return result.data[0]

@router.put("/{agent_id}", response_model=Agent)
def update_agent(
    agent_id: str,
    agent_in: AgentUpdate,
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Update an agent.
    """
    db = get_db(auth.credentials)
    # Exclude fields that were not set (None)
    update_data = agent_in.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    result = db.table("agents").update(update_data).eq("id", agent_id).eq("user_id", current_user.id).execute()

    if not result.data:
         raise HTTPException(status_code=404, detail="Agent not found or creation failed")
         
    return result.data[0]

@router.delete("/{agent_id}", response_model=dict)
def delete_agent(
    agent_id: str,
    current_user = Depends(deps.get_current_user),
    auth: HTTPAuthorizationCredentials = Depends(deps.security)
):
    """
    Delete an agent.
    """
    db = get_db(auth.credentials)
    result = db.table("agents").delete().eq("id", agent_id).eq("user_id", current_user.id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    return {"status": "success", "id": agent_id}
