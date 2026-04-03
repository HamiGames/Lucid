#!/usr/bin/env python3
"""
Normalize Lucid infrastructure env sources (Dockerfiles + Compose YAML):

Dockerfiles (scanned under infrastructure/containers, docker, compose,
  and service_mesh if present):
  - configs/environment and .env.secrets (strip from image build instructions)
  - After root ``COPY configs/ <dest>`` (not ``configs/docker`` etc.), inject
    ``RUN rm -rf configs/environment`` for the current stage when no existing
    ``RUN`` in that stage already removes ``configs/environment`` (defense if
    .dockerignore is not used).
  - master-env-config.txt and image-baked .env.master (COPY from context or --from)
  - infrastructure/containers/host-config.yml and infrastructure/containers/services/
    (COPY from build context or COPY --from=* /build/.../host-config.yml|service_configs)
    so host-specific layout is supplied at runtime via compose bind mounts instead

Compose (.yml / .yaml under those same directories):
  - Replace master-env-config.txt with configs/environment/.env.master in env_file,
    volumes, and comments (relative prefixes like ../../../ are preserved).

Runtime expectation: host files under configs/environment/ (.env.master, .env.secrets),
    wired via compose env_file / bind mounts.

Does not modify .dockerignore (root file may exclude configs/environment, host-config.yml,
  and infrastructure/containers/services/ so the build context cannot reintroduce them).
  Paths outside the default scan roots are skipped unless --root is passed.

Usage (repo root, PowerShell or bash):
  python scripts/strip_dockerfile_configs_environment.py
  python scripts/strip_dockerfile_configs_environment.py --apply
  python scripts/strip_dockerfile_configs_environment.py --skip-compose
  python scripts/strip_dockerfile_configs_environment.py --skip-dockerfiles --apply

After Dockerfile --apply, review builds: COPY configs/ may still ship configs/environment
from the build context unless .dockerignore excludes it.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ROOTS = (
    REPO_ROOT / "infrastructure" / "containers",
    REPO_ROOT / "infrastructure" / "docker",
    REPO_ROOT / "infrastructure" / "compose",
    REPO_ROOT / "compose",
    REPO_ROOT / "infrastructure" / "service_mesh",
)

# Longest-first so ./configs/environment is removed after subdirs.
QUOTED_ENV_FRAGMENTS = (
    "'./configs/environment/development'",
    "'./configs/environment/pi'",
    "'./configs/environment/production'",
    "'./configs/environment/staging'",
    "'./configs/environment'",
    "'./overlord/configs/environment'",
    '"./configs/environment/development"',
    '"./configs/environment/pi"',
    '"./configs/environment/production"',
    '"./configs/environment/staging"',
    '"./configs/environment"',
    '"./overlord/configs/environment"',
)

COPY_LINE = re.compile(
    r"^\s*COPY\s+[^\n]*(?:configs/environment|\.env\.secrets)[^\n]*\s*$",
    re.IGNORECASE,
)

# Root tree copy: COPY configs/ ./configs/ — not COPY configs/docker/ ...
COPY_CONFIGS_ROOT = re.compile(r"^\s*COPY\s+configs/\s+\S", re.IGNORECASE)

RUN_RM_ENV = re.compile(
    r"^(\s*)RUN\s+rm\s+-rf\s+(\./)?configs/environment\s*",
    re.IGNORECASE,
)


def _strip_run_rm_blocks(lines: list[str]) -> list[str]:
    """Remove or rewrite RUN lines that only drop configs/environment."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        raw = line.rstrip("\n\r")
        m = RUN_RM_ENV.match(raw)
        if not m:
            out.append(line)
            i += 1
            continue

        tail = raw[m.end() :].strip()
        # RUN rm -rf ... (nothing else)
        if not tail:
            i += 1
            continue

        # RUN rm -rf ... &&
        if tail == "&&":
            i += 1
            if i >= len(lines):
                break
            nxt = lines[i]
            ns = nxt.strip()
            if "echo" in ns and ".env" in ns:
                i += 1
                continue
            out.append(f"RUN {nxt.lstrip()}")
            i += 1
            continue

        # RUN rm -rf ... && \
        if tail.rstrip() == "&&" + "\\" or (tail.startswith("&&") and "\\" in tail):
            i += 1
            if i >= len(lines):
                break
            nxt = lines[i]
            ns = nxt.strip()
            if "echo" in ns and ".env" in ns:
                i += 1
                continue
            out.append(f"RUN {nxt.lstrip()}")
            i += 1
            continue

        # Unexpected tail — keep line (manual review)
        out.append(line)
        i += 1
    return out


