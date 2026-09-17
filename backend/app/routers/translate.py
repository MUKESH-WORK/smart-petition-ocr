import json
from typing import List, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from cachetools import LRUCache

router = APIRouter(prefix="/translate", tags=["Translation"])


class TranslateRequest(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None
    target_language: str = Field(default="ta", description="Target language code ('ta' for Tamil, 'en' for English)")
    source_language: str = Field(default="auto", description="Source language code")


class TranslateResponse(BaseModel):
    translated_text: Optional[str] = None
    translated_texts: Optional[List[str]] = None
    target_language: str
    source_language: str
    cached: bool = False


# Fast server-side bounded LRU cache (prevents monotonic memory leaks)
TRANSLATION_CACHE = LRUCache(maxsize=5000)


def get_cache_key(text: str, sl: str, tl: str) -> str:
    return f"{sl}_{tl}_{text.strip()}"


def fetch_free_translation(text: str, target_lang: str, source_lang: str = "auto") -> str:
    if not text or not text.strip():
        return text

    clean_text = text.strip()
    tl = target_lang.lower()
    sl = source_lang.lower()

    # User constraint: Apply ONLY for Tamil and English alone, not any other languages
    if tl not in ["ta", "tamil", "en", "english"]:
        return text
    if tl in ["en", "english"]:
        return text

    # Standardize 'tamil' -> 'ta'
    if tl == "tamil":
        tl = "ta"

    cache_key = get_cache_key(clean_text, sl, tl)
    if cache_key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[cache_key]

    # Offline / Zero-Cost Deployment Mode:
    # No external cloud calls are permitted to prevent citizen data leakage in air-gapped Collectorate environment.
    # Return original text if not in preloaded offline dictionary/cache.
    return text


@router.post("", response_model=TranslateResponse)
@router.post("/", response_model=TranslateResponse)
def translate(req: TranslateRequest):
    tl = req.target_language.lower()
    sl = req.source_language.lower()

    # User constraint: Apply ONLY for Tamil and English alone, not any other languages
    if tl not in ["ta", "tamil", "en", "english"]:
        if req.texts is not None:
            return TranslateResponse(translated_texts=req.texts, target_language=tl, source_language=sl)
        return TranslateResponse(translated_text=req.text, target_language=tl, source_language=sl)

    if tl in ["en", "english"]:
        if req.texts is not None:
            return TranslateResponse(translated_texts=req.texts, target_language=tl, source_language=sl)
        return TranslateResponse(translated_text=req.text, target_language=tl, source_language=sl)

    # Standardize 'tamil' to 'ta'
    if tl == "tamil":
        tl = "ta"

    if req.texts is not None:
        translated_list = [fetch_free_translation(t, tl, sl) for t in req.texts]
        return TranslateResponse(translated_texts=translated_list, target_language=tl, source_language=sl)

    if req.text is not None:
        translated_single = fetch_free_translation(req.text, tl, sl)
        return TranslateResponse(translated_text=translated_single, target_language=tl, source_language=sl)

    return TranslateResponse(target_language=tl, source_language=sl)
