# Phase-Wise Implementation Plan — Mutual Fund FAQ Assistant (RAG)

> **Reference documents:** [problemStatement.md](./problemStatement.md) · [architecture.md](./architecture.md)  
> **Stack:** Python 3.11 · ChromaDB · BGE (`bge-base-en-v1.5`) · FastAPI · Groq (`llama-3.3-70b-versatile`) · HTML/CSS/JS

---

## Overview

The project is broken into **5 sequential phases**. Each phase has a clear goal, a concrete deliverable, and an explicit "done" test before moving to the next.

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
  Setup    Ingestion  Indexing   API +     Polish +
  & Corpus & Parsing  & RAG     Guard     UI Demo
           Pipeline   Core      Rails
```

| Phase | Name | Key Output | Est. Effort |
|-------|------|-----------|-------------|
| 1 | Project Setup & Corpus | Repo skeleton + `metadata.json` with 4 source URLs | 0.5 day |
| 2 | Ingestion Pipeline | Raw text files + PDFs in `data/raw/` | 1 day |
| 3 | Indexing & RAG Core | Populated ChromaDB + working retrieval + generation | 1–1.5 days |
| 4 | API + Guard Rails | FastAPI server with `/ask` and `/examples` endpoints | 1 day |
| 5 | Frontend + Integration | Complete `index.html` UI connected to live API | 0.5 day |

---

## Phase 1 — Project Setup & Corpus Definition

**Goal:** Establish the project skeleton, virtual environment, and the source registry (`metadata.json`) that acts as the approved URL allowlist.

### 1.1 Repository & Environment

- [ ] Create project root folder `mutual-fund-rag/`
- [ ] Initialize Git repository (`git init`)
- [ ] Create `.gitignore`:
  - Ignore `data/raw/`, `chroma_db/`, `.env`, `__pycache__/`, `*.pyc`
- [ ] Create Python virtual environment (`python -m venv .venv`)
- [ ] Create `requirements.txt` with initial dependencies:

```
requests
beautifulsoup4
playwright
PyMuPDF
langchain
sentence-transformers
chromadb
fastapi
uvicorn
pydantic
python-dotenv
groq
```

- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Run `playwright install chromium`
- [ ] Create `.env.example` with keys template:
  ```
  GROQ_API_KEY=your_groq_api_key_here
  ```
  > Get a free key at https://console.groq.com

### 1.2 Directory Scaffold

- [ ] Create all directories from the architecture layout:
  ```
  data/raw/
  ingestion/
  indexing/
  retrieval/
  generation/
  guardrails/
  api/
  ui/
  docs/
  chroma_db/
  ```
- [ ] Add `__init__.py` to all Python package directories

### 1.3 Corpus Registry (`data/metadata.json`)

- [ ] Create `data/metadata.json` — the **source allowlist**. Must cover 4 documents across all 4 schemes:

```json
[
  {
    "id": "groww_hdfc_midcap",
    "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "source_name": "Groww — HDFC Mid Cap Opportunities Fund",
    "scheme": "HDFC Mid Cap Opportunities Fund",
    "amc": "HDFC Mutual Fund",
    "doc_type": "scheme_page",
    "content_type": "html_dynamic"
  },
  {
    "id": "groww_hdfc_silver_etf",
    "source_url": "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
    "source_name": "Groww — HDFC Silver ETF FoF",
    "scheme": "HDFC Silver ETF FoF",
    "amc": "HDFC Mutual Fund",
    "doc_type": "scheme_page",
    "content_type": "html_dynamic"
  },
  {
    "id": "groww_hdfc_defence",
    "source_url": "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
    "source_name": "Groww — HDFC Defence Fund",
    "scheme": "HDFC Defence Fund",
    "amc": "HDFC Mutual Fund",
    "doc_type": "scheme_page",
    "content_type": "html_dynamic"
  },
  {
    "id": "groww_hdfc_equity",
    "source_url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "source_name": "Groww — HDFC Equity Fund",
    "scheme": "HDFC Equity Fund",
    "amc": "HDFC Mutual Fund",
    "doc_type": "scheme_page",
    "content_type": "html_dynamic"
  },
  {
    "id": "amfi_riskometer",
    "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center/riskometer.html",
    "source_name": "AMFI — Riskometer",
    "scheme": "general",
    "amc": "general",
    "doc_type": "regulatory_guide",
    "content_type": "html_static"
  },
  {
    "id": "amfi_sip_faq",
    "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center/sip-faq.html",
    "source_name": "AMFI — SIP FAQ",
    "scheme": "general",
    "amc": "general",
    "doc_type": "faq",
    "content_type": "html_static"
  },
  {
    "id": "amfi_exit_load",
    "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center/exit-load.html",
    "source_name": "AMFI — Exit Load Guide",
    "scheme": "general",
    "amc": "general",
    "doc_type": "regulatory_guide",
    "content_type": "html_static"
  },
  {
    "id": "amfi_elss_faq",
    "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center/tax-saving-fund.html",
    "source_name": "AMFI — ELSS/Tax Saving Fund Guide",
    "scheme": "general",
    "amc": "general",
    "doc_type": "faq",
    "content_type": "html_static"
  }
]
```

> **Note:** Supplement this list during Phase 2 with actual HDFC AMC factsheet PDF URLs and SEBI circular links. Target 4 total entries.

### Phase 1 — Done When
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] All directories exist
- [ ] `data/metadata.json` has 4 entries
- [ ] `.env` is populated with a valid `GROQ_API_KEY`

---

## Phase 2 — Ingestion Pipeline

**Goal:** Fetch, parse, and save raw text from every URL in `metadata.json` to `data/raw/`.

### 2.1 Static HTML Scraper (`ingestion/scraper.py`)

Implement two scraping modes driven by `content_type` in `metadata.json`:

**Mode A — Static HTML** (`html_static`): `requests` + `BeautifulSoup`
- Fetch page, strip nav/footer/script/style tags
- Extract main body text
- Save to `data/raw/{id}.txt`

**Mode B — Dynamic HTML** (`html_dynamic`): `Playwright`
- Launch headless Chromium
- Wait for page content to load (wait for a scheme-specific selector)
- Extract rendered text
- Save to `data/raw/{id}.txt`

```python
# scraper.py — key interface
def scrape_static(url: str) -> str: ...
def scrape_dynamic(url: str) -> str: ...
def scrape_document(entry: dict) -> str: ...  # dispatches by content_type
```

### 2.2 PDF Parser (`ingestion/pdf_parser.py`)

- For `content_type = "html_dynamic"` (Groww, AMFI JS pages):
  - Use `playwright` (headless browser)
  - Wait for network idle or specific selector.
  - Aggressively strip footer/sidebar noise.
  - Extract HTML and convert to Markdown using `markdownify` to preserve tables.
- For `content_type = "pdf"` entries:
  - Download PDF via `requests` to a temp path
  - Extract text per page using `PyMuPDF` (`fitz.open()`)
  - Concatenate pages with a `\n--- Page {n} ---\n` separator
  - Save to `data/raw/{id}.txt`

```python
def parse_pdf(url: str) -> str: ...
```

### 2.3 Ingestion Orchestrator (`ingestion/run_ingestion.py`)

- Load `data/metadata.json`
- For each entry: dispatch to correct scraper/parser
- Save raw text to `data/raw/{id}.txt`
- Update `metadata.json` to add `ingested_at` date and `raw_file` path
- **Skip already-ingested files** (idempotent re-runs)
- Print a summary: `✓ ingested / ✗ failed / ⏭ skipped`

```
python -m ingestion.run_ingestion
```

### 2.4 Manual Corpus Expansion (during this phase)

While the scraper runs, manually locate and add to `metadata.json`:
- [ ] HDFC AMC factsheet PDFs for all 4 schemes (monthly factsheets from hdfcfund.com)
- [ ] KIM (Key Information Memorandum) PDFs from HDFC AMC
- [ ] SEBI circular on TER/expense ratios
- [ ] SEBI ELSS circular (lock-in rules)
- [ ] AMFI scheme NAV / classification page

Target: **4 entries total** in `metadata.json` before Phase 3.

### Phase 2 — Done When
- [ ] `python -m ingestion.run_ingestion` runs without unhandled errors
- [ ] `data/raw/` contains 4 `.txt` files, each with non-empty readable text
- [ ] `metadata.json` entries have `ingested_at` and `raw_file` fields populated
- [ ] Groww scheme pages (JS-rendered) are scraped successfully via Playwright

---

## Phase 3 — Indexing & RAG Core

**Goal:** Chunk, embed, and index all raw documents into ChromaDB; wire up the full RAG pipeline end-to-end and verify it returns correct, cited answers from the command line.

### 3.1 Structured LLM Extraction (`ingestion/extractor.py`)
- Read Markdown files from `data/raw/`
- Pass the Markdown to `ChatGroq` (llama3-70b-8192) using `.with_structured_output(FundDetails)`.
- Extract exactly the fields required by the problem statement (expense ratio, exit load, minimum SIP, etc.)
- Output: Structured JSON file per document in `data/cleaned/{id}.json`

### 3.2 Embedder (`indexing/embedder.py`)

```python
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-base-en-v1.5"  # 768-dim, top MTEB retrieval performance

