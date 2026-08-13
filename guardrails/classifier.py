from typing import Literal
import numpy as np
from indexing.embedder import embed_query

ADVISORY_KEYWORDS = [
    "should i", "recommend", "best fund", "which is better",
    "buy", "sell", "invest in", "time to invest", "portfolio", "outperform",
    "which fund", "should i buy", "should i sell",
    "returns", "better returns", "performance"
]

ADVISORY_EXEMPLARS = [
    "Is this a good time to start a SIP?",
    "Which fund should I choose?",
    "Will this fund give good returns?",
    "Should I switch from HDFC Mid Cap to Equity Fund?",
]

_exemplar_embeddings = None

def _get_exemplar_embeddings():
    global _exemplar_embeddings
    if _exemplar_embeddings is None:
        _exemplar_embeddings = [embed_query(ex) for ex in ADVISORY_EXEMPLARS]
    return _exemplar_embeddings

def is_advisory_keyword(query: str) -> bool:
    query_lower = query.lower()
    for keyword in ADVISORY_KEYWORDS:
        if keyword in query_lower:
            return True
    return False

def is_advisory_semantic(query: str, threshold: float = 0.76) -> bool:
    query_embedding = embed_query(query)
    exemplar_embeddings = _get_exemplar_embeddings()
    
    max_score = 0.0
    for ex_emb in exemplar_embeddings:
        # Embeddings are normalized by embed_query so dot product = cosine similarity
        score = np.dot(query_embedding, ex_emb)
        if score > max_score:
            max_score = score
            
    return max_score > threshold

def classify(query: str) -> Literal["factual", "advisory"]:
    if is_advisory_keyword(query):
        return "advisory"
    if is_advisory_semantic(query):
        return "advisory"
    return "factual"
