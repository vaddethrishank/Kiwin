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






While the current approach is solid for a minimum viable product (MVP), there are several areas where it can be heavily optimized for speed, accuracy, and scalability.

Here is a breakdown of the current bottlenecks and how you can optimize the application:

1. Retrieval Quality Optimizations (Accuracy)
Currently, the system uses "naive" vector search (embedding a query and finding nearest neighbors). This can fail on complex queries.

Implement Hybrid Search: You are only using Vector Search. For exact keyword matches (e.g., searching for a specific ID or rare name), vector search struggles. You should combine Vector Search + Full-Text Search (BM25) in Postgres and merge the results.
Query Reformulation (Critical): If a user's 3rd message is "What about the other one?", your system currently embeds that exact string. The vector for that string won't match any useful documents. Optimization: Pass the chat history and the user's latest message to a small, fast LLM (like Llama-3-8b) to rewrite it into a standalone query (e.g., "What about the other health insurance plan?") before embedding it.
Re-ranking: Fetch 15-20 documents from Supabase (instead of 5), and pass them through a lightweight Cross-Encoder model to re-rank them based on actual relevance, then only feed the top 3-5 to the final LLM.
Better Prompt Structuring: Instead of just joining chunks with \n\n, wrap them in XML tags so the LLM knows they are distinct documents:
xml
<documents>
  <doc id="1"> Chunk 1 text... </doc>
  <doc id="2"> Chunk 2 text... </doc>
</documents>
2. Ingestion & Embedding Optimizations (Data Quality)
The phrase "Garbage in, garbage out" applies heavily to RAG. If your chunks are bad, the answers will be bad.

Upgrade PDF Parsing: You are using pypdf. It is fast but terrible at extracting text from complex layouts or tables. Optimization: Switch to PyMuPDF (fitz) or pdfplumber which maintain structural integrity much better.
Semantic Chunking instead of Character Chunking: You are blindly splitting text every 1000 characters. This often cuts sentences or paragraphs in half, destroying context. Look into Semantic Chunking or Langchain's MarkdownTextSplitter if your text has headers.
Metadata Extraction: Right now, you only store chunk_index in metadata. You should use a fast LLM during ingestion to extract a brief summary and keywords for each chunk, and store those in Supabase. This helps Postgres filter results before doing vector math.
3. Performance & Speed Optimizations (Latency)
Fake Streaming: In chat_service.py, you are doing this:
python
final_response = await llm_node.ainvoke(messages)
for i in range(0, len(content), chunk_size): yield content[i:i+chunk_size]
You are waiting for the entire generation to finish before yielding the first chunk. This is "fake" streaming. Optimization: Use LangChain's native .astream() method to yield tokens over the network the exact millisecond Groq generates them. This will make the UI feel 10x faster.

HuggingFace API Latency: You are using the HuggingFaceInferenceAPIEmbeddings over HTTP. Doing this in a loop for every chunk during file upload is slow and heavily vulnerable to rate limits. Optimization: If your server has some RAM, run the embedding model locally using the FastEmbed library. It uses ONNX, requires no GPU, and embeds locally in milliseconds without HTTP overhead. (Your code comments mention FastEmbed, but it is actually using the HTTP API!).
Blocking I/O in Async functions: process_file and generate_response are async def, but they use synchronous Supabase clients and synchronous embedding calls (embed_documents instead of aembed_documents). This blocks your Python event loop, meaning under heavy load, one user uploading a file will freeze chat for other users. Optimization: Switch to supabase.create_async_client and use asyncio.gather for parallel processing.
Summary of Highest ROI Fixes
If you want to optimize immediately, do these three things first:

Fix the "fake streaming" in the chat service by using .astream().
Add query reformulation so follow-up questions work correctly.
Switch from pypdf to PyMuPDF for better text extraction