# BGE requires a query prefix at retrieval time (NOT at indexing time)
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

def load_model() -> SentenceTransformer: ...
def embed_texts(texts: list[str], model: SentenceTransformer) -> list[list[float]]: ...
def embed_query(query: str, model: SentenceTransformer) -> list[float]:
    """Prepends BGE query prefix before embedding user queries."""
    ...
```

- [ ] Load model once at startup (cache with a module-level singleton)
- [ ] `embed_texts()` embeds document chunks **without** the prefix (indexing)
- [ ] `embed_query()` prepends `BGE_QUERY_PREFIX` to every user query before embedding (retrieval)

### 3.3 Index Builder (`indexing/build_index.py`)

Orchestrates the full offline pipeline:

```
Load metadata.json
    ↓
For each ingested document:
    Read data/cleaned/{id}.json
    → format JSON into a rich text chunk (e.g., "Fund: ... Expense Ratio: ...")
    → embed_texts()    → list of vectors
    → chromadb.add()   → stored with metadata
    ↓
Print: "Indexed N chunks from M documents"
```

```
python -m indexing.build_index
```

- [ ] Use a named ChromaDB collection: `"mutual_fund_faq"`
- [ ] Persist to `chroma_db/` directory
- [ ] Make re-runs idempotent (check if collection already contains chunks from same source; skip or replace)

### 3.4 Vector Store Wrapper (`retrieval/vector_store.py`)

```python
def get_collection() -> chromadb.Collection: ...
```

- [ ] Initialize ChromaDB `PersistentClient` pointing to `chroma_db/`
- [ ] Return the `"mutual_fund_faq"` collection
- [ ] Singleton pattern — reuse across requests

### 3.5 Retriever (`retrieval/retriever.py`)

```python
def retrieve(
    query: str,
    top_k: int = 5,
    scheme_filter: str | None = None
) -> list[dict]:
    """
    Returns list of:
    { "text": "...", "metadata": { source_url, source_name, scheme, ingested_at } }
    """
