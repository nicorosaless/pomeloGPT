import ollama
import json

try:
    print("Attempting to list models...")
    response = ollama.list()
    print("Success!")
    print(json.dumps(response, indent=2))
except Exception as e:
    print(f"Error: {e}")
