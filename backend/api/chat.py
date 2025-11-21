from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import ollama
import json
import database

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    model: str
    messages: list
    conversation_id: str | None = None
    stream: bool = True

class CreateChatRequest(BaseModel):
    title: str = "New Chat"

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

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    try:
        # If no conversation_id, create one? Or assume frontend handles it.
        # Let's assume frontend sends one, or we create one if missing.
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = database.create_conversation()

        # Save user message
        # The last message in request.messages is the user's new message
        # But request.messages contains the whole history usually.
        # Let's assume the frontend sends the full context for the LLM, 
        # but we only need to save the *new* user message to the DB.
        # Actually, to be safe and stateless, the frontend should probably just send the new message 
        # and we reconstruct history? 
        # For now, to match existing logic: 
        # We'll assume the frontend sends the full list. We need to extract the last user message to save it.
        # OR, better: The frontend sends the `messages` array for the LLM context, 
        # and we just append the *new* interaction to the DB.
        
        # Let's look at the last message.
        last_message = request.messages[-1]
        if last_message['role'] == 'user':
            database.add_message(conversation_id, 'user', last_message['content'])
            
            # Update title if it's the first message and title is "New Chat"
            # (Simple heuristic: if only 1 user message in DB)
            msgs = database.get_messages(conversation_id)
            if len(msgs) <= 1: # 1 user message
                # Generate a title? For now just use first few words
                new_title = last_message['content'][:30] + "..."
                database.update_conversation_title(conversation_id, new_title)

        def generate():
            full_response = ""
            stream = ollama.chat(
                model=request.model,
                messages=request.messages,
                stream=True
            )
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    full_response += content
                    yield content
            
            # Save assistant response after streaming finishes
            database.add_message(conversation_id, 'assistant', full_response)
        
        return StreamingResponse(
            generate(), 
            media_type="text/plain",
            headers={"X-Conversation-ID": conversation_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
