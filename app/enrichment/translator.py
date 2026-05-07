"""תרגום והסבר בעברית - דרך OpenAI."""
import json

from app.core.config import settings
from app.core.logging import get_logger
from app.enrichment.glossary import add_glossary_to_items

log = get_logger(__name__)


def _openai_client():
    if not settings.use_openai:
        return None
    try:
        from openai import OpenAI

        return OpenAI(api_key=settings.openai_api_key)
    except ImportError:
        log.warning("openai_not_installed")
        return None


def translate_items(items: list[dict], batch_size: int = 20) -> list[dict]:
    """מוסיף לכל פריט: hebrew_translation, hebrew_explanation."""
    client = _openai_client()
    if not client or not items:
        return add_glossary_to_items(items)

    result = list(items)

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        texts = [(it.get("text", "") or "")[:400] for it in batch]
        prompt = (
            "תרגם לעברית וספק הסבר קצר (משפט אחד) לכל כותרת.\n"
            'החזר JSON בלבד - מערך: [{"translation":"...","explanation":"..."}, ...]\n'
            "ההסבר: מה הרלוונטיות למשקיע בשוק האמריקאי.\n\nכותרות:\n"
            + "\n".join(f"{j+1}. {t}" for j, t in enumerate(texts) if t)
        )
        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "אתה מתרגם פיננסי. החזר רק JSON עם translation ו-explanation."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2500,
            )
            raw = resp.choices[0].message.content or ""
            arr = _extract_json_array(raw)
            if not arr:
                continue
            for j, item in enumerate(arr):
                idx = i + j
                if idx < len(result) and isinstance(item, dict):
                    result[idx] = {
                        **result[idx],
                        "hebrew_translation": str(item.get("translation", ""))[:500],
                        "hebrew_explanation": str(item.get("explanation", ""))[:300],
                    }
        except Exception as e:
            log.warning("translate_batch_failed", error=str(e))
            break

    return add_glossary_to_items(result)


def _extract_json_array(raw: str) -> list | None:
    start = raw.find("[")
    if start < 0:
        return None
    depth, end = 1, start + 1
    while end < len(raw) and depth > 0:
        c = raw[end]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        end += 1
    try:
        return json.loads(raw[start:end])
    except Exception:
        return None
