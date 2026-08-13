from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import dotenv

from api.schemas import AskRequest, AskResponse
from guardrails.pii_filter import contains_pii
from guardrails.classifier import classify
from retrieval.retriever import retrieve
from generation.prompt_builder import build_prompt
from generation.llm_client import generate_answer

dotenv.load_dotenv()

app = FastAPI(title="Mutual Fund FAQ Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
async def serve_ui():
    return FileResponse("ui/index.html")

import asyncio

def is_english(text: str) -> bool:
    if not text:
        return False
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return (ascii_chars / len(text)) > 0.8

def get_expected_sources_count(query: str) -> int:
    query_lower = query.lower()
    funds = [
        'hdfc mid cap', 'hdfc midcap', 'mid cap', 'midcap',
        'hdfc silver etf', 'silver etf', 'silver',
        'hdfc defence', 'defence fund', 'defense fund', 'defence', 'defense',
        'hdfc equity', 'equity fund', 'equity',
        'hdfc small cap', 'hdfc smallcap', 'small cap', 'smallcap',
        'hdfc gold etf', 'gold etf', 'sbi gold', 'gold fund', 'hdfc gold', 'gold',
        'hdfc nifty 50', 'nifty 50', 'nifty50',
        'pharma and healthcare', 'pharma', 'healthcare',
        'balanced advantage', 'baf',
        'multi cap', 'multicap',
        'next 50', 'next50',
        'focused fund', 'focused',
        'short term',
        'large and mid', 'large & mid',
        'sensex',
        'manufacturing',
        'large cap', 'largecap',
        'liquid fund', 'liquid',
        'elss', 'tax saver',
        'smallcap 250',
        'bandhan small cap', 'bandhan',
        'parag parikh', 'ppfas',
        'motilal oswal', 'motilal',
        'nippon india', 'nippon'
    ]
    
    count = 0
    temp_query = query_lower
    for fund in sorted(funds, key=len, reverse=True):
        if fund in temp_query:
            occurrences = temp_query.count(fund)
            count += occurrences
            temp_query = temp_query.replace(fund, ' ')
            
    return max(1, count)

@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    query = request.query.strip()

    if not is_english(query):
        return AskResponse(
            answer="I can only process queries in English. Please ask your question in English.",
            refused=True
        )

    # Step 1: PII filter
    if contains_pii(query):
        return AskResponse(
            answer="Your query was refused because it contains personally identifiable information (PII).",
            refused=True
        )

    # Step 2: Guard rail
    if classify(query) == "advisory":
        return AskResponse(
            answer="I am a facts-only assistant and cannot provide investment advice or recommendations. Please consult a registered investment advisor or AMFI.",
            refused=True
        )

    # Step 3: RAG pipeline
    loop = asyncio.get_running_loop()
    chunks = await loop.run_in_executor(None, retrieve, query, 15)
    
    if not chunks:
        return AskResponse(
            answer="I don't have verified information on this. Please check the official HDFC AMC website or AMFI.",
            refused=False
        )
        
    system_prompt, user_msg = build_prompt(query, chunks)
    answer = generate_answer(system_prompt, user_msg)
    
    from api.schemas import Source
    unique_urls = set()
    sources = []
    max_sources = get_expected_sources_count(query)
    
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        url = meta.get("source_url")
        if url and url not in unique_urls:
            unique_urls.add(url)
            sources.append(Source(
                name=meta.get("source_name"),
                url=url,
                ingested_at=meta.get("ingested_at")
            ))
            if len(sources) >= max_sources:
                break

    return AskResponse(
        answer=answer,
        sources=sources,
        refused=False,
    )

@app.get("/examples")
async def get_examples():
    return {
        "examples": [
            "What is the exit load for HDFC Defence Fund?",
            "Who is the fund manager for HDFC Manufacturing Fund?",
            "Compare the expense ratios of HDFC Midcap and SBI Gold Fund"
        ]
    }
