from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.db.supabase import probe_supabase

router = APIRouter(tags=["health"])


@router.get("/health")
def health(check_db: bool = Query(default=False)) -> dict:
    """Liveness probe. Set check_db=true to also probe Supabase connectivity."""
    payload: dict = {
        "status": "ok",
        "service": "ai-rmms-backend",
    }

    if check_db:
        db = probe_supabase()
        payload["database"] = db
        if not db.get("reachable"):
            payload["status"] = "degraded"

    return payload
