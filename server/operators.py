"""
File: /app/server/operators.py
x-lucid-file-path: /app/server/operators.py
x-lucid-file-type: python

FastAPI operator surface + request handling for Lucid server-plane discovery.

Uses infrastructure/containers/host-config.yml (via common.load_host_config) for
service_name, port, host_ip, and tags; optional mesh validation against
master-endpoint.yml happens at startup when LUCID_SERVER_VALIDATE_MESH=1.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.load_host_config import (
    ServiceEndpoint,
    default_host_config_path,
    endpoints_for_tags,
    load_host_registry,
)

from server.host_context import (
    load_server_bundle,
    validate_master_endpoint_registry,
)

ENV_VALIDATE_MESH = "LUCID_SERVER_VALIDATE_MESH"


class OperatorPayload(BaseModel):
    action: str = Field(..., min_length=1, description="Operator verb, e.g. list_registry, get_endpoint")
    registry_key: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class OperatorAck(BaseModel):
    ok: bool
    action: str
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)


def _serialise_endpoint(ep: ServiceEndpoint) -> Dict[str, Any]:
    return {
        "key": ep.key,
        "service_name": ep.service_name,
        "port": ep.port,
        "host_ip": ep.host_ip,
        "http_path_template": ep.http_path_template,
        "tags": sorted(ep.tags),
        "labels": dict(ep.labels),
    }


def _handle_payload(registry: Dict[str, ServiceEndpoint], body: OperatorPayload) -> OperatorAck:
    action = body.action.strip().lower()
    if action == "list_registry":
        return OperatorAck(
            ok=True,
            action=action,
            data={
                "count": len(registry),
                "services": {k: _serialise_endpoint(v) for k, v in sorted(registry.items())},
            },
        )
    if action == "get_endpoint":
        if not body.registry_key:
            return OperatorAck(ok=False, action=action, errors=["registry_key required"])
        ep = registry.get(body.registry_key)
        if ep is None:
            return OperatorAck(ok=False, action=action, errors=[f"unknown key {body.registry_key!r}"])
        return OperatorAck(ok=True, action=action, data={"endpoint": _serialise_endpoint(ep)})
    if action == "list_by_tags":
        if not body.tags:
            return OperatorAck(ok=False, action=action, errors=["tags required"])
        sub = endpoints_for_tags(registry, *body.tags)
        return OperatorAck(
            ok=True,
            action=action,
            data={"services": {k: _serialise_endpoint(v) for k, v in sorted(sub.items())}},
        )
    return OperatorAck(ok=False, action=action, errors=[f"unknown action {body.action!r}"])


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hc = default_host_config_path()
        raw, registry = load_host_registry(hc)
        app.state.host_config_path = str(hc)
        app.state.host_registry = registry
        app.state.host_raw_meta = {k: v for k, v in raw.items() if k != "services"}

        if os.environ.get(ENV_VALIDATE_MESH, "").strip() in ("1", "true", "yes"):
            bundle = load_server_bundle(host_config_path=hc)
            errs = validate_master_endpoint_registry(bundle)
            if errs:
                raise RuntimeError("master-endpoint / host-config validation failed: " + "; ".join(errs))

        yield

    app = FastAPI(
        title="Lucid server operators",
        version="1.0",
        lifespan=lifespan,
    )
    router = APIRouter()

    @router.get("/health")
    async def health() -> Dict[str, Any]:
        reg = getattr(app.state, "host_registry", {})
        return {
            "status": "ok",
            "host_config": app.state.host_config_path,
            "services_registered": len(reg),
        }

    @router.get("/registry/service/{registry_key}")
    async def get_service(registry_key: str) -> Dict[str, Any]:
        reg: Dict[str, ServiceEndpoint] = app.state.host_registry
        ep = reg.get(registry_key)
        if ep is None:
            raise HTTPException(status_code=404, detail=f"unknown registry key {registry_key!r}")
        return _serialise_endpoint(ep)

    @router.post("/operators/dispatch", response_model=OperatorAck)
    async def dispatch(body: OperatorPayload) -> OperatorAck:
        reg: Dict[str, ServiceEndpoint] = app.state.host_registry
        ack = _handle_payload(reg, body)
        if not ack.ok:
            raise HTTPException(status_code=400, detail=ack.model_dump())
        return ack

    app.mount("/app", router)
    return app


app = create_app()
