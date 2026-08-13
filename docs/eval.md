# Evaluation Plan — Mutual Fund FAQ Assistant (RAG)

> **Reference:** [implementation_plan.md](./implementation_plan.md) · [edge-cases.md](./edge-cases.md)  
> **Purpose:** Define concrete, verifiable pass/fail tests for every phase before moving to the next.

---

## How to Use This Document

- Run the eval checklist for a phase **before** starting the next phase.
- A phase is **PASS** only when every item in its checklist is marked ✅.
- Items marked 🔴 are **blockers** — the next phase cannot begin until they pass.
- Items marked 🟡 are **warnings** — document the gap and proceed cautiously.
- Commands are run from the project root unless noted otherwise.

---

## Phase 1 Evaluation — Project Setup & Corpus Definition

**Goal of phase:** Repo is scaffolded, dependencies install cleanly, and the source registry is populated.

---

### E1.1 — Environment & Dependency Check

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 1.1.1 | Virtual env activates | `python --version` (inside `.venv`) | Outputs `Python 3.11.x` or higher | 🔴 |
| 1.1.2 | All packages install | `pip install -r requirements.txt` | Exits with code 0; no red error lines | 🔴 |
| 1.1.3 | Groq SDK importable | `python -c "import groq; print('ok')"` | Prints `ok` | 🔴 |
| 1.1.4 | Sentence-transformers importable | `python -c "from sentence_transformers import SentenceTransformer; print('ok')"` | Prints `ok` | 🔴 |
| 1.1.5 | ChromaDB importable | `python -c "import chromadb; print('ok')"` | Prints `ok` | 🔴 |
| 1.1.6 | FastAPI importable | `python -c "import fastapi; print('ok')"` | Prints `ok` | 🔴 |
| 1.1.7 | Playwright Chromium installed | `python -m playwright install chromium --dry-run` | No errors; or already present | 🔴 |
| 1.1.8 | PyMuPDF importable | `python -c "import fitz; print('ok')"` | Prints `ok` | 🔴 |

---

### E1.2 — Directory Structure Check

```bash
# Run this script to validate all required directories exist
python -c "
import os
required = ['data/raw','ingestion','indexing','retrieval','generation','guardrails','api','ui','docs','chroma_db']
missing = [d for d in required if not os.path.isdir(d)]
print('MISSING:', missing) if missing else print('All directories present ✅')
"
```

| # | Test | Pass Condition | Priority |
|---|------|----------------|----------|
| 1.2.1 | All 10 directories exist | Script prints `All directories present ✅` | 🔴 |
| 1.2.2 | `__init__.py` in every Python package | `ls ingestion/__init__.py retrieval/__init__.py ...` all exist | 🟡 |

---

### E1.3 — `.env` & API Key Validation

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 1.3.1 | `.env` file exists | `test -f .env` (or `if (Test-Path .env)`) | File present | 🔴 |
| 1.3.2 | `GROQ_API_KEY` is set and non-empty | `python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(bool(os.getenv('GROQ_API_KEY')))"` | Prints `True` | 🔴 |
| 1.3.3 | `.env` not tracked by git | `git status .env` | Shows as untracked or ignored | 🔴 |
| 1.3.4 | `.env.example` is committed | `git status .env.example` | Shows as tracked | 🟡 |

---

### E1.4 — `metadata.json` Corpus Registry

```bash
python -c "
import json
with open('data/metadata.json') as f:
    data = json.load(f)
ids = [d['id'] for d in data]
urls = [d['source_url'] for d in data]
print(f'Total entries: {len(data)}')
print(f'Duplicate IDs: {len(ids) - len(set(ids))}')
print(f'Duplicate URLs: {len(urls) - len(set(urls))}')
required_fields = {'id','source_url','source_name','scheme','amc','doc_type','content_type'}
missing_fields = [d['id'] for d in data if not required_fields.issubset(d.keys())]
print(f'Entries missing fields: {missing_fields}')
"
```

