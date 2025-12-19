from duckduckgo_search import DDGS

print("Testing DuckDuckGo Search...")
try:
    results = DDGS().text("test", max_results=1)
    print(f"Success! Found {len(results)} results.")
    print(results)
except Exception as e:
    print(f"FAILURE: {e}")