def _copy_line_bakes_host_config_or_services_tree(raw: str) -> bool:
    """Strip COPY lines that embed host-config or packaged services (runtime bind mounts)."""
    ls = raw.lstrip()
    if not ls.upper().startswith("COPY"):
        return False
    if "infrastructure/containers/host-config.yml" in raw:
        return True
    if "infrastructure/containers/host/host-config.yml" in raw:
        return True
    if "infrastructure/containers/services" in raw:
        return True
    if "--from=" in raw:
        if "host-config.yml" in raw:
            return True
        if "/build/configs/host-config.yml" in raw:
            return True
        # Do not strip generic /build/service_configs/* --from lines (e.g. kubernetes
        # configmaps copied from builder); only context COPYs from
        # infrastructure/containers/services are removed above.
    return False


def _copy_line_removes_master_or_env_master(raw: str) -> bool:
    """True if this COPY bakes master-env-config or .env.master into the image."""
    ls = raw.lstrip()
    if not ls.upper().startswith("COPY"):
        return False
    if "master-env-config.txt" in raw:
        return True
    # Path form /configs/.env.master has no \\b before the dot; use .env.master token match
    if re.search(r"\.env\.master(?:\s|$)", raw):
        return True
    return False


def _stage_already_removes_configs_environment(lines: list[str], start_idx: int) -> bool:
    """True if a later RUN in the same stage (until next FROM) removes configs/environment."""
    j = start_idx + 1
    while j < len(lines):
        raw = lines[j].rstrip("\n\r")
        if re.match(r"^\s*FROM\s+", raw, re.IGNORECASE):
            break
        if re.match(r"^\s*RUN\s+", raw, re.IGNORECASE):
            low = raw.lower()
            if "configs/environment" in low and "rm" in low:
                return True
        j += 1
    return False


def _inject_rm_configs_environment_after_root_copy(lines: list[str]) -> list[str]:
    """
    After ``COPY configs/ <dest>``, ensure the stage strips configs/environment from the image.
    Uses ``configs/environment`` (no ./) so _substring_scrub does not erase the path.
    """
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        raw = line.rstrip("\n\r")
        out.append(line)
        if COPY_CONFIGS_ROOT.match(raw):
            if not _stage_already_removes_configs_environment(lines, i):
                indent_m = re.match(r"^(\s*)", line)
                indent = indent_m.group(1) if indent_m else ""
                out.append(
                    f"{indent}RUN rm -rf configs/environment 2>/dev/null || true\n"
                )
        i += 1
    return out


def _remove_copy_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        raw = line.rstrip("\n\r")
        if COPY_LINE.match(raw):
            continue
        if _copy_line_removes_master_or_env_master(raw):
            continue
        if _copy_line_bakes_host_config_or_services_tree(raw):
            continue
        out.append(line)
    return out


def _repair_broken_tor_comments(text: str) -> str:
    """Fix PUBLIC_TOR_IP comments mangled by earlier passes."""
    text = text.replace(
        "PUBLIC_TOR_IP: .././ ",
        "PUBLIC_TOR_IP: ../../configs/environment/.env.master ",
    )
    text = re.sub(
        r"(PUBLIC_TOR_IP:\s*)\.\./\.\./host-configs/",
        r"\1../../configs/environment/",
        text,
    )
    return text


