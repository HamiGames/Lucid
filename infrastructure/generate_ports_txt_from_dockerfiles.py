# Full path: infrastructure/generate_ports_txt_from_dockerfiles.py
#
# Scans infrastructure/docker/ and infrastructure/containers/ for Dockerfiles,
# extracts EXPOSE ports and infers service_name (Docker DNS / host-config style).
#
# Run from repo root (Lucid):
#   python infrastructure/generate_ports_txt_from_dockerfiles.py
#   python infrastructure/generate_ports_txt_from_dockerfiles.py --generate-tags
#   python infrastructure/generate_ports_txt_from_dockerfiles.py -o infrastructure/generated/ports-from-dockerfiles.yaml
#
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CONTAINERS = ROOT / "infrastructure" / "containers"
DOCKER_INFRA = ROOT / "infrastructure" / "docker"

# Import containers-only service_key fallback when path is under infrastructure/containers/
if str(CONTAINERS) not in sys.path:
    sys.path.insert(0, str(CONTAINERS))

try:
    import _sync_dockerfile_lucid_env as lucid_sync
except ImportError:
    lucid_sync = None  # type: ignore[misc, assignment]


DOCKERFILE_NAME_RE = re.compile(r"(?i)^dockerfile(?:\.|$)|^dockerfile\s")


@dataclass
class DockerfileScan:
    repo_path: str
    service_name: str
    service_name_source: str
    ports: list[int] = field(default_factory=list)
    expose_raw_tokens: list[str] = field(default_factory=list)
    suggested_tags: list[str] = field(default_factory=list)


def _repo_rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _is_dockerfile_path(p: Path) -> bool:
    n = p.name
    if not p.is_file():
        return False
    if DOCKERFILE_NAME_RE.match(n):
        return True
    nl = n.lower()
    return nl.startswith("dockerfile.") or nl == "dockerfile"


def _skip_repo_path(repo_path: str) -> bool:
    if not repo_path.startswith("infrastructure/containers/"):
        return False
    rel = repo_path[len("infrastructure/containers/") :]
    if lucid_sync and rel in lucid_sync.SKIP_REL_PATHS:
        return True
    return rel.startswith(".devcontainer/")


def iter_dockerfiles(*roots: Path) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            try:
                rp = p.resolve()
            except OSError:
                continue
            if rp in seen or not _is_dockerfile_path(p):
                continue
            if _skip_repo_path(_repo_rel(p)):
                continue
            seen.add(rp)
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def extract_expose_ports(text: str) -> tuple[list[int], list[str]]:
    """Return (numeric ports, raw non-numeric tokens e.g. ${PORT})."""
    logical = []
    lines = text.splitlines()
    buf: list[str] = []
    for line in lines:
        buf.append(line)
        stripped = line.rstrip()
        if stripped.endswith("\\") and not stripped.endswith("\\\\"):
            continue
        merged = re.sub(r"\\\s*\n\s*", " ", "\n".join(buf))
        buf = []
        logical.append(merged)

    ports: list[int] = []
    raw_tokens: list[str] = []
    seen: set[int] = set()
    for line in logical:
        s = line.strip()
        if not s.upper().startswith("EXPOSE"):
            continue
        rest = s[6:].strip()
        if not rest or rest.startswith("#"):
            continue
        for tok in rest.split():
            t = tok.strip().strip('"').strip("'")
            if not t or t.startswith("#"):
                continue
            t = re.sub(r"/(tcp|udp)$", "", t, flags=re.I)
            if re.fullmatch(r"\d+", t):
                v = int(t)
                if v not in seen:
                    seen.add(v)
                    ports.append(v)
            else:
                raw_tokens.append(tok.strip())
    return ports, raw_tokens


def _snake_to_kebab(s: str) -> str:
    return s.replace("_", "-")


def _norm_tag_token(s: str) -> str:
    return re.sub(r"\s+", "-", s.strip().lower()).strip("-")


