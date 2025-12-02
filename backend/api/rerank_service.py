from flashrank import Ranker, RerankRequest
import os

# Global cache
_ranker = None

def get_ranker():
    global _ranker
    if _ranker is None:
        print("[RerankService] Loading FlashRank (MiniLM)...")
        # Uses a tiny quantized model (~40MB)
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="./model_cache")
        print("[RerankService] FlashRank loaded.")
    return _ranker

def rerank_documents(query: str, documents: list[dict], top_k: int = 3) -> list[dict]:
    """
    Rerank a list of documents based on the query.
    documents: List of dicts, must contain 'content' and 'metadata'.
    """
    if not documents:
        return []
        
    ranker = get_ranker()
    
    # Prepare for FlashRank
    passages = [
        {"id": str(i), "text": doc["content"], "meta": doc.get("metadata", {})} 
        for i, doc in enumerate(documents)
    ]
    
    rerank_request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(rerank_request)
    
    # Sort results by score and take top_k
    # FlashRank returns a list of results with 'score'
    
    # Map back to original format
    reranked_docs = []
    for res in results[:top_k]:
        # res is like {'id': '0', 'text': '...', 'meta': ..., 'score': 0.9}
        reranked_docs.append({
            "content": res["text"],
            "metadata": res["meta"],
            "score": res["score"]
        })
        
    return reranked_docs
