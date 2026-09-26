from app.api.routes.documents import router as documents_router
from app.api.routes.auth import router as auth_router
from app.api.routes.status import router as status_router

__all__ = ["documents_router", "auth_router", "status_router"]
