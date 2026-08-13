import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

MODEL_NAME = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

_client = None

def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        _client = Groq(api_key=api_key)
    return _client

import re

def truncate_to_three_sentences(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) > 3:
        return " ".join(sentences[:3])
    return text.strip()

def generate_answer(system_prompt: str, user_message: str) -> str:
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=256,
            temperature=0.0
        )
        choice = response.choices[0]
        if choice.finish_reason == "content_filter" or not choice.message.content:
            return "I don't have verified information on this. Please check the official HDFC AMC website or AMFI."
        return truncate_to_three_sentences(choice.message.content)
    except Exception as e:
        if "429" in str(e):
            logger.warning(f"Rate limited on {MODEL_NAME}. Falling back to {FALLBACK_MODEL}.")
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=messages,
                max_tokens=256,
                temperature=0.0
            )
            choice = response.choices[0]
            if choice.finish_reason == "content_filter" or not choice.message.content:
                return "I don't have verified information on this. Please check the official HDFC AMC website or AMFI."
            return truncate_to_three_sentences(choice.message.content)
        raise e
