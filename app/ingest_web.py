import argparse
import asyncio
import urllib.parse
from collections import deque
from typing import Iterable, Set, Tuple, Optional

from app.utils import clean_html, chunk_text
from app.retriever import embed_text, stable_id
from app.neo4j_store import Neo4JStore
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

def same_host(a: str, b: str) -> bool:
    return urllib.parse.urlparse(a).netloc == urllib.parse.urlparse(b).netloc


def _norm_url(base_url: str, href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    u = urllib.parse.urljoin(base_url, href)
    return u.split("#")[0]



async def _crawl_and_ingest_async(seed_url: str, max_pages: int) -> None:
    store = Neo4JStore()
    q: deque[str] = deque([seed_url])
    seen: Set[str] = set()
    count = 0

    async with AsyncWebCrawler() as crawler:
        while q and count < max_pages:
            url = q.popleft()
            if url in seen:
                continue
            seen.add(url)

            cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                remove_overlay_elements=True,
            )

            try:
                res = await crawler.arun(url=url, config=cfg)
            except Exception as e:
                print(f"[SKIP] {url} -> fetch error: {e}")
                continue

            if hasattr(res, "success") and not getattr(res, "success"):
                print(f"[SKIP] {url} -> crawler marked unsuccessful")
                continue

            html = getattr(res, "html", "") or getattr(res, "content", "")
            if not html:
                print(f"[SKIP] {url} -> empty HTML")
                continue

            title = (
                getattr(res, "title", None)
                or (getattr(res, "metadata", {}) or {}).get("title")
                or url
            )

            # Ingest as we go (streaming)
            print(f"[INGEST] {url}")
            text = clean_html(html)
            for idx, chunk in enumerate(chunk_text(text)):
                emb = embed_text(chunk)  # requires Ollama embeddings to be running
                store.upsert_doc(
                    {
                        "id": stable_id(f"{url}#chunk-{idx}"),
                        "title": f"{title} [part {idx+1}]",
                        "url": url,
                        "text": chunk,
                        "embedding": emb,
                    }
                )

            count += 1

            extracted: Set[str] = set()
            links = getattr(res, "links", None)
            for link in links:
                href = None
                if isinstance(link, str):
                    href = link
                else:
                    href = getattr(link, "url", None) or getattr(link, "href", None)
                    if href is None and isinstance(link, dict):
                        href = link.get("url") or link.get("href")
                nxt = _norm_url(url, href)
                if nxt:
                    extracted.add(nxt)


            for nxt in extracted:
                if nxt not in seen and same_host(seed_url, nxt):
                    q.append(nxt)


def crawl_and_ingest(seed_url: str, max_pages: int) -> None:
    asyncio.run(_crawl_and_ingest_async(seed_url, max_pages))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Crawl a site with crawl4ai and ingest into Neo4j.")
    ap.add_argument("--url", required=True, help="Seed URL (e.g., https://www.vibrant-wellness.com/test-menu/)")
    ap.add_argument("--max-pages", type=int, default=80)
    args = ap.parse_args()
    crawl_and_ingest(args.url, args.max_pages)
    print("Ingestion done.")
