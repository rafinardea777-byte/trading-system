"""בדיקות מילון תרגום."""
from app.enrichment.glossary import add_glossary_to_items, quick_translate


def test_translates_inflation():
    out = quick_translate("Inflation cools to 3%")
    assert "אינפלציה" in out


def test_translates_rate_cut():
    out = quick_translate("Fed expected to do rate cuts")
    assert "ריבית" in out


def test_empty_for_unknown():
    assert quick_translate("Cat sat on mat") == ""


def test_add_glossary_skips_existing_translation():
    items = [
        {"text": "inflation rises", "hebrew_translation": "כבר תורגם"},
        {"text": "Fed cuts rates"},
    ]
    out = add_glossary_to_items(items)
    assert out[0].get("hebrew_explanation") in (None, "")  # לא מדרסים תרגום קיים
    assert out[1].get("hebrew_explanation")