def suggest_tags(service_name: str, repo_path: str) -> list[str]:
    """2-3 tag strings for ports.txt-style discovery (kebab, snake, aliases)."""
    sn = _norm_tag_token(service_name)
    if not sn:
        base = Path(repo_path).name
        if base.lower().startswith("dockerfile."):
            sn = _norm_tag_token(base.split(".", 1)[1].replace("_", "-"))
    if not sn:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def push_iter(items: Iterable[str]) -> None:
        for t in items:
            t = _norm_tag_token(t)
            if t and t not in seen:
                seen.add(t)
                candidates.append(t)

    push_iter([sn])
    snake = sn.replace("-", "_")
    if snake != sn:
        push_iter([snake])
    if sn.startswith("lucid-"):
        push_iter([sn[6:]])

    fn = Path(repo_path).name
    if fn.lower().startswith("dockerfile."):
        suf = _norm_tag_token(fn.split(".", 1)[1].replace("_", "-"))
        if suf and suf != sn:
            push_iter([suf])

    parts = [p for p in sn.split("-") if p]
    if len(parts) >= 2:
        tail2 = "-".join(parts[-2:])
        if tail2 != sn:
            push_iter([tail2])
        push_iter([parts[-1]])

    if len(candidates) < 2 and not sn.startswith("lucid-"):
        push_iter([f"lucid-{sn}"])

    if len(candidates) < 2 and len(parts) >= 1:
        push_iter([parts[-1]])

    return candidates[:3]


def _service_name_from_filename(p: Path) -> tuple[str, str]:
    name = p.name
    lower = name.lower()
    if lower == "dockerfile":
        parent = p.parent.name
        return parent, "filename:parent_dir"
    if lower.startswith("dockerfile."):
        tail = name[len("Dockerfile.") :] if name.startswith("Dockerfile.") else name[len("dockerfile.") :]
        tail = tail.strip()
        return tail.replace("_", "-"), "filename:dockerfile.suffix"
    if lower.startswith("dockerfile "):
        tail = name.split(None, 1)[1].strip()
        return tail.replace("_", "-"), "filename:dockerfile space"
    return name, "filename:basename"


def _ports_txt_service_name(repo_path: str, p: Path) -> tuple[str, str] | None:
    """If this Dockerfile maps to a ports.txt service id, return canonical service_name."""
    if not repo_path.startswith("infrastructure/containers/") or not lucid_sync:
        return None
    rel = repo_path[len("infrastructure/containers/") :]
    key = lucid_sync.service_key_from_dockerfile(rel, p.name)
    if not key:
        return None
    try:
        ports_svc = lucid_sync.load_ports_services()
    except Exception:
        return None
    meta = ports_svc.get(key) or {}
    sn = meta.get("service_name")
    if isinstance(sn, str) and sn.strip():
        return sn.strip(), f"ports.txt[{key}].service_name"
    return None


def extract_service_name(p: Path, text: str, repo_path: str) -> tuple[str, str]:
    """Return (service_name, source_label)."""
    flat = re.sub(r"\\\s*\n\s*", " ", text)

    m = re.search(
        r'com\.lucid\.hostconfig\.service_name\s*=\s*"([^"]+)"',
        flat,
        re.I,
    )
    if m:
        return m.group(1).strip(), "LABEL com.lucid.hostconfig.service_name"

    m = re.search(
        r"com\.lucid\.hostconfig\.service_name\s*=\s*'([^']+)'",
        flat,
        re.I,
    )
    if m:
        return m.group(1).strip(), "LABEL com.lucid.hostconfig.service_name"

    m = re.search(
        r"LUCID_HOST_CONFIG_SERVICE_NAME\s*=\s*([^\s\\#]+|\"[^\"]+\"|'[^']+')",
        flat,
    )
    if m:
        raw = m.group(1).strip().strip('"').strip("'")
        if raw and not raw.startswith("$"):
            return raw, "ENV LUCID_HOST_CONFIG_SERVICE_NAME"

    pt = _ports_txt_service_name(repo_path, p)
    if pt:
        return pt

    for var in ("LUCID_HOST_SERVICE_NAME", "LUCID_SERVICE_NAME", "OVERLORD_SERVICE_NAME"):
        pat = rf"{var}\s*=\s*([^\s\\#]+|\"[^\"]+\"|'[^']+')"
        mm = re.search(pat, flat)
        if mm:
            raw = mm.group(1).strip().strip('"').strip("'")
            if raw and not raw.startswith("$"):
                return raw, f"ENV {var}"

    # Comment hints: "service_name: foo" or "host-config service_name: foo"
    for pat in (
        r"#\s*service_name:\s*([a-zA-Z0-9][a-zA-Z0-9_.-]*)",
        r"#\s*host-config\s+service_name:\s*([a-zA-Z0-9][a-zA-Z0-9_.-]*)",
    ):
        mm = re.search(pat, text)
        if mm:
            return mm.group(1).strip().replace("_", "-"), "comment:service_name"

    m = re.search(
        r'SERVICE_NAME\s*=\s*"([^"]+)"',
        flat,
    )
    if m:
        val = m.group(1).strip()
        if val.lower().startswith("lucid-") or "lucid" in val.lower():
            return val, "ENV SERVICE_NAME"

    m = re.search(r"SERVICE_NAME\s*=\s*'([^']+)'", flat)
    if m:
        val = m.group(1).strip()
        if val.lower().startswith("lucid-") or "service-mesh" in val.lower():
            return val, "ENV SERVICE_NAME"

    m = re.search(r'SERVICE_NAME\s*=\s*([a-zA-Z][a-zA-Z0-9_.-]+)', flat)
    if m and m.group(1) not in ("consul", "api"):
        val = m.group(1).strip()
        if "lucid" in val.lower() or "mesh" in val.lower():
            return val, "ENV SERVICE_NAME"

    # infrastructure/containers: stable id -> kebab slug (no ports.txt row)
    if repo_path.startswith("infrastructure/containers/") and lucid_sync:
        rel = repo_path[len("infrastructure/containers/") :]
        key = lucid_sync.service_key_from_dockerfile(rel, p.name)
        if key:
            return _snake_to_kebab(key), f"service_key_from_dockerfile:{key}"

    fn_sn, src = _service_name_from_filename(p)
    return fn_sn, src


