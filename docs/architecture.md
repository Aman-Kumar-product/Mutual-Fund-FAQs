# Architecture — Mutual Fund FAQ Assistant (RAG)

## 1. System Overview

The Mutual Fund FAQ Assistant is a **Retrieval-Augmented Generation (RAG)** system. It does not hallucinate facts — every answer is grounded in a pre-indexed corpus of official public documents. The system is composed of two distinct phases:

- **Offline Phase (Indexing Pipeline):** Runs once (or on refresh). Ingests, processes, and embeds documents into a vector store.
- **Online Phase (Query Pipeline):** Runs per user request. Retrieves relevant chunks, generates a grounded answer, and surfaces a citation.

```
┌─────────────────────────────────────────────────────────────┐
│                        OFFLINE PHASE                        │
│                                                             │
│  Data Sources → Ingestion → Chunking → Embedding → Vector  │
│                                                   Store     │
└─────────────────────────────────────────────────────────────┘
                              ↓  (populated index)
┌─────────────────────────────────────────────────────────────┐
│                        ONLINE PHASE                         │
│                                                             │
│  User Query → Guard → Embed Query → Retrieve → Generate →  │
│               Rail                              Answer +    │
│                                                 Citation    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. High-Level Component Diagram

```
                        ┌──────────────────────┐
                        │       Browser UI      │
                        │  (HTML / CSS / JS)    │
                        └─────────┬────────────┘
                                  │ HTTP (REST)
                        ┌─────────▼────────────┐
                        │      API Server       │
                        │   (FastAPI / Flask)   │
                        └──┬──────────┬────────┘
                           │          │
              ┌────────────▼──┐  ┌────▼──────────────┐
              │  Guard Rail   │  │   Query Engine     │
              │  (Classifier) │  │  (RAG Orchestrator)│
              └───────────────┘  └──┬─────────────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
          ┌─────────▼────┐  ┌──────▼──────┐  ┌─────▼──────────┐
           │ Embed Service │  │ Vector Store │  │  LLM Service   │
           │ (BGE /        │  │ (ChromaDB /  │  │ (Groq API)     │
           │  bge-base-en) │  │  FAISS)      │  │                │
          └──────────────┘  └──────────────┘  └────────────────┘
                                    ▲
                        ┌───────────┴────────────┐
                        │    Indexing Pipeline    │
                        │  (Offline, run once)    │
                        └───────────┬────────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
          ┌─────────▼────┐  ┌──────▼──────┐  ┌─────▼──────────┐
          │  Web Scraper  │  │ PDF Parser  │  │  Metadata Store │
          │ (BeautifulSoup│  │ (PyMuPDF /  │  │  (JSON / SQLite)│
          │  / Playwright)│  │  pdfplumber)│  └────────────────┘
          └──────────────┘  └─────────────┘
```

---

## 3. Offline Phase — Indexing Pipeline

### 3.1 Data Sources

| Source | Type | Content |
|--------|------|---------|
| HDFC AMC website | HTML + PDF | Factsheets, KIM, SID, scheme pages |
| AMFI (amfiindia.com) | HTML | Riskometer guidelines, NAV, scheme classification |
| SEBI (sebi.gov.in) | HTML + PDF | Circulars on expense ratios, exit loads, ELSS rules |
| Groww scheme pages | HTML | Minimum SIP, fund manager, benchmark, category, exit load |

**Target corpus:** 4 pages/documents covering the 4 HDFC schemes in scope.

### 3.2 Ingestion

**Responsibility:** Fetch raw content from each approved URL.

| Content Type | Tool | Output |
|---|---|---|
| Static HTML pages | `requests` + `BeautifulSoup` | Plain text |
| JavaScript-rendered pages (Groww) | `Playwright` (headless Chromium) | Plain text |
| PDF documents (factsheets, SIDs, KIMs) | `PyMuPDF` or `pdfplumber` | Plain text per page |

Each ingested document is saved with metadata:

```json
{
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "source_name": "Groww — HDFC Mid Cap Opportunities Fund",
  "scheme": "HDFC Mid Cap Opportunities Fund",
  "amc": "HDFC Mutual Fund",
  "doc_type": "scheme_page",
  "ingested_at": "2026-08-12",
  "raw_text": "..."
}
```

### 3.3 Chunking

**Responsibility:** Split raw text into semantically coherent, retrievable units.

| Parameter | Value | Rationale |
|---|---|---|
| Chunk size | ~400 tokens | Fits LLM context; granular enough for precision |
| Chunk overlap | ~50 tokens | Prevents context loss at chunk boundaries |
| Strategy | Recursive character splitting | Respects paragraph and sentence boundaries |

Each chunk inherits the full source metadata from its parent document (URL, scheme, ingested date). This is what enables per-answer citations.

### 3.4 Embedding

**Responsibility:** Convert each text chunk into a dense vector representation.

- **Model:** `BAAI/bge-base-en-v1.5` — local, free, state-of-the-art retrieval performance on the MTEB benchmark
- **Dimension:** 768
- **Batch processing:** All chunks embedded in a single offline run
- **Note:** BGE models require prepending `"Represent this sentence for searching relevant passages: "` to query strings at retrieval time (not at indexing time)

### 3.5 Vector Store

**Responsibility:** Persist embeddings and metadata for fast approximate nearest-neighbour (ANN) search.

| Option | Recommendation | Reason |
|---|---|---|
| **ChromaDB** | ✅ Primary | Simple, local, metadata-filtering, no infra |
| FAISS | Alternative | Faster at scale, no built-in metadata |
| Pinecone | Optional | Cloud-managed, best for production scale |

Collection structure:
- `id`: chunk UUID
- `embedding`: float vector
- `document`: chunk text
- `metadata`: `{ source_url, scheme, doc_type, ingested_at }`

---

## 4. Online Phase — Query Pipeline

### 4.1 API Server

**Responsibility:** Single entry point for all client requests.

- **Framework:** FastAPI (Python)
- **Endpoints:**

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/ask` | Submit a user query, receive answer + citation |
| `GET` | `/examples` | Return 3 example questions for the UI |

