"""
ingestion/scraper.py
--------------------
Two-mode HTML scraper for the Mutual Fund FAQ RAG pipeline.

Mode A — Static HTML  (content_type = "html_static")
    Uses requests + BeautifulSoup.  Fast, no browser required.
    Strips boilerplate (nav, footer, ads, scripts, styles) and
    returns the core body text.

Mode B — Dynamic HTML (content_type = "html_dynamic")
    Uses Playwright headless Chromium to fully render JS-heavy
    pages (e.g. Groww scheme pages).  Waits for the main content
    block to appear before extracting text.

Public interface
----------------
    scrape_static(url)          -> str
    scrape_dynamic(url)         -> str
    scrape_document(entry)      -> str   # dispatches on content_type

Both functions raise ScraperError on unrecoverable failures so
callers (run_ingestion.py) can catch, log, and continue.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup
import markdownify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: HTTP headers that mimic a real browser — reduces 403s on financial sites
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

#: Tags whose entire subtrees are noise — stripped before text extraction
_NOISE_TAGS = [
    "script", "style", "noscript",
    "nav", "header", "footer",
    "aside", "advertisement", "iframe",
    "button", "form", "input", "select",
    "svg", "img",
]

#: CSS selectors tried in order to locate the main content block (static pages)
_MAIN_CONTENT_SELECTORS = [
    "main",
    "article",
    '[role="main"]',
    ".content",
    "#content",
    ".main-content",
    "#main-content",
    ".article-body",
    ".page-body",
]

#: Playwright: CSS selectors that indicate Groww / scheme page content is ready
_DYNAMIC_READY_SELECTORS = [
    # Groww fund page — key data sections
    ".fundName",
    ".schemeDetailWrapper",
    "[class*='fundInfo']",
    "[class*='schemeHeader']",
    # Generic fallback — any visible heading
    "h1",
]

#: Playwright: maximum seconds to wait for page + content selector
_PLAYWRIGHT_TIMEOUT_MS = 30_000  # 30 s

#: requests: timeout in seconds
_REQUESTS_TIMEOUT = 20

#: How many times to retry on transient network errors
_MAX_RETRIES = 2

#: Delay between retries (seconds)
_RETRY_DELAY = 3


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScraperError(RuntimeError):
    """Raised when a URL cannot be scraped after all retries."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_text(raw: str) -> str:
    """Collapse excessive whitespace and blank lines from extracted text."""
    # Normalise line endings
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces / tabs on a single line
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _soup_to_text(soup: BeautifulSoup) -> str:
    """
    Remove noise tags and elements with specific classes from *soup* in-place, 
    then try known main-content selectors before falling back to the whole <body>,
    and finally return Markdown using markdownify.
    """
    # Strip noise subtrees
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    # Strip noisy classes aggressively (footers, sidebars)
    noise_classes = re.compile(r"footer|sidebar|bottom|nav|menu", re.I)
    for tag in soup.find_all(class_=noise_classes):
        tag.decompose()
        
    for tag in soup.find_all(id=noise_classes):
        tag.decompose()

    # Try to find the primary content block
    content_el = None
    for selector in _MAIN_CONTENT_SELECTORS:
        content_el = soup.select_one(selector)
        if content_el:
            logger.debug("Static: content found via selector '%s'", selector)
            break

    if content_el is None:
        # Fall back to entire body
        content_el = soup.find("body") or soup

    # Convert the cleaned HTML to Markdown
    md_text = markdownify.markdownify(str(content_el), heading_style="ATX")
    return _clean_text(md_text)


# ---------------------------------------------------------------------------
# Mode A — Static HTML
# ---------------------------------------------------------------------------