def scan_dockerfile(p: Path) -> DockerfileScan:
    repo_path = _repo_rel(p)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        return DockerfileScan(
            repo_path=repo_path,
            service_name="",
            service_name_source=f"read_error:{e}",
        )
    ports, raw = extract_expose_ports(text)
    sn, src = extract_service_name(p, text, repo_path)
    scan = DockerfileScan(
        repo_path=repo_path,
        service_name=sn,
        service_name_source=src,
        ports=ports,
        expose_raw_tokens=raw,
        suggested_tags=suggest_tags(sn, repo_path),
    )
    return scan


def _yaml_scalar(s: str) -> str:
    if not s:
        return '""'
    if re.search(r'[:#\[\]{},"\'\\]', s) or s.strip() != s:
        esc = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{esc}"'
    return s


def render_yaml(scans: list[DockerfileScan], *, include_tags: bool) -> str:
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# =============================================================================",
        "# Lucid - Dockerfile-derived registry (generator output)",
        f"# Generated: {iso}",
        "# Generator: infrastructure/generate_ports_txt_from_dockerfiles.py",
        "#",
        "# Per Dockerfile: dockerfile_path, service_name (inferred), ports (EXPOSE).",
        "# Optional: tags = 2-3 suggested discovery aliases (see --generate-tags).",
        "# Not a drop-in replacement for repo root ports.txt (no image/http_path unless merged).",
        "# Merge manually; run _gen_host_config.py only after enriching canonical ports.txt.",
        "# =============================================================================",
        "",
        "dockerfile_services:",
    ]
    for s in scans:
        lines.append(f"  - dockerfile_path: {_yaml_scalar(s.repo_path)}")
        lines.append(f"    service_name: {_yaml_scalar(s.service_name)}")
        lines.append(f"    service_name_source: {_yaml_scalar(s.service_name_source)}")
        if s.ports:
            lines.append(f"    ports: [{', '.join(str(p) for p in s.ports)}]")
        else:
            lines.append("    ports: []")
        if s.expose_raw_tokens:
            lines.append(
                "    expose_non_numeric: "
                + repr(s.expose_raw_tokens)
            )
        if include_tags and s.suggested_tags:
            lines.append(
                "    tags: ["
                + ", ".join(_yaml_scalar(t) for t in s.suggested_tags)
                + "]"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Scan Lucid Dockerfiles under infrastructure/docker and infrastructure/containers; "
        "emit YAML with path, service_name, and EXPOSE ports.",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "infrastructure" / "generated" / "ports-from-dockerfiles.yaml",
        help="Output YAML path (default: infrastructure/generated/ports-from-dockerfiles.yaml)",
    )
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="Print YAML to stdout instead of writing a file",
    )
    ap.add_argument(
        "--generate-tags",
        action="store_true",
        help="Emit 2-3 suggested tags per service (kebab, snake_case, lucid- strip, Dockerfile suffix)",
    )
    args = ap.parse_args()

    paths = iter_dockerfiles(DOCKER_INFRA, CONTAINERS)
    scans = [scan_dockerfile(p) for p in paths]
    body = render_yaml(scans, include_tags=args.generate_tags)

    if args.stdout:
        sys.stdout.write(body)
        return 0

    out: Path = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)} ({len(scans)} Dockerfiles)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
