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

### 🧠 Knowledge Base (RAG)
Don't just chat—**learn**. Upload your PDF documents, and your agent will use **Retrieval-Augmented Generation (RAG)** to answer questions based specifically on *your* data.

### 🔌 **Embed Anywhere**
Build once, deploy everywhere.
```html
<script 
  src="https://kiwin.app/widget.js" 
  data-agent-id="YOUR_AGENT_ID"
></script>
```
Simply copy-paste this snippet into any website to instantly add your trained chatbot.

### 🛠️ Real-Time Tools
Equip your agents with functionality:
*   **Web Search**: Fetch live data from the internet.
*   **Calculator**: Perform complex math on the fly.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/-Next.js-black?style=flat&logo=next.js) | React Framework for production |
| **Backend** | ![FastAPI](https://img.shields.io/badge/-FastAPI-005571?style=flat&logo=fastapi) | High-performance Python API |
| **Database** | ![Supabase](https://img.shields.io/badge/-Supabase-3ECF8E?style=flat&logo=supabase) | PostgreSQL & Vector Store |
| **AI Model** | ![Groq](https://img.shields.io/badge/-Groq-F55036?style=flat&logo=groq) | Ultra-fast Llama 3.3 70B inference |
| **Embeddings** | ![HuggingFace](https://img.shields.io/badge/-HuggingFace-FFD21E?style=flat&logo=huggingface) | Local BAAI/bge-base-en-v1.5 (free) |

---

## 🏗️ Getting Started

### Prerequisites
*   Node.js 18+
*   Python 3.11+
*   Supabase Account
*   [Groq API Key](https://console.groq.com) (free)

### 1. Clone the Repository
```bash
git clone https://github.com/vaddethrishank/kiwin.git
cd kiwin
```

### 2. Backend Setup
```bash
cd backend
# Copy and fill in your environment variables
cp .env.example .env
# Add your GROQ_API_KEY=gsk_... to .env
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🛡️ Security
*   **Data Isolation**: Strict Row-Level Security (RLS) ensures users only access their own data.
*   **Secure API**: All agent interactions are protected via secure tokens.

---

## 📬 Contact
Have questions? Reach out via the contact form on our website or connect with **Vadde Thrishank** at [thrishank2005@gmail.com](mailto:thrishank2005@gmail.com).

---


