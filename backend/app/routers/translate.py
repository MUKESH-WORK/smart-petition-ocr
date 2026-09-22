import json
import logging
import asyncio
from typing import List, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from cachetools import LRUCache
from core.llm_client import llm_client

logger = logging.getLogger(__name__)

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


import json
import logging
import asyncio
from typing import List, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from cachetools import LRUCache
from core.llm_client import llm_client

logger = logging.getLogger(__name__)

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


# Fast server-side bounded dynamic LRU cache
TRANSLATION_CACHE = LRUCache(maxsize=20000)


def get_cache_key(text: str, sl: str, tl: str) -> str:
    return f"{sl}_{tl}_{text.strip()}"


async def fetch_free_translation_async(text: str, target_lang: str, source_lang: str = "auto") -> str:
    if not text or not str(text).strip():
        return text

    clean_text = str(text).strip()
    tl = target_lang.lower()
    sl = source_lang.lower()

    if tl in ["tamil", "tam"]:
        tl = "ta"
    elif tl in ["english", "eng"]:
        tl = "en"

    if sl in ["tamil", "tam"]:
        sl = "ta"
    elif sl in ["english", "eng"]:
        sl = "en"

    cache_key = get_cache_key(clean_text, sl, tl)
    if cache_key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[cache_key]

    # Real Dynamic LLM Bilingual Translation for Entire Content
    try:
        lang_name = "Tamil" if tl == "ta" else "English"
        sys_prompt = (
            f"You are a professional Tamil Nadu Government bilingual translator. "
            f"Translate the given text accurately, naturally, and contextually into {lang_name}. "
            f"Preserve formatting, numbers, proper nouns, and administrative clarity. "
            f"Output ONLY the translated text without commentary, explanations, or quotes."
        )
        user_prompt = f"Text to translate:\n{clean_text}"
        translated = await llm_client.achat(user_prompt, system_prompt=sys_prompt, temperature=0.1, max_tokens=2000)
        if translated and translated.strip():
            result = translated.strip().strip('"').strip("'")
            TRANSLATION_CACHE[cache_key] = result
            return result
    except Exception as e:
        logger.warning(f"Dynamic translation exception: {e}")

    return clean_text


async def batch_translate_async(texts: List[str], target_lang: str, source_lang: str = "auto") -> List[str]:
    if not texts:
        return []

    tl = target_lang.lower()
    sl = source_lang.lower()
    if tl in ["tamil", "tam"]:
        tl = "ta"
    elif tl in ["english", "eng"]:
        tl = "en"

    results: List[Optional[str]] = [None] * len(texts)
    uncached_indices = []
    uncached_items = []

    for idx, t in enumerate(texts):
        if not t or not str(t).strip():
            results[idx] = t
            continue
        clean = str(t).strip()
        cache_key = get_cache_key(clean, sl, tl)
        if cache_key in TRANSLATION_CACHE:
            results[idx] = TRANSLATION_CACHE[cache_key]
        else:
            uncached_indices.append(idx)
            uncached_items.append(clean)

    if not uncached_items:
        return [r if r is not None else "" for r in results]

    # Translate uncached items dynamically concurrently
    tasks = [fetch_free_translation_async(item, tl, sl) for item in uncached_items]
    translated_batch = await asyncio.gather(*tasks, return_exceptions=True)

    for i, orig_idx in enumerate(uncached_indices):
        item_res = translated_batch[i]
        if isinstance(item_res, Exception):
            results[orig_idx] = uncached_items[i]
        else:
            results[orig_idx] = item_res

    return [r if r is not None else "" for r in results]


@router.post("", response_model=TranslateResponse)
@router.post("/", response_model=TranslateResponse)
async def translate(req: TranslateRequest):
    tl = req.target_language.lower()
    sl = req.source_language.lower()

    if tl in ["tamil", "tam"]:
        tl = "ta"
    elif tl in ["english", "eng"]:
        tl = "en"

    if req.texts is not None:
        translated_list = await batch_translate_async(req.texts, tl, sl)
        return TranslateResponse(translated_texts=translated_list, target_language=tl, source_language=sl)

    if req.text is not None:
        translated_single = await fetch_free_translation_async(req.text, tl, sl)
        return TranslateResponse(translated_text=translated_single, target_language=tl, source_language=sl)

    return TranslateResponse(target_language=tl, source_language=sl)


