import httpx
from typing import List
from app import config

SYS_PROMPT = (
"You are an accurate, concise assistant. Answer ONLY from the provided context. "
"If the answer isn’t in the context, say you don’t know."
)

def call_openrouter(model: str, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://example.com",
        "X-Title": "Vibrant RAG"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2
    }
    with httpx.Client(timeout=60) as client:
        r = client.post("https://openrouter.ai/api/v1/chat/completions",
                        headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

def build_prompt(query: str, docs: List[dict]) -> str:
    ctx = "\n\n---\n\n".join(
        [f"TITLE: {d['title']}\nURL: {d.get('url','')}\nCONTENT:\n{d['text'][:1800]}" for d in docs]
    )
    return f"User question: {query}\n\nContext:\n{ctx}\n\nAnswer the question using ONLY the context above."
