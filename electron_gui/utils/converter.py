"""
File: /app/electron_gui/utils/converter.py
x-lucid-file-path: /app/electron_gui/utils/converter.py
x-lucid-file-type: python

Converts Lucid *.ts / *.tsx into *.py for the Electron GUI.

Pipeline:
- TypeScript / TSX → JavaScript via the same `typescript` package the GUI uses
  (Node subprocess, `transpileModule`; no separate tsc project required per file).
- JavaScript → Python:
  - Mode ``jiphy``: use the ``jiphy`` package when installed (best-effort syntax
    translation; output may still need review).
  - Mode ``embed`` (default when ``jiphy`` is unavailable or fails): emit valid
    Python that exposes the transpiled JS as ``TRANSPILED_JAVASCRIPT_B64`` /
    ``transpiled_javascript()`` so nothing is lost.

Environment:
- ``LUCID_ELECTRON_CONVERTER_TARGET``: output root (default: ``/app/electron-gui``
  if that directory exists, else ``<electron_gui>/_converted_py``).
- ``LUCID_ELECTRON_CONVERTER_MODE``: ``auto`` | ``jiphy`` | ``embed``.
  ``auto`` tries ``jiphy`` first, then falls back to ``embed``.

Container path mapping (repo → target):
- electron_gui/utils/* --> /app/electron-gui/utils/*
- electron_gui/main/* --> /app/electron-gui/main/*
- electron_gui/renderer/* --> /app/electron-gui/renderer/*
- electron_gui/shared/* --> /app/electron-gui/shared/*
- electron_gui/assets/* --> /app/electron-gui/assets/*
- electron_gui/configs/* --> /app/electron-gui/configs/*
- electron_gui/scripts/* --> /app/electron-gui/scripts/*
- electron_gui/tests/* --> /app/electron-gui/tests/*
- electron_gui/package.json --> /app/electron-gui/package.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Iterable, Literal, Optional

ENV_CONVERTER_TARGET = "LUCID_ELECTRON_CONVERTER_TARGET"
ENV_CONVERTER_MODE = "LUCID_ELECTRON_CONVERTER_MODE"
DEFAULT_CONTAINER_TARGET = Path("/app/electron-gui")

ConversionMode = Literal["auto", "jiphy", "embed"]


class ConversionError(RuntimeError):
    """Raised when TypeScript cannot be transpiled or output cannot be written."""


def electron_gui_root() -> Path:
    """Directory that contains ``package.json`` for lucid-electron-gui (``electron_gui``)."""
    return Path(__file__).resolve().parents[1]


def resolve_target_container(electron_root: Optional[Path] = None) -> Path:
    env = os.environ.get(ENV_CONVERTER_TARGET, "").strip()
    if env:
        return Path(env)
    if DEFAULT_CONTAINER_TARGET.is_dir():
        return DEFAULT_CONTAINER_TARGET
    root = electron_root or electron_gui_root()
    return root / "_converted_py"


def map_source_to_target_py(
    source_ts: Path,
    electron_root: Path,
    target_root: Path,
) -> Path:
    """Map ``electron_gui/.../file.ts`` → ``target_root/.../file.py``."""
    rel = source_ts.resolve().relative_to(electron_root.resolve())
    return (target_root / rel).with_suffix(".py")


def _which_node() -> str:
    import shutil

    path = shutil.which("node")
    if not path:
        raise ConversionError("Node.js is not on PATH; install Node >= 18 to transpile TypeScript.")
    return path


def typescript_to_javascript(source: Path, electron_root: Path) -> str:
    """
    Transpile a ``.ts`` or ``.tsx`` file to JavaScript using the GUI's ``typescript``
    package (``electron_gui/node_modules``).
    """
    source = source.resolve()
    electron_root = electron_root.resolve()
    ts_nm = electron_root / "node_modules" / "typescript"
    if not ts_nm.is_dir():
        raise ConversionError(
            f"Missing TypeScript package at {ts_nm}. Run: npm ci (in {electron_root})"
        )
    if not source.is_file():
        raise ConversionError(f"Source file not found: {source}")
    suffix = source.suffix.lower()
    if suffix not in (".ts", ".tsx"):
        raise ConversionError(f"Expected .ts or .tsx, got: {source}")

    node = _which_node()
    is_tsx = suffix == ".tsx"
    # Run from electron_gui so require('typescript') resolves to local node_modules.
    script = textwrap.dedent(
        """
        const path = require('path');
        const fs = require('fs');
        const ts = require(path.join(process.cwd(), 'node_modules', 'typescript'));
        const p = process.argv[1];
        const jsx = process.argv[2] === '1';
        const src = fs.readFileSync(p, 'utf8');
        const r = ts.transpileModule(src, {
          compilerOptions: {
            module: ts.ModuleKind.CommonJS,
            target: ts.ScriptTarget.ES2020,
            esModuleInterop: true,
            skipLibCheck: true,
            jsx: jsx ? ts.JsxEmit.ReactJSX : undefined,
          },
          fileName: p,
        });
        process.stdout.write(r.outputText);
        """
    ).strip()

    try:
        proc = subprocess.run(
            [node, "-e", script, str(source), "1" if is_tsx else "0"],
            cwd=str(electron_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as e:
        raise ConversionError(f"Failed to run Node: {e}") from e

    if proc.returncode != 0:
        err = (proc.stderr or "").strip() or proc.stdout
        raise ConversionError(f"TypeScript transpile failed ({proc.returncode}): {err}")

    return proc.stdout


def _javascript_via_jiphy(js: str) -> str:
    import jiphy  # type: ignore[import-untyped]

    out = jiphy.to.python(js)
    if not isinstance(out, str):
        raise ConversionError("jiphy returned non-string output")
    return out


def _javascript_embed_module(js: str, *, source_label: str) -> str:
    """Valid Python module embedding the JS payload (lossless)."""
    b64 = base64.b64encode(js.encode("utf-8")).decode("ascii")
    return textwrap.dedent(
        f'''\
        """
        Auto-generated from TypeScript/JavaScript ({source_label}).
        Original transpiled JavaScript is embedded below (lossless).
        """
        from __future__ import annotations

        import base64

        TRANSPILED_JAVASCRIPT_B64 = "{b64}"

        def transpiled_javascript() -> str:
            return base64.b64decode(TRANSPILED_JAVASCRIPT_B64).decode("utf-8")


        __all__ = ["TRANSPILED_JAVASCRIPT_B64", "transpiled_javascript"]
        '''
    ).rstrip() + "\n"


def _javascript_try_jiphy(js: str) -> Optional[str]:
    try:
        return _javascript_via_jiphy(js)
    except ImportError:
        return None
    except Exception:
        return None


def javascript_to_python(
    js: str,
    *,
    source_label: str,
    mode: Optional[ConversionMode] = None,
) -> str:
    """
    Convert JavaScript source to Python source.

    * ``embed`` — always emit a module with ``transpiled_javascript()``.
    * ``jiphy`` — require ``jiphy``; raise if conversion fails.
    * ``auto`` — try ``jiphy``, else ``embed``.
    """
    raw = mode or os.environ.get(ENV_CONVERTER_MODE, "auto").strip().lower()
    if raw not in ("auto", "jiphy", "embed"):
        raw = "auto"
    m: ConversionMode = raw  # type: ignore[assignment]

    if m == "embed":
        return _javascript_embed_module(js, source_label=source_label)
    if m == "jiphy":
        return _javascript_via_jiphy(js)

    attempt = _javascript_try_jiphy(js)
    if attempt is not None:
        return attempt
    return _javascript_embed_module(js, source_label=source_label)


def convert_ts_to_py(
    source_ts: Path,
    *,
    electron_root: Optional[Path] = None,
    target_root: Optional[Path] = None,
    mode: Optional[ConversionMode] = None,
) -> Path:
    """
    Transpile one ``.ts`` / ``.tsx`` file and write the corresponding ``.py``
    under the target root (mirroring subpaths under ``electron_gui``).
    """
    electron_root = (electron_root or electron_gui_root()).resolve()
    target_root = (target_root or resolve_target_container(electron_root)).resolve()
    source_ts = source_ts.resolve()

    js = typescript_to_javascript(source_ts, electron_root)
    try:
        rel = source_ts.relative_to(electron_root)
    except ValueError as e:
        raise ConversionError(
            f"Source {source_ts} is not under electron_gui root {electron_root}"
        ) from e
    py_body = javascript_to_python(
        js,
        source_label=rel.as_posix(),
        mode=mode,
    )

    header = (
        f'"""\nGenerated by electron_gui/utils/converter.py from {rel.as_posix()}\n"""\n\n'
    )
    out_path = map_source_to_target_py(source_ts, electron_root, target_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + py_body, encoding="utf-8")
    return out_path


def iter_ts_files(
    electron_root: Path,
    *,
    skip_node_modules: bool = True,
) -> Iterable[Path]:
    patterns = ("**/*.ts", "**/*.tsx")
    for pat in patterns:
        for p in electron_root.glob(pat):
            if skip_node_modules and "node_modules" in p.parts:
                continue
            if "dist" in p.parts:
                continue
            yield p


def convert_tree(
    electron_root: Optional[Path] = None,
    target_root: Optional[Path] = None,
    mode: Optional[ConversionMode] = None,
) -> list[Path]:
    """Convert all ``.ts`` / ``.tsx`` files under ``electron_gui`` (excluding node_modules / dist)."""
    electron_root = (electron_root or electron_gui_root()).resolve()
    written: list[Path] = []
    for ts in sorted(iter_ts_files(electron_root), key=lambda x: str(x)):
        written.append(convert_ts_to_py(ts, electron_root=electron_root, target_root=target_root, mode=mode))
    return written


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert Electron GUI TypeScript to Python modules.")
    p.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional .ts / .tsx files or directories (default: entire electron_gui tree).",
    )
    p.add_argument(
        "--mode",
        choices=("auto", "jiphy", "embed"),
        default=None,
        help="Override LUCID_ELECTRON_CONVERTER_MODE.",
    )
    p.add_argument(
        "--target",
        type=Path,
        default=None,
        help=f"Override output root (default: {ENV_CONVERTER_TARGET} or _converted_py).",
    )
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    root = electron_gui_root()
    mode = args.mode
    target_root = args.target.resolve() if args.target else None

    if not args.paths:
        out = convert_tree(electron_root=root, target_root=target_root, mode=mode)
        print(json.dumps({"written": len(out), "files": [str(x) for x in out]}, indent=2))
        return 0

    written: list[Path] = []
    for raw in args.paths:
        path = raw.resolve()
        if path.is_dir():
            for ts in sorted(path.glob("**/*.ts")) + sorted(path.glob("**/*.tsx")):
                if "node_modules" in ts.parts:
                    continue
                written.append(
                    convert_ts_to_py(ts, electron_root=root, target_root=target_root, mode=mode)
                )
        elif path.suffix.lower() in (".ts", ".tsx"):
            written.append(convert_ts_to_py(path, electron_root=root, target_root=target_root, mode=mode))
        else:
            print(f"Skip (not .ts/.tsx): {path}", file=sys.stderr)

    print(json.dumps({"written": len(written), "files": [str(x) for x in written]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
