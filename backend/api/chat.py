from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import ollama
import json
import database
from api import rag
from api.searxng_service import SearXNGService
import requests
import re
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    model: str
    messages: list
    conversation_id: str | None = None
    stream: bool = True
    use_rag: bool = False
    use_web_search: bool = False
    searxng_url: str = "http://localhost:8080"  # Default to local Docker instance

class CreateChatRequest(BaseModel):
    title: str = "New Chat"

class RenameChatRequest(BaseModel):
    title: str

@router.get("/history")
async def get_history():
    return {"conversations": database.get_conversations()}

@router.post("/new")
async def create_chat(request: CreateChatRequest):
    chat_id = database.create_conversation(request.title)
    return {"id": chat_id, "title": request.title}

@router.get("/{conversation_id}")
async def get_chat_messages(conversation_id: str):
    messages = database.get_messages(conversation_id)
    return {"messages": messages}

@router.delete("/{conversation_id}")
async def delete_chat(conversation_id: str):
    database.delete_conversation(conversation_id)
    return {"status": "success"}

@router.put("/{conversation_id}/title")
async def rename_chat(conversation_id: str, request: RenameChatRequest):
    database.update_conversation_title(conversation_id, request.title)
    return {"status": "success", "title": request.title}

SYSTEM_PROMPT = """You are a helpful assistant.
Respond in the language of the user.
Use inline code (single backticks) for single words, short phrases, or variable names.
Only use code blocks (triple backticks) for multi-line code or longer snippets."""

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    try:
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = database.create_conversation()
        current_system_prompt = SYSTEM_PROMPT
        last_message = request.messages[-1]

        # RAG Integration
        if request.use_rag and last_message["role"] == "user":
            context_chunks = rag.query_collection(last_message["content"], conversation_id=conversation_id)
            if context_chunks:
                context_str = "\n\n".join(context_chunks)
                current_system_prompt += f"""

Context information is below.
---------------------
{context_str}
---------------------
Given the context information and not prior knowledge, answer the query.
"""

        # SearXNG Web Search - Automatic and user-friendly
        web_results = []
        searxng_error_message = None
        
        if request.use_web_search and last_message["role"] == "user":
            try:
                current_date = datetime.now().strftime("%B %d, %Y")
                current_year = datetime.now().year
                
                # Initialize SearXNG service
                searxng = SearXNGService(base_url=request.searxng_url)
                
                # Quick health check
                if not searxng.health_check():
                    print(f"[Web Search] SearXNG is not available at {request.searxng_url}")
                    searxng_error_message = "Web search is currently unavailable. SearXNG service is not running."
                else:
                    # Always append current date to encourage fresh results
                    search_query = f"{last_message['content']} {current_date}"
                    print(f"[Web Search] Using SearXNG at {request.searxng_url}")
                    print(f"[Web Search] Query: {search_query}")
                    
                    # Perform search with time_range='day' for freshest results
                    # Fetch more results initially (20) to allow for effective deduplication
                    all_results = searxng.search(
                        query=search_query,
                        count=20,
                        time_range="day",
                        timeout=15
                    )
                    
                    if all_results:
                        # Score results by freshness
                        scored_results = searxng.score_by_freshness(
                            all_results, 
                            current_date, 
                            current_year
                        )
                        
                        # Take top 5-7 results after scoring and deduplication
                        web_results = [r for _, r in scored_results[:7]]
                        
                        print(f"[Web Search] Found {len(all_results)} results, selected top {len(web_results)} by freshness")
                        for idx, (score, result) in enumerate(scored_results[:7]):
                            print(f"  #{idx+1} (score={score}): {result.get('name', 'No title')[:60]}")
                    else:
                        print(f"[Web Search] No results found")
                    
            except Exception as e:
                print(f"[Web Search] Error: {e}")
                searxng_error_message = f"Web search encountered an error: {str(e)}"

        # Build context for LLM with strong warnings about data reliability
        if web_results:
            # Check if ANY result has a valid datePublished
            has_dates = any(result.get('datePublished') for result in web_results)
            
            # Format results and log what we're sending
            search_context = ""
            for idx, item in enumerate(web_results, 1):
                title = item.get('name') if item.get('name') is not None else 'Untitled'
                url = item.get('url') if item.get('url') is not None else ''
                summary = item.get('summary') if item.get('summary') is not None else 'No summary available'
                date_pub = item.get('datePublished') if item.get('datePublished') is not None else 'Unknown'
                
                # Debug: log the actual summary content
                print(f"[Web Search] Result #{idx} summary: {summary[:200]}...")
                
                search_context += f"\nSOURCE {idx}:\n"
                search_context += f"Title: {title}\n"
                search_context += f"URL: {url}\n"
                search_context += f"Date: {date_pub}\n"
                search_context += f"Content: {summary}\n"
            
            current_system_prompt += f"""

═══════════════════════════════════════════════════════
🌐 WEB SEARCH REPORT ({datetime.now().strftime('%B %d, %Y')})
═══════════════════════════════════════════════════════
{search_context}
═══════════════════════════════════════════════════════

INSTRUCTIONS FOR SYNTHESIS & NARRATIVE:

You are an expert analyst. Your goal is to synthesize the information above into a coherent, well-written narrative.

1. 🧠 SYNTHESIZE, DON'T LIST:
   - DO NOT create a list of "Source 1 says... Source 2 says...".
   - Instead, combine facts into a unified story.
   - Example: "XRP is currently trading around $2.10, with a slight upward trend observed across major exchanges like Bitget and Binance."

2. 🔍 EXTRACT & USE DATA:
   - Aggressively extract prices, dates, and hard numbers from the summaries.
   - If multiple sources confirm a number (e.g., $2.10), state it as a fact.
   - If sources disagree, mention the range (e.g., "trading between $2.08 and $2.12").

3. ✍️ NATURAL CITATIONS:
   - Integrate sources naturally into your sentences.
   - BAD: "According to Source 1 [URL], the price is X."
   - GOOD: "Major exchanges like Bitget ([Source](URL)) and Binance ([Source](URL)) report the price at..."
   - ALWAYS include the URL in parentheses next to the source name.

4. 🛡️ QUALITY CHECK:
   - Before answering, ask yourself: "Am I just repeating headlines?"
   - If yes, rewrite to explain the *meaning* of the news.
   - Deduplicate information: if 3 sources say the same thing, say it once and cite all 3.

5. ⛔ PROHIBITED:
   - DO NOT use your old training data (2023 cutoff).
   - DO NOT say "Information not available" if it IS in the summaries.
   - DO NOT be robotic. Be helpful, direct, and professional.

Answer the user's question now, using ONLY the web search results above.
"""
        elif request.use_web_search and searxng_error_message:
            # Web search was requested but SearXNG is not available
            current_system_prompt += f"""

[System Note: Web search is enabled but currently unavailable.
Reason: {searxng_error_message}

Please inform the user that web search is temporarily unavailable and answer using your general knowledge.
Mention that they can still get answers but they may not include the latest information.]
"""
        elif request.use_web_search:
            current_system_prompt += f"""

[System Note: Web search returned no results. You MUST inform the user that no current information is available.
DO NOT use your training data to answer this question. Your training data is outdated (2023 or earlier).
Today's date is: {datetime.now().strftime('%B %d, %Y')}]
"""

        ollama_messages = [{"role": "system", "content": current_system_prompt}] + request.messages

        async def generate():
            full_response = ""
            try:
                for chunk in ollama.chat(model=request.model, messages=ollama_messages, stream=True):
                    if "message" in chunk and "content" in chunk["message"]:
                        content = chunk["message"]["content"]
                        full_response += content
                        yield json.dumps({"content": content}) + "\n"
                
                # Save messages to DB
                if conversation_id:
                    database.add_message(conversation_id, last_message["role"], last_message["content"])
                    msgs = database.get_messages(conversation_id)
                    if len(msgs) <= 1:
                        new_title = last_message["content"][:30] + "..."
                        database.update_conversation_title(conversation_id, new_title)
                    database.add_message(conversation_id, "assistant", full_response)
            except Exception as e:
                yield json.dumps({"error": str(e)}) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"X-Conversation-ID": conversation_id},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
