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
    conversations = await database.get_conversations()
    return {"conversations": conversations}

@router.post("/new")
async def create_chat(request: CreateChatRequest):
    chat_id = await database.create_conversation(request.title)
    return {"id": chat_id, "title": request.title}

@router.get("/{conversation_id}")
async def get_chat_messages(conversation_id: str):
    messages = await database.get_messages(conversation_id)
    return {"messages": messages}

@router.delete("/{conversation_id}")
async def delete_chat(conversation_id: str):
    await database.delete_conversation(conversation_id)
    return {"status": "success"}

@router.put("/{conversation_id}/title")
async def rename_chat(conversation_id: str, request: RenameChatRequest):
    await database.update_conversation_title(conversation_id, request.title)
    return {"status": "success", "title": request.title}

SYSTEM_PROMPT = """Helpful assistant. Respond in user's language.
If using RAG context, answer ONLY based on context.
ALWAYS use LaTeX for mathematical equations.
- Use $...$ for inline math (e.g., $E=mc^2$).
- Use $$...$$ for block math.
- Do NOT use unicode characters for math (like θ or ∑), use LaTeX commands (\\theta, \\sum).
Always wrap subscripts: $d_1$, $x^2$.
Code: `inline` or ```blocks```."""

async def generate_search_queries(messages: list, model: str = "gemma3:4b") -> dict:
    """
    Uses the LLM to analyze conversation context and decide the best action:
    - Read a specific URL from the context, OR
    - Generate optimized web search queries
    
    Args:
        messages: Full conversation history
        model: LLM model to use for decision-making
    
    Returns:
        dict with either:
        - {"type": "url", "url": "https://..."} to read a URL
        - {"type": "search", "queries": ["query1", "query2", ...]} for web search
    """
    # Get last 5 messages for context (if available)
    recent_messages = messages[-5:] if len(messages) > 5 else messages
    
    # Build conversation context
    conversation_context = ""
    for msg in recent_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        conversation_context += f"{role.upper()}: {content}\n"
    
    # FAST PATH: Check if URLs exist, if not go straight to search
    import re
    has_urls = any(re.search(r'https?://[^\s]+', msg.get("content", "")) for msg in recent_messages)
    
    # Get last user message
    last_user_content = ""
    for msg in reversed(recent_messages):
        if msg.get("role") == "user":
            last_user_content = msg.get("content", "")
            break
    
    # Fast path: generate queries directly (skip decision LLM)
    if not has_urls:
        print(f"[Fast Path] Generating queries")
        query_prompt = f'Generate 2 English search queries for: "{last_user_content}"\nJSON: ["query1", "query2"]'
        
        try:
            client = ollama.AsyncClient()
            response = await client.chat(model=model, messages=[{"role": "user", "content": query_prompt}], stream=False)
            response_text = response["message"]["content"].strip()
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                queries = json.loads(json_match.group())
                if isinstance(queries, list) and len(queries) > 0:
                    return {"type": "search", "queries": queries[:2]}
        except Exception as e:
            print(f"[Fast Path] Failed: {e}")
        
        return {"type": "search", "queries": [last_user_content]}
    
    decision_prompt = f"""CONVERSATION:
{conversation_context}

TASK: Is the user asking about a URL mentioned earlier? Or do they need a web search?

A) URL mentioned earlier + user asks about it → {{"type": "url", "url": "URL"}}
B) No URL or different topic → {{"type": "search", "queries": ["query1", "query2"]}}

QUERY RULES (if search):
- User language: Detect from conversation. Generate queries in the SAME language.
- 1-3 specific keywords (not sentences)
- Add year/"latest" if relevant

JSON only:"""
    
    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model=model,
            messages=[{"role": "user", "content": decision_prompt}],
            stream=False
        )
        
        response_text = response["message"]["content"].strip()
        
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group())
            
            # Validate the decision structure
            if decision.get("type") == "url" and "url" in decision:
                print(f"[LLM Decision] Read URL: {decision['url']}")
                return decision
            elif decision.get("type") == "search" and "queries" in decision:
                queries = decision["queries"]
                if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                    print(f"[LLM Decision] Web search with {len(queries)} queries: {queries}")
                    return {"type": "search", "queries": queries[:3]}  # Limit to 3
        
        # Fallback: if parsing fails, do web search with last user message
        print(f"[LLM Decision] Failed to parse decision, falling back to search")
        last_user_msg = [m["content"] for m in messages if m.get("role") == "user"][-1]
        return {"type": "search", "queries": [last_user_msg]}
        
    except Exception as e:
        print(f"[LLM Decision] Error: {e}, falling back to search")
        # Fallback to search with last user message
        last_user_msg = [m["content"] for m in messages if m.get("role") == "user"][-1]
        return {"type": "search", "queries": [last_user_msg]}

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    try:
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = await database.create_conversation()
        current_system_prompt = SYSTEM_PROMPT
        last_message = request.messages[-1]

        async def generate():
            nonlocal current_system_prompt
            # Yield initial status
            yield json.dumps({"status": "Iniciando..."}) + "\n"

            # RAG Integration
            if request.use_rag and last_message["role"] == "user":
                yield json.dumps({"status": "Consultando documentos..."}) + "\n"
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

            # SearXNG Web Search / URL Reading - LLM-driven decision
            web_results = []
            url_content = None
            searxng_error_message = None
            
            if request.use_web_search and last_message["role"] == "user":
                try:
                    yield json.dumps({"status": "Analizando intención..."}) + "\n"
                    from api.url_reader import read_url_content
                    
                    current_date = datetime.now().strftime("%B %d, %Y")
                    current_year = datetime.now().year
                    
                    # Step 1: Let LLM decide: read URL or web search?
                    decision = await generate_search_queries(request.messages, request.model)
                    
                    if decision["type"] == "url":
                        # LLM decided to read a specific URL from context
                        target_url = decision["url"]
                        yield json.dumps({"status": f"Leyendo URL: {target_url}..."}) + "\n"
                        print(f"[Action] Reading URL: {target_url}")
                        
                        url_content = await read_url_content(target_url)
                        print(f"[URL Reader] Read {len(url_content)} characters from {target_url}")
                        
                    elif decision["type"] == "search":
                        # LLM decided to perform web search
                        optimized_queries = decision["queries"]
                        yield json.dumps({"status": f"Buscando: {optimized_queries[0]}..."}) + "\n"
                        print(f"[Action] Web search with {len(optimized_queries)} queries")
                        
                        # Initialize SearXNG service
                        searxng = SearXNGService(base_url=request.searxng_url)
                        
                        # Quick health check
                        if not await searxng.health_check():
                            print(f"[Web Search] SearXNG is not available at {request.searxng_url}")
                            searxng_error_message = "Web search is currently unavailable. SearXNG service is not running."
                        else:
                            print(f"[Web Search] Using SearXNG at {request.searxng_url}")
                            
                            # Perform searches for each optimized query
                            all_results = []
                            seen_urls = set()
                            
                            for query_idx, search_query in enumerate(optimized_queries, 1):
                                yield json.dumps({"status": f"Buscando: {search_query}..."}) + "\n"
                                # Don't add date to query - let time_range handle freshness
                                print(f"[Web Search] Query #{query_idx}: {search_query}")
                                
                                # Perform search with time_range='year' for better quality results
                                # 'day' is too restrictive for evergreen content like books/tutorials
                                query_results = await searxng.search(
                                    query=search_query,
                                    count=15,  # Reduced per query since we're doing multiple queries
                                    time_range="year",  # Changed from 'day' to 'year'
                                    timeout=15
                                )
                                
                                # Deduplicate by URL across all queries
                                for result in query_results:
                                    url = result.get('url')
                                    if url and url not in seen_urls:
                                        seen_urls.add(url)
                                        all_results.append(result)
                                
                                print(f"[Web Search]   Found {len(query_results)} results for query #{query_idx}")
                            
                            if all_results:
                                yield json.dumps({"status": "Filtrando y clasificando resultados..."}) + "\n"
                                # Score results by freshness
                                scored_results = searxng.score_by_freshness(
                                    all_results, 
                                    current_date, 
                                    current_year
                                )
                                
                                # Take top 8 results after scoring, filtering, and deduplication
                                web_results = [r for _, r in scored_results[:8]]
                                
                                print(f"[Web Search] Total unique results: {len(all_results)}, selected top {len(web_results)} by freshness")
                                for idx, (score, result) in enumerate(scored_results[:8]):
                                    print(f"  #{idx+1} (score={score}): {result.get('name', 'No title')[:60]}")
                            else:
                                print(f"[Web Search] No results found across all queries")
                        
                except Exception as e:
                    print(f"[Web Search] Error: {e}")
                    searxng_error_message = f"Web search encountered an error: {str(e)}"

            # Build context for LLM
            yield json.dumps({"status": "Sintetizando respuesta..."}) + "\n"
            if url_content:
                # URL was read directly
                current_system_prompt += f"""

URL CONTENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{url_content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the above URL content to answer the user's question accurately.
"""
            elif web_results:
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