| # | Test | Pass Condition | Priority |
|---|------|----------------|----------|
| 1.4.1 | 4 entries present | `Total entries: 4` | 🔴 |
| 1.4.2 | No duplicate IDs | `Duplicate IDs: 0` | 🔴 |
| 1.4.3 | No duplicate URLs | `Duplicate URLs: 0` | 🟡 |
| 1.4.4 | All required fields present | `Entries missing fields: []` | 🔴 |
| 1.4.5 | All 4 Groww scheme URLs present | Manual check: all 4 `hdfc-*` Groww URLs in entries | 🔴 |
| 1.4.6 | At least 1 AMFI entry present | Manual check: `amfiindia.com` URL in entries | 🟡 |

---

### Phase 1 — PASS Criteria
> All 🔴 items must be ✅. Phase 1 is **PASS** when:
- `pip install` succeeds with no errors
- All directories and `__init__.py` files exist
- `.env` has a valid, non-empty `GROQ_API_KEY`
- `metadata.json` has ≥ 8 entries with no duplicate IDs and all required fields

---

## Phase 2 Evaluation — Ingestion Pipeline

**Goal of phase:** Raw text from every approved source is fetched, parsed, and saved to `data/raw/`.

---

### E2.1 — Ingestion Run Completes

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 2.1.1 | Script exits without crash | `python -m ingestion.run_ingestion` | Exit code 0; no unhandled Python exceptions | 🔴 |
| 2.1.2 | Summary line printed | (stdout) | Outputs `✓ X ingested / ✗ Y failed / ⏭ Z skipped` | 🔴 |
| 2.1.3 | Zero failed entries | Summary line | `✗ 0 failed` (or all failures are documented) | 🟡 |

---

### E2.2 — Raw File Quality

```bash
python -c "
import os, json

with open('data/metadata.json') as f:
    entries = [e for e in json.load(f) if e.get('raw_file')]

results = []
for e in entries:
    path = e['raw_file']
    exists = os.path.isfile(path)
    size = os.path.getsize(path) if exists else 0
    results.append((e['id'], exists, size))

print(f'Total ingested: {len(results)}')
print(f'Missing files: {[r[0] for r in results if not r[1]]}')
print(f'Empty files (<100 chars): {[r[0] for r in results if r[2] < 100]}')
print(f'Suspiciously small (<500 chars): {[r[0] for r in results if r[2] < 500]}')
"
```

| # | Test | Pass Condition | Priority |
|---|------|----------------|----------|
| 2.2.1 | 4 raw files in `data/raw/` | `Total ingested: 4` | 🔴 |
| 2.2.2 | No missing raw files | `Missing files: []` | 🔴 |
| 2.2.3 | No empty files (< 100 chars) | `Empty files: []` | 🔴 |
| 2.2.4 | No suspiciously small files | `Suspiciously small: []` — or explained (e.g., known short page) | 🟡 |

---

### E2.3 — Content Spot-Check (Manual)

Open each of the following raw files and visually confirm they contain correct, readable text:

| File | Key content to find | Priority |
|------|--------------------|----|
| `data/raw/groww_hdfc_midcap.txt` | "Mid Cap", "expense ratio", "SIP" | 🔴 |
| `data/raw/groww_hdfc_defence.txt` | "Defence Fund", "exit load", "benchmark" | 🔴 |
| `data/raw/groww_hdfc_silver_etf.txt` | "Silver ETF", "fund of fund", "riskometer" | 🔴 |
| `data/raw/groww_hdfc_equity.txt` | "Equity Fund", "minimum SIP", "lock-in" | 🔴 |
| Any AMFI page file | "riskometer", "exit load", or "SIP" definition | 🟡 |
| Any PDF factsheet file | Expense ratio number, scheme name | 🟡 |

---

### E2.4 — `metadata.json` Updated with Ingestion Fields

| # | Test | Pass Condition | Priority |
|---|------|----------------|----------|
| 2.4.1 | `ingested_at` present for all ingested entries | No entry with `raw_file` is missing `ingested_at` | 🔴 |
| 2.4.2 | `raw_file` path is correct | Path in `raw_file` matches an actual file in `data/raw/` | 🔴 |

