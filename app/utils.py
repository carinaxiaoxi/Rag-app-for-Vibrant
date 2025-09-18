import re
from bs4 import BeautifulSoup

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # remove scripts/styles/navs
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return normalize_ws(text)

def normalize_ws(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text) 
    return text.strip()

def chunk_text(text: str, max_chars: int = 1800, overlap: int = 200):
    # simple char-based chunking suitable for web pages.
    text = text.strip()
    if len(text) <= max_chars:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end]
        yield chunk
        if end == len(text):
            break
        start = end - overlap
        if start < 0:
            start = 0