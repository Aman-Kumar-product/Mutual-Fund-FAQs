"""
indexing/build_index.py
-----------------------
Orchestrates loading JSON files, embedding them, and inserting into ChromaDB.
"""
import json
import logging
from pathlib import Path

from indexing.embedder import embed_texts
from retrieval.vector_store import get_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CLEANED_DIR = BASE_DIR / "data" / "cleaned"

from indexing.chunker import chunk_documents

def build_index():
    collection = get_collection()
    
    # Load metadata registry
    metadata_path = BASE_DIR / "data" / "metadata.json"
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_registry = json.load(f)
    meta_dict = {entry["id"]: entry for entry in metadata_registry if "id" in entry}

    # --- PIPELINE 1: Structured JSON (Tier 1 & 2) ---
    json_files = list(CLEANED_DIR.glob("*.json"))
    
    ids = []
    documents = []
    metadatas = []

    if json_files:
        for file_path in json_files:
            doc_id = file_path.stem
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Format the JSON into a readable document chunk for embedding
            content = f"Fund Document ID: {doc_id}\n"
            for key, value in data.items():
                if value is not None:
                    formatted_key = key.replace("_", " ").title()
                    content += f"{formatted_key}: {value}\n"
                    
            documents.append(content)
            ids.append(f"{doc_id}_json")
            entry = meta_dict.get(doc_id, {})
            metadatas.append({
                "source_id": doc_id, 
                "doc_type": "structured",
                "scheme": entry.get("scheme", "general"),
                "source_url": entry.get("source_url", ""),
                "source_name": entry.get("source_name", ""),
                "ingested_at": entry.get("ingested_at", "Unknown Date")
            })
    else:
        logger.warning("No JSON files found in data/cleaned/")

    # --- PIPELINE 2: Unstructured Documents (Tier 3) ---
    metadata_path = BASE_DIR / "data" / "metadata.json"
    raw_chunks = chunk_documents(metadata_path)
    
    # Filter for Tier 3 docs (documents not processed as JSON)
    # We will just ingest all raw chunks for PDFs.
    for i, chunk in enumerate(raw_chunks):
        if chunk.metadata.get("content_type") == "pdf" or chunk.metadata.get("doc_type") in ["kim", "factsheet", "sid", "circular"]:
            documents.append(chunk.page_content)
            ids.append(f"{chunk.metadata.get('source_id')}_chunk_{i}")
            # Ensure metadata values are strings, ints, floats, or bools
            clean_metadata = {k: v for k, v in chunk.metadata.items() if v is not None}
            clean_metadata["doc_type"] = "unstructured_" + clean_metadata.get("doc_type", "unknown")
            metadatas.append(clean_metadata)

    if not documents:
        logger.warning("No documents to index.")
        return

    logger.info(f"Generating embeddings for {len(documents)} documents (Structured + Unstructured)...")
    # BGE embedder
    embeddings = embed_texts(documents)

    logger.info("Upserting into ChromaDB...")
    # Upsert handles inserting or updating existing entries by ID
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
    
    logger.info(f"Successfully indexed {len(documents)} documents into ChromaDB.")

if __name__ == "__main__":
    build_index()
