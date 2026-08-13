"""
indexing/chunker.py
-------------------
Phase 3.1: Text Cleaning & Chunking

Reads raw scraped text from data/raw/, cleans boilerplate, 
and chunks the text into manageable pieces for vector search.
"""

import json
import logging
import re
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CLEANED_DIR = BASE_DIR / "data" / "cleaned"
CLEANED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Cleaning Utilities
# ---------------------------------------------------------------------------

def clean_text(raw_text: str) -> str:
    """
    Remove excessive newlines and spaces. The heavy lifting of 
    boilerplate removal is now handled by scraper.py.
    """
    # Remove excessive consecutive newlines and spaces
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

# ---------------------------------------------------------------------------
# Core Chunker Logic
# ---------------------------------------------------------------------------

def chunk_documents(metadata_path: str | Path) -> List[Document]:
    """
    Read metadata, load raw text files, clean them, and chunk them.
    
    Returns
    -------
    List[Document]
        A list of Langchain Document objects with populated metadata.
    """
    metadata_path = Path(metadata_path)
    if not metadata_path.exists():
        logger.error("Metadata file not found: %s", metadata_path)
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_registry = json.load(f)

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    # Configure the character chunker as secondary fallback
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    all_docs = []

    for entry in metadata_registry:
        doc_id = entry.get("id")
        raw_file_rel = entry.get("raw_file")
        
        if not raw_file_rel:
            logger.warning("Skipping %s: Not ingested yet (no raw_file)", doc_id)
            continue
            
        raw_file_abs = BASE_DIR / raw_file_rel
        if not raw_file_abs.exists():
            logger.warning("Skipping %s: File %s does not exist", doc_id, raw_file_abs)
            continue
            
        logger.info("Processing & Chunking: %s", doc_id)
        
        # Read the raw text
        with open(raw_file_abs, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        # Clean the text
        cleaned_text = clean_text(raw_text)
        
        # Save cleaned text for review/debugging
        cleaned_file = CLEANED_DIR / f"{doc_id}.txt"
        with open(cleaned_file, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        
        if not cleaned_text:
            logger.warning("Skipping %s: No text remained after cleaning", doc_id)
            continue
            
        # Construct metadata dict for the chunks
        chunk_meta = {
            "source_id": doc_id,
            "source_url": entry.get("source_url", ""),
            "source_name": entry.get("source_name", ""),
            "doc_type": entry.get("doc_type", "unknown"),
            "scheme": entry.get("scheme", "general"),
            "amc": entry.get("amc", "general"),
            "ingested_at": entry.get("ingested_at", "Unknown Date"),
        }
        
        # Split by Markdown headers first
        md_docs = markdown_splitter.split_text(cleaned_text)
        
        # Inject our base metadata into all markdown splits
        for doc in md_docs:
            doc.metadata.update(chunk_meta)
            
        # Then split by size if any markdown section is still too large
        chunks = text_splitter.split_documents(md_docs)
        
        # Filter out chunks that are too small (EC-016)
        valid_chunks = [c for c in chunks if len(c.page_content.strip()) >= 30]
        
        logger.info("  -> Created %d chunks (%d valid)", len(chunks), len(valid_chunks))
        all_docs.extend(valid_chunks)

    logger.info("Total chunks created across all documents: %d", len(all_docs))
    return all_docs


# ---------------------------------------------------------------------------
# Smoke Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    test_meta = BASE_DIR / "data" / "metadata.json"
    print(f"\n{'='*70}\nTesting Text Cleaning & Chunking (Phase 3.1)\n{'='*70}")
    
    docs = chunk_documents(test_meta)
    
    if docs:
        print(f"\n[OK] Successfully created {len(docs)} chunks total.")
        print("\n--- Sample Chunk (Index 0) ---")
        print(f"Metadata: {json.dumps(docs[0].metadata, indent=2)}")
        print(f"Content length: {len(docs[0].page_content)} chars")
        
        # ASCII-safe preview
        preview = docs[0].page_content[:400].encode('ascii', errors='replace').decode('ascii')
        print(f"Content Preview:\n{preview}...\n")
        
        # Let's also look at a chunk from the middle
        mid = len(docs) // 2
        print(f"\n--- Sample Chunk (Index {mid}) ---")
        print(f"Metadata: {json.dumps(docs[mid].metadata, indent=2)}")
        print(f"Content length: {len(docs[mid].page_content)} chars")
        
        mid_preview = docs[mid].page_content[:400].encode('ascii', errors='replace').decode('ascii')
        print(f"Content Preview:\n{mid_preview}...\n")
    else:
        print("\n[FAIL] No chunks generated.")