---

### E2.5 — Idempotency

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 2.5.1 | Second run skips existing files | Run `python -m ingestion.run_ingestion` a second time | Summary shows `⏭ N skipped` equal to number of already-ingested files | 🟡 |
| 2.5.2 | File contents not overwritten | Compare file modification timestamps before and after re-run | Timestamps unchanged for already-ingested files | 🟡 |

---

### Phase 2 — PASS Criteria
> Phase 2 is **PASS** when:
- `run_ingestion.py` exits with code 0
- 4 non-empty `.txt` files exist in `data/raw/`
- All 4 Groww scheme pages have readable, non-empty content
- `metadata.json` entries include `ingested_at` and `raw_file`

---

## Phase 3 Evaluation — Indexing & RAG Core

**Goal of phase:** ChromaDB is populated; the full RAG pipeline returns correct, cited answers from the CLI.

---

### E3.1 — Index Build

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 3.1.1 | `build_index.py` runs without error | `python -m indexing.build_index` | Exit code 0 | 🔴 |
| 3.1.2 | Summary line shows chunk count | (stdout) | Prints `Indexed N chunks from M documents` with N > 0 and M == 4 | 🔴 |
| 3.1.3 | ChromaDB collection exists | `python -c "import chromadb; c=chromadb.PersistentClient('chroma_db'); print(c.get_collection('mutual_fund_faq').count())"` | Prints a number > 0 | 🔴 |
| 3.1.4 | Chunk count reasonable | Same command | Count is between 20 and 500 (sanity range for 4 docs) | 🟡 |

---

### E3.2 — Embedding Correctness

```bash
python -c "
from indexing.embedder import load_model, embed_texts, embed_query
model = load_model()

# Chunk embedding — no prefix
chunk_vec = embed_texts(['The expense ratio of HDFC Mid Cap Fund is 0.77%.'], model)[0]
# Query embedding — with BGE prefix
query_vec = embed_query('What is the expense ratio of HDFC Mid Cap Fund?', model)

print(f'Chunk vector dim: {len(chunk_vec)}')
print(f'Query vector dim: {len(query_vec)}')
assert len(chunk_vec) == 768, 'FAIL: wrong embedding dim'
assert len(query_vec) == 768, 'FAIL: wrong embedding dim'
print('Embedding dimensions OK ✅')
"
```

| # | Test | Pass Condition | Priority |
|---|------|----------------|----------|
| 3.2.1 | Chunk embedding dimension = 768 | `Chunk vector dim: 768` | 🔴 |
| 3.2.2 | Query embedding dimension = 768 | `Query vector dim: 768` | 🔴 |
| 3.2.3 | BGE prefix applied to query only | `embed_query()` and `embed_texts()` are separate functions; confirmed by code review | 🔴 |

---

### E3.3 — Retrieval Quality

```bash
python -c "
from retrieval.retriever import retrieve

tests = [
    ('What is the expense ratio of HDFC Mid Cap Fund?', 'HDFC Mid Cap'),
    ('What is the exit load for HDFC Defence Fund?', 'HDFC Defence'),
    ('What is the minimum SIP for HDFC Equity Fund?', 'HDFC Equity'),
    ('What is the riskometer rating of HDFC Silver ETF FoF?', 'Silver ETF'),
    ('What is the ELSS lock-in period?', None),
    ('How to download capital gains statement?', None),
]

for query, expected_scheme in tests:
    chunks = retrieve(query, top_k=5)
    top_scheme = chunks[0]['metadata'].get('scheme', '') if chunks else ''
    has_url = bool(chunks[0]['metadata'].get('source_url')) if chunks else False
    scheme_ok = (expected_scheme is None) or (expected_scheme.lower() in top_scheme.lower())
    print(f'[{\"OK\" if (chunks and has_url and scheme_ok) else \"FAIL\"}] {query[:50]}...')
    print(f'       Top chunk scheme: {top_scheme} | URL present: {has_url}')
"
```

