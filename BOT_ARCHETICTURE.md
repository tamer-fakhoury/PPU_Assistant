# BOT_ARCHITECTURE.md — PPU Assistant

## 1. هُوية البوت (Bot Identity)

- **الاسم:** مساعد جامعة بوليتكنك فلسطين (PPU Assistant)
- **الدور:** بوت محادثة يُرشد زوار موقع الجامعة إلى المعلومات الرسمية عبر روابط مباشرة
- **الجمهور:** طلبة جدد، طلبة حاليين، زوار الموقع
- **اللغة:** العربية (أساسي) والإنجليزية
- **واجهة الاستخدام:** واجهة محادثة عائمة (Floating Chat Widget) تُحقن في أي صفحة ويب عبر `<script>`
- **مبدأ أساسي:** لا يُولّد البوت معلومات من عنده — يعتمد كليًا على محتوى موقع الجامعة الرسمي

---

## 2. حالات البوت (Bot States)

```
                                        ┌─────────────────┐
                                        │    $idle        │
                                        │  (انتظار سؤال)  │
                                        └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │  $classifying   │
                                        │ (تصنيف القصد)   │
                                        └────────┬────────┘
                                                 │
                   ┌──────────────────────────────┼──────────────────────────────┐
                   │                              │                              │
                   ▼                              ▼                              ▼
          ┌────────────────┐           ┌─────────────────────┐         ┌───────────────────┐
          │  $greeting     │           │  $template_respond  │         │  $rag_searching   │
          │ (ترحيب)        │           │  (رد ثابت)          │         │ (بحث في المصادر)  │
          └────────┬───────┘           └──────────┬──────────┘         └──────────┬────────┘
                   │                              │                               │
                   ▼                              ▼                               ▼
          ┌────────────────┐           ┌─────────────────────┐         ┌────────────────────┐
          │ رد ترحيب ثابت  │           │   رد بنص ثابت +     │         │  توليد جواب + رابط │
          │                │           │   روابط من YAML     │         │  (LLM answer + URL)│
          └────────────────┘           └─────────────────────┘         └────────────────────┘
```

### 2.1 قائمة الحالات

| الحالة | الشرح |
|--------|--------|
| `$idle` | البوت في انتظار إدخال المستخدم. شاشة البداية تظهر رسالة ترحيب مع قائمة بالمواضيع |
| `$classifying` | البوت يُصنّف قصد المستخدم: إما (1) LLM عبر Groq، أو (2) Embedding Fallback |
| `$greeting` | تم اكتشاف تحية → رد ترحيب ثابت فوري (بدون استدعاء LLM) |
| `$template_respond` | تم تصنيف القصد كأحد النوايا الثابتة (contact, location, about, navigation) → رد مباشر من ملف YAML |
| `$rag_searching` | تم تصنيف القصد كأحد نوايا RAG (admission, tuition, colleges, ...) أو `llm` عام → بحث + LLM |
| `$fallback_help` | لم يُعثر على نتيجة مناسبة → عرض قائمة المساعدة مع المواضيع المتاحة |

---

## 3. النوايا (Intents)

### 3.1 جدول النوايا العشرة

| المعرف (Intent Name) | النوع (Type) | الوظيفة | المصدر (Source URL) |
|----------------------|-------------|---------|---------------------|
| `contact` | template | أرقام الهاتف، البريد الإلكتروني، التواصل | `/ar/contact` |
| `location` | template | العنوان، الحرم الجامعي، الخريطة | `/ar/contact` |
| `about` | template | نبذة عن الجامعة، التاريخ، الرؤية | `/ar/about` |
| `navigation` | template | روابط البوابة، المكتبة، البريد، التعليم الإلكتروني | متعددة |
| `colleges` | rag | الكليات والتخصصات والبرامج | `/ar/Colleges-Deanships` |
| `admission` | rag | شروط القبول والتسجيل والتقديم | `/ar/admission` |
| `tuition` | rag | الرسوم الدراسية والتكاليف والأقساط | `/ar/admission` (fees 404) |
| `academic_calendar` | rag | التقويم الأكاديمي ومواعيد الامتحانات | `/ar/academic-calendar` |
| `jobs` | rag | الوظائف الشاغرة والتعيينات | `/ar/jobs` |
| `student_services` | rag | الخدمات الطلابية والسجل والوثائق | `/ar/student-services` |

