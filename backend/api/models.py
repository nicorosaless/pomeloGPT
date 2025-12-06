from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ollama
from typing import List, Optional
import time

# Simple in-memory cache
_models_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 60  # seconds
}

router = APIRouter(prefix="/models", tags=["models"])

class PullModelRequest(BaseModel):
    name: str
    tag: str = "latest"

class ModelInfo(BaseModel):
    name: str
    size: int
    digest: str
    details: dict

# Curated list of models < 15B
AVAILABLE_MODELS = [
    {
        "name": "gemma:2b",
        "title": "Gemma 2B",
        "description": "Google's lightweight open model, 2B parameters.",
        "size_approx": "1.4GB",
        "tags": ["latest", "text"],
        "performance": {"velocity": "A", "quality": "C"},
        "recommended_quantization": "q4_k_m",
        "quantization_options": [
            {"tag": "q4_k_m", "desc": "Balanced (Recommended)", "details": "Good balance of speed and quality. 4-bit quantization."},
            {"tag": "q8_0", "desc": "High Precision", "details": "Higher quality, larger size. 8-bit quantization."},
            {"tag": "fp16", "desc": "Full Precision", "details": "Best quality, largest size. 16-bit floating point."}
        ]
    },
    {
        "name": "gemma:7b",
        "title": "Gemma 7B",
        "description": "Google's open model, 7B parameters.",
        "size_approx": "5.0GB",
        "tags": ["latest", "text"],
        "performance": {"velocity": "B", "quality": "B"},
        "recommended_quantization": "q4_k_m",
        "quantization_options": [
            {"tag": "q4_k_m", "desc": "Balanced (Recommended)", "details": "Standard 4-bit quantization."},
            {"tag": "q8_0", "desc": "High Precision", "details": "8-bit quantization, requires more RAM."},
        ]
    },
    {
        "name": "gemma3:4b",
        "title": "Gemma 3 4B",
        "description": "Google's latest open model, 4B parameters.",
        "size_approx": "2.8GB",
        "tags": ["latest", "text"],
        "performance": {"velocity": "A", "quality": "B+"},
        "recommended_quantization": "q4_k_m",
        "quantization_options": [
            {"tag": "q4_k_m", "desc": "Balanced (Recommended)", "details": "Optimized for most systems."},
            {"tag": "q8_0", "desc": "High Precision", "details": "Better reasoning capabilities."},
        ]
    },
    {
        "name": "llama3:8b",
        "title": "Llama 3 8B",
        "description": "Meta's Llama 3, 8B parameters. High performance.",
        "size_approx": "4.7GB",
        "tags": ["latest", "text", "instruct"],
        "performance": {"velocity": "B", "quality": "A"},
        "recommended_quantization": "q4_k_m",
        "quantization_options": [
            {"tag": "q4_k_m", "desc": "Balanced (Recommended)", "details": "Optimized for most systems."},
            {"tag": "q8_0", "desc": "High Precision", "details": "Better reasoning capabilities, slower generation."},
        ]
    },
    {
        "name": "mistral:7b",
        "title": "Mistral 7B",
        "description": "Mistral AI's 7B model. Very popular and efficient.",
        "size_approx": "4.1GB",
        "tags": ["latest", "text", "instruct"],
        "performance": {"velocity": "B", "quality": "B"},
        "recommended_quantization": "q4_k_m",
        "quantization_options": [
            {"tag": "q4_k_m", "desc": "Balanced (Recommended)", "details": "Good general purpose quantization."},
            {"tag": "q5_k_m", "desc": "Higher Quality", "details": "Slightly better than q4, slightly larger."},
        ]
    },
    {
        "name": "phi3:3.8b",
        "title": "Phi-3 Mini",
        "description": "Microsoft's Phi-3 Mini. 3.8B parameters.",
        "size_approx": "2.3GB",
        "tags": ["latest", "text"],
        "performance": {"velocity": "A", "quality": "B"},
        "recommended_quantization": "q4_k_m",
        "quantization_options": [
            {"tag": "q4_k_m", "desc": "Balanced (Recommended)", "details": "Very fast on M1 chips."},
            {"tag": "q8_0", "desc": "High Precision", "details": "Maximum quality for this size."},
        ]
    },
    {
        "name": "qwen:7b",
        "title": "Qwen 7B",
        "description": "Alibaba's Qwen model. Strong performance.",
        "size_approx": "4.5GB",
        "tags": ["latest", "text"],
        "performance": {"velocity": "B", "quality": "B"},
        "recommended_quantization": "q4_k_m",
        "quantization_options": [
            {"tag": "q4_k_m", "desc": "Balanced (Recommended)", "details": "Standard choice."},
        ]
    },
    {
        "name": "tinyllama",
        "title": "TinyLlama 1.1B",
        "description": "TinyLlama 1.1B. Extremely fast, good for testing.",
        "size_approx": "637MB",
        "tags": ["latest"],
        "performance": {"velocity": "A+", "quality": "C"},
        "recommended_quantization": "latest",
        "quantization_options": [
            {"tag": "latest", "desc": "Default", "details": "Standard distribution."},
        ]
    }
]

