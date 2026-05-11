import logging
import yaml
import os
import re
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

log = logging.getLogger("ppu.router")

_INTENTS_CACHE = None
_EMBEDDING_MODEL = None

GREETING_PATTERNS = re.compile(
    r"^(مرحبا|اهلا|سلام|كيفك|كيف حالك|hello|hi|hey|how are you|good morning|thanks|شكرا|kefak|kifak|hala)\b",
    re.IGNORECASE,
)

_RAG_INTENTS = {"colleges", "admission", "tuition", "academic_calendar", "jobs", "student_services"}


def _load_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = SentenceTransformer("intfloat/multilingual-e5-small")
    return _EMBEDDING_MODEL


def _load_intents():
    global _INTENTS_CACHE
    if _INTENTS_CACHE is not None:
        return _INTENTS_CACHE
    yaml_path = os.path.join(os.path.dirname(__file__), "intents.yaml")
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _INTENTS_CACHE = data["intents"]
    return _INTENTS_CACHE


def _detect_lang(text: str) -> str:
    for ch in text:
        if "\u0600" <= ch <= "\u06FF":
            return "ar"
    return "en"


def _is_greeting(query: str) -> bool:
    return bool(GREETING_PATTERNS.match(query.strip()))


class IntentResult:
    def __init__(self, action: str, intent_name: str | None, lang: str):
        self.action = action
        self.intent_name = intent_name
        self.lang = lang


def parse_llm_output(output: str) -> IntentResult | None:
    output = output.strip().lower()
    m = re.match(r"(template|rag|llm|greeting):?(\w*)?", output)
    if not m:
        return None
    action = m.group(1)
    intent_name = m.group(2) or None
    return IntentResult(action=action, intent_name=intent_name, lang="ar")


def resolve_intent_via_llm(query: str, llm_classify_fn) -> IntentResult | None:
    # Quick greeting detection without LLM
    if _is_greeting(query):
        return IntentResult(action="greeting", intent_name=None, lang=_detect_lang(query))

    raw = llm_classify_fn(query)
    if not raw:
        log.info("LLM classify unavailable, falling back to embedding router")
        return _resolve_intent_embedding(query)
    result = parse_llm_output(raw)
    if result:
        result.lang = _detect_lang(query)
        # Safety net: if LLM says template but intent is a rag intent, correct it
        if result.action == "template" and result.intent_name in _RAG_INTENTS:
            log.info("LLM misclassified '%s' as template -> correcting to rag", result.intent_name)
            result.action = "rag"
    return result


def _resolve_intent_embedding(query: str) -> IntentResult | None:
    intents = _load_intents()
    try:
        model = _load_model()
    except Exception:
        return None

    embed_path = os.path.join(os.path.dirname(__file__), "..", "data", "intents_embedded.pkl")
    if not os.path.exists(embed_path):
        log.error("intents_embedded.pkl not found.")
        return None

    with open(embed_path, "rb") as f:
        exemplar_embs = pickle.load(f)

    from .normalize import normalize_arabic
    q_emb = model.encode("query: " + normalize_arabic(query), normalize_embeddings=True)

    best_name = None
    best_sim = 0.0
    best_type = None
    for name, intent in intents.items():
        ex_embs = exemplar_embs.get(name)
        if ex_embs is None or len(ex_embs) == 0:
            continue
        sims = np.dot(ex_embs, q_emb)
        max_sim = float(sims.max())
        if max_sim >= intent.get("threshold", 0.5) and max_sim > best_sim:
            best_name = name
            best_sim = max_sim
            best_type = intent["type"]

    if best_name is None:
        return IntentResult(action="llm", intent_name=None, lang=_detect_lang(query))

    return IntentResult(action=best_type, intent_name=best_name, lang=_detect_lang(query))


def get_template_response(intent_name: str, lang: str = "ar") -> tuple[str, list[str]]:
    intents = _load_intents()
    intent = intents.get(intent_name)
    if not intent:
        return "", []
    key = f"response_{lang}"
    text = intent.get(key) or intent.get("response_ar", "")
    sources = intent.get("sources", [])
    return text, sources


def get_greeting_response(lang: str = "ar") -> tuple[str, list[str]]:
    if lang == "ar":
        return "مرحباً بك في مساعد جامعة بوليتكنك فلسطين. كيف يمكنني مساعدتك؟", []
    return "Welcome to PPU Assistant. How can I help you?", []


def get_fallback_search_query(intent_name: str, lang: str = "ar") -> str | None:
    intents = _load_intents()
    intent = intents.get(intent_name)
    if not intent:
        return None
    ex = intent.get("exemplars", {})
    lang_ex = ex.get(lang, ex.get("ar", ex.get("en", [])))
    if not lang_ex:
        return None
    return lang_ex[0]


def get_help_template(lang: str = "ar") -> tuple[str, list[str]]:
    if lang == "ar":
        return (
            "يمكنني مساعدتك في:\n"
            "• أرقام التواصل والعنوان\n"
            "• الكليات والتخصصات\n"
            "• شروط القبول والتسجيل\n"
            "• الرسوم الدراسية\n"
            "• التقويم الأكاديمي\n"
            "• الوظائف الشاغرة\n"
            "• الخدمات الطلابية\n"
            "• روابط البوابة الإلكترونية والمكتبة\n\n"
            "اكتب سؤالك وسأوجهك للصفحة المناسبة."
        ), ["https://www.ppu.edu/p/ar"]
    return (
        "I can help you with:\n"
        "• Contact info and location\n"
        "• Colleges and programs\n"
        "• Admission requirements\n"
        "• Tuition fees\n"
        "• Academic calendar\n"
        "• Job vacancies\n"
        "• Student services\n"
        "• Portal and library links\n\n"
        "Ask me a question and I will direct you to the right page."
    ), ["https://www.ppu.edu/p/en"]
