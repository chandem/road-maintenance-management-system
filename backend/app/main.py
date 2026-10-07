from fastapi import FastAPI

from app.api.routes.ai import router as ai_router
from app.api.routes.assets import router as assets_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.documents import router as documents_router
from app.api.routes.employees import router as employees_router
from app.api.routes.finance import router as finance_router
from app.api.routes.health import router as health_router
from app.api.routes.machinery import router as machinery_router
from app.api.routes.maintenance_plans import router as maintenance_plans_router
from app.api.routes.road_sections import router as road_sections_router
from app.api.routes.roads import router as roads_router
from app.api.routes.system import router as system_router
from app.api.routes.work_orders import router as work_orders_router

app = FastAPI(title="AI-RMMS API", version="0.1.0")

app.include_router(health_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")
app.include_router(roads_router, prefix="/api/v1")
app.include_router(road_sections_router, prefix="/api/v1")
app.include_router(work_orders_router, prefix="/api/v1")
app.include_router(maintenance_plans_router, prefix="/api/v1")
app.include_router(machinery_router, prefix="/api/v1")
app.include_router(employees_router, prefix="/api/v1")
app.include_router(finance_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "AI-RMMS API", "status": "running", "version": "0.1.0"}
