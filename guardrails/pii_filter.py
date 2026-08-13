import re

PII_PATTERNS = [
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",           # PAN
    r"(?<!\d)\d{12}(?!\d)",                   # Aadhaar
    r"(?<!\d)[6-9]\d{9}(?!\d)",               # Indian mobile
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",  # email
]

def contains_pii(text: str) -> bool:
    for pattern in PII_PATTERNS:
        if re.search(pattern, text):
            return True
    return False
