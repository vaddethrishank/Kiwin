# Kiwin Platform Documentation

## 1. Overview
Kiwin is a comprehensive, no-code AI Agent Platform designed to democratize the creation of intelligent assistants. It allows users to build, train, deploy, and embed custom AI agents without writing complex code.

## 2. The Main Motto
> "Each time after creating a website, no need to build a chatbot for everything. One simple snippet can solve it, and it is absolutely free."

Kiwin solves the repetitive pain of building support bots. Instead of coding a new bot for every project, you build it **once** on Kiwin and embed it **anywhere** with a single line of code.

**Owner & Creator:** Vadde Thrishank

---

## 3. Core Philosophy
1. **Simplicity** — Build powerful agents with zero code.
2. **Zero Cost** — The platform is free to use.
3. **One Snippet** — Copy-paste integration for any website.
4. **Performance-First** — Every layer is optimized: caching, streaming, async I/O, background processing.

---

## 4. Key Features

### 4.1 Custom Agent Creation
Users can create multiple agents, each with a unique:
- **Name** — The identity of the bot.
- **Role / Persona** — Defined via a system prompt (e.g., "You are a customer support specialist").
- **Model** — Groq-powered Llama 3.3 70B or other models.

### 4.2 Knowledge Base (Hybrid RAG)
Kiwin uses **Retrieval-Augmented Generation (RAG)** to ground answers in uploaded documents.

**Pipeline:**
1. User uploads a PDF or text file
2. Text is extracted via **PyMuPDF** (handles complex multi-column layouts)
3. Text is chunked using `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap)
4. Each chunk is embedded using **Google Gemini `models/gemini-embedding-2`** (768-dim vectors)
5. Embeddings and full-text are stored in **Supabase (pgvector + tsvector)**
6. At query time, **Hybrid Search** fuses vector similarity and BM25 full-text via **Reciprocal Rank Fusion (RRF)**

### 4.3 Embeddable Widget
Every agent has a unique auto-generated JavaScript snippet:
```html
<script
  src="https://kiwin.app/widget.js"
  data-agent-id="YOUR_AGENT_ID"
  data-color="#000000"
  data-icon-size="60"
  data-api-url="https://your-backend.com"