def scrape_static(url: str) -> str:
    """
    Fetch *url* with requests, strip boilerplate with BeautifulSoup,
    and return cleaned plain text.

    Retries up to ``_MAX_RETRIES`` times on connection / timeout errors.

    Raises
    ------
    ScraperError
        If the page cannot be fetched or yields no usable text.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 2):  # 1-indexed; total = retries + 1
        try:
            logger.info("Static scrape attempt %d: %s", attempt, url)
            response = requests.get(
                url,
                headers=_HEADERS,
                timeout=_REQUESTS_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            text = _soup_to_text(soup)

            if not text:
                raise ScraperError(f"No text extracted from {url}")

            logger.info(
                "Static scrape OK: %d chars from %s", len(text), url
            )
            return text

        except requests.exceptions.HTTPError as exc:
            # 4xx client errors — no point retrying
            raise ScraperError(
                f"HTTP {exc.response.status_code} fetching {url}"
            ) from exc

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as exc:
            last_exc = exc
            logger.warning(
                "Static scrape attempt %d failed (%s). %s",
                attempt,
                type(exc).__name__,
                "Retrying…" if attempt <= _MAX_RETRIES else "Giving up.",
            )
            if attempt <= _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

    raise ScraperError(
        f"Failed to fetch {url} after {_MAX_RETRIES + 1} attempts"
    ) from last_exc


# ---------------------------------------------------------------------------
# Mode B — Dynamic HTML (Playwright)
# ---------------------------------------------------------------------------


def scrape_dynamic(url: str) -> str:
    """
    Render *url* in a headless Chromium browser via Playwright, wait for
    visible content, and return cleaned plain text.

    The function tries each selector in ``_DYNAMIC_READY_SELECTORS`` and
    uses the first one that appears within ``_PLAYWRIGHT_TIMEOUT_MS``.
    Falls back to a plain ``networkidle`` wait if no selector matches.

    Raises
    ------
    ScraperError
        If Playwright is not installed, the page fails to load, or no
        text can be extracted.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError as exc:
        raise ScraperError(
            "Playwright is not installed. Run: pip install playwright "
            "and playwright install chromium"
        ) from exc

    logger.info("Dynamic scrape: %s", url)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                user_agent=_HEADERS["User-Agent"],
                locale="en-US",
                viewport={"width": 1280, "height": 900},
                # Pretend to be a real browser — helps bypass bot-detection
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = context.new_page()

            # Navigate to the URL
            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=_PLAYWRIGHT_TIMEOUT_MS,
                )
            except PWTimeout as exc:
                raise ScraperError(
                    f"Playwright timed out loading {url}"
                ) from exc

            # Wait for meaningful content to appear
            content_appeared = False
            for selector in _DYNAMIC_READY_SELECTORS:
                try:
                    page.wait_for_selector(
                        selector,
                        state="visible",
                        timeout=8_000,  # 8 s per selector attempt
                    )
                    logger.debug(
                        "Dynamic: content ready via selector '%s'", selector
                    )
                    content_appeared = True
                    break
                except PWTimeout:
                    continue  # try next selector

            if not content_appeared:
                # Final fallback: wait for network to go quiet
                logger.warning(
                    "No content selector matched — falling back to networkidle for %s",
                    url,
                )
                try:
                    page.wait_for_load_state(
                        "networkidle", timeout=_PLAYWRIGHT_TIMEOUT_MS
                    )
                except PWTimeout:
                    logger.warning(
                        "networkidle wait timed out for %s — extracting anyway", url
                    )

            # Give JS one extra tick to finish rendering
            page.wait_for_timeout(1_500)

            # Extract the full rendered HTML and parse with BeautifulSoup
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        text = _soup_to_text(soup)

        if not text:
            raise ScraperError(f"No text extracted from dynamic page {url}")

        logger.info(
            "Dynamic scrape OK: %d chars from %s", len(text), url
        )
        return text

    except ScraperError:
        raise  # re-raise our own errors unchanged
    except Exception as exc:
        raise ScraperError(
            f"Unexpected error scraping {url}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def scrape_document(entry: dict) -> str:
    """
    Dispatch to the correct scraping mode based on ``entry["content_type"]``.

    Parameters
    ----------
    entry : dict
        A single record from ``data/metadata.json``.  Must contain at least
        ``source_url`` and ``content_type``.

    Returns
    -------
    str
        Cleaned plain text scraped from the document.

    Raises
    ------
    ScraperError
        On any scraping failure, or if ``content_type`` is unrecognised.
    ValueError
        If required fields are missing from *entry*.
    """
    required = {"id", "source_url", "content_type"}
    missing = required - entry.keys()
    if missing:
        raise ValueError(
            f"Metadata entry is missing required fields: {missing}"
        )

    url = entry["source_url"]
    content_type = entry["content_type"]

    if content_type == "html_static":
        return scrape_static(url)

    elif content_type == "html_dynamic":
        return scrape_dynamic(url)

    elif content_type == "pdf":
        # PDFs are handled by ingestion/pdf_parser.py — callers should
        # use that module directly.  Raise a clear error here so nothing
        # is silently skipped.
        raise ScraperError(
            f"Entry '{entry['id']}' has content_type='pdf'. "
            "Use ingestion.pdf_parser.parse_pdf() instead."
        )

    else:
        raise ScraperError(
            f"Unknown content_type '{content_type}' for entry '{entry['id']}'. "
            "Expected one of: html_static, html_dynamic, pdf."
        )


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly: python -m ingestion.scraper)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Default test against a known static AMFI page
    test_entries = [
        {
            "id": "amfi_sip_faq",
            "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center/sip-faq.html",
            "source_name": "AMFI — SIP FAQ",
            "content_type": "html_static",
        },
    ]

    # If a metadata.json path is given as an argument, load all static entries
    if len(sys.argv) > 1:
        metadata_path = sys.argv[1]
        with open(metadata_path, encoding="utf-8") as f:
            entries = json.load(f)
        test_entries = [e for e in entries if e["content_type"] == "html_static"][:2]

    passed = failed = 0
    for entry in test_entries:
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"Testing: {entry['id']}  ({entry['content_type']})")
        print(f"URL: {entry['source_url']}")
        print(sep)
        try:
            text = scrape_document(entry)
            # Print first 500 chars as a preview (ASCII-safe)
            preview = text[:500].encode("ascii", errors="replace").decode("ascii")
            preview = preview.replace("\n", " | ")
            print(f"[OK]  Extracted {len(text):,} chars")
            print(f"      Preview: {preview}...")
            passed += 1
        except (ScraperError, ValueError) as e:
            print(f"[FAIL] {e}")
            failed += 1

    print(f"\n--- Smoke test done: {passed} passed, {failed} failed ---")
