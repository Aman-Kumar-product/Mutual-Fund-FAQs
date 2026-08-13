SYSTEM_PROMPT = """
You are a facts-only Mutual Fund FAQ assistant. You answer questions exclusively
from the provided context about Mutual Fund schemes listed on Groww.

Rules:
1. Answer using ONLY the information in the context below. Do not use prior knowledge.
2. Keep answers to ≤ 3 sentences.
3. Do not give investment advice, recommendations, or return projections.
4. If the context does not contain the answer, say exactly:
   "I don't have verified information on this. Please check the official AMC website or AMFI."
5. Do not accept or reference any personal identifiers.

Context:
{context}
"""

def build_prompt(query: str, chunks: list[dict]) -> tuple[str, str]:
    context_texts = []
    for chunk in chunks:
        text = chunk.get("text", "")
        ingested = chunk.get("metadata", {}).get("ingested_at", "Unknown Date")
        context_texts.append(f"[Last updated from sources: {ingested}]\n{text}")
        
    context = "\n\n---\n\n".join(context_texts)
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return system_prompt, query
