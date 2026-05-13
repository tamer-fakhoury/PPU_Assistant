# PROJECT_MAP.md — PPU Assistant

## Current State (Updated 2026-05-13)

### Architecture Overview

```
User (Chat UI)
    │ GET /query?q=...
    ▼
FastAPI Server (main.py)
    │
    ├─ Intent Router (engine/router.py)
    │   ├─ Greeting regex  →  greeting
    │   ├─ LLM classify    →  template:X | rag:X | llm | greeting
    │   └─ Embedding fallback (E5-small)
    │
    ├─ Template intents → get_template_response() → static text + sources
    ├─ Greeting         → get_greeting_response()
    ├─ RAG/LLM intents:
    │   1. _resolve_search_query()  →  LLM generates Arabic search query
    │   2. search()                 →  FAISS top_k=25 chunks
    │   3. _pick_intent_chunk()     →  intent-URL-prioritized best chunk
    │   4. ask()                    →  LLM generates answer from top 5 chunks
    │   5. Format: [LLM answer]<br><br>رابط الصفحة: [URL link]
    │
    └─ Unknown/low-relevance → get_help_template()
```

### Key Components

| File | Role |
|------|------|
| `main.py` | FastAPI app entry point: `/query`, `/query/stream`, `/health`, `/` |
| `engine/llm.py` | Groq client: `classify_intent` (≤70 tok), `generate_search_query` (≤30 tok), `ask` (≤120 tok) |
| `engine/router.py` | Intent resolution: LLM primary, E5 embedding fallback; template/greeting/help responders |
| `engine/rag.py` | FAISS + E5-small search; `"query: "` prefix on encode |
| `engine/response.py` | `PPUResponse` dataclass + `format_response()` |
| `engine/intents.yaml` | 10 intents with exemplars, templates, thresholds, sources |
| `preload/build_index.py` | Scrapes 30 seed URLs, builds 300-char chunks with E5-small embeddings |
| `preload/build_intents.py` | Embeds exemplars with E5-small for fallback router |
| `static/widget.js` | Self-contained floating chat widget (IIFE, RTL) |
| `static/index.html` | Landing page + embed documentation |
| `wsgi.py` | WSGI entry point via `a2wsgi` |

### Query Pipeline (RAG path)

1. `classify_intent(query)` → Groq → `rag:admission` / `llm`
2. `_resolve_search_query()` → Groq generates Arabic search query
3. `search(query, top_k=25)` → FAISS: E5 "query:" embedding → 25 chunks with scores
4. `_pick_intent_chunk(chunks, intent_name)` → first chunk matching intent URL keywords
5. `ask(query, chunks)` → sends top 5 chunks to Groq → generates short answer (≤120 tok)
6. Response: `{answer}<br><br>رابط الصفحة: <a class="link" href="{url}">{url}</a>`
7. If LLM unavailable or no chunks, falls back to help template

### Response Types

| Type | Handler | Content |
|------|---------|---------|
| `greeting` | `get_greeting_response()` | Static welcome text |
| `template` | `get_template_response()` | Static template text from intents.yaml |
| `rag`/`llm` | `ask()` + URL link | LLM-generated answer + clickable source URL |
| `help` | `get_help_template()` | Help instructions with available topics |

### Environment

- **LLM**: Groq API (`llama-3.1-8b-instant`)
- **Embedding**: `intfloat/multilingual-e5-small` (384-dim)
- **Vector DB**: FAISS `IndexFlatIP`, 33 chunks from 29 PPU pages
- **Corpus Format**: `passage: رابط: {url} | صفحة: {title} | {chunk_text}` (300-char chunks)

### Bot Architecture Documentation

`BOT_ARCHETICTURE.md` — describes the system as a conversational bot: identity, states, intents, intent paths, response types, fallback chain, edge cases, knowledge base, LLM configuration, and full flow diagrams. Updated whenever intents or routing logic changes.

### Test Results (2026-05-13)

All 4 paths pass:
- Greeting → `method=greeting`
- Template (contact) → `method=template`
- Unknown → `method=help`
- RAG (admission) → `method=rag` with LLM answer + "رابط الصفحة:" link

### Known Limitations

- 300-char chunks may not contain enough detail for LLM to answer fully → LLM says "لا أعلم" but link is always provided
- Fees page (`/ar/fees`) returns 404 → tuition queries fall back to admission page
- Small corpus (33 chunks) limits coverage; college-specific subpages not indexed
- LLM may misclassify "how to apply" as `template:contact` (not caught by safety net)
- `ask()` is a sync call in async streaming endpoint (matches existing pattern)
