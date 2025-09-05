from fastapi import FastAPI
from app.routes import health

app = FastAPI(title="Lucid API", version="0.1.0")

app.include_router(health.router, prefix="/health", tags=["Health"])

@app.get("/")
async def root():
    return {"status": "ok", "service": "lucid_api"}
