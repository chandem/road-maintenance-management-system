from fastapi import FastAPI

app = FastAPI(
    title="AI-RMMS API",
    version="0.1.0",
    description="AI-Powered Road Maintenance Management System API",
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-rmms"}
