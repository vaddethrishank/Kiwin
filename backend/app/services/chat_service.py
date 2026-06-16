from langchain_groq import ChatGroq
from langchain_community.embeddings import FastEmbedEmbeddings
# Use langchain_core for newer versions compatibility
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from app.core.config import settings
from supabase import create_client, Client
from app.services.tools import get_tools_for_agent, execute_tool

# Shared FastEmbed model (ONNX-based, ~150MB — fits Render free tier, 768-dim matches Supabase)
_embeddings_model = None

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = FastEmbedEmbeddings(
            model_name="BAAI/bge-base-en-v1.5"
        )
    return _embeddings_model

# embeddings = GoogleGenerativeAIEmbeddings(
#     model="models/text-embedding-004", 
#     google_api_key=settings.GOOGLE_API_KEY
# )

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

async def get_chat_history(agent_id: str, user_id: str, is_public: bool = False):
    """
    Fetch the last 50 messages for the chat UI.
    Supports both Authenticated Users (UUID) and Anonymous Sessions (String).
    """
    db = get_db()
    try:
        query = db.table("messages").select("role, content").eq("agent_id", agent_id)
        
        if not is_public and is_valid_uuid(user_id):
            query = query.eq("user_id", user_id)
        else:
            # It's an anonymous session ID
            query = query.eq("session_id", user_id)
            
        res = query.order("created_at", desc=True).limit(50).execute()
        # Return in chronological order
        return res.data[::-1] if res.data else []
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []


async def generate_response(agent_id: str, message: str, user_id: str, is_public: bool = False):
    """
    RAG + Agents Logic:
    1. Fetch Agent & Tools
    2. RAG Context
    3. Agentic Loop (Reason -> Tool -> Result -> Answer)
    """
    db = get_db()
    
    try:
        agent_res = db.table("agents").select("name, role, description, system_prompt, tools, model, api_key").eq("id", agent_id).single().execute()
        agent = agent_res.data
    except Exception as e:
        print(f"Error fetching agent: {e}")
        yield f"Error: Could not find agent."
        return

    # 2. Fetch Chat History (Last 10 messages)
    past_messages = []
    try:
        query = db.table("messages").select("role, content").eq("agent_id", agent_id)
        
        if not is_public and is_valid_uuid(user_id):
            query = query.eq("user_id", user_id)
        else:
            query = query.eq("session_id", user_id)
            
        history_res = query.order("created_at", desc=True).limit(10).execute()
        raw_msgs = history_res.data[::-1] if history_res.data else []
        for m in raw_msgs:
            if m["role"] == "user":
                past_messages.append(HumanMessage(content=m["content"]))
            else:
                past_messages.append(AIMessage(content=m["content"]))
    except Exception as e:
        print(f"Warning: Could not fetch history: {e}")


    # 3. Embed Query & Retrieve Context (RAG)
    query_vector = None
    context_text = ""
    
    # Determine API Key first (moved up from step 5)
    api_key = agent.get('api_key') or settings.GROQ_API_KEY
    
    if api_key:
        try:
            # Use local FastEmbed (ONNX, ~150MB, no PyTorch needed)
            embeddings = get_embeddings_model()
            query_vector = embeddings.embed_query(message)
        except Exception as e:
            print(f"Error embedding: {e}")

        if query_vector:
            params = {
                "query_embedding": query_vector,
                "match_threshold": 0.3,
                "match_count": 5,
                "filter_agent_id": agent_id
            }
        try:
            res = db.rpc("match_documents", params).execute()
            if res.data:
                chunks = [item['content'] for item in res.data]
                context_text = "\n\n".join(chunks)
        except Exception as e:
            print(f"Error searching documents: {e}")

    # 4. Construct System Prompt & Message List
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
    
    # 5. Bind Tools & Initialize LLM (Dynamic Model & Key)
    tools_def = get_tools_for_agent(agent_id, [])
    print(f"DEBUG: Binding {len(tools_def)} tools to agent {agent_id}")

    tools_def = get_tools_for_agent(agent_id, [])
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

    # 6. Save *User* Message to DB
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
            
        db.table("messages").insert(msg_data).execute()
    except Exception as e:
        print(f"Error saving user message: {e}")
        
    # 7. Agentic Loop (Execute -> Observation -> Final Answer)
    # The user requirements STRICTLY limit this to ONE tool call per request.
    
    try:
        # Step 1: Call LLM
        response = await llm_node.ainvoke(messages)
        
        # Step 2: Check for Tool Call
        if response.tool_calls:
            # It wants to use a tool!
            # 1. Add the AIMessage with tool calls to history
            messages.append(response)
            
            # 2. Execute each tool
            # (Limitation: Only processing the first tool call for simplicity if multiple are somehow generated.
            # We handle all to be safe but usually it's one turn.)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # yield f"DEBUG: Calling {tool_name}...\n"
                
                # Execute securely
                tool_result = execute_tool(agent_id, tool_name, tool_args)
                
                # 3. Add Tool Message with result
                messages.append(ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=str(tool_result)
                ))
            
            # Step 3: Get Final Answer (Recursion Level 2 - Final)
            final_response = await llm_node.ainvoke(messages)
            
            # Stream the final answer
            content = final_response.content
            chunk_size = 10
            for i in range(0, len(content), chunk_size):
                yield content[i:i+chunk_size]
                
            # Persist Final Answer
            full_content = final_response.content
        
        else:
            # No tool called, just a normal response
            content = response.content
            chunk_size = 10
            for i in range(0, len(content), chunk_size):
                yield content[i:i+chunk_size]
            full_content = response.content

        # Save *AI* Message to DB
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

            db.table("messages").insert(ai_msg_data).execute()

    except Exception as e:
        error_msg = f"Error during generation: {str(e)}"
        print(error_msg)
        yield error_msg
