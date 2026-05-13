import os
import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from engine.router import resolve_intent_via_llm, get_template_response, get_greeting_response, get_help_template, get_fallback_search_query
from engine.rag import search
from engine.llm import classify_intent, generate_search_query, ask
from engine.response import format_response

load_dotenv()
load_dotenv(dotenv_path=".env.example", override=False)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ppu")

RELEVANCE_THRESHOLD = 0.15

_INTENT_URL_KEYWORDS = {
    "admission": ["admission"],
    "tuition": ["admission", "fees"],
    "colleges": ["colleges", "deanships"],
    "academic_calendar": ["academic", "calendar", "calender"],
    "jobs": ["jobs"],
    "student_services": ["student", "services"],
    "contact": ["contact"],
    "location": ["contact"],
    "about": ["about"],
}


def _pick_intent_chunk(chunks: list[dict], intent_name: str | None) -> dict | None:
    if not chunks or not intent_name:
        return chunks[0] if chunks else None
    keywords = _INTENT_URL_KEYWORDS.get(intent_name)
    if not keywords:
        return chunks[0] if chunks else None
    for c in chunks:
        if any(k.lower() in c.get("url", "").lower() for k in keywords):
            return c
    return chunks[0] if chunks else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("PPU Assistant starting...")
    yield
    log.info("PPU Assistant stopped.")


app = FastAPI(title="PPU Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


def _resolve_search_query(q: str, intent) -> str:
    if not intent or intent.action not in ("rag", "llm"):
        return q
    sq = generate_search_query(q, intent.intent_name)
    if not sq:
        sq = get_fallback_search_query(intent.intent_name, intent.lang)
    return sq or q


@app.get("/query")
def query(q: str = Query(..., min_length=1, max_length=500)):
    log.info("Query: %s", q[:80])

    intent = resolve_intent_via_llm(q, classify_intent)

    # ── Greeting → no RAG, no LLM ──
    if intent and intent.action == "greeting":
        text, _ = get_greeting_response(intent.lang)
        return format_response(text, [], "greeting").to_dict()

    # ── Template → no RAG, no LLM ──
    if intent and intent.action == "template" and intent.intent_name:
        text, sources = get_template_response(intent.intent_name, intent.lang)
        if text:
            return format_response(text, sources, "template").to_dict()

    # ── RAG / LLM → resolve search query → retrieve → LLM answer + URL ──
    if intent and intent.action in ("rag", "llm"):
        search_query = _resolve_search_query(q, intent)
        chunks = search(search_query, top_k=25)
        best = _pick_intent_chunk(chunks, intent.intent_name)
        if best and best.get("score", 0) >= RELEVANCE_THRESHOLD:
            sources = list(dict.fromkeys(c.get("url", "") for c in chunks if c.get("url")))
            answer = ask(q, chunks)
            best_url = best.get("url", "")
            url_html = f'<a class="link" href="{best_url}" target="_blank">{best_url}</a>'
            text = f"{answer}<br><br>رابط الصفحة: {url_html}" if answer else f"رابط الصفحة: {url_html}"
            return format_response(text, sources, intent.action).to_dict()

    text, sources = get_help_template("ar")
    return format_response(text, sources, "help").to_dict()


@app.get("/query/stream")
def query_stream(q: str = Query(..., min_length=1, max_length=500)):
    intent = resolve_intent_via_llm(q, classify_intent)

    if intent and intent.action == "greeting":
        text, _ = get_greeting_response(intent.lang)
        return format_response(text, [], "greeting").to_dict()

    if intent and intent.action == "template" and intent.intent_name:
        text, sources = get_template_response(intent.intent_name, intent.lang)
        if text:
            return format_response(text, sources, "template").to_dict()

    async def generate():
        yield f"data: {json.dumps({'type': 'status', 'text': 'جاري البحث...'})}\n\n"

        if intent and intent.action in ("rag", "llm"):
            search_query = _resolve_search_query(q, intent)
            chunks = search(search_query, top_k=25)
            best = _pick_intent_chunk(chunks, intent.intent_name)
            if best and best.get("score", 0) >= RELEVANCE_THRESHOLD:
                sources = list(dict.fromkeys(c.get("url", "") for c in chunks if c.get("url")))
                answer = ask(q, chunks)
                best_url = best.get("url", "")
                url_html = f'<a class="link" href="{best_url}" target="_blank">{best_url}</a>'
                text = f"{answer}<br><br>رابط الصفحة: {url_html}" if answer else f"رابط الصفحة: {url_html}"
                yield f"data: {json.dumps({'text': text, 'sources': sources, 'method': intent.action})}\n\n"
                return

        text, sources = get_help_template("ar")
        yield f"data: {json.dumps({'text': text, 'sources': sources, 'method': 'help'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
