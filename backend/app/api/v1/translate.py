# Re-export router from app.routers.translate
from app.routers.translate import (
    router,
    TranslateRequest,
    TranslateResponse,
    fetch_free_translation_async,
    batch_translate_async,
    TRANSLATION_CACHE,
    get_cache_key
)

fetch_free_translation = fetch_free_translation_async

__all__ = [
    "router",
    "TranslateRequest",
    "TranslateResponse",
    "fetch_free_translation",
    "fetch_free_translation_async",
    "batch_translate_async",
    "TRANSLATION_CACHE",
    "get_cache_key"
]


