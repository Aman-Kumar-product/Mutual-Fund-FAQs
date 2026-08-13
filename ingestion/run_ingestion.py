"""
ingestion/run_ingestion.py
--------------------------
Ingestion orchestrator for the Mutual Fund FAQ RAG pipeline.

Reads data/metadata.json, processes each entry using the appropriate parser
(scraper for HTML, pdf_parser for PDFs), saves the raw text to data/raw/,
and updates metadata.json with the ingestion timestamp and file path.
Skips entries that have already been ingested.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from ingestion.scraper import scrape_document, ScraperError
from ingestion.pdf_parser import parse_pdf, PDFParserError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_PATH = BASE_DIR / "data" / "metadata.json"
RAW_DIR = BASE_DIR / "data" / "raw"

# Ensure raw directory exists
RAW_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------------

def run():
    logger.info("Starting ingestion pipeline...")
    
    if not METADATA_PATH.exists():
        logger.error(f"Metadata file not found: {METADATA_PATH}")
        return

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    stats = {"success": 0, "failed": 0, "skipped": 0}

    for entry in metadata:
        doc_id = entry.get("id")
        if not doc_id:
            logger.warning("Skipping entry with no 'id': %s", entry)
            stats["failed"] += 1
            continue

        # Idempotency check: skip if already ingested and file exists
        raw_file_rel = entry.get("raw_file")
        if raw_file_rel and entry.get("ingested_at"):
            raw_file_abs = BASE_DIR / raw_file_rel
            if raw_file_abs.exists():
                logger.info("Skipping already ingested document: %s", doc_id)
                stats["skipped"] += 1
                continue

        url = entry.get("source_url")
        content_type = entry.get("content_type")
        logger.info("Processing %s (%s)...", doc_id, content_type)
        
        try:
            # Dispatch to appropriate parser
            if content_type == "pdf":
                text = parse_pdf(url)
            elif content_type in ("html_static", "html_dynamic"):
                text = scrape_document(entry)
            else:
                raise ValueError(f"Unknown content_type: {content_type}")
            
            # Save raw text
            out_file = RAW_DIR / f"{doc_id}.txt"
            with open(out_file, "w", encoding="utf-8") as out_f:
                out_f.write(text)
            
            # Update entry metadata
            entry["raw_file"] = f"data/raw/{doc_id}.txt"
            entry["ingested_at"] = datetime.now(timezone.utc).isoformat()
            
            stats["success"] += 1
            logger.info("Successfully ingested %s", doc_id)
            
        except (ScraperError, PDFParserError, ValueError) as e:
            logger.error("Failed to ingest %s: %s", doc_id, e)
            stats["failed"] += 1
        except Exception as e:
            logger.exception("Unexpected error ingesting %s: %s", doc_id, e)
            stats["failed"] += 1

    # Save updated metadata
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    logger.info("Ingestion complete. ✓ Success: %d | ✗ Failed: %d | ⏭ Skipped: %d", 
                stats["success"], stats["failed"], stats["skipped"])

if __name__ == "__main__":
    run()
