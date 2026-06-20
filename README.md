# 🥝 Kiwin - AI Agent Platform

> **"Each time after creating a website, no need to build a chatbot for everything. One simple snippet can solve it, and it is absolutely free."**

![Project Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Tech Stack](https://img.shields.io/badge/Stack-Next.js%20%7C%20FastAPI%20%7C%20Supabase%20%7C%20Redis-orange)

## 🚀 Overview

**Kiwin** is a powerful, no-code AI platform that democratizes the creation of intelligent assistants. Build, train, and deploy a custom AI agent in minutes — then embed it into any website with a single line of code.

**Created by: Vadde Thrishank**

---

## ✨ Features

### 🤖 Intelligent Agents
Create custom personas with unique roles. Whether it's a **customer support bot**, a **travel guide**, or a **coding assistant**, Kiwin's agents are powered by **Groq's ultra-fast LLMs** like **Llama 3.3 70B** — completely free.

### 🧠 Knowledge Base (Hybrid RAG)
Don't just chat — **learn**. Upload your PDF documents and your agent will answer questions based specifically on *your* data using a **Hybrid Search** pipeline:

- **Vector Search** — dense semantic embeddings via `Google Gemini (models/gemini-embedding-2)`
- **BM25 Full-Text Search** — exact keyword matching via PostgreSQL `tsvector`
- **Reciprocal Rank Fusion (RRF)** — fuses both result lists for best-of-both-worlds accuracy

PDF text extraction is powered by **PyMuPDF** for accurate multi-column and complex layout handling.

### ⚡ True Token Streaming
Responses are streamed token-by-token the **exact millisecond** Groq generates them using LangChain's native `.astream()`. The UI feels instant — no waiting for the full response.

### 🚀 Redis Semantic Cache
Repeated or semantically similar questions are answered in **<10ms** from Redis cache — bypassing Groq, Gemini, and Postgres entirely:
- **Semantic similarity** via cosine distance on Gemini embeddings (configurable threshold, default 95%)
- **Fast chat history** — active session history stored in Redis (`LRANGE <1ms`); Postgres is cold storage only
- **Smart invalidation** — cache cleared automatically when the knowledge base changes

### 🔌 Embed Anywhere
Build once, deploy everywhere.
```html
<script 
  src="https://kiwin.app/widget.js" 
  data-agent-id="YOUR_AGENT_ID"
></script>
```
Simply copy-paste this snippet into any website to instantly add your trained chatbot.

### 🛠️ Real-Time Tools
Equip your agents with live functionality:
- **Web Search** — fetch live data from the internet via Tavily
- **Calculator** — perform complex math on the fly

### 📄 Non-Blocking File Processing
Uploading or deleting knowledge base files never freezes the UI:
- File appears in the list **instantly** with a live progress badge
- RAG processing (chunk → embed → store) runs entirely in the background
- Real-time status updates stream to the browser via **Server-Sent Events (SSE)**: `Downloading → Extracting → Chunking → Embedding → Storing → ✅ Ready`

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/-Next.js-black?style=flat&logo=next.js) | React framework with streaming SSE support |
| **Backend** | ![FastAPI](https://img.shields.io/badge/-FastAPI-005571?style=flat&logo=fastapi) | Async Python API — full non-blocking I/O |
| **Database** | ![Supabase](https://img.shields.io/badge/-Supabase-3ECF8E?style=flat&logo=supabase) | PostgreSQL + pgvector + full-text search |
| **Cache** | ![Redis](https://img.shields.io/badge/-Redis-DC382D?style=flat&logo=redis) | Semantic response cache + hot session history |
| **AI Model** | ![Groq](https://img.shields.io/badge/-Groq-F55036?style=flat&logo=groq) | Ultra-fast Llama 3.3 70B inference |
| **Embeddings** | ![Google Gemini](https://img.shields.io/badge/-Google%20Gemini-8E75B2?style=flat&logo=googlegemini) | models/gemini-embedding-2 via Google Generative AI API |
| **PDF Parsing** | PyMuPDF | High-fidelity text extraction from complex PDFs |

---

## 🏗️ Architecture

```
User Message
    │
    ├─ Embed query → Gemini (768-dim)
    │
    ├─ Redis Semantic Cache check (cosine similarity ≥ 0.95)
    │   └─ HIT → return cached answer instantly (<10ms) ✅
    │
    └─ MISS — full pipeline:
        ├─ asyncio.gather ──────────────────────────────────────┐
        │   ├─ Fetch Agent config (Supabase)                    │
        │   └─ Fetch Chat History (Redis → Postgres fallback)   │
        │                                                       │
        ├─ hybrid_search() — PostgreSQL RPC                     │
        │   ├─ Vector leg:  embedding <=> query_vector (ranked) │
        │   ├─ FTS leg:     fts @@ plainto_tsquery  (ranked)    │
        │   └─ RRF fusion:  1/(60+rank_v) + 1/(60+rank_fts)    │
        │                                                       │
        ├─ Build system prompt + context + history              │
        │                                                       │
        ├─ LLM (Groq) → .astream() → token-by-token to browser │
        │                                                       │
        └─ Background tasks (non-blocking):                     │
            ├─ Store answer in Redis semantic cache             │
            ├─ Append messages to Redis history list            │
            └─ Write-through to Postgres (durable storage)      │
```

---

## 🏁 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Supabase account
- [Groq API Key](https://console.groq.com) (free)
- [Gemini API Key](https://aistudio.google.com/app/apikey) (free)
- [Upstash Redis](https://upstash.com) account (free tier — for caching)

### 1. Clone the Repository
```bash
git clone https://github.com/vaddethrishank/kiwin.git
cd kiwin
```

### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY, GEMINI_API_KEY
# Optional: REDIS_URL (from Upstash) for semantic caching
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Database Migration
Run the master schema file once in your **Supabase Dashboard → SQL Editor**:
```bash
# File: backend/complete_schema.sql
```
This sets up all tables, storage, vectors, and the `hybrid_search()` PostgreSQL function.

### 5. Redis Setup (Optional — Recommended)
1. Create a free database at [upstash.com](https://upstash.com)
2. Copy the **Redis URL** (format: `rediss://default:PASSWORD@HOST:PORT`)
3. Add to `backend/.env`:
```env
REDIS_URL=rediss://default:YOUR_PASSWORD@YOUR_HOST.upstash.io:PORT
```
Without this, the app works normally — caching is simply skipped.

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Service role key (bypasses RLS for backend) |
| `GROQ_API_KEY` | ✅ | Groq LLM inference key |
| `GEMINI_API_KEY` | ✅ | Google Gemini embedding key |
| `REDIS_URL` | ⭐ Optional | Upstash Redis URL for semantic cache + fast history |
| `REDIS_SEMANTIC_CACHE_THRESHOLD` | ⭐ Optional | Similarity threshold for cache hits (default: `0.95`) |
| `REDIS_CACHE_TTL` | ⭐ Optional | Cache TTL in seconds (default: `3600` = 1 hour) |
| `TAVILY_API_KEY` | ⭐ Optional | Enables Web Search tool for agents |

---

## 🛡️ Security
- **Data Isolation**: Strict Row-Level Security (RLS) ensures users only access their own data.
- **Secure API**: All agent interactions are protected via secure JWT tokens.
- **Non-blocking I/O**: All Supabase calls run in `asyncio.to_thread` — one slow query never blocks other users.

---

## 📬 Contact
Have questions? Reach out via the contact form on our website or connect with **Vadde Thrishank** at [thrishank2005@gmail.com](mailto:thrishank2005@gmail.com).

---
