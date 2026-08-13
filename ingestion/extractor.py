"""
ingestion/extractor.py
----------------------
Information Extraction Pipeline (Phase 3.1)

Reads raw Markdown scraped from data/raw/ and uses LLM (Groq)
with structured output to extract strictly the factual key-value pairs
required by the Problem Statement into a clean JSON file.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables (for GROQ_API_KEY)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_PATH = BASE_DIR / "data" / "metadata.json"
RAW_DIR = BASE_DIR / "data" / "raw"
CLEANED_DIR = BASE_DIR / "data" / "cleaned"

CLEANED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Schema Definition (Strictly tied to problemStatement.md)
# ---------------------------------------------------------------------------

class FundDetails(BaseModel):
    """Extraction schema for mutual fund details and investor facts."""
    # Tier 1 Fields
    expense_ratio: Optional[str] = Field(description="The expense ratio of the fund (e.g. '0.90%')")
    minimum_sip: Optional[str] = Field(description="The minimum SIP amount for the fund (e.g. '₹100')")
    minimum_investment: Optional[str] = Field(description="The minimum initial investment amount")
    exit_load: Optional[str] = Field(description="The exit load conditions (e.g. '1% if redeemed within 1 year')")
    riskometer_rating: Optional[str] = Field(description="The risk rating of the fund (e.g. 'Very High')")
    fund_manager: Optional[str] = Field(description="The name of the fund manager(s)")
    benchmark: Optional[str] = Field(description="The benchmark index of the fund")
    category: Optional[str] = Field(description="The category of the mutual fund (e.g. 'Mid Cap Fund')")
    investment_objective: Optional[str] = Field(description="The investment objective of the scheme")
    plan_option: Optional[str] = Field(description="The plan or option (e.g. 'Direct Growth')")

    # Tier 2 Fields
    asset_allocation: Optional[str] = Field(description="Details about asset allocation (e.g. 'Equity: 90%, Debt: 10%')")
    portfolio_characteristics: Optional[str] = Field(description="Portfolio characteristics or ratios like P/E, P/B if mentioned")
    inception_date: Optional[str] = Field(description="The inception date or launch date of the fund")
    nav_and_date: Optional[str] = Field(description="The latest NAV and its date (e.g. '₹150.5 on Aug 10, 2026')")
    additional_investment_minimum: Optional[str] = Field(description="Minimum amount for additional purchase/investment")
    purchase_redemption_info: Optional[str] = Field(description="Information regarding purchase or redemption process")
    cut_off_info: Optional[str] = Field(description="Cut-off timing for NAV applicability")

    # Extra
    elss_lock_in_period: Optional[str] = Field(description="The lock-in period if it is an ELSS fund (e.g. '3 years'). Null if not applicable.")
    download_capital_gains_statement: Optional[str] = Field(description="Instructions on how to download a capital gains statement, if present in the text.")

# ---------------------------------------------------------------------------
# Extraction Logic
# ---------------------------------------------------------------------------

def extract_facts_to_json():
    """Iterate over all ingested documents and extract facts to JSON."""
    if not METADATA_PATH.exists():
        logger.error("Metadata file not found: %s", METADATA_PATH)
        return

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Initialize the Groq Chat model with structured output
    # using llama-3.3-70b-versatile which is excellent at precise extraction
    llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
    structured_llm = llm.with_structured_output(FundDetails)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert financial data extractor. Extract the precise requested facts from the provided Mutual Fund document. If a specific fact is not present in the text, leave the field null. Do not hallucinate."),
        ("human", "Document text:\n\n{text}")
    ])

    extraction_chain = prompt | structured_llm

    stats = {"success": 0, "failed": 0, "skipped": 0}

    for entry in metadata:
        doc_id = entry.get("id")
        raw_file_rel = entry.get("raw_file")

        if not doc_id or not raw_file_rel:
            continue

        raw_file_abs = BASE_DIR / raw_file_rel
        out_file = CLEANED_DIR / f"{doc_id}.json"

        content_type = entry.get("content_type", "")
        doc_type = entry.get("doc_type", "")
        
        # Skip Tier 3 unstructured documents
        if content_type == "pdf" or doc_type in ["kim", "factsheet", "sid", "circular"]:
            logger.info("Skipping unstructured doc from extraction: %s", doc_id)
            stats["skipped"] += 1
            continue

        if out_file.exists():
            logger.info("Skipping already extracted doc: %s", doc_id)
            stats["skipped"] += 1
            continue

        if not raw_file_abs.exists():
            logger.warning("Raw file missing for %s", doc_id)
            stats["failed"] += 1
            continue

        logger.info("Extracting facts from %s...", doc_id)
        
        with open(raw_file_abs, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # If text is excessively long for Llama3 8k window, we might need to truncate
        # but our scraped markdown is generally ~400-500 lines, which easily fits.
        try:
            result: FundDetails = extraction_chain.invoke({"text": raw_text})
            
            with open(out_file, "w", encoding="utf-8") as out_f:
                # Use model_dump() for Pydantic v2
                json.dump(result.model_dump(), out_f, indent=2)
                
            stats["success"] += 1
            logger.info("Successfully extracted %s", doc_id)
            
        except Exception as e:
            logger.exception("Failed to extract %s: %s", doc_id, e)
            stats["failed"] += 1
            
        # Add a short delay to avoid hitting LLM rate limits (TPM)
        time.sleep(3)

    logger.info("Extraction complete. ✓ Success: %d | ✗ Failed: %d | ⏭ Skipped: %d", 
                stats["success"], stats["failed"], stats["skipped"])


if __name__ == "__main__":
    # Ensure GROQ API key is present
    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY environment variable is missing! Check .env file.")
        exit(1)
        
    extract_facts_to_json()