**Request schema (`/ask`):**
```json
{ "query": "What is the expense ratio of HDFC Mid Cap Fund?" }
```

**Response schema (`/ask`):**
```json
{
  "answer": "The expense ratio of HDFC Mid Cap Opportunities Fund (Direct Plan) is 0.77% per annum.",
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "source_name": "Groww — HDFC Mid Cap Opportunities Fund",
  "ingested_at": "2026-08-12",
  "refused": false
}
```

**Refusal response schema:**
```json
{
  "answer": "This assistant answers facts-only questions about mutual fund schemes. Investment advice is outside its scope. For guidance, visit https://www.amfiindia.com/investor-corner/knowledge-center.",
  "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center",
  "refused": true
}
```

### 4.2 Guard Rail (Input Classifier)

**Responsibility:** Classify user queries as either **factual** (allowed) or **advisory/opinion** (refused) before routing to the RAG pipeline.

**Detection method — keyword + semantic classifier (two-stage):**

1. **Stage 1 — Keyword blocklist (fast):**
   - Triggers on: `should I`, `recommend`, `best fund`, `which is better`, `buy`, `sell`, `invest in`, `portfolio`, `returns`, `outperform`
   - If matched → immediate refusal response

2. **Stage 2 — Semantic classifier (fallback):**
   - Embed query and compare cosine similarity against a small set of "advisory intent" exemplars
   - If similarity > threshold → refusal

**PII filter (runs in parallel):**
- Regex blocklist for PAN (`[A-Z]{5}[0-9]{4}[A-Z]`), Aadhaar (12-digit), phone, email patterns
- If PII detected → reject with a privacy message, do not log query

### 4.3 Query Embedding

- Same embedding model used during indexing (critical for cosine similarity consistency)
- User query → single dense vector

### 4.4 Retrieval

- **Top-k:** Retrieve top 5 chunks by cosine similarity
- **Metadata filtering:** Optionally filter by scheme name if detected in query (e.g., "HDFC Defence Fund" → filter `metadata.scheme`)
- **Re-ranking (optional):** Cross-encoder re-ranking of top-5 for precision improvement (`cross-encoder/ms-marco-MiniLM-L-6-v2`)

### 4.5 Generation (LLM)

**Responsibility:** Synthesise a grounded, factual answer from retrieved chunks only.

**Model:**

| Model | Provider | Notes |
|---|---|---|
| `llama-3.3-70b-versatile` | **Groq** ✅ Primary | Ultra-fast inference, free tier, strong instruction following |
| `mixtral-8x7b-32768` | Groq | Longer context window (32k tokens), good for large retrieved chunks |
| `llama3-8b-8192` | Groq | Lightweight fallback, minimal latency |

**System prompt (strict grounding):**