></script>
```
Customization: widget color, icon size, position.

### 4.4 Real-Time Agentic Tools
Agents can be equipped with executable tools:
- **Web Search** — Tavily API for live internet data
- **Calculator** — precise math without hallucination

### 4.5 True Token Streaming
Responses stream token-by-token using LangChain's `.astream()` directly over HTTP. The UI renders words as they are generated — zero buffering, zero fake streaming.

---

## 5. Optimizations Implemented

### 5.1 ✅ True Streaming (Fixed Fake Streaming)
**Problem:** The original code used `ainvoke()` and then fake-streamed the completed response in chunks. Users waited for the full LLM response before seeing anything.

**Fix:** Replaced with LangChain's native `.astream()` — tokens are yielded to the browser the exact millisecond Groq generates them.

**Impact:** ~10× perceived latency improvement.

---

### 5.2 ✅ Hybrid Search RAG (Vector + BM25 + RRF)
**Problem:** Pure vector search fails on exact keyword queries (e.g., specific IDs, rare names, technical terms).

**Fix:** Implemented a `hybrid_search()` PostgreSQL RPC function combining:
- **Vector leg:** cosine distance via pgvector (`embedding <=> query_vector`)
- **FTS leg:** full-text search via `tsvector` and `plainto_tsquery`
- **RRF fusion:** `1/(60 + rank_v) + 1/(60 + rank_fts)` — best-of-both-worlds ranking

**Impact:** Significantly higher retrieval accuracy on mixed query types.

---

### 5.3 ✅ Non-Blocking Async I/O
**Problem:** Supabase client calls were synchronous inside `async def` functions, blocking the event loop. One user uploading a file would stall chat responses for all other users.

**Fix:** All blocking DB and HTTP calls wrapped in `asyncio.to_thread()`. Independent fetches (agent config, chat history, embedding) run concurrently with `asyncio.gather()`.

**Impact:** Platform stays responsive under concurrent load.

---

### 5.4 ✅ PyMuPDF PDF Extraction
**Problem:** The original `pypdf` parser failed on complex layouts, tables, multi-column PDFs, and embedded fonts — producing garbled or empty text.

**Fix:** Switched to **PyMuPDF (`fitz`)** which preserves reading order, handles ligatures, and correctly extracts from complex documents.

**Impact:** Dramatically higher quality knowledge base content → better RAG answers.

---

### 5.5 ✅ Optimistic UI + SSE Progress Streaming (File Operations)
**Problem:** Uploading or deleting a file froze the UI because the frontend waited for full server-side processing (which includes embedding all chunks — can take 10–60s for large PDFs).

**Fix — Upload:**
- Backend returns the file record **instantly** after storage upload + DB insert
- RAG processing (chunking → embedding → storing) runs in a **FastAPI BackgroundTask**
- A new `GET /api/v1/files/progress/{file_id}` **SSE endpoint** streams live progress events to the browser
- Frontend adds the file to the list **immediately** with a `🔄 Processing…` badge that updates in real-time

**Fix — Delete:**
- Frontend removes the file from the list **instantly** (optimistic update)
- Server-side DB + storage deletion runs in the background
- Rollback to previous state if server reports an error

**SSE progress stages:** `downloading → extracting → chunking → embedding → storing → ✅ ready` (or `❌ error`)

**New files:**
- `backend/app/core/job_store.py` — in-memory `asyncio.Queue` per file for SSE event routing
- `frontend/components/knowledge/file-upload.tsx` — drag-and-drop, optimistic
- `frontend/components/knowledge/file-list.tsx` — live SSE status badges

**Impact:** UI never freezes. Users see instant feedback even for 50MB PDFs.

---

### 5.6 ✅ Redis Semantic Cache + Fast Chat History
**Problem:**
1. Every user message triggered a full pipeline: Gemini embedding + Postgres vector search + Groq LLM call (~2–5 seconds).
2. Chat history loaded from Postgres on every message (~100–300ms DB read).

**Fix — Semantic Cache:**
- After every LLM response, the answer is stored in Redis as a hash containing the **Gemini embedding** + answer text
- On each new message, the incoming query embedding is compared to all cached entries for that agent using **cosine similarity (numpy)**
- If similarity ≥ **0.95** (configurable): return cached answer immediately — **no Groq, no Gemini, no Postgres vector search**
- Cache entries expire after **1 hour** (configurable via `REDIS_CACHE_TTL`)
- Cache is **automatically invalidated** when a new file is uploaded or deleted (knowledge base changed → stale answers cleared)

**Fix — Fast Chat History:**
- Active session history stored in a Redis `LIST` keyed by `(agent_id, user_id)`
- Reads use `LRANGE` (sub-millisecond) instead of a Postgres query
- Cold-start: first access hydrates Redis from Postgres, subsequent reads are pure Redis
- Every new message pair is appended to Redis with `RPUSH` + `LTRIM` (capped at 50 messages, 24hr TTL)
- Postgres remains as **write-through durable cold storage**

**New files:**
- `backend/app/core/redis_client.py` — async Redis singleton with graceful degradation
- `backend/app/services/semantic_cache.py` — cosine similarity cache (get/set/invalidate)
- `backend/app/services/history_cache.py` — Redis-first history with Postgres fallback

**Graceful degradation:** If `REDIS_URL` is not set or Redis is unreachable, all cache operations are silent no-ops. The app falls back to the original Postgres behaviour with zero errors.

**Redis provider:** [Upstash](https://upstash.com) (free tier, cloud-hosted, works in all deployment environments)

**Performance impact:**

| Scenario | Before | After |
|---|---|---|
| Repeated / similar question | 2–5 seconds (full LLM call) | **<10 ms** (Redis cache hit) |
| Chat history load | 100–300 ms (Postgres query) | **<2 ms** (Redis LRANGE) |
| Cache miss (new question) | 2–5 seconds | 2–5 seconds (unchanged) |

---

### 5.7 ✅ Token Bucket Rate Limiting
**Problem:** Public chat widgets could be easily abused, leading to spam and skyrocketing LLM token costs if bad actors sent thousands of messages.

**Fix:** 
- Implemented an atomic **Token Bucket Algorithm** using a custom **Lua script** executed directly in Redis.
- **Public endpoints:** Keyed by `session_id`. Limit of 10 burst messages, refilling at 1 message every 5 seconds. Exceeding this instantly returns `429 Too Many Requests`.
- **Authenticated endpoints:** Keyed by `user_id`. Limit of 20 burst messages, refilling at 1 message every 2 seconds.
- Fails gracefully: If Redis is unreachable, the rate limiting is bypassed to ensure maximum availability.

**Impact:** Robust protection against abuse with zero runtime overhead on the web server (O(1) Redis execution).

---

### 5.8 ✅ Fire-and-Forget Database Writes
**Problem:** During chat generation, writing the user message and the final LLM response to Postgres synchronously caused slight delays before the stream started, or delayed the closing of the HTTP connection.

**Fix:** 
- Moved database writes (`_persist_user_message` and `_persist_ai_message`) into background tasks using `asyncio.create_task()`.
- Within those tasks, blocking Supabase operations are offloaded using `asyncio.to_thread()`.

**Impact:** LLM streaming begins instantly and finishes cleanly, completely decoupled from Postgres I/O latency.

---

## 6. Security & Data Privacy
- **Data Isolation** — Strict Row-Level Security (RLS) on all Supabase tables. Users only access their own agents, files, and messages.
- **Admin Client** — Backend uses `SUPABASE_SERVICE_ROLE_KEY` for storage operations that require bypassing RLS (with manual ownership checks in code).
- **JWT Auth** — All API endpoints protected via Supabase JWT tokens.
- **SSE Auth** — SSE progress endpoints accept token via query param (since `EventSource` cannot set custom headers) and validate against Supabase directly.

---

## 7. Technical Architecture

```
User Message
     │
     ▼