```

- [ ] Embed the query using `embedder.embed_query()` (applies BGE prefix automatically)
- [ ] Query ChromaDB with optional `where={"scheme": scheme_filter}` metadata filter
- [ ] Return top-k results with their metadata

### 3.6 Prompt Builder (`generation/prompt_builder.py`)

```python
SYSTEM_PROMPT = """
You are a facts-only Mutual Fund FAQ assistant. You answer questions exclusively
from the provided context about HDFC Mutual Fund schemes listed on Groww.

Rules:
1. Answer using ONLY the information in the context below. Do not use prior knowledge.
2. Keep answers to ≤ 3 sentences.
3. Do not give investment advice, recommendations, or return projections.
4. If the context does not contain the answer, say exactly:
   "I don't have verified information on this. Please check the official HDFC AMC website or AMFI."
5. Do not accept or reference any personal identifiers.

Context:
{context}
"""

def build_prompt(query: str, chunks: list[dict]) -> tuple[str, str]:
    """Returns (system_prompt, user_message)"""
```

### 3.7 LLM Client (`generation/llm_client.py`)

```python
from groq import Groq

MODEL_NAME = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama3-8b-8192"  # lower latency fallback

def get_client() -> Groq: ...
def generate_answer(system_prompt: str, user_message: str) -> str: ...
```

- [ ] Initialise `Groq(api_key=os.getenv("GROQ_API_KEY"))`
- [ ] Call `client.chat.completions.create()` with `model=MODEL_NAME`, passing `system` and `user` messages
- [ ] Return `response.choices[0].message.content` as plain text
- [ ] On rate-limit error (HTTP 429), retry once with `FALLBACK_MODEL`

### 3.8 End-to-End RAG Test (CLI)

Create `indexing/test_rag.py` — a simple command-line test:

```python
query = "What is the expense ratio of HDFC Mid Cap Fund?"
chunks = retrieve(query, top_k=5)
system_prompt, user_msg = build_prompt(query, chunks)
answer = generate_answer(system_prompt, user_msg)
citation = chunks[0]["metadata"]
print(f"Answer: {answer}")
print(f"Source: {citation['source_name']} — {citation['source_url']}")
```

### Phase 3 — Done When
- [ ] `python -m indexing.build_index` completes — ChromaDB contains chunks from all ingested docs
- [ ] `python -m indexing.test_rag` returns a factually correct, ≤ 3-sentence answer with a valid citation URL for each of the 6 question types
- [ ] Answer for "What is the ELSS lock-in period?" returns "3 years" (or equivalent)
- [ ] "I don't have verified information" fallback triggers correctly for an out-of-corpus question

---

## Phase 4 — API Server & Guard Rails

**Goal:** Wrap the RAG pipeline in a FastAPI server with PII filtering, advisory query detection, and clean JSON responses.

### 4.1 PII Filter (`guardrails/pii_filter.py`)

```python
import re