def _substring_scrub(text: str) -> str:
    for frag in QUOTED_ENV_FRAGMENTS:
        text = text.replace(frag + " \\", "")
        text = text.replace(frag + "\\", "")
        text = text.replace(frag + " ", " ")
        text = text.replace(frag, "")
    # Unquoted variants in RUN / paths (avoid matching inside ../../configs/environment).
    # Do not strip ./configs/environment on RUN lines that remove it (injected cleanup).
    scrubbed_lines: list[str] = []
    for ln in text.splitlines():
        if re.match(r"^\s*RUN\s+", ln, re.IGNORECASE) and "configs/environment" in ln:
            scrubbed_lines.append(ln)
            continue
        scrubbed_lines.append(
            re.sub(
                r"(?<!\.)"
                r"\./configs/environment(?:/development|/pi|/production|/staging)?\b",
                "",
                ln,
            )
        )
    text = "\n".join(scrubbed_lines)
    text = re.sub(r"\./overlord/configs/environment\b", "", text)
    text = text.replace("/app/configs/environment", "/app/configs")
    # Tidy doubled spaces left between adjacent './…' path tokens in mkdir/rsync lines
    text = re.sub(r"(?m)('\./[^']+')(\s{2,})('\./)", r"\1 \3", text)
    return text


_LABEL_SKIP_PARTS = frozenset({".env.secrets", ".env.master"})


def _scrub_env_secrets_mentions(text: str) -> str:
    """Remove .env.secrets / .env.master from LABELs and tidy related comments."""
    def label_repl(m: re.Match[str]) -> str:
        key, val = m.group(1), m.group(2)
        parts = [
            p.strip()
            for p in val.split(",")
            if p.strip() and p.strip() not in _LABEL_SKIP_PARTS
        ]
        inner = ",".join(parts)
        if not inner:
            inner = ".env.foundation"
        return f'{key}="{inner}"'

    text = re.sub(
        r'(com\.lucid\.env\.config)="([^"]*)"',
        label_repl,
        text,
        flags=re.IGNORECASE,
    )

    def comment_line_repl(line: str) -> str:
        if not line.lstrip().startswith("#"):
            return line
        s = line
        for token, patterns in (
            (
                ".env.secrets",
                (
                    r"\s*\.env\.secrets\s*\+\s*",
                    r"\+\s*\.env\.secrets\s*",
                    r",\s*\.env\.secrets\s*",
                    r"\s*\.env\.secrets\s*",
                ),
            ),
            (
                ".env.master",
                (
                    r"\s*\.env\.master\s*\+\s*",
                    r"\+\s*\.env\.master\s*",
                    r",\s*\.env\.master\s*",
                    r"\s*\.env\.master\s*",
                ),
            ),
        ):
            if token not in s:
                continue
            for pat in patterns:
                s = re.sub(pat, " ", s)
        s = re.sub(r"\+\s*\+", "+", s)
        s = re.sub(r"\s+\+\s*$", "", s)
        s = re.sub(r"(# LUCID_IMAGE_CONFIG:)\s{2,}", r"\1 ", s)
        s = re.sub(r"^\s*#\s*LUCID_IMAGE_CONFIG:\s*\+\s*", "# LUCID_IMAGE_CONFIG: ", s)
        s = re.sub(r"^\s*#\s*LUCID_IMAGE_CONFIG:\s*$", "", s)
        s = re.sub(r"\(\s*\)", "", s)
        return s.rstrip()

    lines_out: list[str] = []
    for L in text.splitlines():
        ls = L.lstrip()
        if ls.startswith("#"):
            if "master-env-config.txt" in L:
                L = L.replace(
                    "master-env-config.txt",
                    "../../configs/environment/.env.master",
                )
            if "configs/environment" in L:
                if re.match(r"^#\s+-\s+.*configs/environment", ls):
                    continue
                # Keep compose-relative path ../../configs/environment/... intact in comments
                if "../../configs/environment" in L:
                    pass
                else:
                    L = L.replace("configs/environment/", "host-configs/")
                    L = L.replace("configs/environment", "host-configs")
                    L = L.replace(
                        "../../host-configs/.env.master",
                        "../../configs/environment/.env.master",
                    )
        lines_out.append(comment_line_repl(L))
    text = "\n".join(lines_out) + ("\n" if text.endswith("\n") else "")
    return text


