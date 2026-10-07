from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/system/config")
def system_config() -> dict[str, str]:
    return {
        "service": "ai-rmms-backend",
        "database": "supabase",
        "status": "configured",
    }