```
You are a facts-only Mutual Fund FAQ assistant. You answer questions exclusively
from the provided context about HDFC Mutual Fund schemes listed on Groww.

Rules:
1. Answer using ONLY the information in the context below. Do not use prior knowledge.
2. Keep answers to ≤ 3 sentences.
3. Do not give investment advice, recommendations, or return projections.
4. If the context does not contain the answer, say: "I don't have verified information
   on this. Please check the official HDFC AMC website or AMFI."
5. Do not accept or reference any personal identifiers (PAN, Aadhaar, phone, email).

Context:
{retrieved_chunks}
```

**User message template:**
```
Question: {user_query}
```

---

## 5. Citation Flow

Every answer surfaces the citation of the **top-ranked retrieved chunk**, not a hallucinated URL.

```
Retrieve top chunk
       ↓
Extract chunk.metadata.source_url
Extract chunk.metadata.source_name
Extract chunk.metadata.ingested_at
       ↓
Attach to LLM response as citation
       ↓
Display in UI as: "Source: [source_name](source_url) · Last updated: ingested_at"
```

---

## 6. Frontend (UI)

**Responsibility:** Minimal, clean chat interface. No login, no PII fields.

**Tech stack:** HTML + Vanilla CSS + Vanilla JS (single `index.html` file — zero build step)

**UI components:**

| Component | Description |
|---|---|
| **Welcome banner** | App name, one-line description, facts-only disclaimer |
| **Example questions** | 3 clickable pill buttons pre-filled into the input |
| **Chat window** | Scrollable message thread (user bubbles + assistant bubbles) |
| **Input bar** | Text input + Send button |
| **Citation footer** | Per-answer: source link + "Last updated from sources: [date]" |
| **Refusal message** | Styled differently (grey/muted) with an educational link |

**UI states:**

```
IDLE → user types / clicks example → LOADING (spinner) → ANSWER displayed
                                                        → REFUSAL displayed (if advisory)
                                                        → ERROR displayed (if API fails)
```

---

## 7. Data Flow — End-to-End

```
User types query
      │
      ▼
[PII Filter] ── PII detected? ──► Reject (privacy message)
      │
      ▼ clean query
[Guard Rail Classifier]
      │
      ├── Advisory/opinion? ──► Return refusal + educational link
      │
      ▼ factual query
[Embed Query] → dense vector
      │
      ▼
[ChromaDB] → cosine search → top-5 chunks + metadata
      │
      ▼
[Optional re-ranker] → re-ordered top-5
      │
      ▼
[LLM Prompt] = system_prompt + context (top chunks) + user_query
      │
      ▼
[LLM Response] → grounded answer (≤3 sentences)
      │
      ▼
[Attach citation] → source_url, source_name, ingested_at from top chunk metadata
      │
      ▼
[API Response JSON] → UI renders answer + citation
```

---

## 8. Project Directory Structure

```
mutual-fund-rag/
│
├── docs/
│   ├── problemStatement.md
│   └── architecture.md               ← this file
│
├── data/
│   ├── raw/                          ← scraped HTML/PDFs (gitignored)
│   │   ├── groww_hdfc_midcap.txt
│   │   ├── hdfc_midcap_factsheet.pdf
│   │   └── ...
│   └── metadata.json                 ← source registry (url, name, type, date)
│
├── ingestion/
│   ├── scraper.py                    ← HTML scraper (requests + Playwright)
│   ├── pdf_parser.py                 ← PDF text extractor (PyMuPDF)
│   └── run_ingestion.py              ← orchestrates full ingestion run
│
├── indexing/
│   ├── chunker.py                    ← recursive text splitter
│   ├── embedder.py                   ← batch embedding (sentence-transformers)
│   └── build_index.py                ← populates ChromaDB collection
│
├── retrieval/
│   ├── vector_store.py               ← ChromaDB client wrapper
│   └── retriever.py                  ← top-k retrieval + optional re-ranking
│
├── generation/
│   ├── prompt_builder.py             ← assembles system prompt + context
│   └── llm_client.py                 ← Gemini / OpenAI API wrapper
│
├── guardrails/
│   ├── classifier.py                 ← advisory intent detection
│   └── pii_filter.py                 ← PII regex blocklist
│
├── api/
│   ├── main.py                       ← FastAPI app (routes: /ask, /examples)
│   └── schemas.py                    ← Pydantic request/response models
│
├── ui/
│   └── index.html                    ← single-file frontend (HTML+CSS+JS)
│
├── chroma_db/                        ← ChromaDB persisted collection (gitignored)
│
├── requirements.txt
├── .env.example                      ← API keys template (never commit .env)
└── README.md
```

