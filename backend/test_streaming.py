import requests
import json
import time

def test_streaming():
    url = "http://localhost:8000/chat/stream"
    payload = {
        "model": "gemma3:4b", 
        "messages": [{"role": "user", "content": "Count from 1 to 10 slowly"}],
        "stream": True,
        "use_rag": False,
        "use_web_search": False
    }
    
    print(f"Connecting to {url}...")
    start_time = time.time()
    
    try:
        with requests.post(url, json=payload, stream=True) as r:
            print(f"Response status: {r.status_code}")
            if r.status_code != 200:
                print(r.text)
                return

            last_chunk_time = time.time()
            chunk_count = 0
            
            for line in r.iter_lines():
                if line:
                    current_time = time.time()
                    delta = current_time - last_chunk_time
                    last_chunk_time = current_time
                    chunk_count += 1
                    
                    try:
                        data = json.loads(line)
                        content = data.get('content', '')
                        print(f"Chunk {chunk_count}: '{content}' (delta: {delta:.4f}s)")
                    except json.JSONDecodeError:
                        print(f"Chunk {chunk_count}: [Invalid JSON] {line} (delta: {delta:.4f}s)")
                        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_streaming()