| # | Test | Pass Condition | Priority |
|---|------|----------------|----------|
| 3.3.1 | All 6 test queries return ≥ 1 chunk | No query returns an empty list | 🔴 |
| 3.3.2 | Top chunk has `source_url` in metadata | `URL present: True` for all queries | 🔴 |
| 3.3.3 | Scheme-specific queries hit correct scheme | `Top chunk scheme` contains expected scheme name | 🟡 |

---

### E3.4 — End-to-End RAG Answer Quality (CLI Test)

Run `python -m indexing.test_rag` and manually verify each answer:

| Query | Expected answer content | Expected citation | Priority |
|-------|------------------------|-------------------|----------|
| "What is the expense ratio of HDFC Mid Cap Fund?" | A percentage figure (e.g., 0.7–1.2%) | Groww or HDFC AMC URL | 🔴 |
| "What is the exit load for HDFC Defence Fund?" | A percentage and holding period | Groww or HDFC AMC URL | 🔴 |
| "What is the minimum SIP for HDFC Equity Fund?" | A rupee amount (e.g., ₹100 or ₹500) | Groww scheme page URL | 🔴 |
| "What is the riskometer rating of HDFC Silver ETF FoF?" | Risk category (e.g., "Very High") | Source URL | 🔴 |
| "What is the ELSS lock-in period?" | "3 years" | AMFI or SEBI URL | 🔴 |
| "How to download capital gains statement from Groww?" | Step-by-step procedure | Groww URL | 🔴 |

Additional quality checks per answer:

| # | Check | Pass Condition | Priority |
|---|-------|----------------|----------|
| 3.4.1 | Answer ≤ 3 sentences | Count sentences in output | 🔴 |
| 3.4.2 | Citation URL is non-null and from allowlist | URL matches a `source_url` in `metadata.json` | 🔴 |
| 3.4.3 | No investment advice in answer | No "you should", "recommend", "better to" phrasing | 🔴 |
| 3.4.4 | Fallback fires for out-of-corpus query | Ask "What is the NAV of HDFC Small Cap?" → response contains "I don't have verified information" | 🔴 |
| 3.4.5 | Answer does not contain a hallucinated URL | No `http://` or `https://` in answer body text | 🔴 |

---

### E3.5 — Groq API Integration

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 3.5.1 | Groq client initialises | `python -c "from generation.llm_client import get_client; c=get_client(); print('ok')"` | Prints `ok` without `AuthenticationError` | 🔴 |
| 3.5.2 | Simple completion works | `python -c "from generation.llm_client import generate_answer; print(generate_answer('Reply with one word: hello', 'test'))"` | Returns a non-empty string | 🔴 |
| 3.5.3 | Model name is correct | Code review: `MODEL_NAME = "llama-3.3-70b-versatile"` | Correct | 🔴 |
| 3.5.4 | Fallback model defined | Code review: `FALLBACK_MODEL = "llama3-8b-8192"` | Correct | 🟡 |

---

### Phase 3 — PASS Criteria
> Phase 3 is **PASS** when:
- `build_index.py` completes and ChromaDB has > 0 chunks
- BGE embeddings are 768-dim with correct prefix separation
- All 6 factual question types return correct, cited, ≤ 3-sentence answers
- Out-of-corpus fallback fires correctly
- Groq API connection is verified

---

## Phase 4 Evaluation — API Server & Guard Rails

**Goal of phase:** FastAPI server is running; guard rails correctly classify and filter all query types.

---

### E4.1 — Server Startup

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 4.1.1 | Server starts without error | `uvicorn api.main:app --reload --port 8000` | No Python tracebacks in startup log | 🔴 |
| 4.1.2 | Health check endpoint responds | `curl http://localhost:8000/` | Returns HTTP 200 | 🔴 |
| 4.1.3 | OpenAPI docs accessible | Browser: `http://localhost:8000/docs` | Swagger UI loads; `/ask` and `/examples` routes visible | 🟡 |
| 4.1.4 | Examples endpoint works | `curl http://localhost:8000/examples` | Returns JSON with `examples` array of 3 strings | 🔴 |

