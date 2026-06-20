from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import users, agents, files, chat, public


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    On startup: eagerly checks Redis connectivity and logs clear status.
    On shutdown: closes the Redis connection pool cleanly.
    """
    # ── Startup ────────────────────────────────────────────────────────────
    from app.core.redis_client import redis_available, get_redis
    ok = await redis_available()
    if ok:
        print("=" * 60)
        print("✅  Redis connected — Semantic cache + fast history ACTIVE")
        print(f"    Threshold : {settings.REDIS_SEMANTIC_CACHE_THRESHOLD * 100:.0f}% similarity")
        print(f"    Cache TTL : {settings.REDIS_CACHE_TTL}s ({settings.REDIS_CACHE_TTL // 3600}h)")
        print("=" * 60)
    else:
        print("=" * 60)
        if settings.REDIS_URL:
            print("⚠️   Redis UNREACHABLE — falling back to Postgres only")
            print(f"    URL tried : {settings.REDIS_URL[:40]}...")
        else:
            print("ℹ️   Redis not configured (REDIS_URL not set)")
            print("    Add REDIS_URL to .env to enable semantic caching")
        print("=" * 60)

    yield   # ← server runs here

    # ── Shutdown ───────────────────────────────────────────────────────────
    r = get_redis()
    if r:
        await r.aclose()
        print("Redis connection closed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    # allow_origins=[origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",")],
    allow_origin_regex=".*", # Allow ALL origins (easiest for public widgets)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}/files", tags=["files"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(public.router, prefix=f"{settings.API_V1_STR}/public", tags=["public"])

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Agent Platform API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
