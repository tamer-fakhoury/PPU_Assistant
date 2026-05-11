import os
import sys
import json
import logging
import re
import hashlib
from urllib.parse import urljoin

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("build_index")

PPU_BASE = "https://www.ppu.edu/p"
SEED_URLS = [
    f"{PPU_BASE}/ar",
    f"{PPU_BASE}/ar/about",
    f"{PPU_BASE}/ar/Colleges-Deanships",
    f"{PPU_BASE}/ar/contact",
    f"{PPU_BASE}/ar/admission",
    f"{PPU_BASE}/ar/about/academic-calender",
    f"{PPU_BASE}/ar/jobs",
    f"{PPU_BASE}/ar/about/structure",
    f"{PPU_BASE}/ar/about/laws",
    f"{PPU_BASE}/ar/about/Mission-Strategic-Plan",
    f"{PPU_BASE}/en",
    f"{PPU_BASE}/en/about",
    f"{PPU_BASE}/en/Colleges-Deanships",
    f"{PPU_BASE}/en/contact",
    "https://cet.ppu.edu/en",
    "https://cap.ppu.edu/en",
    "https://student.ppu.edu",
    "https://dspace.ppu.edu",
    f"{PPU_BASE}/en/about/structure",
    f"{PPU_BASE}/en/about/laws",
    f"{PPU_BASE}/ar/Announcements",
    f"{PPU_BASE}/ar/newsletter",
    f"{PPU_BASE}/en/newsletter",
]

EXCLUDE_PATTERNS = [
    r"/news/", r"/ppuregtour", r"\.pdf$", r"/sites/default/files",
    r"/user/", r"/node/", r"/print/",
]

MAX_PAGES = 30
CHUNK_SIZE = 300


def chunk_text(text: str, url: str, title: str) -> list[dict]:
    sentences = re.split(r"(?<=[.!?])\s+|(?<=[.!?])\s*\n", text)
    chunks = []
    current = []
    current_len = 0
    # Prepend URL and title to every chunk so FAISS retrieves them by relevance
    url_prefix = f"رابط: {url} | صفحة: {title} | "
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        current.append(s)
        current_len += len(s.split())
        if current_len >= CHUNK_SIZE:
            full = url_prefix + " ".join(current)
            chunks.append({"text": full, "url": url, "title": title})
            current = []
            current_len = 0
    if current:
        full = url_prefix + " ".join(current)
        chunks.append({"text": full, "url": url, "title": title})
    return chunks


def scrape() -> list[dict]:
    all_chunks = []
    visited = set()
    queue = list(SEED_URLS)

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        while queue and len(visited) < MAX_PAGES:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception as e:
                log.warning("Failed %s: %s", url, e)
                continue

            content_type = resp.headers.get("content-type", "")
            if "pdf" in content_type or url.endswith(".pdf"):
                log.info("Skipping PDF: %s", url)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else url

            for unwanted in soup.select(".sidebar, nav, .menu, #block-views-exp-links-block, .quick-links, footer"):
                unwanted.decompose()
            main = soup.find("main") or soup.find("article") or soup.find("div", class_=["content", "page-content", "region-content"]) or soup.find("body")
            if not main:
                main = soup
            text = main.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"[^\u0600-\u06FF\u0750-\u077Fa-zA-Z0-9\s\.\,\:\;\-\/\@\(\)\[\]\"\'\+\#\_0-9]", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 10:
                log.info("Skipping %s (too short: %d chars)", url, len(text))
                continue

            chunks = chunk_text(text, url, title)
            all_chunks.extend(chunks)
            log.info("Scraped %s (%d chunks)", url, len(chunks))

            for a in soup.find_all("a", href=True):
                href = a["href"]
                full = urljoin(PPU_BASE, href)
                if not full.startswith(PPU_BASE):
                    continue
                if any(re.search(p, full) for p in EXCLUDE_PATTERNS):
                    continue
                if full not in visited:
                    queue.append(full)

    log.info("Total chunks: %d from %d pages", len(all_chunks), len(visited))
    return all_chunks


def build_index(chunks: list[dict]):
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    chunks_path = os.path.join(out_dir, "ppu_chunks.json")
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    log.info("Embedding %d chunks...", len(chunks))
    model = SentenceTransformer("intfloat/multilingual-e5-small")
    texts = ["passage: " + c["text"] for c in chunks]
    embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    import faiss
    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(np.array(embs).astype(np.float32))
    faiss.write_index(index, os.path.join(out_dir, "faiss_index.bin"))
    log.info("FAISS index saved (%d vectors)", len(chunks))


def main():
    log.info("Starting PPU site scrape...")
    chunks = scrape()
    if not chunks:
        log.error("No chunks scraped. Check PPU site accessibility.")
        sys.exit(1)
    build_index(chunks)
    log.info("Build complete: %d chunks indexed.", len(chunks))


if __name__ == "__main__":
    main()
