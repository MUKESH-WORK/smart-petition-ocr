import json
import urllib.parse
import urllib.request
from typing import List, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

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


# Fast server-side in-memory cache
TRANSLATION_CACHE: Dict[str, str] = {}


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

    # Primary Method: Google Free GTX Web API (Zero Key, No Billing Required)
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t&q={urllib.parse.quote(clean_text)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                # Google GTX returns [[['translated_sentence', 'original_sentence', ...], ...]]
                translated_parts = [part[0] for part in data[0] if part and part[0]]
                result = "".join(translated_parts)
                if result:
                    TRANSLATION_CACHE[cache_key] = result
                    return result
    except Exception:
        pass

    # Secondary Method: MyMemory Free Translation API Fallback
    try:
        pair = f"{'en' if sl == 'auto' else sl}|{tl}"
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean_text[:450])}&langpair={pair}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                result = data.get("responseData", {}).get("translatedText")
                if result and "MYMEMORY WARNING" not in result.upper():
                    TRANSLATION_CACHE[cache_key] = result
                    return result
    except Exception:
        pass

    # Fallback to original text if offline or unreachable
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
