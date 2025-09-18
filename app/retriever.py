import os, hashlib
import numpy as np
import requests
from typing import List, Dict
from rank_bm25 import BM25Okapi
from app.neo4j_store import Neo4JStore
from dotenv import load_dotenv
load_dotenv()

# where the Ollama daemon is listening
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

def _call_embeddings(payload):
    r = requests.post(f"{OLLAMA_HOST}/api/embeddings", json=payload, timeout=60)
    r.raise_for_status()
    d = r.json()
    if "embeddings" in d:   # batch
        return d["embeddings"]
    if "embedding" in d:    # single
        return [d["embedding"]]
    return None

def _ollama_embed(texts: List[str], model: str) -> List[List[float]]:
    x = texts if len(texts) > 1 else texts[0]
    vecs = _call_embeddings({"model": model, "input": x})
    if not vecs or any(len(v) == 0 for v in vecs):
        vecs = _call_embeddings({"model": model, "prompt": x})
    if not vecs or any(len(v) == 0 for v in vecs):
        raise RuntimeError(f"Empty embeddings from Ollama for model '{model}'.")
    return vecs

def embed_text(text: str) -> List[float]:
    return _ollama_embed([text], EMBED_MODEL)[0]

def embed_texts(texts: List[str]) -> List[List[float]]:
    # kept for compatibility, but we won't use it for docs anymore
    return [embed_text(t) for t in texts]

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def mmr(query_vec, doc_vecs, lambda_mult=0.7, k=4):
    doc_vecs = np.array(doc_vecs)
    n = len(doc_vecs)
    selected, candidates = [], list(range(n))
    sims = doc_vecs @ query_vec / (np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-9)
    for _ in range(min(k, n)):
        if not selected:
            idx = int(np.argmax(sims))
            selected.append(idx); candidates.remove(idx); continue
        div = []
        for c in candidates:
            max_sim_to_selected = max(cosine(doc_vecs[c], doc_vecs[s]) for s in selected)
            score = lambda_mult * sims[c] - (1 - lambda_mult) * max_sim_to_selected
            div.append((score, c))
        div.sort(reverse=True)
        chosen = div[0][1]
        selected.append(chosen); candidates.remove(chosen)
    return selected

def _fetch_embeddings_and_text(store: Neo4JStore, ids: List[str]) -> Dict[str, Dict]:
    """
    Bulk fetch {id: {embedding, text}} to avoid re-embedding docs at query.
    """
    if not ids:
        return {}
    cypher = """
    UNWIND $ids AS id
    MATCH (d:Doc {id:id})
    RETURN d.id AS id, d.embedding AS embedding, d.text AS text
    """
    out = {}
    with store.driver.session() as s:
        for r in s.run(cypher, ids=ids):
            out[r["id"]] = {"embedding": r["embedding"], "text": r["text"]}
    return out

def retrieve(query: str, top_k=8, rerank_k=4) -> List[Dict]:
    store = Neo4JStore()

    # embed the query 
    q_emb = embed_text(query)
    qv = np.array(q_emb, dtype=np.float32)

    # get candidates
    vec_hits = store.vector_search(q_emb, top_k)    
    kw_hits  = store.fulltext_search(query, top_k) 

    # score keyword hits
    bm25 = BM25Okapi([ (d.get("text") or "").split()[:2000] for d in kw_hits ] or [[""]])
    kw_scored = []
    if kw_hits:
        scores = bm25.get_scores(query.split())
        for d, s in zip(kw_hits, scores):
            d2 = dict(d); d2["bm25"] = float(s); kw_scored.append(d2)

    # merge
    merged = {d["id"]: {**d, "vec_score": float(d.get("score", 0.0))} for d in vec_hits}
    for i, d in enumerate(kw_scored):
        if d["id"] in merged:
            merged[d["id"]]["bm25"] = float(d["bm25"])
            for k in ("title","url","text"):
                if not merged[d["id"]].get(k):
                    merged[d["id"]][k] = d.get(k)
        else:
            merged[d["id"]] = {**d, "vec_score": 0.0}

    candidates = list(merged.values())
    if not candidates:
        return []

    # fetch stored embeddings
    id_list = [c["id"] for c in candidates]
    id2data = _fetch_embeddings_and_text(store, id_list)
    keep, doc_vecs = [], []
    for c in candidates:
        data = id2data.get(c["id"])
        emb = data["embedding"] if data else None
        if emb:
            c.setdefault("text", data.get("text"))
            keep.append(c)
            doc_vecs.append(np.array(emb, dtype=np.float32))
    candidates = keep
    if not candidates:
        return []

    #  MMR using stored embeddings
    idxs = mmr(qv, doc_vecs, k=rerank_k)
    return [candidates[i] for i in idxs]

def stable_id(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

