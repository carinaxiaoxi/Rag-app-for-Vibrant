import os, sys, requests, traceback
from dotenv import load_dotenv
load_dotenv()

from app.retriever import retrieve

TOP_K=int(os.getenv("TOP_K","8"))
RERANK_K=int(os.getenv("RERANK_K","4"))
def generate_answer_from_context(question: str, ctx: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "https://local.cli", 
        "X-Title": "rag-cli"
    }
    payload = {
        "model": os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct"),
        "messages": [
            {"role":"system","content":"Answer ONLY from the Context. If not present, apologize and say that you don't know. If the user didn't ask a question, simply ask them to ask a question and tell them that you can only answer questions. Be concise and don't provide sources."},
            {"role":"user","content": f"Question: {question}\n\nContext:\n{ctx}\n\nAnswer:"}
        ]
    }
    resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                         headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def main():
    if len(sys.argv) < 2:
        print("usage: python -m app.cli 'your question here'")
        sys.exit(1)

    q = " ".join(sys.argv[1:])
    print(f"[cli] Question: {q}", flush=True)

    print("[cli] Retrieving...", flush=True)
    hits = retrieve(q, top_k=TOP_K, rerank_k=RERANK_K)
    print(f"[cli] Retrieved {len(hits)} docs", flush=True)

    # Build compact context
    ctx = "\n\n".join(
        f"[{i+1}] {h.get('title')}\nURL: {h.get('url')}\n{(h.get('text') or '')[:1200]}"
        for i, h in enumerate(hits)
    )

    try:
        print("[cli] Generating answer...", flush=True)
        answer = generate_answer_from_context(q, ctx)
        print("\n=== Answer ===\n" + answer)
    except Exception as e:
        print(f"[cli] Generation failed: {e}", file=sys.stderr)
        traceback.print_exc()
        print("\n=== No answer generated===")


if __name__ == "__main__":
    main()
