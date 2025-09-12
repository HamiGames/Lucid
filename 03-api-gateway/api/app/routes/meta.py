from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from app.schemas import HealthResponse
from app.config import Settings
from app.deps import get_config

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_config)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.SERVICE_NAME,
        time=datetime.now(timezone.utc).isoformat(),
        version=settings.VERSION,
    )
