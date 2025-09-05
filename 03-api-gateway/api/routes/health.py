from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": "lucid_api",
        "time": datetime.utcnow().isoformat() + "Z"
    }