PII_PATTERNS = [
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",           # PAN
    r"\b\d{12}\b",                            # Aadhaar
    r"\b[6-9]\d{9}\b",                        # Indian mobile
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",  # email
]

def contains_pii(text: str) -> bool: ...
```

- [ ] Returns `True` if any pattern matches
- [ ] Does not log the matched text

### 4.2 Advisory Classifier (`guardrails/classifier.py`)

**Stage 1 — Keyword blocklist:**
```python
ADVISORY_KEYWORDS = [
    "should i", "recommend", "best fund", "which is better",
    "buy", "sell", "invest in", "portfolio", "outperform",
    "which fund", "should i buy", "should i sell",
]

def is_advisory_keyword(query: str) -> bool: ...
```

**Stage 2 — Semantic classifier (fallback):**
```python
ADVISORY_EXEMPLARS = [
    "Is this a good time to start a SIP?",
    "Which fund should I choose?",
    "Will this fund give good returns?",
    "Should I switch from HDFC Mid Cap to Equity Fund?",
]

def is_advisory_semantic(query: str, threshold: float = 0.75) -> bool: ...
```

- [ ] Embed query and exemplars using the same `BAAI/bge-base-en-v1.5` BGE model (via `embed_query()`)
- [ ] If max cosine similarity > threshold → advisory

```python
def classify(query: str) -> Literal["factual", "advisory"]: ...
```

### 4.3 Pydantic Schemas (`api/schemas.py`)

```python
from pydantic import BaseModel

class AskRequest(BaseModel):
    query: str

class AskResponse(BaseModel):
    answer: str
    source_url: str | None
    source_name: str | None
    ingested_at: str | None
    refused: bool
```

### 4.4 FastAPI App (`api/main.py`)

```python
@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    query = request.query.strip()

    # Step 1: PII filter
    if contains_pii(query):
        return AskResponse(answer="...", refused=True, ...)

    # Step 2: Guard rail
    if classify(query) == "advisory":
        return AskResponse(answer="...", refused=True, ...)

    # Step 3: RAG pipeline
    chunks = retrieve(query, top_k=5)
    system_prompt, user_msg = build_prompt(query, chunks)
    answer = generate_answer(system_prompt, user_msg)
    top_chunk_meta = chunks[0]["metadata"]

    return AskResponse(
        answer=answer,
        source_url=top_chunk_meta["source_url"],
        source_name=top_chunk_meta["source_name"],
        ingested_at=top_chunk_meta["ingested_at"],
        refused=False,
    )

@app.get("/examples")
async def get_examples():
    return {
        "examples": [
            "What is the expense ratio of HDFC Mid Cap Fund?",
            "What is the minimum SIP amount for HDFC Equity Fund?",
            "How do I download a capital gains statement from Groww?",
        ]
    }
```

- [ ] Add `uvicorn` startup in `api/main.py`: `uvicorn api.main:app --reload --port 8000`
- [ ] Enable CORS middleware (allow `*` for prototype)

### 4.5 API Smoke Tests

Test each scenario with `curl` or a Python `httpx` script:

| Test Case | Expected `refused` | Expected behaviour |
|---|---|---|
| "What is the expense ratio of HDFC Mid Cap Fund?" | `false` | Factual answer + citation |
| "Should I buy HDFC Defence Fund?" | `true` | Polite refusal + AMFI link |
| "Is this a good time to invest?" | `true` | Semantic classifier refusal |
| Query containing a PAN number | `true` | PII rejection message |
| "How to download capital gains statement?" | `false` | Procedural answer + citation |

### Phase 4 — Done When
- [x] `uvicorn api.main:app --reload` starts with no errors
- [x] All 5 smoke test cases return the expected `refused` flag and non-empty `answer`
- [x] FastAPI auto-docs at `http://localhost:8000/docs` show correct schema
- [x] No PAN or query text appears in server logs