def process_dockerfile(content: str) -> str:
    lines = content.splitlines(keepends=True)
    # Normalise to \n for processing
    lines_no_nl = [ln.rstrip("\n\r") for ln in lines]
    lines_no_nl = _remove_copy_lines(lines_no_nl)
    lines_no_nl = _strip_run_rm_blocks(lines_no_nl)
    text = "\n".join(lines_no_nl)
    if content.endswith("\n"):
        text += "\n"
    text = _substring_scrub(text)
    text = _repair_broken_tor_comments(text)
    text = _scrub_env_secrets_mentions(text)
    lines_post = text.splitlines()
    lines_post = _inject_rm_configs_environment_after_root_copy(lines_post)
    text = "\n".join(lines_post)
    # Final pass: lines that became empty or whitespace-only
    text = "\n".join(
        ln for ln in text.splitlines() if ln.strip() or ln == ""
    )
    if content.endswith("\n") and not text.endswith("\n"):
        text += "\n"
    return text


def iter_dockerfiles(roots: tuple[Path, ...]) -> list[Path]:
    found: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            name = p.name
            if "layout.bak" in name:
                continue
            if not (name.startswith("Dockerfile") or name.startswith("dockerfile")):
                continue
            # dockerfile_*.py / .pyc in tree are not container Dockerfiles
            if name.endswith(
                (".json", ".md", ".py", ".pyc", ".yaml", ".yml", ".toml", ".lock")
            ):
                continue
            found.add(p)
    return sorted(found)


MASTER_ENV_CONFIG_TXT = "master-env-config.txt"
MASTER_ENV_YAML_TARGET = "configs/environment/.env.master"


def iter_compose_yaml(roots: tuple[Path, ...]) -> list[Path]:
    found: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if "layout.bak" in p.name:
                continue
            if p.suffix.lower() not in (".yml", ".yaml"):
                continue
            found.add(p)
    return sorted(found)


def _posix_rel(from_dir: Path, target: Path) -> str:
    # Compose YAML expects forward slashes even on Windows.
    rel = os.path.relpath(str(target), str(from_dir))
    return rel.replace("\\", "/")


def _compose_env_and_volumes_target_dir(rel_path: str) -> bool:
    # Only run the env/volumes correction where you asked.
    rel_path = rel_path.replace("\\", "/").lstrip("./")
    return (
        rel_path.startswith("infrastructure/compose/")
        or rel_path == "compose/.env.example"
        or rel_path.startswith("compose/")
        or rel_path.startswith("infrastructure/containers/services/")
    )


def _fix_fused_volume_items(text: str) -> str:
    # Split entries like ":ro      - ..." into separate YAML lines.
    # Keep indentation of the "-".
    return re.sub(
        # IMPORTANT: do NOT consume the indentation spaces before the dash.
        # Some of your files ended up with "- ..." items at column 0 because
        # the older regex ate those spaces.
        r"(?m)(:\s*(?:ro|rw))(\s*-\s+)",
        r"\1\n\2",
        text,
    )


