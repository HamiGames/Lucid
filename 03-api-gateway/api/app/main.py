from fastapi import FastAPI
from datetime import datetime, UTC
from .routes import health

app = FastAPI(title="Lucid RDP API Gateway")

# Register routers
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "api-gateway",
        "time": datetime.now(UTC).isoformat(),
        "block_onion": "",
        "block_rpc_url": "",
    }
