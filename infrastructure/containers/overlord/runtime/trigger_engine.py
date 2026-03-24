"""
YAML trigger runner for node-overlord (baked bundle under OVERLORD_BUNDLE_ROOT).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

BUNDLE_ROOT = Path(os.environ.get("OVERLORD_BUNDLE_ROOT", "/app/over_lord"))
CONFIG_ROOT = Path(os.environ.get("OVERLORD_CONFIG_ROOT", "/app/configs/environment"))
SPEC_PATH = Path(os.environ.get("OVERLORD_TRIGGERS_PATH", str(BUNDLE_ROOT / "triggers.yaml")))


def _deep_get(data: Any, dotted: str) -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def load_spec() -> dict[str, Any]:
    if not SPEC_PATH.is_file():
        return {"version": 1, "triggers": [], "startup": {"run_triggers": []}}
    with SPEC_PATH.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        return {"version": 1, "triggers": [], "startup": {"run_triggers": []}}
    raw.setdefault("triggers", [])
    raw.setdefault("startup", {})
    if isinstance(raw["startup"], dict):
        raw["startup"].setdefault("run_triggers", [])
    return raw


def list_triggers() -> list[dict[str, Any]]:
    spec = load_spec()
    out: list[dict[str, Any]] = []
    for t in spec.get("triggers", []):
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        if not tid:
            continue
        out.append(
            {
                "id": tid,
                "description": t.get("description", ""),
                "step_count": len(t.get("steps") or []),
            }
        )
    return out


def _run_copy_file(step: dict[str, Any]) -> dict[str, Any]:
    src = step.get("src")
    dest = step.get("dest")
    if not src or not dest:
        return {"ok": False, "error": "copy_file requires src and dest"}
    src_path = (BUNDLE_ROOT / src).resolve()
    if not str(src_path).startswith(str(BUNDLE_ROOT.resolve())):
        return {"ok": False, "error": "src escapes bundle root"}
    if not src_path.is_file():
        return {"ok": False, "error": f"missing source: {src}"}
    dest_path = (CONFIG_ROOT / dest).resolve()
    if not str(dest_path).startswith(str(CONFIG_ROOT.resolve())):
        return {"ok": False, "error": "dest escapes config root"}
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(src_path.read_bytes())
    return {"ok": True, "wrote": str(dest_path)}


def _run_yaml_to_dotenv(step: dict[str, Any]) -> dict[str, Any]:
    yfile = step.get("yaml_file")
    outfile = step.get("outfile")
    mappings = step.get("mappings") or []
    header = step.get("header") or ""
    if not yfile or not outfile:
        return {"ok": False, "error": "yaml_to_dotenv requires yaml_file and outfile"}
    ypath = (BUNDLE_ROOT / yfile).resolve()
    if not str(ypath).startswith(str(BUNDLE_ROOT.resolve())):
        return {"ok": False, "error": "yaml_file escapes bundle root"}
    if not ypath.is_file():
        return {"ok": False, "error": f"missing yaml: {yfile}"}
    with ypath.open(encoding="utf-8") as f:
        tree = yaml.safe_load(f)
    lines: list[str] = []
    if header:
        lines.append(header.rstrip("\n"))
        if not lines[-1].endswith("\n"):
            lines.append("")
    for m in mappings:
        if not isinstance(m, dict):
            continue
        yk = m.get("yaml")
        ek = m.get("env")
        if not yk or not ek:
            continue
        val = _deep_get(tree, yk)
        if val is None:
            continue
        if isinstance(val, (dict, list)):
            continue
        lines.append(f"{ek}={val}")
    body = "\n".join(lines) + ("\n" if lines else "")
    out_path = (CONFIG_ROOT / outfile).resolve()
    if not str(out_path).startswith(str(CONFIG_ROOT.resolve())):
        return {"ok": False, "error": "outfile escapes config root"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return {"ok": True, "wrote": str(out_path), "lines": len(lines)}


def run_trigger(trigger_id: str) -> dict[str, Any]:
    spec = load_spec()
    trigger: dict[str, Any] | None = None
    for t in spec.get("triggers", []):
        if isinstance(t, dict) and t.get("id") == trigger_id:
            trigger = t
            break
    if not trigger:
        return {"ok": False, "error": f"unknown trigger: {trigger_id}"}
    steps = trigger.get("steps") or []
    results: list[dict[str, Any]] = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            results.append({"step": i, "ok": False, "error": "invalid step"})
            continue
        stype = step.get("type")
        if stype == "copy_file":
            results.append({"step": i, "type": stype, **_run_copy_file(step)})
        elif stype == "yaml_to_dotenv":
            results.append({"step": i, "type": stype, **_run_yaml_to_dotenv(step)})
        else:
            results.append({"step": i, "ok": False, "error": f"unknown step type: {stype}"})
    ok = all(r.get("ok") for r in results if "ok" in r)
    return {"ok": ok, "trigger_id": trigger_id, "steps": results}


def run_startup_triggers() -> list[dict[str, Any]]:
    spec = load_spec()
    su = spec.get("startup") or {}
    ids = su.get("run_triggers") or []
    if not isinstance(ids, list):
        return []
    out: list[dict[str, Any]] = []
    for tid in ids:
        if isinstance(tid, str) and tid.strip():
            out.append(run_trigger(tid.strip()))
    return out