### 3.2 أنواع النوايا (Intent Types)

**النوع الأول: template** — نوايا ثابتة لا تحتاج بحث
- الرد مكتوب مسبقًا في `intents.yaml` (حقل `response_ar` / `response_en`)
- لا يستدعي LLM ولا RAG
- يناسب الأسئلة التي إجاباتها قصيرة وثابتة (رقم الهاتف، العنوان)

**النوع الثاني: rag** — نوايا تحتاج بحث في قاعدة المعرفة
- يمر بمسار: LLM classify → generate search query → FAISS search → _pick_intent_chunk → ask() → LLM answer + URL
- يناسب الأسئلة التي تحتاج محتوى من صفحات الجامعة (شروط القبول، الكليات، الرسوم)

**النوع الثالث: greeting** — تحيات يكتشفها Regex
- أسرع مسار: يطابق regex مباشرة → رد ترحيب فوري
- لا يمر على LLM أبدًا

**النوع الرابع: llm** — أسئلة عامة/غير واضحة
- يُعالج مثل RAG: يبحث في قاعدة المعرفة ويحاول الإجابة
- إذا لم يجد نتيجة → يظهر قائمة المساعدة

---

## 4. مسارات النوايا (Intent Paths)

### المسار A: تحية (Greeting)

```
إدخال المستخدم → GREETING_PATTERNS (regex) → $greeting → نص ترحيب ثابت
```

- **الكشف:** `router.py` — `_is_greeting()` تفحص النص بـ regex قبل أي استدعاء LLM
- **الاستجابة:** `get_greeting_response(lang)` — نص welcome hardcoded
- **زمن الاستجابة:** < 1ms (بدون شبكة)

### المسار B: قالب ثابت (Template)

```
إدخال المستخدم → LLM classify (Groq) → template:contact → get_template_response("contact") → نص من YAML
```

- **الكشف:** Groq يُصنّف القصد كـ `template:X` (حيث X = contact/location/about/navigation)
- **الاستجابة:** يُقرأ النص من حقل `response_ar`/`response_en` في `intents.yaml`
- **زمن الاستجابة:** < 2 ثانية (استدعاء Groq واحد)
- **ملاحظة:** إذا صنّفها Groq خطأ كـ `rag:admission` → لا تصحيح، تبقى RAG

### المسار C: بحث + LLM (RAG)

```
إدخال المستخدم
    ↓
LLM classify → rag:admission
    ↓
_resolve_search_query()  ← generate_search_query (Groq) ← get_fallback_search_query (من exemplars)
    ↓
search(query, top_k=25)  ← E5 embedding → FAISS IndexFlatIP → 25 chunk
    ↓
_pick_intent_chunk()  ← يبحث عن أول chunk يطابق URL النية (admission → "/admission")
    ↓
ask(query, chunks[:5])  ← Groq (ASK_SYSTEM) يقرأ أفضل 5 chunks ويولّد جوابًا ≤120 توكن
    ↓
صياغة الرد: [answer]<br><br>رابط الصفحة: <a href="{url}">{url}</a>
```

- **الكشف:** Groq يُصنّف القصد كـ `rag:X` أو Embedding Router يُصنّفها كـ `rag:X`
- **الأمان (Safety Net):** إذا صنّفها Groq خطأ كـ `template:admission` (لأن admission لها معنى "استقبال") → `_RAG_INTENTS` يصححها إلى `rag:admission`
- **توليد جواب البحث:** Groq يولّد كلمات بحث عربية (3-7 كلمات) بنظام `SEARCH_SYSTEM`
- **البحث:** E5-small encode بـ `"query: "` prefix → FAISS (inner product) → 25 نتيجة
- **اختيار الأفضل:** `_pick_intent_chunk` لا تعتمد على score FAISS بل على مطابقة URL مع كلمات intent
- **توليد الإجابة:** Groq يستلم 5 chunks كسياق ويولّد جوابًا قصيرًا. إذا لم يجد جوابًا → يقول "لا أعلم"
- **الرابط:** دائمًا يظهر رابط الصفحة بعد الإجابة

