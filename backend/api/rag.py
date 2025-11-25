from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from pydantic import BaseModel
import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
from typing import List
import pypdf
import shutil
import warnings

# Suppress pypdf cryptography deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

router = APIRouter(prefix="/rag", tags=["rag"])

# Configuration
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "documents"
UPLOAD_DIR = "./uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB
MAX_FILES_PER_CHAT = 5

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
        text = ""
        if file.filename.lower().endswith(".pdf"):
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        else:
            # Assume text file
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")
            
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
        raise HTTPException(status_code=500, detail=str(e))

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
            n_results=request.n_results,
            where=where_clause
        )
        
        # Flatten results
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        response = []
        for i in range(len(documents)):
            response.append({
                "content": documents[i],
                "metadata": metadatas[i],
                "distance": distances[i]
            })
            
        return {"results": response}
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
