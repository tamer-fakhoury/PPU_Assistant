import re

TATWEEL = re.compile(r"\u0640+")
DIACRITICS = re.compile(r"[\u064B-\u065F\u0670]")

def normalize_arabic(text: str) -> str:
    text = TATWEEL.sub("", text)
    text = DIACRITICS.sub("", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه")
    text = text.replace("ى", "ا").replace("ؤ", "و").replace("ئ", "ي")
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()