---

## 9. Technology Stack Summary

- **Information Extraction (LLM-to-JSON):**
  - Read dynamic and static HTML converted into clean Markdown.
  - Use `langchain-groq` (llama3-70b-8192) to parse the unstructured markdown.
  - Extract structured Pydantic schemas (Expense Ratio, Min SIP, Exit Load, etc.) into clean `.json` files.
  - Drop all remaining raw text to eliminate noise.

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11+ | Ecosystem for NLP/ML tooling |
| Web scraping (static) | `requests` + `BeautifulSoup4` | Lightweight, sufficient for most pages |
| Web scraping (dynamic) | `Playwright` | Handles JS-rendered pages (Groww) |
| PDF parsing | `PyMuPDF` (`fitz`) | Fast, reliable, preserves table structure |
| Text splitting | `langchain.text_splitter` | Recursive character splitting |
| Embedding model | `BAAI/bge-base-en-v1.5` (sentence-transformers) | Local, free, 768-dim, top MTEB retrieval performance |
| Vector store | `ChromaDB` | Persistent, local, metadata-filtering |
| LLM | `llama-3.3-70b-versatile` via **Groq API** | Ultra-fast inference, free tier, strong instruction following |
| API server | `FastAPI` | Async, auto-docs, Pydantic validation |
| Frontend | HTML + CSS + JS | Zero build step, portable |

---

## 10. Key Design Decisions

### Why RAG over a fine-tuned model?
- Data changes (factsheet updates, SEBI circulars). RAG re-indexes; fine-tuning requires full retraining.
- Citations are a first-class requirement. RAG naturally surfaces the source chunk's URL.
- Corpus is small (4 docs). RAG is proportionally the right approach.

### Why ChromaDB over FAISS?
- ChromaDB stores metadata natively alongside embeddings, enabling citation extraction without a separate lookup.
- FAISS requires a parallel metadata store and manual ID→metadata mapping.

### Why BGE over all-MiniLM-L6-v2 or OpenAI embeddings?
- `BAAI/bge-base-en-v1.5` ranks significantly higher on the MTEB retrieval benchmark versus MiniLM-L6.
- It is fully local (no API key, no cost, no data leaving the machine), unlike OpenAI `text-embedding-3-small`.
- The 768-dim representation captures richer semantic nuance than MiniLM's 384-dim, improving retrieval precision for financial terminology.

### Why Groq over Gemini / OpenAI?
- Groq's LPU inference engine delivers sub-second response times even for large models (70B parameters).
- Free tier is available with generous rate limits suitable for a prototype.
- `llama-3.3-70b-versatile` on Groq matches GPT-4o-mini quality for structured Q&A tasks at zero per-token cost during development.

### Why a two-stage guard rail?
- Keyword blocklist is O(1) and catches 90% of advisory queries immediately.
- Semantic classifier catches paraphrased advisory queries the blocklist misses (e.g., "Is this a good time to start SIP?").

### Why a single `index.html` UI?
- Zero build toolchain required. The prototype is deployable by simply opening the file or serving it with `python -m http.server`.
- Keeps the project scope focused on the RAG pipeline, not frontend complexity.

---

## 11. Constraints Mapped to Architecture

| Constraint | Architectural Enforcement |
|---|---|
| Public sources only | `metadata.json` source registry acts as an allowlist; scraper only fetches registered URLs |
| No PII | `pii_filter.py` runs before any processing; API never logs query text containing PII patterns |
| No performance claims | System prompt explicitly forbids return computation; guard rail blocks "returns" queries |
| Facts only / ≤3 sentences | System prompt enforces length and factual-only constraint on LLM |
| Citation per answer | Top chunk metadata (URL, name, date) is always attached to LLM response in `schemas.py` |
| No investment advice | Guard rail classifier + system prompt dual enforcement |

---

## 12. Scalability & Extension Notes

> These are **out of scope for v1** but documented for future reference.

- **Multi-AMC support:** Add AMC field to metadata schema; add AMC-level filter to retriever.
- **Auto-refresh corpus:** Schedule scraper + re-indexer as a cron job (weekly, on HDFC factsheet publish dates).
- **Streaming responses:** Switch FastAPI endpoint to `StreamingResponse` and use LLM streaming API for faster perceived latency.
- **Evaluation harness:** Build a golden Q&A set (20 questions with expected answers) and run automated faithfulness + citation-accuracy evals.
- **Observability:** Log query → retrieved chunks → LLM response triplets (without PII) for debugging retrieval quality.