---

## Phase 5 — Frontend UI & Final Integration

**Goal:** Build the single-file `ui/index.html` chat interface, connect it to the running API, and validate all success criteria end-to-end.

### 5.1 UI Structure (`ui/index.html`)

All HTML, CSS, and JS in one file. Components to implement:

**Layout:**
```
┌──────────────────────────────────────┐
│  🪙 MF FAQ Assistant                 │
│  Facts-only. No investment advice.   │
├──────────────────────────────────────┤
│  [ Chat Window — scrollable ]        │
│                                      │
│  [Bot] Welcome! Ask me about HDFC    │
│        Mutual Fund schemes...        │
│                                      │
│  [Example] [Example] [Example]       │
├──────────────────────────────────────┤
│  [ Type your question... ] [Send]    │
└──────────────────────────────────────┘
```

**Chat bubble anatomy:**
```
User bubble:   right-aligned, accent color
Bot bubble:    left-aligned, dark card
  └─ Answer text
  └─ Citation: 🔗 [source_name] · Last updated: ingested_at
  └─ Refusal: grey card with educational link (if refused=true)
Loading state: animated "..." dots spinner
Error state:   red-bordered card "Could not reach the server."
```

### 5.2 JS Logic

- [ ] On page load: call `GET /examples`, render 3 pill buttons
- [ ] Clicking a pill: pre-fill input field with that question
- [ ] On Send: `POST /ask` with `{ query: inputText }`
- [ ] While awaiting: show loading spinner in chat
- [ ] On response: render answer bubble + citation footer
- [ ] On `refused: true`: render grey refusal card
- [ ] On network error: render error card
- [ ] Input field: `Enter` key submits; send button disabled while loading
- [ ] Auto-scroll chat window to latest message

### 5.3 Serving the UI

```bash
# Start API (Terminal 1)
uvicorn api.main:app --reload --port 8000

# Serve UI (Terminal 2)
python -m http.server 3000 --directory ui/
```

Point browser to `http://localhost:3000`.

> **Note:** Update the JS `API_BASE_URL` constant to `http://localhost:8000` for local dev.

### 5.4 End-to-End Validation

Walk through all success criteria from the problem statement:

| Success Criterion | How to Verify |
|---|---|
| Answers all 6 factual question types | Manually test one question per type, all 4 schemes |
| Every answer has a valid citation link | Click each source link — must open a real, relevant page |
| Advisory questions refused with polite message | Test "Should I invest in HDFC Mid Cap?" |
| UI shows welcome, 3 examples, disclaimer | Load the UI — visually confirm all 3 elements |
| No PII accepted or stored | Send a query with a PAN number — confirm rejection |
| All sources from approved allowlist | Cross-check every citation URL against `metadata.json` |

### 5.5 README (`README.md`)

- [ ] Project description (1 paragraph)
- [ ] Setup instructions (clone → venv → install → add `.env`)
- [ ] How to run the indexing pipeline
- [ ] How to start the API + UI
- [ ] List of 6 example questions to demo

### Phase 5 — Done When
- [ ] All 6 success criteria from the problem statement pass manually
- [ ] Citation links in UI are all clickable and valid
- [ ] UI loads in under 2 seconds on localhost
- [ ] README has working setup instructions (tested on a clean shell)

---

## Cross-Phase Dependency Map

```
Phase 1 (Setup)
    │
    └──► Phase 2 (Ingestion)
              │
              └──► Phase 3 (Indexing & RAG Core)
                        │
                        └──► Phase 4 (API + Guard Rails)
                                  │
                                  └──► Phase 5 (UI + Integration)
```

Each phase **must fully pass its "Done When" criteria** before the next phase begins.

---

## Key Files Created Per Phase

| Phase | Files Created |
|-------|--------------|
| 1 | `requirements.txt`, `.env.example`, `data/metadata.json`, all empty dirs |
| 2 | `ingestion/scraper.py`, `ingestion/pdf_parser.py`, `ingestion/run_ingestion.py`, `data/raw/*.txt` |
| 3 | `indexing/chunker.py`, `indexing/embedder.py`, `indexing/build_index.py`, `retrieval/vector_store.py`, `retrieval/retriever.py`, `generation/prompt_builder.py`, `generation/llm_client.py`, `chroma_db/` |
| 4 | `guardrails/pii_filter.py`, `guardrails/classifier.py`, `api/schemas.py`, `api/main.py` |
| 5 | `ui/index.html`, `README.md` |
