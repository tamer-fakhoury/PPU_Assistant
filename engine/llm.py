import os
import logging
from groq import Groq

log = logging.getLogger("ppu.llm")

_client = None

CLASSIFY_SYSTEM = (
    "Classify the PPU query. Output one line: "
    "template:X | rag:X | llm | greeting\n"
    "X = contact | location | about | navigation | colleges | admission | tuition | academic_calendar | jobs | student_services\n\n"
    "Examples:\n"
    "- 'phone number' , 'رقم الهاتف' -> template:contact\n"
    "- 'address' , 'العنوان' , 'أين تقع' -> template:location\n"
    "- 'about PPU' , 'نبذة' , 'تاريخ' -> template:about\n"
    "- 'portal' , 'بوابة' , 'مكتبة' , 'library' -> template:navigation\n"
    "- 'colleges' , 'الكليات' , 'تخصصات' , 'طب الأسنان' -> rag:colleges\n"
    "- 'admission' , 'التسجيل' , 'القبول' -> rag:admission\n"
    "- 'fees' , 'الرسوم' , 'أسعار' , 'مصاريف' , 'تكلفة' -> rag:tuition\n"
    "- 'calendar' , 'التقويم' , 'الامتحانات' -> rag:academic_calendar\n"
    "- 'jobs' , 'وظائف' -> rag:jobs\n"
    "- 'student services' , 'خدمات طلابية' , 'سجل' -> rag:student_services\n"
    "- 'hello' , 'مرحبا' , 'كيفك' , 'شكرا' -> greeting\n"
    "- anything else , complex , unclear -> llm\n"
    "Output the line only."
)

MAX_TOKENS = 70
MAX_TOKENS_SEARCH = 30

SEARCH_SYSTEM = (
    "Given a user query and detected intent, output a short Arabic search query "
    "(3-7 words) to find relevant pages on the university site. "
    "Output the search query only.\n\n"
    "Examples:\n"
    "- query: 'how much is tuition' intent: tuition -> 'الرسوم الدراسية والمصاريف'\n"
    "- query: 'what colleges' intent: colleges -> 'كليات الجامعة والتخصصات'\n"
    "- query: 'exam dates' intent: academic_calendar -> 'التقويم الأكاديمي مواعيد الامتحانات'\n"
    "- query: 'admission requirements' intent: admission -> 'شروط القبول والتسجيل'\n"
    "- query: 'كيف اسعار الدراسة' intent: tuition -> 'الرسوم الدراسية والمصاريف'\n"
)


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            log.error("GROQ_API_KEY not set. LLM calls will fail.")
            return None
        _client = Groq(api_key=api_key)
    return _client


def classify_intent(query: str) -> str | None:
    client = _get_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": query},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.0,
        )
        return resp.choices[0].message.content.strip().lower()
    except Exception as e:
        log.error("Groq classify failed: %s", e)
        return None


def generate_search_query(query: str, intent_name: str | None) -> str | None:
    client = _get_client()
    if client is None:
        return None
    intent_label = intent_name or "general"
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SEARCH_SYSTEM},
                {"role": "user", "content": f"query: '{query}' intent: {intent_label}"},
            ],
            max_tokens=MAX_TOKENS_SEARCH,
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error("Groq search query gen failed: %s", e)
        return None