### المسار D: عام/غير معروف (LLM → Help)

```
إدخال المستخدم → LLM classify → llm → search(query) → low score → get_help_template()
```

- **متى يحدث:** (1) سؤال خارج نطاق النوايا العشرة، (2) score FAISS < 0.15، (3) Embedding Router لا يجد تطابقًا
- **الاستجابة:** قائمة بالمواضيع التي يمكن للبوت المساعدة فيها

---

## 5. آلية التصنيف (Intent Classification)

### المسار الأساسي: LLM (Groq)

```
classify_intent(query) → Groq (llama-3.1-8b-instant, temp=0.0, max_tokens=70)
    → CLASSIFY_SYSTEM prompt → "template:contact" or "rag:admission" or "greeting" or "llm"
```

### المسار الاحتياطي: Embedding Router

```
عند فشل LLM (لا API key أو خطأ شبكة):
_resolve_intent_embedding(query)
    → E5 encode "query: " prefix
    → dot product مع exemplars المضمنة مسبقًا (intents_embedded.pkl)
    → أعلى تشابه يتجاوز threshold → intent + type
    → إذا لم يتجاوز threshold → action="llm" (يبحث بشكل عام)
```

### شبكة الأمان (Safety Net)

```
في resolve_intent_via_llm():
    if result.action == "template" AND result.intent_name in _RAG_INTENTS:
        result.action = "rag"  # تصحيح تلقائي
```

**لماذا؟** LLM أحيانًا يخلط بين `admission` (بمعنى "استقبال/دخول" كـ template) و`admission` (بمعنى "القبول والتسجيل" كـ RAG). الـ Safety Net يضمن أن أي نية معرفة في `_RAG_INTENTS` تُعامَل كـ RAG دائمًا.

---

## 6. أنواع الردود (Response Types)

| النوع | المكونات | مثال |
|-------|---------|------|
| `greeting` | نص ترحيب ثابت | "مرحباً بك في مساعد جامعة بوليتكنك فلسطين. كيف يمكنني مساعدتك؟" |
| `template` | نص ثابت + روابط مصدر | "رقم هاتف الجامعة: 02-2233050..." + ["https://www.ppu.edu/p/ar/contact"] |
| `rag` | جواب LLM + رابط الصفحة | "[جواب مولد]<br><br>رابط الصفحة: <a href='...'>...</a>" + ["url1", "url2", ...] |
| `help` | قائمة بالمواضيع + رابط عام | "يمكنني مساعدتك في: • أرقام التواصل..." + ["https://www.ppu.edu/p/ar"] |

### هيكل الاستجابة JSON (API)

```json
{
  "text": "تتطلب دراسة الطب معدلاً مرتفعاً في الثانوية العامة...<br><br>رابط الصفحة: <a class=\"link\" href=\"https://www.ppu.edu/p/ar/Colleges-Deanships\" target=\"_blank\">https://www.ppu.edu/p/ar/Colleges-Deanships</a>",
  "sources": ["https://www.ppu.edu/p/ar/Colleges-Deanships", "https://www.ppu.edu/p/ar/admission"],
  "method": "rag"
}
```

---

## 7. سلسلة الاحتياط (Fallback Chain)

```
1. تحية؟ → $greeting (تجاوز كل شيء)
2. LLM متاح؟ → classify_intent() → IntentResult
3. LLM غير متاح؟ → _resolve_intent_embedding() → IntentResult
4. Embedding غير متاح؟ → action="llm" (بحث عام)

--- داخل مسار RAG/LLM ---

5. search() → chunks + best
6. best.score >= 0.15؟ → proceed
7. best.score < 0.15؟ → $fallback_help
8. ask() → answer (قد يكون "لا أعلم")
9. answer موجود؟ → نص + رابط
10. answer = None؟ → رابط فقط
```

