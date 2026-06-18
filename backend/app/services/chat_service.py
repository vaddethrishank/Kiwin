import asyncio
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from app.core.config import settings
from supabase import create_client, Client
from app.services.tools import get_tools_for_agent, execute_tool

# HuggingFace Inference API embeddings - pure HTTP calls, NO local model, zero extra RAM
# Model: BAAI/bge-base-en-v1.5 → 768-dim (matches Supabase vector column)
_embeddings_model = None

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = HuggingFaceInferenceAPIEmbeddings(
            api_key=settings.HF_TOKEN or "",
            model_name="BAAI/bge-base-en-v1.5"
        )
    return _embeddings_model

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
# event loop while Supabase or the HuggingFace API does network I/O.
# ---------------------------------------------------------------------------

def _fetch_agent_sync(db: Client, agent_id: str):
    return db.table("agents").select(
        "name, role, description, system_prompt, tools, model, api_key"
    ).eq("id", agent_id).single().execute()

def _fetch_history_sync(db: Client, agent_id: str, user_id: str, is_public: bool):
    query = db.table("messages").select("role, content").eq("agent_id", agent_id)
    if not is_public and is_valid_uuid(user_id):
        query = query.eq("user_id", user_id)
    else:
        query = query.eq("session_id", user_id)
    return query.order("created_at", desc=True).limit(10).execute()

def _embed_query_sync(message: str):
    return get_embeddings_model().embed_query(message)

def _rpc_hybrid_search_sync(db: Client, params: dict):
    return db.rpc("hybrid_search", params).execute()

def _insert_message_sync(db: Client, msg_data: dict):
    return db.table("messages").insert(msg_data).execute()

def _fetch_history_50_sync(db: Client, agent_id: str, user_id: str, is_public: bool):
    query = db.table("messages").select("role, content").eq("agent_id", agent_id)
    if not is_public and is_valid_uuid(user_id):
        query = query.eq("user_id", user_id)
    else:
        query = query.eq("session_id", user_id)
    return query.order("created_at", desc=True).limit(50).execute()

# ---------------------------------------------------------------------------

async def get_chat_history(agent_id: str, user_id: str, is_public: bool = False):
    """
    Fetch the last 50 messages for the chat UI.
    Supports both Authenticated Users (UUID) and Anonymous Sessions (String).
    """
    db = get_db()
    try:
        res = await asyncio.to_thread(_fetch_history_50_sync, db, agent_id, user_id, is_public)
        # Return in chronological order
        return res.data[::-1] if res.data else []
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []


