
from tavily import TavilyClient
from app.core.config import settings





def web_search_tool(query: str) -> str:
    try:
        api_key = settings.TAVILY_API_KEY
        if not api_key:
            return "Error: Tavily API key is missing."

        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(
            query=query,
            search_depth="basic",
            max_results=3
        )

        results = response.get("results", [])
        if not results:
            return "No results found."

        formatted = []
        for r in results:
            formatted.append(
                f"Title: {r.get('title')}\n"
                f"URL: {r.get('url')}\n"
                f"Content: {r.get('content')}"
            )

        return "\n\n".join(formatted)

    except Exception as e:
        return f"Tavily error: {str(e)}"


AVAILABLE_TOOLS = {
    "web_search": web_search_tool
}


def get_tools_for_agent(agent_id: str, enabled_tools: list[str] = None):
    return [
        {
            "name": "web_search",
            "description": "Search the internet for current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    ]


def execute_tool(agent_id: str, tool_name: str, tool_args: dict) -> str:
    print(f"[TOOL] Executing {tool_name} with args {tool_args}")

    if tool_name == "web_search":
        return web_search_tool(tool_args.get("query", ""))

    return f"Error: Tool '{tool_name}' not found."