---

## 8. حالات الحافة (Edge Cases)

| السيناريو | التصرف |
|-----------|--------|
| المستخدم يكتب "how to apply" → LLM يصنّفها `template:contact` | لا يُصحّح (contact ليس في `_RAG_INTENTS`) → يُظهر رقم الهاتف بدل تعليمات التقديم |
| المستخدم يسأل عن الرسوم الدراسية → الرابط `/ar/fees` يعود 404 | `_INTENT_URL_KEYWORDS` يوجّه إلى `/ar/admission` (الصفحة المتاحة الأقرب) |
| المستخدم يسأل سؤالاً خارج نطاق الجامعة | `classify → llm` → بحث → score < 0.15 → قائمة المساعدة |
| المستخدم يرسل نصًا فارغًا | FastAPI validation (`min_length=1`) يرفض الطلب |
| مفتاح Groq غير صالح | `classify_intent` → None → Embedding Router (إذا متاح) → Help |
| الـ LLM لا يجد جوابًا في الـ chunks | يقول "لا أعلم" + يظهر رابط الصفحة (لا يخترع معلومات) |
| المستخدم يكتب بالإنجليزية | `_detect_lang` → English → ردود إنجليزية إن وجدت |
| تكرار URL في المصادر | `dict.fromkeys()` يزيل التكرارات ويحافظ على الترتيب |

---

## 9. قاعدة المعرفة (Knowledge Base)

- **المصادر:** 29 صفحة من موقع PPU (مأخوذة من 30 URL بذريّة)
- **عدد الـ chunks:** 33 قطعة (كل قطعة ~300 حرف)
- **نظام التضمين:** `intfloat/multilingual-e5-small` (384 بُعدًا)
- **محرك البحث:** FAISS IndexFlatIP (بحث بالضرب الداخلي)
- **تنسيق الـ chunk:**
  ```
  passage: رابط: {url} | صفحة: {title} | {نص المقطع}
  ```
- **حد الصلة (Relevance Threshold):** 0.15 (أي نتيجة تحت هذا الرقم تُعتبر غير ذات صلة)

### القيود المعروفة للمعرفة

- الـ chunks بطول 300 حرف فقط → قد لا تحتوي على تفاصيل كافية لـ LLM ليُجيب إجابة كاملة
- صفحة الرسوم الدراسية غير موجودة → تعتمد على صفحة القبول
- لا توجد صفحات للكليات الفرعية (مثلاً: صفحات خاصة بكلية الهندسة أو كلية الطب)

---

## 10. تفاصيل الـ LLM

| الخاصية | القيمة |
|---------|--------|
| المزود | Groq Cloud |
| الموديل | `llama-3.1-8b-instant` |
| تصنيف النية | temperature=0.0, max_tokens=70 |
| توليد كلمات البحث | temperature=0.1, max_tokens=30 |
| توليد الإجابة | temperature=0.3, max_tokens=120 |
| الـ Prompts | 3 أنظمة منفصلة: CLASSIFY_SYSTEM, SEARCH_SYSTEM, ASK_SYSTEM — كل في `engine/llm.py` |

### مبدأ عمل الـ Prompts

1. **CLASSIFY_SYSTEM:** يُطلب منه إخراج سطر واحد فقط: `template:X | rag:X | llm | greeting`
2. **SEARCH_SYSTEM:** يُطلب منه إخراج 3-7 كلمات بحث عربية
3. **ASK_SYSTEM:** يُطلب منه الإجابة فقط من السياق المُعطى، ≤100 كلمة، يقول "لا أعلم" إن لم يجد

---