async def generate_response(agent_id: str, message: str, user_id: str, is_public: bool = False):
    """
    RAG + Agents Logic:
    1. Fetch Agent & Tools  (parallel with history fetch)
    2. RAG Context          (embedding offloaded to thread)
    3. Agentic Loop (Reason -> Tool -> Result -> Answer)
    """
    db = get_db()

    # ── 1 & 2. Fetch agent + history IN PARALLEL ──────────────────────────
    try:
        agent_task = asyncio.to_thread(_fetch_agent_sync, db, agent_id)
        history_task = asyncio.to_thread(_fetch_history_sync, db, agent_id, user_id, is_public)
        agent_res, history_res = await asyncio.gather(agent_task, history_task)
        agent = agent_res.data
    except Exception as e:
        print(f"Error fetching agent: {e}")
        yield "Error: Could not find agent."
        return

    # Build past messages from history result
    past_messages = []
    try:
        raw_msgs = history_res.data[::-1] if history_res.data else []
        for m in raw_msgs:
            if m["role"] == "user":
                past_messages.append(HumanMessage(content=m["content"]))
            else:
                past_messages.append(AIMessage(content=m["content"]))
    except Exception as e:
        print(f"Warning: Could not process history: {e}")

    # ── 3. Embed Query & Retrieve Context (RAG) ───────────────────────────
    query_vector = None
    context_text = ""

    # Determine API Key first (moved up from step 5)
    api_key = agent.get('api_key') or settings.GROQ_API_KEY

    if api_key:
        try:
            # Offload blocking HTTP call to a thread pool worker
            query_vector = await asyncio.to_thread(_embed_query_sync, message)
        except Exception as e:
            print(f"Error embedding: {e}")

        if query_vector:
            params = {
                "query_text":      message,       # BM25 full-text leg
                "query_embedding": query_vector,  # vector similarity leg
                "filter_agent_id": agent_id,
                "match_count":     5,
                "rrf_k":           60             # RRF smoothing constant
            }
            try:
                res = await asyncio.to_thread(_rpc_hybrid_search_sync, db, params)
                if res.data:
                    chunks = [item['content'] for item in res.data]
                    context_text = "\n\n".join(chunks)
            except Exception as e:
                print(f"Error in hybrid search: {e}")

    # ── 4. Construct System Prompt & Message List ─────────────────────────
    system_instruction = f"""
    You are {agent['name']}, a {agent['role']}.
    Description: {agent['description']}
    
    System Instructions:
    {agent.get('system_prompt', '')}
    
    Relevant Knowledge Base:
    {context_text}
    """

    # Building the conversation chain state
    messages = [SystemMessage(content=system_instruction)] + past_messages + [HumanMessage(content=message)]

    # ── 5. Bind Tools & Initialize LLM (Dynamic Model & Key) ─────────────
    tools_def = get_tools_for_agent(agent_id, agent.get('tools') or [])
    print(f"DEBUG: Binding {len(tools_def)} tools to agent {agent_id}")

    # Determine Model (Key already determined above)
    model_name = agent.get('model') or "llama-3.3-70b-versatile"

    if not api_key:
        yield "Error: No Groq API Key available for this agent."
        return

    try:
        llm_dynamic = ChatGroq(
            model=model_name,
            groq_api_key=api_key,
            temperature=0.7
        )
        llm_node = llm_dynamic.bind_tools(tools_def)
    except Exception as e:
        yield f"Error initializing model {model_name}: {str(e)}"
        return

    # ── 6. Save *User* Message to DB (non-blocking) ───────────────────────
    try:
        msg_data = {
            "agent_id": agent_id,
            "role": "user",
            "content": message
        }
        if not is_public and is_valid_uuid(user_id):
            msg_data["user_id"] = user_id
        else:
            msg_data["session_id"] = user_id

        # Fire-and-forget in a thread so we don't block the stream startup
        asyncio.create_task(asyncio.to_thread(_insert_message_sync, db, msg_data))
    except Exception as e:
        print(f"Error saving user message: {e}")

    # ── 7. Agentic Loop (Execute -> Observation -> Final Answer) ──────────
    try:
        # Step 1: Stream from LLM
        stream = llm_node.astream(messages)
        try:
            first_chunk = await anext(stream)
        except StopAsyncIteration:
            return

        # Step 2: Check for Tool Call
        if first_chunk.tool_calls or first_chunk.tool_call_chunks:
            # Accumulate the full tool-call response first
            response = first_chunk
            async for chunk in stream:
                response += chunk

            # 1. Add the AIMessage with tool calls to history
            messages.append(response)

            # 2. Execute each tool
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Execute securely
                tool_result = execute_tool(agent_id, tool_name, tool_args)

                # 3. Add Tool Message with result
                messages.append(ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=str(tool_result)
                ))

            # Step 3: Get Final Answer — stream it live
            full_content = ""
            async for chunk in llm_node.astream(messages):
                if chunk.content:
                    full_content += chunk.content
                    yield chunk.content

        else:
            # No tool called, just a normal response — stream directly
            full_content = ""
            if first_chunk.content:
                full_content += first_chunk.content
                yield first_chunk.content

            async for chunk in stream:
                if chunk.content:
                    full_content += chunk.content
                    yield chunk.content

        # Save *AI* Message to DB (non-blocking)
        if full_content:
            ai_msg_data = {
                "agent_id": agent_id,
                "role": "assistant",
                "content": full_content
            }
            if not is_public and is_valid_uuid(user_id):
                ai_msg_data["user_id"] = user_id
            else:
                ai_msg_data["session_id"] = user_id

            asyncio.create_task(asyncio.to_thread(_insert_message_sync, db, ai_msg_data))

    except Exception as e:
        error_msg = f"Error during generation: {str(e)}"
        print(error_msg)
        yield error_msg
