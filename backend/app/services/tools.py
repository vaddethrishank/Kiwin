from app.core.config import settings

AVAILABLE_TOOLS = {}

ALL_TOOL_DEFINITIONS = {}

def get_tools_for_agent(agent_id: str, enabled_tools: list[str] = None):
    """
    Returns only the tool definitions that are in the agent's enabled_tools list.
    """
    if not enabled_tools:
        return []
    return [
        ALL_TOOL_DEFINITIONS[name]
        for name in enabled_tools
        if name in ALL_TOOL_DEFINITIONS
    ]

def execute_tool(agent_id: str, tool_name: str, tool_args: dict) -> str:
    print(f"[TOOL] Executing {tool_name} with args {tool_args}")
    return f"Error: Tool '{tool_name}' not found or has been disabled."
