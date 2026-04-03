"""One-shot: trim LUCID_X_FILES_SKELETON to manifest-relative dirs. Delete after use."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # Lucid repo root from infrastructure/containers

minimal_user = r"""# LUCID_X_FILES_SKELETON_BEGIN
# user-interface_manifest + user Electron layout: repo-relative dirs only (WORKDIR /build).
RUN set -eux; \
  for d in \
    '.' \
    './common' \
    './configs' \
    './electron_gui' \
    './gui' \
    './infrastructure/containers' \
  ; do \
    mkdir -p "$d"; \
    printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_X_FILES_SKELETON_END

"""

minimal_node = r"""# LUCID_X_FILES_SKELETON_BEGIN
# node-interface_manifest + npm bundle layout: repo-relative dirs only (WORKDIR /build).
RUN set -eux; \
  for d in \
    '.' \
    './common' \
    './configs' \
    './configs/kubernetes' \
    './electron_gui' \
    './gui' \
    './infrastructure/containers' \
    './scripts' \
    './main' \
    './renderer/node' \
    './renderer/common' \
    './shared' \
    './assets' \
  ; do \
    mkdir -p "$d"; \
    printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_X_FILES_SKELETON_END

"""

minimal_admin = r"""# LUCID_X_FILES_SKELETON_BEGIN
# admin-interface_manifest + npm admin layout: repo-relative dirs only (WORKDIR /build).
RUN set -eux; \
  for d in \
    '.' \
    './assets' \
    './common' \
    './configs' \
    './electron_gui' \
    './gui' \
    './infrastructure/containers' \
    './infrastructure/service_mesh' \
    './main' \
    './renderer/admin' \
    './renderer/common' \
    './scripts' \
    './shared' \
  ; do \
    mkdir -p "$d"; \
    printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_X_FILES_SKELETON_END

"""


def replace_x_files_block(path: Path, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    key = "# LUCID_X_FILES_SKELETON_BEGIN\n"
    i0 = text.index(key)
    i1 = text.index("# LUCID_X_FILES_SKELETON_END", i0)
    i1 = text.index("\n", i1) + 1
    path.write_text(text[:i0] + replacement + text[i1:], encoding="utf-8")


minimal_hw = r"""# LUCID_X_FILES_SKELETON_BEGIN
# gui-hardware-manager_manifest: repo-relative dirs only (WORKDIR /build).
RUN set -eux; \
  for d in \
    '.' \
    './common' \
    './configs' \
    './configs/kubernetes' \
    './gui_hardware_manager' \
    './infrastructure/containers' \
    './scripts' \
  ; do \
    mkdir -p "$d"; \
    printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_X_FILES_SKELETON_END

"""

minimal_tor = r"""# LUCID_X_FILES_SKELETON_BEGIN
# gui-tor-manager_manifest + service_configs/tor stub: repo-relative dirs only.
RUN set -eux; \
  for d in \
    '.' \
    './common' \
    './configs' \
    './configs/kubernetes' \
    './gui_tor_manager' \
    './infrastructure/containers' \
    './infrastructure/service_mesh' \
    './scripts' \
    './service_configs' \
    './service_configs/tor' \
  ; do \
    mkdir -p "$d"; \
    printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_X_FILES_SKELETON_END

"""

minimal_bridge = r"""# LUCID_X_FILES_SKELETON_BEGIN
# gui-api-bridge_manifest + wheels/tmp: repo-relative dirs only.
RUN set -eux; \
  for d in \
    '.' \
    './common' \
    './configs' \
    './gui_api_bridge' \
    './infrastructure/containers' \
    './infrastructure/service_mesh' \
    './scripts' \
    './service_configs' \
    './wheels' \
    './tmp' \
  ; do \
    mkdir -p "$d"; \
    printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_X_FILES_SKELETON_END

"""

minimal_docker_mgr = r"""# LUCID_X_FILES_SKELETON_BEGIN
# gui-docker-manager_manifest: repo-relative dirs only (WORKDIR /build).
RUN set -eux; \
  for d in \
    '.' \
    './common' \
    './configs' \
    './gui_docker_manager' \
    './infrastructure/containers' \
    './infrastructure/service_mesh' \
  ; do \
    mkdir -p "$d"; \
    printf 'LUCID_X_FILES_SKELETON_%s' "$(date +%s)" > "$d/.keep"; \
    touch "$d/.keep"; \
  done
# LUCID_X_FILES_SKELETON_END

"""


def main() -> None:
    eg = ROOT / "infrastructure/containers/electron_gui"
    replace_x_files_block(eg / "Dockerfile.user", minimal_user)
    replace_x_files_block(eg / "Dockerfile.node", minimal_node)
    replace_x_files_block(eg / "Dockerfile.admin", minimal_admin)
    gui = ROOT / "infrastructure/containers/gui"
    replace_x_files_block(gui / "Dockerfile.gui-hardware-manager", minimal_hw)
    replace_x_files_block(gui / "Dockerfile.gui-tor-manager", minimal_tor)
    replace_x_files_block(gui / "Dockerfile.gui-api-bridge", minimal_bridge)
    replace_x_files_block(gui / "Dockerfile.gui-docker-manager", minimal_docker_mgr)
    print("Skeleton blocks trimmed (electron_gui + gui).")


if __name__ == "__main__":
    main()
