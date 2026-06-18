import os
import requests

# Parse .env manually
env_vars = {}
with open('c:/Users/thris/Kiwin/backend/.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env_vars[k.strip()] = v.strip()

jina_key = env_vars.get("JINA_API_KEY")

print(f"Testing Jina API with key: {jina_key[:10]}...")

try:
    response = requests.post(
        "https://api.jina.ai/v1/embeddings",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jina_key}",
        },
        json={
            "model": "jina-embeddings-v2-base-en",
            "input": ["Test query"],
        },
        timeout=10,
    )
    
    if response.status_code == 200:
        data = response.json()
        print("Success! Jina API returned embeddings.")
        print(f"Vector size: {len(data['data'][0]['embedding'])}")
    else:
        print(f"Error! Jina API returned status code {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
