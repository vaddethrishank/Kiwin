import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Agent Platform"
    API_V1_STR: str = "/api/v1"
    
    # Supabase (Get these from your Supabase Dashboard)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Google Gemini
    GOOGLE_API_KEY: str | None = None
    
    # Optional: Service Role Key for backend administration (bypasses RLS)
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # Tools
    TAVILY_API_KEY: str | None = None
    
    class Config:
        env_file = ".env"

settings = Settings()
