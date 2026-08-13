"""
retrieval/vector_store.py
-------------------------
Manages the connection to the local ChromaDB persistent store.
"""

from pathlib import Path
import chromadb
from chromadb.config import Settings

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"

_client = None

def get_client() -> chromadb.PersistentClient:
    """Returns a singleton PersistentClient for ChromaDB."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
    return _client

def get_collection() -> chromadb.Collection:
    """Gets or creates the main mutual_fund_faq collection."""
    client = get_client()
    # We do NOT use Chroma's built-in embedding function because we are managing
    # BGE embeddings manually via indexing/embedder.py to handle prefixes correctly.
    return client.get_or_create_collection(name="mutual_fund_faq")
