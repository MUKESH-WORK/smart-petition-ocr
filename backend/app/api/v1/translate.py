# Re-export router from app.routers.translate
from app.routers.translate import (
    router,
    TranslateRequest,
    TranslateResponse,
    fetch_free_translation,
    TRANSLATION_CACHE,
    get_cache_key
)

__all__ = [
    "router",
    "TranslateRequest",
    "TranslateResponse",
    "fetch_free_translation",
    "TRANSLATION_CACHE",
    "get_cache_key"
]
