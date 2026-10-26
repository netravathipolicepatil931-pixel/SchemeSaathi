import json
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/translations", tags=["Localization & Translations"])

TRANSLATIONS_FILE = Path(__file__).resolve().parent.parent / "data" / "translations_seed.json"

def _load_translations() -> dict:
    if TRANSLATIONS_FILE.exists():
        with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@router.get("")
def get_translations(
    language: Annotated[str, Query(description="Target language code: en, kn, hi")] = "en",
):
    """
    Get UI localization strings for specified language (or fallback to English).
    """
    all_translations = _load_translations()
    lang = language if language in all_translations else "en"
    return {
        "language": lang,
        "strings": all_translations.get(lang, all_translations.get("en", {})),
    }

@router.get("/languages")
def get_supported_languages():
    """
    Returns list of supported language codes and their native display names.
    """
    return [
        {"code": "en", "name": "English", "native": "English"},
        {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ"},
        {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
    ]
