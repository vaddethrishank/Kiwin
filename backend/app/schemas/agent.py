from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# Shared properties
class AgentBase(BaseModel):
    name: str
    role: str = "assistant"
    description: Optional[str] = None
    model: str = "llama-3.3-70b-versatile"
    system_prompt: Optional[str] = None
    tools: List[str] = []
    api_key: Optional[str] = None

# Properties to receive on creation
class AgentCreate(AgentBase):
    api_key: str

# Properties to receive on update
class AgentUpdate(AgentBase):
    name: Optional[str] = None
    role: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    api_key: Optional[str] = None

# Properties shared by models stored in DB
class AgentInDBBase(AgentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Properties to return to client
class Agent(AgentInDBBase):
    pass
