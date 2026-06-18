import requests
import os

key = os.environ.get("GEMINI_API_KEY")

if not key:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
models = res.json()
for m in models.get("models", []):
    if "embed" in m["name"]:
        print(m["name"])
