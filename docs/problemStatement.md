# Problem Statement — Mutual Fund FAQ Assistant (RAG)

## Overview

This project is a **Retrieval-Augmented Generation (RAG) FAQ assistant** focused on **Mutual Fund schemes**. It answers factual queries about specific HDFC Mutual Fund schemes using only verified, publicly available official sources — no opinions, no investment advice, no third-party blogs.

The assistant is built as part of a **LIP (Learning In Public) Challenge**, with **Groww** selected as the product reference platform.

---

## Product Context

**Platform chosen:** [Groww](https://groww.in)  
**AMC chosen:** HDFC Mutual Fund  
**Schemes in scope (4 schemes):**

| Scheme | Groww URL |
|--------|-----------|
| HDFC Mid Cap Opportunities Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| HDFC Silver ETF FoF – Direct Growth | https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth |
| HDFC Defence Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth |
| HDFC Equity Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |

---

## Problem Being Solved

Retail investors comparing mutual fund schemes face a fragmented research experience:

- Factsheets, KIMs, SIDs, and SEBI/AMFI pages are scattered across many URLs.
- Common factual questions (expense ratio, exit load, lock-in period, SIP minimum, riskometer level, benchmark) require manually opening multiple PDFs or pages.
- Support teams repeatedly answer the same 10–15 questions.

This assistant consolidates those facts into a single conversational interface backed by a RAG pipeline grounded in official sources.

---

## Goal

Build a **working FAQ assistant prototype** that:

1. Answers **factual, scheme-specific queries** such as:
   - *"What is the expense ratio of HDFC Mid Cap Fund?"*
   - *"What is the ELSS lock-in period?"*
   - *"What is the minimum SIP amount for HDFC Equity Fund?"*
   - *"What is the exit load for HDFC Defence Fund?"*
   - *"What is the riskometer rating of HDFC Silver ETF FoF?"*
   - *"How do I download a capital gains statement from Groww?"*

2. **Refuses** subjective or advisory questions politely:
   - *"Should I invest in HDFC Mid Cap Fund?"* → Declined with a polite, facts-only message and a relevant educational link.

3. Displays **one clear citation link** per answer (source traceability).

4. Shows a minimal UI with:
   - A welcome line
   - 3 example questions
   - A disclaimer: *"Facts-only. No investment advice."*
   - Answer timestamps: *"Last updated from sources: [date]"*

---

## Data Scope (Tiers 1, 2, and 3)

The assistant must extract and serve the following data points for the 4 schemes:

**Tier 1 — Core Factual Data:**
- Expense ratio
- Minimum SIP & Minimum investment
- Exit load
- Riskometer
- Fund manager
- Benchmark
- Category
- Investment objective
- Plan/option
- Source URL & Last updated

**Tier 2 — Advanced Factual Data:**
- Asset allocation & Portfolio characteristics
- Inception date
- NAV + NAV date
- Additional investment minimum
- Purchase/redemption information & Cut-off information

> **Only official, public sources.** No screenshots of app back-ends, no third-party blogs, no social media.

---

## Key Constraints

| Constraint | Description |
|------------|-------------|
| **Public sources only** | No private/internal data, no third-party editorial content |
| **No PII** | Do not accept, process, or store PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers |
| **No performance claims** | Do not compute, compare, or project returns; link to the official factsheet if asked |
| **Facts only** | Answers ≤ 3 sentences; always include a citation link |
| **No investment advice** | Politely decline any advisory/portfolio questions |
| **Transparency** | Every answer must show its source and an approximate "last updated" date |

---

## Technical Scope

| Layer | Details |
|-------|---------|
| **Data ingestion** | Scrape / download 4 official pages; parse PDFs and HTML |
| **Chunking & Embedding** | Split documents into chunks; embed with `BAAI/bge-base-en-v1.5` (local BGE model) |
| **Vector Store** | Store 768-dim BGE embeddings in ChromaDB for semantic retrieval |
| **Retrieval** | Top-k cosine similarity search; BGE query prefix applied at retrieval time |
| **Generation** | **Groq API** (`llama-3.3-70b-versatile`) generates answers grounded strictly in retrieved chunks |
| **Citation** | Each answer references the source URL from metadata |
| **UI** | Minimal chat interface — welcome message, 3 example Qs, facts-only disclaimer |

---

## Who This Helps

- **Retail investors** comparing HDFC MF schemes before investing
- **Support / content teams** answering repetitive factual MF questions
- **Financial educators** who need a citation-grounded reference tool

---

## Out of Scope

- Portfolio recommendations or returns analysis
- Real-time NAV tracking or price alerts
- Login / authentication / user accounts
- Any non-HDFC AMC schemes (for this iteration)
- Opinionated comparisons between schemes

---

## Success Criteria

- [ ] Assistant correctly answers all 6 core factual question types for each scheme
- [ ] Every answer includes a valid, working source citation link
- [ ] Advisory/opinion questions are refused with a polite message
- [ ] UI shows welcome message, 3 example questions, and the facts-only disclaimer
- [ ] No PII is accepted or stored anywhere in the pipeline
- [ ] All retrieved data originates from the approved official sources list