WEB RESULTS:
{search_context}

Answer using above info. Cite sources: [Name](URL). If no answer, say so.
"""
            elif request.use_web_search and searxng_error_message:
                # Web search was requested but SearXNG is not available
                current_system_prompt += f"""

[Web search unavailable: {searxng_error_message}
Inform the user and answer using general knowledge. Mention information may not be current.]
"""
            elif request.use_web_search:
                current_system_prompt += f"""

[No web results found. Inform the user. DO NOT use training data (2023 cutoff). Today: {datetime.now().strftime('%B %d, %Y')}]
"""

            ollama_messages = [{"role": "system", "content": current_system_prompt}] + request.messages

            full_response = ""
            client = ollama.AsyncClient()
            try:
                # Clear status before streaming content
                # yield json.dumps({"status": ""}) + "\n"
                async for chunk in await client.chat(model=request.model, messages=ollama_messages, stream=True):
                    if "message" in chunk and "content" in chunk["message"]:
                        content = chunk["message"]["content"]
                        full_response += content
                        yield json.dumps({"content": content}) + "\n"
                
                # Save messages to DB
                if conversation_id:
                    await database.add_message(conversation_id, last_message["role"], last_message["content"])
                    msgs = await database.get_messages(conversation_id)
                    if len(msgs) <= 1:
                        new_title = last_message["content"][:30] + "..."
                        await database.update_conversation_title(conversation_id, new_title)
                    await database.add_message(conversation_id, "assistant", full_response)
            except Exception as e:
                yield json.dumps({"error": str(e)}) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"X-Conversation-ID": conversation_id},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