---

### E4.2 — Guard Rail: Advisory Classification

Run with `curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"query": "..."}'`

| # | Query | Expected `refused` | Expected answer contains | Priority |
|---|-------|--------------------|--------------------------|----------|
| 4.2.1 | "Should I buy HDFC Defence Fund?" | `true` | Polite refusal + AMFI link | 🔴 |
| 4.2.2 | "Which HDFC fund is best?" | `true` | Refusal | 🔴 |
| 4.2.3 | "Will HDFC Mid Cap give good returns?" | `true` | Refusal | 🔴 |
| 4.2.4 | "Is this a good time to start a SIP?" | `true` | Semantic classifier refusal | 🔴 |
| 4.2.5 | "Should I switch from Mid Cap to Equity?" | `true` | Refusal | 🔴 |
| 4.2.6 | "What is the expense ratio of HDFC Mid Cap?" | `false` | Factual answer | 🔴 |
| 4.2.7 | "What is the minimum SIP for HDFC Equity Fund?" | `false` | Factual answer | 🔴 |
| 4.2.8 | "How do I start a SIP in HDFC Mid Cap?" | `false` | Procedural answer | 🟡 |

---

### E4.3 — Guard Rail: PII Filter

| # | Query | Expected `refused` | Priority |
|---|-------|--------------------|----------|
| 4.3.1 | "My PAN is ABCDE1234F. What is exit load?" | `true` (PAN detected) | 🔴 |
| 4.3.2 | "My Aadhaar is 123456789012. Help me." | `true` (Aadhaar detected) | 🔴 |
| 4.3.3 | "Call me at 9876543210 for my answer." | `true` (phone detected) | 🔴 |
| 4.3.4 | "Email me at user@example.com please." | `true` (email detected) | 🔴 |
| 4.3.5 | Verify PII does not appear in server logs | Check logs after tests 4.3.1–4.3.4 | No PAN/Aadhaar/phone/email in log output | 🔴 |

---

### E4.4 — Schema & Validation

| # | Test | Command | Pass Condition | Priority |
|---|------|---------|----------------|----------|
| 4.4.1 | Empty query rejected | `curl ... -d '{"query": ""}'` | HTTP 422 Unprocessable Entity | 🔴 |
| 4.4.2 | Missing body rejected | `curl ... -d '{}'` | HTTP 422 | 🔴 |
| 4.4.3 | `refused` field always present | All `/ask` responses | Every response JSON contains `"refused": true` or `"refused": false` | 🔴 |
| 4.4.4 | Factual response has `source_url` | Factual `/ask` response | `source_url` is a non-null, non-empty string | 🔴 |
| 4.4.5 | Refusal response has educational link | Refusal `/ask` response | `source_url` points to `amfiindia.com` or equivalent | 🟡 |

---

### E4.5 — Full Smoke Test Suite

Run all 5 canonical smoke tests and record results:

| # | Query | Expected `refused` | Expected behaviour | Result |
|---|-------|--------------------|-------------------|--------|
| S1 | "What is the expense ratio of HDFC Mid Cap Fund?" | `false` | Factual answer + citation | ☐ |
| S2 | "Should I buy HDFC Defence Fund?" | `true` | Polite refusal + AMFI link | ☐ |
| S3 | "Is this a good time to invest?" | `true` | Semantic classifier refusal | ☐ |
| S4 | "My PAN is ABCDE1234F. Help me." | `true` | PII rejection message | ☐ |
| S5 | "How to download capital gains statement?" | `false` | Procedural answer + citation | ☐ |

> **Phase 4 gates on all 5 smoke tests passing.**

---

### Phase 4 — PASS Criteria
> Phase 4 is **PASS** when:
- Server starts and all endpoints return correct HTTP status codes
- All 5 advisory queries in E4.2 return `refused: true`
- All 4 PII queries in E4.3 return `refused: true` with no PII in logs
- All 5 smoke tests (E4.5) pass
- Schema validation rejects empty/missing queries with HTTP 422

