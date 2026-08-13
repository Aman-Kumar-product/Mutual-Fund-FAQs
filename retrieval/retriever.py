"""
retrieval/retriever.py
----------------------
Handles querying the ChromaDB vector store using BGE embeddings.
"""

from indexing.embedder import embed_query
from retrieval.vector_store import get_collection

def extract_scheme_from_query(query: str) -> str | None:
    query_lower = query.lower()
    if "mid cap" in query_lower or "midcap" in query_lower:
        return "HDFC Mid Cap Opportunities Fund"
    if "defence" in query_lower or "defense" in query_lower:
        return "HDFC Defence Fund"
    if "silver" in query_lower:
        return "HDFC Silver ETF FoF"
    if "equity" in query_lower:
        return "HDFC Equity Fund"
    return None

def retrieve(query: str, top_k: int = 5, scheme_filter: str | None = None) -> list[dict]:
    """
    Retrieves the top_k most relevant chunks for a given query.
    Returns a list of dicts with 'text' and 'metadata'.
    """
    collection = get_collection()
    query_embedding = embed_query(query)
    
    where = None
    if scheme_filter:
        where = {"scheme": scheme_filter}
        
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where
    )
    
    if not results['documents'] or not results['documents'][0]:
        return []
        
    chunks = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        chunks.append({
            "text": doc,
            "metadata": meta
        })
        
    return chunks

if __name__ == "__main__":
    # Quick sanity test
    import sys
    test_query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the expense ratio for HDFC Defence fund?"
    print(f"Query: {test_query}")
    
    res = retrieve(test_query, top_k=2)
    for i, r in enumerate(res):
        print(f"\n--- Result {i+1} ---")
        print(f"Metadata: {r['metadata']}")
        print(f"Text:\n{r['text'].encode('utf-8', errors='replace').decode('utf-8')}")