def _split_line_eol(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def _normalize_envfile_volumes_block_list_indent(text: str) -> str:
    """
    Ensure block-list items under `env_file:` and `volumes:` are indented consistently.

    Your expected style (per the compose files) is:
      <base_indent>env_file:
      <base_indent+2>- item
    """
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        m = re.match(r"^(?P<indent>\s*)(env_file|volumes):\s*$", line)
        if not m:
            out.append(line)
            i += 1
            continue

        base_indent_len = len(m.group("indent"))
        expected_dash_indent = base_indent_len + 2
        out.append(line)
        i += 1

        # Normalize subsequent dash items until indentation returns to the key level.
        # NOTE: Earlier fused-volume splitting bugs can place dash-items at column 0.
        # So we must not stop just because cur_indent <= base_indent_len when the line
        # is still a YAML list item (`- ...`).
        last_was_blank = False
        prev_nonblank_is_dash = False
        while i < len(lines):
            cur = lines[i]
            if cur.strip() == "":
                # If prev+next non-blank are both dash-items, drop blank line.
                k = i + 1
                while k < len(lines) and lines[k].strip() == "":
                    k += 1
                next_is_dash = False
                if k < len(lines):
                    next_is_dash = re.match(r"^\s*-\s+", lines[k]) is not None
                if prev_nonblank_is_dash and next_is_dash:
                    i += 1
                    continue

                if not last_was_blank:
                    out.append(cur)
                last_was_blank = True
                i += 1
                continue

            cur_indent = len(cur) - len(cur.lstrip(" "))
            is_dash_item = re.match(r"^\s*-\s+", cur) is not None
            if cur_indent <= base_indent_len and not is_dash_item:
                break

            if is_dash_item:
                cur_no_eol, eol = _split_line_eol(cur)
                remainder = cur_no_eol.lstrip(" ")
                out.append((" " * expected_dash_indent) + remainder + eol)
                i += 1
                last_was_blank = False
                prev_nonblank_is_dash = True
                continue

            out.append(cur)
            i += 1
            last_was_blank = False
            prev_nonblank_is_dash = False

    return "".join(out)


def _fix_compose_envfile_and_volumes_lines(
    path: Path,
    content: str,
    *,
    rel_env_master: str,
    rel_env_secrets: str,
    rel_services_tree: str,
    rel_host_config: str,
) -> str:
    """
    Line-based YAML editing for compose-like fragments:
    - env_file lists: ensure host paths for .env.master/.env.secrets
    - volumes list: ensure required mounts exist for /app configs and /app/service_configs
    """
    nl = "\r\n" if "\r\n" in content else "\n"

    # Fix env_file entries that incorrectly point at container paths.
    # Example bad line: "- /app/configs/.env.master"
    content = re.sub(
        r"(?m)^(\s*-\s*)/app/configs/\.env\.master\s*$",
        r"\1" + rel_env_master,
        content,
    )
    content = re.sub(
        r"(?m)^(\s*-\s*)/app/configs/\.env\.secrets\s*$",
        r"\1" + rel_env_secrets,
        content,
    )

    # Fix volume entries that incorrectly use /app/configs as host path.
    # Example bad line: "- /app/configs/.env.master:/app/configs/.env.master:ro"
    def _fix_env_master_host_mount(m: re.Match[str]) -> str:
        indent_minus = m.group(1)
        mode = m.group(2)
        return f"{indent_minus}{rel_env_master}:/app/configs/.env.master:{mode}"

    content = re.sub(
        r"(?m)^(\s*-\s*)/app/configs/\.env\.master:/app/configs/\.env\.master:(ro|rw)\s*$",
        _fix_env_master_host_mount,
        content,
    )

    def _fix_env_secrets_host_mount(m: re.Match[str]) -> str:
        indent_minus = m.group(1)
        mode = m.group(2)
        return f"{indent_minus}{rel_env_secrets}:/app/configs/.env.secrets:{mode}"

    content = re.sub(
        r"(?m)^(\s*-\s*)/app/configs/\.env\.secrets:/app/configs/\.env\.secrets:(ro|rw)\s*$",
        _fix_env_secrets_host_mount,
        content,
    )

    # Fix broken volume syntax where both sides use host paths (missing container destination):
    # Example bad: "- ../../../../configs/environment/.env.secrets:../../../../configs/environment/.env.secrets:ro"
    def _fix_broken_env_volume(m: re.Match[str]) -> str:
        indent_minus = m.group(1)
        host_path = m.group("host")
        typ = m.group("typ")  # master|secrets
        mode = m.group("mode")
        return f"{indent_minus}{host_path}:/app/configs/.env.{typ}:{mode}"

    content = re.sub(
        r"(?m)^(\s*-\s+)(?P<host>.+configs/environment/\.env\.(?P<typ>master|secrets)):(?P<rhs_host>.+configs/environment/\.env\.(?P=typ)):(?P<mode>ro|rw)\s*$",
        _fix_broken_env_volume,
        content,
    )

    # Split fused volumes entries into separate YAML lines before we try to analyze blocks.
    content = _fix_fused_volume_items(content)

    # From here, do structured line-level edits in the context of each service block.
    lines = content.splitlines(keepends=True)

    services_re = re.compile(r"^(\s*)services:\s*$")
    service_key_re = re.compile(r"^(\s*)([A-Za-z0-9_.-]+):\s*$")
    env_file_re = re.compile(r"^(\s*)env_file:\s*(.*)$")
    volumes_re = re.compile(r"^(\s*)volumes:\s*(.*)$")
    dash_item_re = re.compile(r"^(\s*)-\s*(.+?)\s*$")

    out: list[str] = []
    i = 0
    while i < len(lines):
        m_services = services_re.match(lines[i])
        if not m_services:
            out.append(lines[i])
            i += 1
            continue

        services_indent_str = m_services.group(1)
        services_indent = len(services_indent_str)
        out.append(lines[i])
        i += 1

        # Determine service indent by first matching service key under this services block.
        service_indent: int | None = None
        # Walk until indentation returns to services indent or EOF.
        while i < len(lines):
            if lines[i].strip() == "":
                out.append(lines[i])
                i += 1
                continue

            indent = len(lines[i]) - len(lines[i].lstrip(" "))
            if indent <= services_indent:
                break

            if service_indent is None:
                m_key = service_key_re.match(lines[i])
                if m_key and len(m_key.group(1)) > services_indent:
                    service_indent = indent
                out.append(lines[i])
                i += 1
                continue

            if indent == service_indent:
                m_key = service_key_re.match(lines[i])
                if not m_key:
                    out.append(lines[i])
                    i += 1
                    continue

                service_name = m_key.group(2)

                # Copy service block, but we may rewrite env_file/volumes inside.
                start = i
                i += 1
                while i < len(lines):
                    if lines[i].strip() == "":
                        i += 1
                        continue
                    ind2 = len(lines[i]) - len(lines[i].lstrip(" "))
                    if ind2 == service_indent:
                        # Next service (or some other key at same level).
                        m_next = service_key_re.match(lines[i])
                        if m_next:
                            break
                    if ind2 <= services_indent:
                        break
                    i += 1
                end = i

                block_lines = lines[start:end]
                rewritten = _rewrite_service_env_and_volumes_block(
                    block_lines,
                    rel_env_master=rel_env_master,
                    rel_env_secrets=rel_env_secrets,
                    rel_services_tree=rel_services_tree,
                    rel_host_config=rel_host_config,
                    nl=nl,
                    env_file_re=env_file_re,
                    volumes_re=volumes_re,
                    dash_item_re=dash_item_re,
                )
                out.extend(rewritten)
                continue

            out.append(lines[i])
            i += 1

    return "".join(out)


def _rewrite_service_env_and_volumes_block(
    block_lines: list[str],
    *,
    rel_env_master: str,
    rel_env_secrets: str,
    rel_services_tree: str,
    rel_host_config: str,
    nl: str,
    env_file_re: re.Pattern[str],
    volumes_re: re.Pattern[str],
    dash_item_re: re.Pattern[str],
) -> list[str]:
    # Rewrite env_file and volumes subsections inside a single service mapping.
    # NOTE: We do NOT attempt to interpret YAML anchors (env_file: *anchor).
    out = list(block_lines)

    # Work in-place by scanning for "env_file:" and "volumes:" subsections.
    idx = 0
    while idx < len(out):
        m_env = env_file_re.match(out[idx])
        if m_env:
            indent_env = len(m_env.group(1))
            rest = m_env.group(2).strip()
            # Skip anchor usage, but global regex fixes may already have corrected anchor values.
            if rest.startswith("*"):
                idx += 1
                continue
            # Only handle env_file as a block list (env_file: then list below).
            if rest != "":
                idx += 1
                continue

            # Find list item lines immediately following.
            items: list[tuple[int, str]] = []
            j = idx + 1
            item_indent: int | None = None
            while j < len(out):
                if out[j].strip() == "":
                    j += 1
                    continue
                ind = len(out[j]) - len(out[j].lstrip(" "))
                if ind <= indent_env:
                    break
                m_item = dash_item_re.match(out[j])
                if not m_item:
                    break
                if item_indent is None:
                    item_indent = len(m_item.group(1))
                items.append((j, m_item.group(2)))
                j += 1

            if item_indent is None:
                idx = j
                continue

            has_master = any("configs/environment/.env.master" in it for _, it in items)
            has_secrets = any("configs/environment/.env.secrets" in it for _, it in items)

            # Fix any existing env_file item that references host env configs but with wrong prefix.
            for k, item_text in items:
                if "configs/environment/.env.master" in item_text:
                    out[k] = f"{' ' * item_indent}- {rel_env_master}{nl}"
                elif "configs/environment/.env.secrets" in item_text:
                    out[k] = f"{' ' * item_indent}- {rel_env_secrets}{nl}"

            # Insert missing master/secrets entries.
            insert_at = j
            inserts: list[str] = []
            if not has_master:
                inserts.append(f"{' ' * item_indent}- {rel_env_master}{nl}")
            if not has_secrets:
                inserts.append(f"{' ' * item_indent}- {rel_env_secrets}{nl}")
            if inserts:
                out[insert_at:insert_at] = inserts
                j += len(inserts)

            idx = j
            continue

        m_vol = volumes_re.match(out[idx])
        if m_vol:
            indent_vol = len(m_vol.group(1))
            rest = m_vol.group(2).strip()
            # Only handle block-list volumes: "volumes:" with no inline content.
            if rest != "":
                idx += 1
                continue

            list_start = idx + 1
            list_items_idx: list[int] = []
            first_item_indent: int | None = None
            j = list_start
            while j < len(out):
                if out[j].strip() == "":
                    j += 1
                    continue
                ind = len(out[j]) - len(out[j].lstrip(" "))
                if ind <= indent_vol:
                    break
                m_item = dash_item_re.match(out[j])
                if not m_item:
                    break
                if first_item_indent is None:
                    first_item_indent = len(m_item.group(1))
                list_items_idx.append(j)
                j += 1

            if first_item_indent is None:
                idx = j
                continue

            has_master_mount = any("/app/configs/.env.master" in out[k] for k in list_items_idx)
            has_secrets_mount = any("/app/configs/.env.secrets" in out[k] for k in list_items_idx)
            has_host_config_mount = any("/app/configs/host-config.yml" in out[k] for k in list_items_idx)
            has_service_configs_mount = any("/app/service_configs" in out[k] for k in list_items_idx)

            inserts: list[str] = []
            if not has_master_mount:
                inserts.append(
                    f"{' ' * first_item_indent}- {rel_env_master}:/app/configs/.env.master:ro{nl}"
                )
            if not has_secrets_mount:
                inserts.append(
                    f"{' ' * first_item_indent}- {rel_env_secrets}:/app/configs/.env.secrets:ro{nl}"
                )
            if not has_service_configs_mount:
                inserts.append(
                    f"{' ' * first_item_indent}- {rel_services_tree}:/app/service_configs:ro{nl}"
                )
            if not has_host_config_mount:
                inserts.append(
                    f"{' ' * first_item_indent}- {rel_host_config}:/app/configs/host-config.yml:ro{nl}"
                )

            if inserts:
                out[list_start:list_start] = inserts
                j = j + len(inserts)

            idx = j
            continue

        idx += 1

    return out


def process_compose_yaml(path: Path, content: str) -> str:
    """
    Normalize compose-like YAML:
    - Replace master-env-config.txt references with configs/environment/.env.master
    - Fix fused volume entries (two list items on one line)
    - For compose stacks / fragments under:
        infrastructure/compose/, compose/, infrastructure/containers/services/
      rewrite env_file: and ensure volumes: mounts for .env.* / host-config.yml / services tree.
    """
    new = content.replace(MASTER_ENV_CONFIG_TXT, MASTER_ENV_YAML_TARGET)
    new = _fix_fused_volume_items(new)
    new = _normalize_envfile_volumes_block_list_indent(new)

    rel = path.relative_to(REPO_ROOT)
    if not _compose_env_and_volumes_target_dir(str(rel)):
        return new

    from_dir = path.parent
    rel_env_master = _posix_rel(from_dir, REPO_ROOT / "configs" / "environment" / ".env.master")
    rel_env_secrets = _posix_rel(from_dir, REPO_ROOT / "configs" / "environment" / ".env.secrets")
    rel_services_tree = _posix_rel(from_dir, REPO_ROOT / "infrastructure" / "containers" / "services")
    rel_host_config = _posix_rel(from_dir, REPO_ROOT / "infrastructure" / "containers" / "host-config.yml")

    new = _fix_compose_envfile_and_volumes_lines(
        path,
        new,
        rel_env_master=rel_env_master,
        rel_env_secrets=rel_env_secrets,
        rel_services_tree=rel_services_tree,
        rel_host_config=rel_host_config,
    )
    new = _normalize_envfile_volumes_block_list_indent(new)
    return new


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write changes; omit for dry-run (list only).",
    )
    ap.add_argument(
        "--root",
        action="append",
        type=Path,
        help="Extra root to scan (can repeat). Default: infrastructure/containers, docker, compose.",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print one line per examined file (OK or DRY/WRITE).",
    )
    ap.add_argument(
        "--skip-compose",
        action="store_true",
        help="Do not scan or modify .yml / .yaml under the scan roots.",
    )
    ap.add_argument(
        "--skip-dockerfiles",
        action="store_true",
        help="Do not scan or modify Dockerfiles (compose YAML only).",
    )
    args = ap.parse_args()
    if args.skip_compose and args.skip_dockerfiles:
        print("Error: cannot use both --skip-compose and --skip-dockerfiles.", file=sys.stderr)
        return 2
    roots = tuple(DEFAULT_ROOTS)
    if args.root:
        roots = roots + tuple((REPO_ROOT / r if not r.is_absolute() else r) for r in args.root)

    print(f"Repo root: {REPO_ROOT}")
    for root in roots:
        if not root.is_dir():
            print(f"Warning: scan root missing (skip): {root}", file=sys.stderr)

    df_changed = df_examined = 0
    yml_changed = yml_examined = 0

    if not args.skip_dockerfiles:
        files = iter_dockerfiles(roots)
        if not files:
            print(
                "No Dockerfiles matched (Dockerfile* / dockerfile* under scan roots, "
                "excluding *layout.bak*).",
                file=sys.stderr,
            )
        else:
            for path in files:
                try:
                    original = path.read_text(encoding="utf-8", errors="replace")
                except OSError as e:
                    print(f"skip read {path}: {e}", file=sys.stderr)
                    continue
                df_examined += 1
                new = process_dockerfile(original)
                rel = path.relative_to(REPO_ROOT)
                if new == original:
                    if args.verbose:
                        print(f"OK  dockerfile {rel}")
                    continue
                df_changed += 1
                print(f"{'WRITE' if args.apply else 'DRY'} dockerfile {rel}")
                if args.apply:
                    path.write_text(new, encoding="utf-8", newline="\n")

    if not args.skip_compose:
        yfiles = iter_compose_yaml(roots)
        if not yfiles:
            print("No .yml/.yaml files under scan roots.", file=sys.stderr)
        else:
            for path in yfiles:
                try:
                    original = path.read_text(encoding="utf-8", errors="replace")
                except OSError as e:
                    print(f"skip read {path}: {e}", file=sys.stderr)
                    continue
                yml_examined += 1
                new = process_compose_yaml(path, original)
                rel = path.relative_to(REPO_ROOT)
                if new == original:
                    if args.verbose:
                        print(f"OK  compose {rel}")
                    continue
                yml_changed += 1
                print(f"{'WRITE' if args.apply else 'DRY'} compose {rel}")
                if args.apply:
                    path.write_text(new, encoding="utf-8", newline="\n")

    if not args.skip_dockerfiles and df_examined == 0 and args.skip_compose:
        return 1
    if not args.skip_compose and yml_examined == 0 and args.skip_dockerfiles:
        return 1
    if df_examined == 0 and yml_examined == 0:
        return 1

    df_ok = df_examined - df_changed
    yml_ok = yml_examined - yml_changed
    parts = []
    if not args.skip_dockerfiles:
        parts.append(
            f"Dockerfiles: examined {df_examined}, "
            f"{df_changed} {'updated' if args.apply else 'would change'}, {df_ok} OK"
        )
    if not args.skip_compose:
        parts.append(
            f"Compose YAML: examined {yml_examined}, "
            f"{yml_changed} {'updated' if args.apply else 'would change'}, {yml_ok} OK"
        )
    print("Done.", " | ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