---

## Phase 5 Evaluation — Frontend UI & Final Integration

**Goal of phase:** The `index.html` chat interface is connected to the live API and all success criteria from the problem statement are verified end-to-end.

---

### E5.1 — UI Load & Initial State

| # | Test | How to verify | Pass Condition | Priority |
|---|------|---------------|----------------|----------|
| 5.1.1 | Page loads in < 2 seconds | Browser DevTools → Network tab (with API running) | `DOMContentLoaded` < 2s | 🔴 |
| 5.1.2 | Welcome message visible | Visual inspection | Welcome banner with app name present on load | 🔴 |
| 5.1.3 | Facts-only disclaimer visible | Visual inspection | *"Facts-only. No investment advice."* text visible | 🔴 |
| 5.1.4 | 3 example question pills visible | Visual inspection | 3 clickable pills rendered with actual questions | 🔴 |
| 5.1.5 | No JS errors on load | Browser DevTools → Console tab | Console shows 0 errors | 🟡 |

---

### E5.2 — Interactive Flow

| # | Test | Steps | Pass Condition | Priority |
|---|------|-------|----------------|----------|
| 5.2.1 | Example pill pre-fills input | Click a pill | Input field populates with the question text | 🔴 |
| 5.2.2 | Send button submits | Click Send / press Enter | Loading spinner appears in chat | 🔴 |
| 5.2.3 | Answer renders in chat | Wait for response | Answer bubble appears; spinner disappears | 🔴 |
| 5.2.4 | Citation renders below answer | Visual inspection | *"Source: [name] · Last updated: [date]"* visible under answer | 🔴 |
| 5.2.5 | Citation link is clickable | Click citation link | Opens valid web page in new tab | 🔴 |
| 5.2.6 | Refusal renders differently | Submit "Should I buy HDFC Defence Fund?" | Refusal message styled differently (grey/muted); educational link shown | 🔴 |
| 5.2.7 | Input disabled while loading | Submit query; observe immediately | Send button disabled; input not editable during loading | 🟡 |
| 5.2.8 | Chat auto-scrolls | Submit several queries | Chat window scrolls to latest message after each response | 🟡 |
| 5.2.9 | Error state on API down | Stop API server; submit a query | Red-bordered error card: *"Could not reach the server."* | 🟡 |

---

### E5.3 — End-to-End Success Criteria Verification

These are the exact 6 success criteria from `problemStatement.md`:

| # | Success Criterion | Test method | Pass Condition | Priority |
|---|-------------------|-------------|----------------|----------|
| 5.3.1 | Answers all 6 factual question types for each scheme | Submit 1 question per type × 4 schemes = 24 queries; log answers | All 24 return factual, non-empty answers with citations | 🔴 |
| 5.3.2 | Every answer includes a valid, working citation link | Click all citation links from 5.3.1 | All 24 links open real, relevant pages (no 404s) | 🔴 |
| 5.3.3 | Advisory questions refused with polite message | Submit 5 advisory queries via UI | All 5 show styled refusal with educational link | 🔴 |
| 5.3.4 | UI shows welcome, 3 examples, facts-only disclaimer | Visual check on fresh load | All 3 elements present simultaneously | 🔴 |
| 5.3.5 | No PII accepted or stored | Submit query with PAN via UI; check server logs | UI shows rejection message; PAN absent from logs | 🔴 |
| 5.3.6 | All sources from approved allowlist | Cross-reference all citation URLs from 5.3.1 against `data/metadata.json` | Every URL appears in `metadata.json` as a `source_url` | 🔴 |

---

### E5.4 — 24-Query Matrix (Full Factual Coverage)

Submit each query via the UI and record the result:

| Query | Scheme | Expected content | Citation URL from allowlist? | ≤3 sentences? |
|-------|--------|-----------------|------------------------------|----------------|
| Expense ratio of HDFC Mid Cap Fund? | Mid Cap | % figure | ☐ | ☐ |
| Exit load for HDFC Mid Cap Fund? | Mid Cap | % + period | ☐ | ☐ |
| Minimum SIP for HDFC Mid Cap Fund? | Mid Cap | ₹ amount | ☐ | ☐ |
| Riskometer of HDFC Mid Cap Fund? | Mid Cap | Risk label | ☐ | ☐ |
| Benchmark of HDFC Mid Cap Fund? | Mid Cap | Index name | ☐ | ☐ |
| Fund manager of HDFC Mid Cap Fund? | Mid Cap | Name | ☐ | ☐ |
| Expense ratio of HDFC Equity Fund? | Equity | % figure | ☐ | ☐ |
| Exit load for HDFC Equity Fund? | Equity | % + period | ☐ | ☐ |
| Minimum SIP for HDFC Equity Fund? | Equity | ₹ amount | ☐ | ☐ |
| Riskometer of HDFC Equity Fund? | Equity | Risk label | ☐ | ☐ |
| Benchmark of HDFC Equity Fund? | Equity | Index name | ☐ | ☐ |
| Fund manager of HDFC Equity Fund? | Equity | Name | ☐ | ☐ |
| Expense ratio of HDFC Defence Fund? | Defence | % figure | ☐ | ☐ |
| Exit load for HDFC Defence Fund? | Defence | % + period | ☐ | ☐ |
| Minimum SIP for HDFC Defence Fund? | Defence | ₹ amount | ☐ | ☐ |
| Riskometer of HDFC Defence Fund? | Defence | Risk label | ☐ | ☐ |
| Benchmark of HDFC Defence Fund? | Defence | Index name | ☐ | ☐ |
| Fund manager of HDFC Defence Fund? | Defence | Name | ☐ | ☐ |
| Expense ratio of HDFC Silver ETF FoF? | Silver ETF | % figure | ☐ | ☐ |
| Exit load for HDFC Silver ETF FoF? | Silver ETF | % + period | ☐ | ☐ |
| Minimum SIP for HDFC Silver ETF FoF? | Silver ETF | ₹ amount | ☐ | ☐ |
| Riskometer of HDFC Silver ETF FoF? | Silver ETF | Risk label | ☐ | ☐ |
| ELSS lock-in period? | General | 3 years | ☐ | ☐ |
| How to download capital gains statement? | General | Steps | ☐ | ☐ |

> **Phase 5 gates on ≥ 22 of 24 queries passing (≥ 90%).**

---

### E5.5 — README Validation

| # | Test | Pass Condition | Priority |
|---|------|----------------|----------|
| 5.5.1 | README exists | `README.md` present in project root | 🟡 |
| 5.5.2 | Setup instructions are complete | Clone → venv → install → `.env` → `run_ingestion` → `build_index` → `uvicorn` steps all present | 🟡 |
| 5.5.3 | Instructions work on a clean shell | Follow README from scratch in a new terminal; no undocumented steps needed | 🟡 |

---

### Phase 5 — PASS Criteria
> Phase 5 is **PASS** (project complete) when:
- All 6 success criteria from the problem statement are verified ✅
- ≥ 22 of 24 queries in the full matrix return cited, factual answers
- All citation links are clickable, valid, and from the allowlist
- Advisory and PII queries are correctly refused in the UI
- README instructions work on a clean shell

---

## Overall Project Sign-Off Checklist

```
Phase 1:  Setup & Corpus         [ ] PASS
Phase 2:  Ingestion Pipeline     [ ] PASS
Phase 3:  Indexing & RAG Core    [ ] PASS
Phase 4:  API + Guard Rails      [ ] PASS
Phase 5:  UI & Integration       [ ] PASS

Hard constraint verification:
  [ ] No PII accepted or logged at any layer
  [ ] No investment advice returned for any query
  [ ] No citation URL outside data/metadata.json allowlist
  [ ] No hallucinated URL in any answer body
  [ ] Answer length ≤ 3 sentences for all factual responses
  [ ] "Last updated from sources: [date]" visible on every answer
```

> **Project is complete when all 5 phases are PASS and all 6 hard constraints are verified.**
