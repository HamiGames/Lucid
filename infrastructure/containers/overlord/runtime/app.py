"""
Lucid overlord — FastAPI for env templates, health, and (node plane) YAML triggers.

OVERLORD_DOMAIN: node | session | database | admin (controls API prefix and env file name).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

_DOMAIN = os.environ.get("OVERLORD_DOMAIN", "node").strip().lower()
if _DOMAIN not in ("node", "session", "database", "admin"):
    raise RuntimeError(f"Invalid OVERLORD_DOMAIN: {_DOMAIN!r}")

_ENV_BASENAME = {
    "node": ".env.node",
    "session": ".env.sessions",
    "database": ".env.database",
    "admin": ".env.admin",
}[_DOMAIN]

_SERVICE = {
    "node": "node-overlord",
    "session": "session-overlord",
    "database": "database-overlord",
    "admin": "admin-overlord",
}[_DOMAIN]

_API_PREFIX = f"/api/v1/{_DOMAIN}/overlord"
_CONFIG_ROOT = Path(os.environ.get("OVERLORD_CONFIG_ROOT", "/app/configs/environment"))
_TEMPLATES = Path(os.environ.get("OVERLORD_TEMPLATES_ROOT", "/app/templates"))
_BUNDLE_ROOT = Path(os.environ.get("OVERLORD_BUNDLE_ROOT", "/app/over_lord"))


@asynccontextmanager
async def _lifespan(_: FastAPI):
    if _DOMAIN in ("node", "admin") and (_BUNDLE_ROOT / "triggers.yaml").is_file():
        try:
            from trigger_engine import run_startup_triggers

            run_startup_triggers()
        except OSError as e:
            logger.warning("overlord startup triggers skipped: %s", e)
    yield


app = FastAPI(
    title=f"Lucid {_SERVICE}",
    version="1.0.0",
    docs_url=f"{_API_PREFIX}/docs",
    redoc_url=None,
    openapi_url=f"{_API_PREFIX}/openapi.json",
    lifespan=_lifespan,
)


def _trigger_auth(request: Request) -> None:
    secret = os.environ.get("OVERLORD_TRIGGER_SECRET", "").strip()
    if not secret:
        return
    token = request.headers.get("X-Overlord-Trigger-Token")
    if token != secret:
        raise HTTPException(status_code=401, detail="invalid trigger token")


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "healthy", "service": _SERVICE, "domain": _DOMAIN}


@app.get(_API_PREFIX, tags=["Overlord"])
def overlord_root() -> dict:
    out = {
        "service": _SERVICE,
        "domain": _DOMAIN,
        "config_dir": str(_CONFIG_ROOT),
        "env_file": str(_CONFIG_ROOT / _ENV_BASENAME),
        "bundle_root": str(_BUNDLE_ROOT),
    }
    if _DOMAIN in ("node", "admin"):
        out["triggers_spec"] = str(_BUNDLE_ROOT / "triggers.yaml")
    return out


@app.get(f"{_API_PREFIX}/templates/{{name}}", tags=["Overlord"])
def get_template(name: str) -> PlainTextResponse:
    """Return a baked-in template by basename (e.g. env.node.template)."""
    safe = Path(name).name
    path = _TEMPLATES / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"template not found: {safe}")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@app.get(f"{_API_PREFIX}/environment", tags=["Overlord"])
def get_rendered_env() -> PlainTextResponse:
    """Return current rendered env file if present on disk (typically volume-mounted)."""
    path = _CONFIG_ROOT / _ENV_BASENAME
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"missing: {path}")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


if _DOMAIN in ("node", "admin"):

    @app.get(f"{_API_PREFIX}/triggers", tags=["Triggers"])
    def list_triggers_ep() -> dict:
        from trigger_engine import SPEC_PATH, list_triggers

        return {
            "triggers": list_triggers(),
            "spec_path": str(SPEC_PATH),
            "bundle_root": str(_BUNDLE_ROOT),
        }

    @app.post(f"{_API_PREFIX}/triggers/{{trigger_id}}/run", tags=["Triggers"])
    def run_trigger_ep(trigger_id: str, request: Request) -> dict:
        _trigger_auth(request)
        from trigger_engine import run_trigger

        result = run_trigger(trigger_id)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result

    @app.get(f"{_API_PREFIX}/bundle/{{relpath:path}}", tags=["Overlord"])
    def get_bundle_file(relpath: str) -> PlainTextResponse:
        """Read-only fetch of a file under the baked over_lord bundle directory."""
        rel = Path(relpath)
        if rel.is_absolute() or ".." in rel.parts:
            raise HTTPException(status_code=400, detail="invalid path")
        full = (_BUNDLE_ROOT / rel).resolve()
        root = _BUNDLE_ROOT.resolve()
        if not str(full).startswith(str(root)) or not full.is_file():
            raise HTTPException(status_code=404, detail="not found")
        return PlainTextResponse(full.read_text(encoding="utf-8"))
