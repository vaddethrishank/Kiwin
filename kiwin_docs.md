# Kiwin Platform Documentation

## 1. Overview
Kiwin is a comprehensive, no-code AI Agent Platform designed to democratize the creation of intelligent assistants. It allows users to build, train, deploy, and embed custom AI agents without writing complex code.

## 2. The Main Motto
> "Each time after creating a website, no need to build a chatbot for everything. One simple snippet can solve it, and it is absolutely free."

Kiwin is designed to solve the repetitive pain of building support bots. Instead of coding a new bot for every project, you build it **once** on Kiwin and embed it **anywhere** with a single line of code.

**Owner & Creator:** Vadde Thrishank

## Core Philosophy
1.  **Simplicity**: Build powerful agents with zero code.
2.  **Zero Cost**: The platform is free to use.
3.  **One Snippet**: Copy-paste integration for any website.

## Key Features

### 1. Custom Agent Creation
Users can create multiple agents, each with a unique:
- **Name**: The identity of the bot.
- **Persona/Role**: Defined via a "System Prompt" (e.g., "You are a customer support specialist").
- **Model**: Choice between `Gemini 1.5 Flash` (High speed, lower cost) and `Gemini 1.5 Pro` (Complex reasoning).

### 2. Knowledge Base (RAG)
Kiwin utilizes **Retrieval-Augmented Generation (RAG)**.
- Users can upload PDF documents to an agent's knowledge base.
- When a query is asked, the agent searches these documents for relevant context before answering.
- This ensures answers are accurate and specific to the user's data, rather than just general knowledge.

### 3. Embeddable Widget
- Every agent comes with a unique, auto-generated Javascript snippet.
- This snippet can be pasted into any website (HTML, React, WordPress) to display a chat widget.
- **Customization**: Users can customize the widget's **Primary Color**, **Icon Size**, and **Position** (Left/Right).
- **Format**: `<script src="..." data-agent-id="..." data-color="#..." ...></script>`

### 4. Real-Time Tools
Agents can be equipped with executable tools:
- **Web Search**: Allows the agent to fetch live information from the internet.
- **Calculator**: Enables precise mathematical calculations.

## Security & Data Privacy
Kiwin prioritizes user privacy through a strict **Row-Level Security (RLS)** model.

- **Data Isolation**: "Users can only access their own data."
- A user logged into Kiwin can ONLY view, edit, or delete the agents and files they created.
- They cannot see any other user's agents or knowledge base files.
- **API Security**: Secure API keys and tokens ensure that backend communication is authenticated and authorized for the specific user context.

## Technical Architecture
- **Frontend**: Built with **Next.js 14**, providing a fast, responsive, and server-rendered user interface.
- **Backend**: Powered by **FastAPI (Python)**, handling complex logic and AI orchestration.
- **Database**: Uses **Supabase (PostgreSQL)** for structured data and **pgvector** for vector embeddings (used in RAG).
- **AI Engine**: Integrated with **Google Gemini** models via LangChain.

## Contact & Support
For inquiries, users can reach out via the Contact form on the website. Messages are securely stored and reviewed by the administration.
