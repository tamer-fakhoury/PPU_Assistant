import os
import sys
import yaml
import pickle
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sentence_transformers import SentenceTransformer
from engine.normalize import normalize_arabic

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("build_intents")


def main():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "engine", "intents.yaml")
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "intents_embedded.pkl")

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    model = SentenceTransformer("intfloat/multilingual-e5-small")
    intents = data["intents"]
    result = {}

    for name, intent in intents.items():
        all_exemplars = []
        for lang in ("ar", "en"):
            all_exemplars.extend(intent.get("exemplars", {}).get(lang, []))
        if not all_exemplars:
            log.warning("No exemplars for intent '%s'", name)
            result[name] = []
            continue
        normalized = ["query: " + normalize_arabic(ex) for ex in all_exemplars]
        embs = model.encode(normalized, normalize_embeddings=True)
        result[name] = embs
        log.info("Intent '%s': %d exemplars embedded", name, len(all_exemplars))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump(result, f)
    log.info("Saved to %s", out_path)


if __name__ == "__main__":
    main()
