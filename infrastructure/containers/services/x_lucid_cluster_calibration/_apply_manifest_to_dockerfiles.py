"""Apply allocation_manifest.json calibration COPY lines to Dockerfiles under infrastructure/containers.

Derives builder/runtime paths from the existing container-runtime-layout.yml COPY when present.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONTAINERS = ROOT / "infrastructure" / "containers"
MANIFEST = (
    CONTAINERS
    / "services"
    / "x_lucid_cluster_calibration"
    / "allocation_manifest.json"
)


def normalize_dockerfile_path(raw: str) -> str:
    p = raw.replace("\\", "/")
    if p.startswith("infrastructure/containers/"):
        return p
    return "infrastructure/containers/" + p.lstrip("/")


def under_containers(path: Path) -> bool:
    try:
        path.resolve().relative_to(CONTAINERS.resolve())
        return True
    except ValueError:
        return False


def load_manifest_entries() -> dict[str, dict]:
    with MANIFEST.open(encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, dict] = {}
    for cluster, entries in (data.get("dockerfiles") or {}).items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            df = e.get("dockerfile") or ""
            if not df or df.endswith(".md"):
                continue
            norm = normalize_dockerfile_path(df)
            full = (ROOT / norm).resolve()
            if not full.is_file() or not under_containers(full):
                continue
            key = str(full)
            if key not in out:
                out[key] = {"cluster": cluster, **e}
    return out


LABEL_SERVICE_RE = re.compile(r'com\.lucid\.service="([^"]*)"')
LABEL_CLUSTER_RE = re.compile(r'com\.lucid\.cluster="([^"]*)"')


def is_multistage_build(text: str) -> bool:
    from_count = sum(
        1 for ln in text.splitlines() if re.match(r"^\s*FROM\s+", ln, re.IGNORECASE)
    )
    return from_count >= 2 and re.search(r"WORKDIR\s+/build", text) is not None


def resolve_calibration_repo(meta: dict) -> str:
    repo = (meta.get("calibration_repo_path") or "").strip()
    if repo:
        return repo
    sc = (meta.get("suggested_copy_line") or "").strip()
    m = re.match(
        r"^COPY\s+(infrastructure/containers/services/x_lucid_cluster_calibration/\S+)\s+(\S+)\s*$",
        sc,
    )
    return m.group(1) if m else ""


def standard_calibration_lines(repo: str, name: str) -> tuple[str, str, str]:
    builder = f"COPY {repo} ./service_configs/x_lucid_cluster_calibration/{name}"
    runtime = (
        "COPY --from=builder --chown=65532:65532 "
        f"/build/service_configs/x_lucid_cluster_calibration/{name} "
        f"/app/service_configs/x_lucid_cluster_calibration/{name}"
    )
    return builder, runtime, name


def calibration_lines(meta: dict, text: str) -> tuple[str, str, str] | None:
    repo = resolve_calibration_repo(meta)
    if not repo:
        return None
    name = Path(repo).name

    m = re.search(
        r"COPY\s+infrastructure/containers/services/container-runtime-layout\.yml\s+(\S+)",
        text,
    )
    if m:
        layout_dest = m.group(1)
        dir_part = layout_dest.rsplit("/", 1)[0]
        if dir_part.startswith("/build/"):
            builder = f"COPY {repo} {dir_part}/x_lucid_cluster_calibration/{name}"
            runtime = (
                "COPY --from=builder --chown=65532:65532 "
                f"{dir_part}/x_lucid_cluster_calibration/{name} "
                f"/app{dir_part[len('/build') : ]}/x_lucid_cluster_calibration/{name}"
            )
        elif dir_part.startswith("./"):
            builder = f"COPY {repo} {dir_part}/x_lucid_cluster_calibration/{name}"
            rel = dir_part[2:]
            runtime = (
                "COPY --from=builder --chown=65532:65532 "
                f"/build/{rel}/x_lucid_cluster_calibration/{name} "
                f"/app/{rel}/x_lucid_cluster_calibration/{name}"
            )
        else:
            return None
        return builder, runtime, name

    sc = (meta.get("suggested_copy_line") or "").strip()
    m2 = re.match(
        r"^COPY\s+(\S+)\s+(/app/service_configs/x_lucid_cluster_calibration/\S+)\s*$",
        sc,
    )
    if m2:
        return standard_calibration_lines(repo, name)

    # Bulk services tree or other Dockerfiles: use standard paths under /build/service_configs
    return standard_calibration_lines(repo, name)


def copies_whole_build_configs_to_app(text: str) -> bool:
    """True when runtime copies entire /build/configs/ into /app/configs (single COPY)."""
    return bool(
        re.search(
            r"COPY\s+--from=\S+\s+[^\n]*/build/configs/\s+(?:/app/configs/|\./configs/)",
            text,
        )
    )


def insert_after_line(text: str, needle_line: str, block: str) -> str | None:
    if needle_line not in text:
        return None
    idx = text.index(needle_line)
    end = idx + len(needle_line)
    if end < len(text) and text[end] == "\n":
        end += 1
    insert = block if block.endswith("\n") else block + "\n"
    return text[:end] + insert + text[end:]


def _insert_runtime_after_known_anchor(text: str, runtime: str) -> str:
    rt_line = find_runtime_layout_line(text)
    if rt_line:
        text2 = insert_after_line(text, rt_line, runtime + "\n")
        return text2 if text2 else text
    for anchor in (
        "COPY --from=builder --chown=65532:65532 "
        "/build/host/host-config.yml /app/host/host-config.yml",
        "COPY --from=builder --chown=65532:65532 "
        "/build/configs/host-config.yml /app/configs/host-config.yml",
        "COPY --from=builder --chown=65532:65532 /build/configs/.env.master /app/configs/.env.master",
    ):
        if anchor in text:
            text2 = insert_after_line(text, anchor, runtime + "\n")
            if text2:
                return text2
    return text


def find_runtime_layout_line(text: str) -> str | None:
    for line in text.splitlines():
        if (
            "COPY --from=builder" in line
            and "container-runtime-layout.yml" in line
            and line.strip().startswith("COPY")
        ):
            return line
    return None


def apply_multistage(text: str, builder: str, runtime: str, name: str) -> str:
    if f"x_lucid_cluster_calibration/{name}" in text:
        return text

    skip_runtime = copies_whole_build_configs_to_app(text)

    anchor_bulk = "COPY infrastructure/containers/services/"
    if (
        anchor_bulk in text
        and "container-runtime-layout.yml" not in text
    ):
        i = text.index(anchor_bulk)
        line_end = text.index("\n", i)
        line = text[i:line_end]
        if "configs/services" in line:
            text2 = insert_after_line(text, line, builder + "\n")
            if text2:
                text = text2
            if not skip_runtime:
                text = _insert_runtime_after_known_anchor(text, runtime)
            return text

    anchor = "COPY infrastructure/containers/services/container-runtime-layout.yml"
    if anchor in text:
        i = text.index(anchor)
        line = text[i : text.index("\n", i)]
        text2 = insert_after_line(text, line, builder + "\n")
        if text2:
            text = text2
    else:
        anchor2 = "COPY infrastructure/containers/host-config.yml ./service_configs/host-config.yml"
        if anchor2 in text:
            text2 = insert_after_line(text, anchor2, builder + "\n")
            if text2:
                text = text2
        elif (
            m_hc := re.search(
                r"^COPY\s+infrastructure/containers/host-config\.yml\s+\./configs/host-config\.yml\s*$",
                text,
                re.MULTILINE,
            )
        ):
            line = m_hc.group(0)
            text2 = insert_after_line(text, line, builder + "\n")
            if text2:
                text = text2
        else:
            m = re.search(
                r"(RUN mkdir -p \./host \./service_configs[^\n]*\n)",
                text,
            )
            if m:
                pos = m.end()
                insert = builder + ("\n" if not builder.endswith("\n") else "")
                text = text[:pos] + insert + text[pos:]
            else:
                env_master = "COPY master-env-config.txt /build/configs/.env.master"
                if env_master in text:
                    text2 = insert_after_line(text, env_master, builder + "\n")
                    if text2:
                        text = text2

    if not skip_runtime:
        text = _insert_runtime_after_known_anchor(text, runtime)

    return text


def apply_singlestage(text: str, suggested: str) -> str:
    if "x_lucid_cluster_calibration" in text:
        return text
    m = re.search(r"^WORKDIR\s+(\S+)\s*$", text, re.MULTILINE)
    wd = m.group(1) if m else "/app"
    line = suggested.strip()
    if wd != "/app":
        line = re.sub(
            r"(\s+)/app/configs/",
            rf"\1{wd.rstrip('/')}/configs/",
            line,
        )
    if m:
        out = insert_after_line(text, m.group(0), line + "\n")
        if out:
            return out
    return text + "\n" + line + "\n"


def ensure_labels(text: str, service_label: str, cluster: str) -> str:
    if 'com.lucid.service="' in text:
        text = LABEL_SERVICE_RE.sub(
            lambda _: f'com.lucid.service="{service_label}"',
            text,
            count=1,
        )
    if 'com.lucid.cluster="' in text:
        text = LABEL_CLUSTER_RE.sub(
            lambda _: f'com.lucid.cluster="{cluster}"',
            text,
            count=1,
        )
    return text


def patch_dockerfile(path: Path, meta: dict) -> str | None:
    text = path.read_text(encoding="utf-8")
    orig = text
    cl = calibration_lines(meta, text)
    if not cl:
        return None
    builder, runtime, name = cl

    if is_multistage_build(text):
        text = apply_multistage(text, builder, runtime, name)
    else:
        sug = meta.get("suggested_copy_line") or ""
        text = apply_singlestage(text, sug)

    svc = meta.get("com_lucid_service_label") or ""
    cluster = meta.get("cluster") or ""
    if svc and cluster:
        text = ensure_labels(text, svc, cluster)

    if text != orig:
        return text
    return None


def main() -> int:
    entries = load_manifest_entries()
    changed = 0
    for path_str in sorted(entries):
        path = Path(path_str)
        meta = entries[path_str]
        new = patch_dockerfile(path, meta)
        if new is not None:
            path.write_text(new, encoding="utf-8", newline="\n")
            changed += 1
            print("updated", path.relative_to(ROOT))
    print("manifest entries (under containers):", len(entries))
    print("files changed:", changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