@router.get("/installed")
async def list_installed_models():
    global _models_cache
    current_time = time.time()
    
    # Check cache
    if _models_cache["data"] and (current_time - _models_cache["timestamp"] < _models_cache["ttl"]):
        print("Returning cached models list")
        return _models_cache["data"]

    print("Fetching installed models from Ollama...")
    try:
        client = ollama.AsyncClient()
        response = await client.list()
        print(f"Ollama response: {response}")
        
        # Update cache
        _models_cache["data"] = response
        _models_cache["timestamp"] = current_time
        
        return response
    except Exception as e:
        print(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available")
async def list_available_models():
    return {"models": AVAILABLE_MODELS}

@router.get("/{name}/info")
async def get_model_info(name: str):
    try:
        client = ollama.AsyncClient()
        response = await client.show(name)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pull")
async def pull_model(request: PullModelRequest):
    model_name = f"{request.name}:{request.tag}"
    
    async def generate():
        try:
            client = ollama.AsyncClient()
            # stream=True yields a stream of progress objects
            async for progress in await client.pull(model_name, stream=True):
                # Yield progress as a JSON string line
                yield json.dumps(progress) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    from fastapi.responses import StreamingResponse
    import json
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@router.delete("/{name}")
async def delete_model(name: str):
    try:
        client = ollama.AsyncClient()
        await client.delete(name)
        return {"status": "success", "message": f"Deleted {name}"}
    except Exception as e:
        # Ollama might return 404 if not found, handle gracefully?
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lookup/{name}")
async def lookup_model_tags(name: str):
    """
    Scrapes the Ollama library page for a given model to find available tags.
    """
    import requests
    from bs4 import BeautifulSoup
    import re

    url = f"https://ollama.com/library/{name}/tags"
    print(f"Scraping tags from: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return {"tags": []}
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch Ollama library page")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tags = []
        
        # Ollama tags page structure (best guess based on current layout)
        # Usually they are in links or divs.
        # Looking at the page source would be ideal, but let's try a generic approach
        # or target specific classes if known.
        # As of late 2024/2025, tags are often in elements with specific classes.
        # Let's try to find elements that look like tags.
        
        # Strategy: Look for links to specific tag versions
        # The tags page lists versions as links like: <a href="/library/model:tag">
        # Example: /library/ministral-3:latest, /library/ministral-3:3b
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Pattern: /library/{name}:{tag}
            # We need to be careful to match exactly the model name followed by a colon
            prefix = f"/library/{name}:"
            if href.startswith(prefix):
                tag = href[len(prefix):]
                # Some links might be complex, but usually it's just the tag
                # Filter out any potential noise and "cloud" tags
                if tag and tag not in tags and "cloud" not in tag.lower():
                    tags.append(tag)
        
        # Fallback: sometimes tags might be listed differently or the URL structure changes.
        # But for now, this seems to be the standard way Ollama lists tags.
        
        # If no tags found, try to find "latest" in text as a fallback
        if not tags and "latest" in response.text:
            tags.append("latest")
            
        return {"tags": tags[:30]} # Increased limit slightly
        
    except Exception as e:
        print(f"Error scraping tags: {e}")
        # Don't fail hard, just return empty list so UI can fallback to manual entry
        return {"tags": [], "error": str(e)}
