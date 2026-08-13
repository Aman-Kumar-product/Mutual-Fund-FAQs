import numpy as np
from indexing.embedder import embed_query, embed_texts

ADVISORY_EXEMPLARS = [
    "Is this a good time to start a SIP?",
    "Which fund should I choose?",
    "Will this fund give good returns?",
    "Should I switch funds?",
]

def test_sim():
    queries = [
        "What is the expense ratio of HDFC Mid Cap Fund?",
        "Should I buy HDFC Defence Fund?",
        "Is this a good time to invest?",
        "How to download capital gains statement?"
    ]
    
    print("QUERY: EMBED_QUERY | EXEMPLAR: EMBED_TEXTS")
    ex_emb = embed_texts(ADVISORY_EXEMPLARS)
    for q in queries:
        q_emb = embed_query(q)
        scores = [np.dot(q_emb, ex) for ex in ex_emb]
        print(f"'{q}': max = {max(scores):.4f}")
        
    print("QUERY: EMBED_TEXTS | EXEMPLAR: EMBED_QUERY")
    ex_emb = [embed_query(ex) for ex in ADVISORY_EXEMPLARS]
    for q in queries:
        q_emb = embed_texts([q])[0]
        scores = [np.dot(q_emb, ex) for ex in ex_emb]
        print(f"'{q}': max = {max(scores):.4f}")

if __name__ == "__main__":
    test_sim()
