"""
ingestion/pdf_parser.py
-----------------------
Parser for PDF documents in the Mutual Fund FAQ RAG pipeline.

For `content_type = "pdf"` entries:
Downloads the PDF via `requests` to a temporary file, extracts text
page-by-page using `PyMuPDF` (fitz), and returns the concatenated string
with page separators.

Public interface
----------------
    parse_pdf(url) -> str

Raises ValueError on download or parsing failures so callers can catch and log.
"""

import logging
import tempfile
import os

import requests
import pymupdf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: HTTP headers that mimic a real browser — reduces 403s
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}

#: requests: timeout in seconds
_REQUESTS_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PDFParserError(RuntimeError):
    """Raised when a PDF cannot be downloaded or parsed."""


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def parse_pdf(url: str) -> str:
    """
    Download a PDF from *url*, extract text page-by-page, and return
    a single string with page number separators.

    Parameters
    ----------
    url : str
        The direct URL to the PDF file.

    Returns
    -------
    str
        The extracted text.

    Raises
    ------
    PDFParserError
        If the download fails or the PDF cannot be processed.
    """
    logger.info("Downloading PDF: %s", url)

    # Use a NamedTemporaryFile to securely save the PDF to disk
    # This avoids loading potentially huge PDFs entirely into RAM at once
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)  # Close the file descriptor, we'll use the path with requests

    try:
        # 1. Download the PDF
        try:
            response = requests.get(
                url,
                headers=_HEADERS,
                timeout=_REQUESTS_TIMEOUT,
                stream=True
            )
            response.raise_for_status()

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as exc:
            raise PDFParserError(f"Failed to download PDF from {url}: {exc}") from exc

        # 2. Extract text with PyMuPDF
        logger.debug("Parsing PDF at temp path: %s", temp_path)
        extracted_text_chunks = []
        try:
            with pymupdf.open(temp_path) as doc:
                total_pages = len(doc)
                if total_pages == 0:
                    raise PDFParserError("The PDF document has 0 pages.")

                for page_num in range(total_pages):
                    page = doc.load_page(page_num)
                    # Extract text. 'text' preserves basic layout order.
                    text = page.get_text("text").strip()
                    
                    if text:
                        # Append page separator
                        extracted_text_chunks.append(f"\n--- Page {page_num + 1} ---\n")
                        extracted_text_chunks.append(text)
                    
        except Exception as exc:
            if not isinstance(exc, PDFParserError):
                raise PDFParserError(f"Failed to parse PDF using PyMuPDF: {exc}") from exc
            raise

        full_text = "\n".join(extracted_text_chunks).strip()
        
        if not full_text:
             raise PDFParserError(f"No text extracted from PDF (might be scanned images): {url}")
             
        logger.info("PDF parse OK: %d chars extracted across %d pages", len(full_text), total_pages)
        return full_text

    finally:
        # 3. Clean up the temporary file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError as e:
            logger.warning("Failed to clean up temp file %s: %s", temp_path, e)


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly: python -m ingestion.pdf_parser)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # A simple test PDF (SEBI master circular)
    test_url = "https://www.sebi.gov.in/sebi_data/attachdocs/1497258357731.pdf"
    
    # If a URL is passed via CLI, use that instead
    if len(sys.argv) > 1:
        test_url = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"Testing PDF parser")
    print(f"URL: {test_url}")
    print("="*60)

    try:
        text = parse_pdf(test_url)
        # Print preview (ASCII-safe)
        preview = text[:500].encode("ascii", errors="replace").decode("ascii")
        preview = preview.replace("\n", " | ")
        print(f"\n[OK] Extracted {len(text):,} chars")
        print(f"     Preview: {preview}...")
    except Exception as e:
        print(f"\n[FAIL] {e}")
