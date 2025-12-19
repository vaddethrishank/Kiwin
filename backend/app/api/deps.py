from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase.client import Client

from app.db.supabase import supabase

security = HTTPBearer()

async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    token = credentials.credentials
    try:
        # Verify user by calling Supabase Auth API
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_response.user
    except Exception as e:
        print(f"Auth Error: {e}")
        # DEBUG: Print details (remove in prod)
        print(f"DEBUG: Token prefix: {token[:10]}...")
        from app.core.config import settings
        print(f"DEBUG: Backend Supabase URL: {settings.SUPABASE_URL}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials. Error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
