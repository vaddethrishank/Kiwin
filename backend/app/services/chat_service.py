import asyncio
import requests
from typing import List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from app.core.config import settings
from supabase import create_client, Client
from app.services.tools import get_tools_for_agent, execute_tool
from app.services.semantic_cache import get_cached_response, set_cached_response
from app.services.history_cache import (
    get_history_for_llm,
    get_history_for_ui,
    append_messages,
)

# ---------------------------------------------------------------------------
# Google Gemini AI Embeddings — 768-dim
# ---------------------------------------------------------------------------

# Placeholder value written to .env by default — detect it to skip the HTTP call
_GEMINI_PLACEHOLDER = "your_gemini_api_key_here"

def _has_gemini_key() -> bool:
    """Return True only when a real (non-placeholder) Gemini API key is configured."""
    key = settings.GEMINI_API_KEY
    return bool(key) and key != _GEMINI_PLACEHOLDER

def _gemini_embed_sync(texts: List[str]) -> List[List[float]]:
    """Call Google Gemini embeddings API and return a list of 768-dim vectors."""
    if not texts:
        return []
    requests_payload = [
        {
            "model": "models/gemini-embedding-2", 
            "content": {"parts": [{"text": t}]},
            "outputDimensionality": 768
        }
        for t in texts
    ]
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={settings.GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={"requests": requests_payload},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return [item["values"] for item in data.get("embeddings", [])]

def get_db() -> Client:
    # Always use Service Role for backend processing to ensure we can read documents
    if settings.SUPABASE_SERVICE_ROLE_KEY:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def is_valid_uuid(val):
    import uuid
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

# ---------------------------------------------------------------------------
# Internal sync helpers — called via asyncio.to_thread to avoid blocking the
# event loop while Supabase or the Gemini API does network I/O.
# ---------------------------------------------------------------------------

def _fetch_agent_sync(db: Client, agent_id: str):
    return db.table("agents").select(
        "name, role, description, system_prompt, tools, model, api_key"
    ).eq("id", agent_id).single().execute()

def _embed_query_sync(message: str) -> List[float]:
    return _gemini_embed_sync([message])[0]

def _rpc_hybrid_search_sync(db: Client, params: dict):
    return db.rpc("hybrid_search", params).execute()

def _insert_message_sync(db: Client, msg_data: dict):
    return db.table("messages").insert(msg_data).execute()

# ---------------------------------------------------------------------------

async def get_chat_history(agent_id: str, user_id: str, is_public: bool = False):
    """
    Fetch the last 50 messages for the chat UI.
    Redis-first with Postgres fallback.
    Supports both Authenticated Users (UUID) and Anonymous Sessions (String).
    """
    db = get_db()
    return await get_history_for_ui(agent_id, user_id, db, is_public)


async def generate_response(agent_id: str, message: str, user_id: str, is_public: bool = False):
    """
    RAG + Agents Logic with Redis Semantic Cache + Fast History:

    0. Embed query
    1. Semantic cache check  → HIT: yield cached answer instantly (<10ms)
    2. MISS: Fetch Agent & history (parallel with embedding)
    3. Hybrid RAG search
    4. Groq LLM streaming
    5. Store answer in semantic cache + Redis history (background tasks)
    6. Write-through to Postgres (background task)
    """
    db = get_db()

    # ── 0. Embed the query (needed for cache lookup AND RAG search) ────────
    query_vector = None
    if _has_gemini_key():
        print(f"[RAG] Embedding query: '{message[:60]}...'")
        try:
            query_vector = await asyncio.to_thread(_embed_query_sync, message)
            print(f"[RAG] Embedding done. Vector size: {len(query_vector)}")
        except Exception as e:
            print(f"[RAG] Embedding failed: {e}")

    # ── 1. Semantic cache check ────────────────────────────────────────────
    if query_vector is not None:
        cached = await get_cached_response(agent_id, query_vector)
        if cached is not None:
            print(f"[SemanticCache] Cache HIT — returning cached response instantly.")
            yield cached
            # Still persist the user message to history (non-blocking)
            asyncio.create_task(_persist_user_message(db, agent_id, user_id, message, is_public))
            asyncio.create_task(_persist_ai_message(db, agent_id, user_id, cached, is_public))
            asyncio.create_task(append_messages(agent_id, user_id, [
                {"role": "user", "content": message},
                {"role": "assistant", "content": cached},
            ]))
            return

    # ── 2. Fetch agent + history IN PARALLEL ──────────────────────────────
    try:
        agent_task = asyncio.to_thread(_fetch_agent_sync, db, agent_id)
        history_task = get_history_for_llm(agent_id, user_id, db, is_public)
        agent_res, past_msg_dicts = await asyncio.gather(
            agent_task, history_task,
            return_exceptions=True
        )

        if isinstance(agent_res, Exception):
            raise agent_res
        agent = agent_res.data
    except Exception as e:
        print(f"Error fetching agent: {e}")
        yield "Error: Could not find agent."
        return

    # Build LangChain message objects from history
    past_messages = []
    try:
        if not isinstance(past_msg_dicts, Exception):
            for m in (past_msg_dicts or []):
                if m["role"] == "user":
                    past_messages.append(HumanMessage(content=m["content"]))
                else:
                    past_messages.append(AIMessage(content=m["content"]))
    except Exception as e:
        print(f"Warning: Could not process history: {e}")

    # ── 3. Hybrid RAG Search ───────────────────────────────────────────────
    context_text = ""
    api_key = agent.get('api_key') or settings.GROQ_API_KEY

    if query_vector:
        print(f"[RAG] Running hybrid_search for agent {agent_id}...")
        params = {
            "query_text":      message,
            "query_embedding": query_vector,
            "filter_agent_id": agent_id,
            "match_count":     5,
            "rrf_k":           60
        }
        try:
            res = await asyncio.to_thread(_rpc_hybrid_search_sync, db, params)
            if res.data:
                chunks = [item['content'] for item in res.data]
                context_text = "\n\n".join(chunks)
                print(f"[RAG] {len(chunks)} chunks retrieved. Context: {len(context_text)} chars.")
            else:
                print(f"[RAG] No chunks found — knowledge base empty or no match.")
        except Exception as e:
            print(f"[RAG] Hybrid search error: {e}")

    # ── 4. Build prompt ────────────────────────────────────────────────────
    system_instruction = f"""
    You are {agent['name']}, a {agent['role']}.
    Description: {agent['description']}
    
    System Instructions:
    {agent.get('system_prompt', '')}
    
    Relevant Knowledge Base:
    {context_text}
    """

    messages = [SystemMessage(content=system_instruction)] + past_messages + [HumanMessage(content=message)]

    # ── 5. Initialize LLM ─────────────────────────────────────────────────
    tools_def = get_tools_for_agent(agent_id, agent.get('tools') or [])
    print(f"DEBUG: Binding {len(tools_def)} tools to agent {agent_id}")
    model_name = agent.get('model') or "llama-3.3-70b-versatile"

    if not api_key:
        yield "Error: No Groq API Key available for this agent."
        return

    try:
        llm_dynamic = ChatGroq(model=model_name, groq_api_key=api_key, temperature=0.7)
        llm_node = llm_dynamic.bind_tools(tools_def) if tools_def else llm_dynamic
    except Exception as e:
        yield f"Error initializing model {model_name}: {str(e)}"
        return

    # ── 6. Persist user message (non-blocking) ────────────────────────────
    asyncio.create_task(_persist_user_message(db, agent_id, user_id, message, is_public))

    # ── 7. Agentic Loop ───────────────────────────────────────────────────
    full_content = ""
    try:
        stream = llm_node.astream(messages)
        try:
            first_chunk = await anext(stream)
        except StopAsyncIteration:
            return

        if first_chunk.tool_calls or first_chunk.tool_call_chunks:
            # Accumulate full tool-call response
            response = first_chunk
            async for chunk in stream:
                response += chunk

            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_result = await asyncio.to_thread(execute_tool, agent_id, tool_name, tool_args)
                messages.append(ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=str(tool_result)
                ))

            # Stream final answer after tool use
            async for chunk in llm_node.astream(messages):
                if chunk.content:
                    full_content += chunk.content
                    yield chunk.content
        else:
            # Normal (no tool) streaming
            if first_chunk.content:
                full_content += first_chunk.content
                yield first_chunk.content

            async for chunk in stream:
                if chunk.content:
                    full_content += chunk.content
                    yield chunk.content

    except Exception as e:
        error_msg = f"Error during generation: {str(e)}"
        print(error_msg)
        yield error_msg
        return

    # ── 8. Post-response: cache + history (all non-blocking) ─────────────
    if full_content:
        # a) Store in semantic cache (only if we have an embedding)
        if query_vector is not None:
            asyncio.create_task(
                set_cached_response(agent_id, message, query_vector, full_content)
            )

        # b) Append to Redis history
        asyncio.create_task(append_messages(agent_id, user_id, [
            {"role": "user", "content": message},
            {"role": "assistant", "content": full_content},
        ]))

        # c) Persist AI message to Postgres (write-through)
        asyncio.create_task(_persist_ai_message(db, agent_id, user_id, full_content, is_public))


# ── Private helpers ────────────────────────────────────────────────────────────

async def _persist_user_message(db, agent_id, user_id, content, is_public):
    """Fire-and-forget Postgres write for user message."""
    try:
        msg_data = {"agent_id": agent_id, "role": "user", "content": content}
        if not is_public and is_valid_uuid(user_id):
            msg_data["user_id"] = user_id
        else:
            msg_data["session_id"] = user_id
        await asyncio.to_thread(_insert_message_sync, db, msg_data)
    except Exception as e:
        print(f"[Persist] Error saving user message: {e}")


async def _persist_ai_message(db, agent_id, user_id, content, is_public):
    """Fire-and-forget Postgres write for AI message."""
    try:
        ai_msg_data = {"agent_id": agent_id, "role": "assistant", "content": content}
        if not is_public and is_valid_uuid(user_id):
            ai_msg_data["user_id"] = user_id
        else:
            ai_msg_data["session_id"] = user_id
        await asyncio.to_thread(_insert_message_sync, db, ai_msg_data)
    except Exception as e:
        print(f"[Persist] Error saving AI message: {e}")
