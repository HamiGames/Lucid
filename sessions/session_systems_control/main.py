"""
File: /app/sessions/session_systems_control/main.py
x-lucid-file-path: /app/sessions/session_systems_control/main.py
x-lucid-file-type: python

Session systems control plane — aggregates /health across Lucid session stack services.
Registry matches infrastructure/containers/sessions/docker-compose.session-images.yml.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Default registry: service id, DNS name on lucid-session-network, internal port
_DEFAULT_REGISTRY: list[dict[str, Any]] = [
    {"id": "session-pipeline", "host": "session-pipeline", "port": 8083},
    {"id": "session-recorder", "host": "session-recorder", "port": 8090},
    {"id": "session-chunk-processor", "host": "session-chunk-processor", "port": 8010},
    {"id": "session-storage", "host": "session-storage", "port": 8020},
    {"id": "session-api", "host": "session-api", "port": 8113},
    {"id": "session-anchoring", "host": "session-anchoring", "port": 8084},
    {"id": "session-pipeline-manager", "host": "session-pipeline-manager", "port": 7990},
    {"id": "session-management", "host": "session-management", "port": 9090},
]


def _load_registry() -> list[dict[str, Any]]:
    raw = os.environ.get("SESSION_SERVICES_JSON", "").strip()
    if raw:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("SESSION_SERVICES_JSON must be a JSON array")
        return data
    return list(_DEFAULT_REGISTRY)


def _health_path(svc: dict[str, Any]) -> str:
    return str(svc.get("health_path", "/health"))


def _timeout_seconds() -> float:
    return float(os.environ.get("SESSION_CONTROL_PROBE_TIMEOUT", "3.0"))


REGISTRY = _load_registry()

app = FastAPI(
    title="Lucid Session Systems Control",
    version="1.0.0",
    description="Supervision and health aggregation for Lucid session stack containers",
)


class ServiceProbeResult(BaseModel):
    id: str = Field(..., description="Logical service id")
    ok: bool
    host: str
    port: int
    url: str
    status_code: int | None = None
    error: str | None = None


async def _probe_one(client: httpx.AsyncClient, svc: dict[str, Any]) -> ServiceProbeResult:
    host = svc["host"]
    port = int(svc["port"])
    sid = str(svc["id"])
    path = _health_path(svc)
    url = f"http://{host}:{port}{path}"
    try:
        r = await client.get(url)
        ok = 200 <= r.status_code < 300
        return ServiceProbeResult(
            id=sid,
            ok=ok,
            host=host,
            port=port,
            url=url,
            status_code=r.status_code,
            error=None if ok else r.text[:200] if r.text else None,
        )
    except Exception as exc:  # noqa: BLE001 — surface any probe failure
        return ServiceProbeResult(
            id=sid,
            ok=False,
            host=host,
            port=port,
            url=url,
            status_code=None,
            error=str(exc),
        )


async def probe_all() -> list[ServiceProbeResult]:
    timeout = httpx.Timeout(_timeout_seconds())
    async with httpx.AsyncClient(timeout=timeout) as client:
        return list(await asyncio.gather(*[_probe_one(client, s) for s in REGISTRY]))


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness for this container; includes session stack matrix (always HTTP 200 if app runs)."""
    results = await probe_all()
    bad = [r for r in results if not r.ok]
    return {
        "status": "healthy" if not bad else "degraded",
        "service": "session-systems-control",
        "unhealthy_count": len(bad),
        "total": len(results),
        "services": [r.model_dump() for r in results],
    }


@app.get("/v1/registry")
async def get_registry() -> dict[str, Any]:
    """Configured supervision targets (from env or defaults)."""
    return {"services": REGISTRY}


@app.get("/v1/status")
async def status() -> dict[str, Any]:
    """Full async probe of every registered session service."""
    results = await probe_all()
    bad = [r for r in results if not r.ok]
    return {
        "summary": {
            "healthy": len(results) - len(bad),
            "unhealthy": len(bad),
            "total": len(results),
        },
        "services": [r.model_dump() for r in results],
    }


@app.get("/v1/services/{service_id}/health")
async def service_health(service_id: str) -> ServiceProbeResult:
    """Probe a single service by id."""
    match = next((s for s in REGISTRY if s["id"] == service_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Unknown service id: {service_id}")
    timeout = httpx.Timeout(_timeout_seconds())
    async with httpx.AsyncClient(timeout=timeout) as client:
        result = await _probe_one(client, match)
    if not result.ok:
        raise HTTPException(
            status_code=503,
            detail=result.model_dump(),
        )
    return result
