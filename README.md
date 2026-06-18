# 🥝 Kiwin - AI Agent Platform

> **"Each time after creating a website, no need to build a chatbot for everything. One simple snippet can solve it, and it is absolutely free."**

![Project Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Tech Stack](https://img.shields.io/badge/Stack-Next.js%20%7C%20FastAPI%20%7C%20Supabase-orange)

## 🚀 Overview

**Kiwin** is a powerful, no-code AI platform that democratizes the creation of intelligent assistants. We believe that building a custom chatbot shouldn't require a degree in computer science. With Kiwin, you can create, train, and deploy an AI agent in minutes.

**Created by: Vadde Thrishank**

---

## ✨ Features

### 🤖 Intelligent Agents
Create custom personas with unique roles. Whether it's a **customer support bot**, a **travel guide**, or a **coding assistant**, Kiwin's agents are powered by **Groq's ultra-fast LLMs** like **Llama 3.3 70B** — completely free.

### 🧠 Knowledge Base (Hybrid RAG)
Don't just chat — **learn**. Upload your PDF documents and your agent will answer questions based specifically on *your* data using a **Hybrid Search** pipeline:

- **Vector Search** — dense semantic embeddings via `BAAI/bge-base-en-v1.5`
- **BM25 Full-Text Search** — exact keyword matching via PostgreSQL `tsvector`
- **Reciprocal Rank Fusion (RRF)** — fuses both result lists for best-of-both-worlds accuracy

PDF text extraction is powered by **PyMuPDF** for accurate multi-column and complex layout handling.

### ⚡ True Token Streaming
Responses are streamed token-by-token the **exact millisecond** Groq generates them using LangChain's native `.astream()`. The UI feels instant — no waiting for the full response.

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

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/-Next.js-black?style=flat&logo=next.js) | React framework with streaming SSE support |
| **Backend** | ![FastAPI](https://img.shields.io/badge/-FastAPI-005571?style=flat&logo=fastapi) | Async Python API — full non-blocking I/O |
| **Database** | ![Supabase](https://img.shields.io/badge/-Supabase-3ECF8E?style=flat&logo=supabase) | PostgreSQL + pgvector + full-text search |
| **AI Model** | ![Groq](https://img.shields.io/badge/-Groq-F55036?style=flat&logo=groq) | Ultra-fast Llama 3.3 70B inference |
| **Embeddings** | ![HuggingFace](https://img.shields.io/badge/-HuggingFace-FFD21E?style=flat&logo=huggingface) | BAAI/bge-base-en-v1.5 via Inference API |
| **PDF Parsing** | PyMuPDF | High-fidelity text extraction from complex PDFs |

---

## 🏗️ Architecture

```
User Message
    │
    ├─ asyncio.gather ─────────────────────────────────────┐
    │   ├─ Fetch Agent config (Supabase)                   │
    │   └─ Fetch Chat History (Supabase)                   │
    │                                                      │
    ├─ Embed query → BAAI/bge-base-en-v1.5 (HuggingFace) ─┘
    │
    ├─ hybrid_search() — PostgreSQL RPC
    │   ├─ Vector leg:  embedding <=> query_vector  (ranked)
    │   ├─ FTS leg:     fts @@ plainto_tsquery      (ranked)
    │   └─ RRF fusion:  1/(60+rank_v) + 1/(60+rank_fts)
    │
    ├─ Build system prompt + context + history
    │
    └─ LLM (Groq) → .astream() → token-by-token to browser
```

---

## 🏁 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Supabase account
- [Groq API Key](https://console.groq.com) (free)

### 1. Clone the Repository
```bash
git clone https://github.com/vaddethrishank/kiwin.git
cd kiwin
```

### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY, HF_TOKEN
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
Run the hybrid search migration once in your **Supabase Dashboard → SQL Editor**:
```bash
# File: backend/migrations/001_hybrid_search.sql
```
This adds the `fts` tsvector column, GIN index, and `hybrid_search()` PostgreSQL function.

---

## 🛡️ Security
- **Data Isolation**: Strict Row-Level Security (RLS) ensures users only access their own data.
- **Secure API**: All agent interactions are protected via secure JWT tokens.
- **Non-blocking I/O**: All Supabase calls run in `asyncio.to_thread` — one slow query never blocks other users.

---

## 📬 Contact
Have questions? Reach out via the contact form on our website or connect with **Vadde Thrishank** at [thrishank2005@gmail.com](mailto:thrishank2005@gmail.com).

---