## 11. مخطط التدفق الكامل (Full Flow Diagram)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        المستخدم (User)                              │
│                  يكتب سؤالاً في واجهة المحادثة                      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  $classifying                                                       │
│                                                                     │
│  ┌─ هل هو تحية؟ ───────────────────────────────────────── $greeting │
│  │                                                                  │
│  ├─ LLM Groq متاح؟ ──► classify_intent(query)                      │
│  │     │                                                            │
│  │     ├─ template:X ──► (هل X في _RAG_INTENTS؟)                   │
│  │     │     ├─ لا → $template_respond                             │
│  │     │     └─ نعم → صحّح إلى rag → $rag_searching                │
│  │     │                                                            │
│  │     ├─ rag:X ────► $rag_searching                               │
│  │     ├─ greeting ──► $greeting                                   │
│  │     └─ llm ──────► $rag_searching (بحث عام)                     │
│  │                                                                  │
│  └─ Groq غير متاح؟ ──► Embedding Router                           │
│        │                                                            │
│        ├─ وجد نية تطابق threshold → IntentResult(action, name)     │
│        └─ لم يجد → action=llm → $rag_searching                     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  $rag_searching                                                     │
│                                                                     │
│  1. _resolve_search_query()                                         │
│     ├─ generate_search_query (Groq) → كلمات بحث عربية              │
│     └─ فشل؟ → get_fallback_search_query (أول exemplar في YAML)      │
│                                                                     │
│  2. search(query, top_k=25)                                         │
│     ├─ normalize_arabic()                                           │
│     ├─ E5 encode ("query: " prefix)                                 │
│     ├─ FAISS search → 25 chunks with scores                        │
│     └─ لا نتائج؟ → $fallback_help                                  │
│                                                                     │
│  3. _pick_intent_chunk(chunks, intent_name)                         │
│     ├─ يبحث عن أول chunk يطابق URL keywords للنية                  │
│     └─ لا تطابق؟ → أول chunk في القائمة (highest score)            │
│                                                                     │
│  4. best.score >= 0.15؟                                            │
│     ├─ نعم → أكمل                                                   │
│     └─ لا → $fallback_help                                          │
│                                                                     │
│  5. ask(query, chunks[:5]) → Groq يقرأ السياق ويولّد جوابًا        │
│                                                                     │
│  6. صياغة الرد:                                                     │
│     ├─ answer موجود؟ → [answer]<br><br>رابط الصفحة: [link]        │
│     └─ answer = None؟ → رابط الصفحة: [link] فقط                    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  $fallback_help                                                     │
│                                                                     │
│  get_help_template("ar") أو ("en")                                  │
│  → قائمة بالمواضيع التي يمكن للبوت المساعدة فيها                   │
│  → رابط عام لموقع الجامعة                                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  $idle ← يعود البوت لانتظار السؤال التالي                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 12. تبعات خارجية (External Dependencies)

| الخدمة | الاستخدام | بديل عند الفشل |
|--------|-----------|----------------|
| Groq API (llama-3.1-8b-instant) | تصنيف النية، توليد كلمات البحث، توليد الإجابة | Embedding Router + قوالب YAML |
| FAISS index | البحث المتجهي في قاعدة المعرفة | لا بديل — البوت لا يعمل بدون index |
| PPU Website | المصدر الأساسي للمعلومات | لا بديل — المحتوى مأخوذ من الموقع |
| `intfloat/multilingual-e5-small` | تضمين النصوص للبحث | Embedding Router فقط |

---

## 13. مؤشرات الأداء (Performance Notes)

- **متوسط زمن الاستجابة (Template):** ~1-2 ثانية (استدعاء Groq للتصنيف فقط)
- **متوسط زمن الاستجابة (RAG):** ~5-10 ثوانٍ (3 استدعاءات Groq: تصنيف + بحث + إجابة)
- **متوسط زمن الاستجابة (Greeting):** < 1ms (بدون شبكة)
- **حجم قاعدة المعرفة:** 33 chunk (~10 KB)
- **حجم نموذج E5:** 118 MB (يُحمّل عند أول استعلام RAG)
