from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from pydantic import BaseModel
import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
from typing import List
import pypdf
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings

# Suppress pypdf cryptography deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

# Import SOTA services
try:
    from .vision_service import extract_text_from_pdf_with_vision
    from .rerank_service import rerank_documents
except ImportError:
    # Fallback for running directly or if dependencies missing
    from api.vision_service import extract_text_from_pdf_with_vision
    from api.rerank_service import rerank_documents

router = APIRouter(prefix="/rag", tags=["rag"])

# Configuration
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "documents"
UPLOAD_DIR = "./uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB
MAX_FILES_PER_CHAT = 5

# Global progress tracker
# Format: { "conversation_id": { "status": "processing", "progress": 0, "message": "..." } }
upload_progress = {}

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize ChromaDB
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Use a lightweight embedding model
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=sentence_transformer_ef
    )
except Exception as e:
    print(f"Error initializing ChromaDB: {e}")
    # Fallback or handle error appropriately in production
    collection = None

class QueryRequest(BaseModel):
    query: str
    n_results: int = 3
    conversation_id: str | None = None

class DocumentInfo(BaseModel):
    id: str
    filename: str
    chunks: int

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: str = Form(...)
):
    global upload_progress
    upload_progress[conversation_id] = {"status": "starting", "progress": 0, "message": "Iniciando subida..."}
    
    if not collection:
        raise HTTPException(status_code=500, detail="Vector database not initialized")
        
    try:
        # Check file size (approximate, as we read it)
        # For strict checking we might need to read into memory or check headers if reliable
        
        # Check existing file count for this conversation
        existing_docs = collection.get(where={"conversation_id": conversation_id})['metadatas']
        unique_files = set(m['filename'] for m in existing_docs)
        if len(unique_files) >= MAX_FILES_PER_CHAT:
             raise HTTPException(status_code=400, detail=f"Limit reached: Maximum {MAX_FILES_PER_CHAT} files per chat.")

        # Save file temporarily
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Check size
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"File too large. Limit is {MAX_FILE_SIZE/1024/1024}MB.")
            
        # Extract text
        upload_progress[conversation_id] = {"status": "processing", "progress": 10, "message": "Leyendo archivo..."}
        text = ""
        if file.filename.lower().endswith(".pdf"):
            # Use Florence-2 Vision Service for SOTA extraction
            try:
                def update_progress(current, total):
                    percent = 10 + int((current / total) * 80) # 10% to 90%
                    upload_progress[conversation_id] = {
                        "status": "processing", 
                        "progress": percent, 
                        "message": f"Analizando página {current} de {total}..."
                    }
                
                # Run blocking vision extraction in a thread pool
                loop = asyncio.get_running_loop()
                text = await loop.run_in_executor(
                    None, 
                    lambda: extract_text_from_pdf_with_vision(file_path, progress_callback=update_progress)
                )
            except Exception as e:
                print(f"Vision extraction failed, falling back to pypdf: {e}")
                upload_progress[conversation_id] = {"status": "processing", "progress": 50, "message": "Vision falló, usando modo rápido..."}
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        else:
            # Assume text file
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")
            
        upload_progress[conversation_id] = {"status": "indexing", "progress": 90, "message": "Indexando documentos..."}
        
        # Chunk text (Simple chunking by characters for now)
        # In production, use a smarter splitter (recursive character splitter)
        chunk_size = 1000
        overlap = 100
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            
        # Add to ChromaDB
        ids = [f"{conversation_id}_{file.filename}_{i}" for i in range(len(chunks))]
        metadatas = [{"filename": file.filename, "chunk_index": i, "conversation_id": conversation_id} for i in range(len(chunks))]
        
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        # Clean up temp file
        os.remove(file_path)
        
        return {"status": "success", "filename": file.filename, "chunks_processed": len(chunks)}
        
    except Exception as e:
        upload_progress[conversation_id] = {"status": "error", "progress": 0, "message": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Keep success status for a moment so frontend sees 100%
        if conversation_id in upload_progress and upload_progress[conversation_id]["status"] != "error":
             upload_progress[conversation_id] = {"status": "complete", "progress": 100, "message": "Completado"}

@router.get("/progress/{conversation_id}")
async def get_upload_progress(conversation_id: str):
    return upload_progress.get(conversation_id, {"status": "idle", "progress": 0, "message": ""})

@router.get("/documents")
async def list_documents(conversation_id: str = Query(...)):
    if not collection:
        raise HTTPException(status_code=500, detail="Vector database not initialized")
        
    # Chroma doesn't have a direct "list unique metadata values" efficiently for all cases,
    # but we can get all metadata and aggregate. For small scale this is fine.
    try:
        result = collection.get(where={"conversation_id": conversation_id})
        metadatas = result['metadatas']
        
        docs = {}
        for meta in metadatas:
            filename = meta['filename']
            if filename not in docs:
                docs[filename] = 0
            docs[filename] += 1
            
        return {"documents": [{"filename": k, "chunks": v} for k, v in docs.items()]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{filename}")
async def delete_document(filename: str, conversation_id: str = Query(...)):
    if not collection:
        raise HTTPException(status_code=500, detail="Vector database not initialized")
        
    try:
        print(f"[RAG] Deleting document: {filename} for chat: {conversation_id}")
        collection.delete(where={"filename": filename, "conversation_id": conversation_id})
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_rag(request: QueryRequest):
    if not collection:
        raise HTTPException(status_code=500, detail="Vector database not initialized")
        
    try:
        where_clause = {}
        if request.conversation_id:
            where_clause["conversation_id"] = request.conversation_id

        results = collection.query(
            query_texts=[request.query],
            n_results=15, # Fetch more candidates for reranking
            where=where_clause
        )
        
        # Flatten results
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        # Prepare for Reranking
        candidates = []
        for i in range(len(documents)):
            candidates.append({
                "content": documents[i],
                "metadata": metadatas[i]
            })
            
        # Rerank with FlashRank
        reranked_results = rerank_documents(request.query, candidates, top_k=request.n_results)
        
        return {"results": reranked_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def query_collection(query_text: str, conversation_id: str = None, n_results: int = 3):
    """Internal helper to query the collection"""
    if not collection:
        return []
        
    where_clause = {}
    if conversation_id:
        where_clause["conversation_id"] = conversation_id

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_clause
    )
    return results['documents'][0]
