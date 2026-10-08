from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/system/config")
def system_config() -> dict:
    """Non-secret configuration summary for ops and deployment checks."""
    settings = get_settings()

    return {
        "service": "ai-rmms-backend",
        "database": "supabase",
        "supabase": {
            "configured": settings.has_supabase,
            "region": settings.supabase_region,
            "project_ref": settings.supabase_project_ref or "not-set",
            "service_role_configured": settings.has_service_role,
            "url_host": _url_host(settings.supabase_url) if settings.has_supabase else None,
        },
        "ai": {
            "gemini_configured": settings.has_gemini,
            "gemini_model": settings.gemini_model,
            "embedding_model": settings.gemini_embedding_model,
        },
        "status": "configured" if settings.has_supabase else "missing-supabase-env",
    }


def _url_host(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"