① Embed query (Gemini 768-dim)
     │
     ▼
② Redis Semantic Cache check (cosine sim ≥ 0.95)
     │
   HIT → Return cached answer (<10ms) ✅
     │
   MISS
     │
     ▼
③ asyncio.gather [parallel]:
   ├─ Fetch agent config (Supabase)
   └─ Fetch history (Redis LRANGE → Postgres fallback)
     │
     ▼
④ hybrid_search() PostgreSQL RPC
   ├─ Vector:  embedding <=> query_vector
   ├─ FTS:     tsvector @@ plainto_tsquery
   └─ RRF:     1/(60+rank_v) + 1/(60+rank_fts)
     │
     ▼
⑤ Build prompt: system + RAG context + history + user message
     │
     ▼
⑥ Groq LLM → .astream() → token-by-token to browser
     │
     ▼
⑦ Background tasks (non-blocking):
   ├─ Store in Redis semantic cache (with embedding)
   ├─ Append to Redis history list (RPUSH + LTRIM)
   └─ Write-through to Postgres (durable storage)
```

---

## 8. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Service role key for backend admin operations |
| `GROQ_API_KEY` | ✅ | Groq LLM API key |
| `GEMINI_API_KEY` | ✅ | Google Gemini embedding API key |
| `REDIS_URL` | ⭐ Recommended | Upstash Redis URL (`rediss://default:...`) |
| `REDIS_SEMANTIC_CACHE_THRESHOLD` | Optional | Cache similarity threshold (default `0.95`) |
| `REDIS_CACHE_TTL` | Optional | Answer cache lifetime in seconds (default `3600`) |
| `TAVILY_API_KEY` | Optional | Enables Web Search tool |

---

## 9. Contact & Support
For inquiries, reach out via the Contact form on the website or contact **Vadde Thrishank** at [thrishank2005@gmail.com](mailto:thrishank2005@gmail.com).