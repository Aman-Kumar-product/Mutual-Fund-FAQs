"""
indexing/embedder.py
--------------------
Handles loading and generating embeddings using the local BGE model.
"""

import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# BGE is a top-performing embedding model of reasonable size
MODEL_NAME = "BAAI/bge-base-en-v1.5"

# BGE requires this prefix for queries to perform optimally against document embeddings
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model_instance = None

def get_model() -> SentenceTransformer:
    """Returns a singleton instance of the SentenceTransformer model."""
    global _model_instance
    if _model_instance is None:
        logger.info(f"Loading embedding model: {MODEL_NAME} ...")
        try:
            _model_instance = SentenceTransformer(MODEL_NAME)
        except OSError as e:
            logger.error(f"Model not found. Run once with internet access to download. Details: {e}")
            raise
    return _model_instance

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embeds a list of document texts.
    Documents do not require the BGE query prefix.
    """
    if not texts:
        return []
    
    model = get_model()
    # normalize_embeddings=True is recommended for cosine similarity
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()

def embed_query(query: str) -> list[float]:
    """
    Embeds a single query string, prepending the necessary BGE prefix.
    """
    model = get_model()
    prefixed_query = BGE_QUERY_PREFIX + query
    embedding = model.encode(prefixed_query, normalize_embeddings=True)
    return embedding.tolist()
