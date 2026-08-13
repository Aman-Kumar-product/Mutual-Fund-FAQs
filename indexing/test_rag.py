"""
indexing/test_rag.py
"""
import sys
import logging
from dotenv import load_dotenv
load_dotenv()
from retrieval.retriever import retrieve
from generation.prompt_builder import build_prompt
from generation.llm_client import generate_answer

logging.basicConfig(level=logging.ERROR)

def test_rag(query: str):
    print(f"Query: {query}")
    chunks = retrieve(query, top_k=5)
    if not chunks:
        print("Answer: I don't have verified information on this. Please check the official HDFC AMC website or AMFI.")
        return
    
    system_prompt, user_msg = build_prompt(query, chunks)
    answer = generate_answer(system_prompt, user_msg)
    citation = chunks[0]["metadata"]
    
    print(f"Answer: {answer}")
    print(f"Source: {citation.get('source_name')} — {citation.get('source_url')}")

if __name__ == "__main__":
    test_queries = [
        "What is the expense ratio of HDFC Mid Cap Fund?",
        "What is the exit load for HDFC Defence Fund?",
        "What is the minimum SIP for HDFC Equity Fund?",
        "What is the riskometer rating of HDFC Silver ETF FoF?",
        "What is the ELSS lock-in period?",
        "How to download capital gains statement from Groww?",
        "What is the NAV of HDFC Small Cap?"
    ]
    
    if len(sys.argv) > 1:
        test_queries = [" ".join(sys.argv[1:])]
        
    for q in test_queries:
        test_rag(q)
        print("-" * 40)
