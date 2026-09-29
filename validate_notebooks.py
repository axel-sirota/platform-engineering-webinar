#!/usr/bin/env python3
"""
Notebook validator for the Platform Engineering Foundations webinar demos.

The source of truth is imp_docs/demos.md (SPEC). Three Gradio notebooks, each with a
Spaces backup folder built from the same code.

Checks per notebook:
    1. Cell count and cell types match SPEC.
    2. Cell 0 has the "Synthetic data" line; cell 1 pins gradio.
    3. Every code cell starts with a comment line.
    4. Python syntax per code cell (IPython lines stripped).
    5. pyflakes over all code cells concatenated in order (if pyflakes is installed).
    6. Imports only from stdlib, gradio, pandas, numpy, plotly (google.colab allowed).
    7. No network modules, no upload components.
    8. GRADIO_ANALYTICS_ENABLED set before the first gradio import.
    9. Self-check cell prints "All Demo N checks passed".
   10. Launch cell uses demo.queue(default_concurrency_limit=64).launch(share=True.
   11. ADMIN_KEY never printed.
   12. No real client or company names (DENYLIST).
   13. AI-tells: em dash, en dash, Unicode multiplication, bare --- in markdown.
   14. Outputs cleared.
   15. Gradio pin matches spaces/<demo>/requirements.txt and README sdk_version.
   16. Optional deploy cell: DEPLOY_TO_SPACES = False, and its APP_PY, REQUIREMENTS_TXT and
       README_MD strings equal the files in spaces/<demo>/.

Optional:
    --selfcheck  run code cells 2..self-check in a subprocess and require the PASS line
    --parity     every notebook line in the app range appears, in order, in app.py

Usage:
    .venv/bin/python3 validate_notebooks.py notebooks/demo3_rollout.ipynb
    .venv/bin/python3 validate_notebooks.py notebooks/demo3_rollout.ipynb --selfcheck --parity
    .venv/bin/python3 validate_notebooks.py --all --selfcheck --parity
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class DemoSpec:
    """Shape of one demo notebook as fixed by SPEC."""

    number: int
    notebook: str
    space: str
    cells: int
    selfcheck_cell: int
    launch_cell: int
    app_first: int
    app_last: int
    deploy_cell: int


# SPEC cell counts plus one optional "deploy to Spaces" cell before the instructor notes.
DEMOS: dict[int, DemoSpec] = {
    1: DemoSpec(1, "notebooks/demo1_portal.ipynb", "spaces/demo1_portal", 13, 6, 10, 2, 9, 11),
    2: DemoSpec(2, "notebooks/demo2_funding_game.ipynb", "spaces/demo2_funding_game", 14, 8, 11, 2, 10, 12),
    3: DemoSpec(3, "notebooks/demo3_rollout.ipynb", "spaces/demo3_rollout", 12, 6, 9, 2, 8, 10),
}

ALLOWED_THIRD_PARTY = {"gradio", "pandas", "numpy", "plotly", "google", "huggingface_hub"}
# The deploy cell embeds the Spaces files as string constants with these names.
DEPLOY_CONSTANTS = {"APP_PY": "app.py", "REQUIREMENTS_TXT": "requirements.txt", "README_MD": "README.md"}
NETWORK_MODULES = {"requests", "urllib", "urllib3", "httpx", "socket", "http", "aiohttp"}
UPLOAD_PATTERNS = [re.compile(r"\bgr\.File\s*\("), re.compile(r"\bgr\.UploadButton\s*\(")]
# Real names that must never appear, one per line, kept out of git in plans/denylist.txt.
_DENYLIST_FILE = ROOT / "plans" / "denylist.txt"
DENYLIST = (
    [ln.strip().lower() for ln in _DENYLIST_FILE.read_text().splitlines() if ln.strip()]
    if _DENYLIST_FILE.exists()
    else []
)
AI_TELLS = [("—", "em dash"), ("–", "en dash"), ("×", "unicode multiplication")]
# Lines that legitimately differ between the notebook and the Spaces app.py.
PARITY_SKIP = ("ADMIN_KEY", "getpass", "userdata", "google.colab", "except", "try:")
LAUNCH_SNIPPET = "demo.queue(default_concurrency_limit=64).launch(share=True"


def cell_src(cell: dict) -> str:
    """Return a cell's source as one string."""
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else src


def strip_ipython(src: str) -> str:
    """Comment out %magic and !shell lines so the rest parses as Python."""
    out = []
    for line in src.splitlines():
        if line.lstrip().startswith(("%", "!")):
            out.append("# " + line)
        else:
            out.append(line)
    return "\n".join(out)


def load_nb(path: Path) -> dict:
    """Load a notebook as JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def code_cells(nb: dict) -> list[tuple[int, str]]:
    """Return (index, python source) for every code cell."""
    return [
        (i, strip_ipython(cell_src(c)))
        for i, c in enumerate(nb["cells"])
        if c["cell_type"] == "code"
    ]


def demo_for(path: Path) -> DemoSpec | None:
    """Find the DemoSpec from a filename like demo3_rollout.ipynb."""
    m = re.search(r"demo(\d)_", path.name)
    return DEMOS.get(int(m.group(1))) if m else None


def check_shape(nb: dict, spec: DemoSpec) -> list[str]:
    """Cell count, first and last cells markdown, the rest code."""
    errs = []
    cells = nb["cells"]
    if len(cells) != spec.cells:
        errs.append(f"expected {spec.cells} cells (SPEC), found {len(cells)}")
        return errs
    for i, c in enumerate(cells):
        want = "markdown" if i in (0, spec.cells - 1) else "code"
        if c["cell_type"] != want:
            errs.append(f"cell {i}: expected {want}, found {c['cell_type']}")
    if "Synthetic data" not in cell_src(cells[0]):
        errs.append("cell 0: missing the 'Synthetic data' line")
    if not re.search(r"gradio==[\w.]+", cell_src(cells[1])):
        errs.append("cell 1: install cell does not pin gradio==<version>")
    return errs


def check_top_comment(nb: dict) -> list[str]:
    """Every code cell starts with a comment saying what it does."""
    errs = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        lines = [ln for ln in cell_src(c).splitlines() if ln.strip()]
        if lines and not lines[0].lstrip().startswith("#"):
            errs.append(f"cell {i}: first line is not a comment")
    return errs


def check_syntax(nb: dict) -> list[str]:
    """ast.parse each code cell."""
    errs = []
    for i, src in code_cells(nb):
        try:
            ast.parse(src)
        except SyntaxError as e:
            errs.append(f"cell {i}: SyntaxError line {e.lineno}: {e.msg}")
    return errs


def check_pyflakes(nb: dict) -> list[str]:
    """pyflakes over all code cells in order, which also catches forward references."""
    try:
        from pyflakes.api import check
        from pyflakes.reporter import Reporter
    except ImportError:
        return ["pyflakes not installed: .venv/bin/python3 -m pip install pyflakes"]
    code = "\n\n".join(src for _, src in code_cells(nb))
    out, err = io.StringIO(), io.StringIO()
    check(code, "notebook", Reporter(out, err))
    msgs = [ln for ln in (out.getvalue() + err.getvalue()).splitlines() if ln.strip()]
    return [f"pyflakes: {m}" for m in msgs]


def _imported_modules(src: str) -> list[str]:
    """Top-level module names imported by a code string."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module.split(".")[0])
    return names


def check_imports(nb: dict) -> list[str]:
    """Only stdlib plus the SPEC stack. No network modules."""
    errs = []
    stdlib = set(sys.stdlib_module_names)
    for i, src in code_cells(nb):
        for mod in _imported_modules(src):
            if mod in NETWORK_MODULES:
                errs.append(f"cell {i}: network module '{mod}' imported (SPEC: no network calls)")
            elif mod not in stdlib and mod not in ALLOWED_THIRD_PARTY:
                errs.append(f"cell {i}: '{mod}' is outside the SPEC stack")
    return errs


def check_no_uploads(nb: dict) -> list[str]:
    """Public links: no upload components."""
    errs = []
    for i, src in code_cells(nb):
        for pat in UPLOAD_PATTERNS:
            if pat.search(src):
                errs.append(f"cell {i}: upload component /{pat.pattern}/ (SPEC: no uploads)")
    return errs


def check_analytics_first(nb: dict) -> list[str]:
    """GRADIO_ANALYTICS_ENABLED must be set before gradio is imported."""
    code = "\n".join(src for _, src in code_cells(nb))
    m_import = re.search(r"^\s*(import gradio|from gradio)", code, re.M)
    m_env = re.search(r"GRADIO_ANALYTICS_ENABLED", code)
    if not m_import:
        return []
    if not m_env or m_env.start() > m_import.start():
        return ["GRADIO_ANALYTICS_ENABLED is not set before the first gradio import"]
    return []


def check_selfcheck_and_launch(nb: dict, spec: DemoSpec) -> list[str]:
    """The PASS line and the exact launch call sit in the cells SPEC names."""
    errs = []
    cells = nb["cells"]
    if len(cells) <= max(spec.selfcheck_cell, spec.launch_cell):
        return errs
    pass_line = f'print("All Demo {spec.number} checks passed")'
    if pass_line not in cell_src(cells[spec.selfcheck_cell]):
        errs.append(f"cell {spec.selfcheck_cell}: missing {pass_line}")
    if LAUNCH_SNIPPET not in cell_src(cells[spec.launch_cell]):
        errs.append(f"cell {spec.launch_cell}: launch must use {LAUNCH_SNIPPET}...")
    return errs


def check_admin_key_private(nb: dict) -> list[str]:
    """ADMIN_KEY is never printed."""
    errs = []
    for i, src in code_cells(nb):
        if re.search(r"print\([^)]*\bADMIN_KEY\b", src):
            errs.append(f"cell {i}: ADMIN_KEY passed to print()")
    return errs


def check_denylist(nb: dict) -> list[str]:
    """No real client or company names anywhere."""
    errs = []
    for i, c in enumerate(nb["cells"]):
        low = cell_src(c).lower()
        for name in DENYLIST:
            if name in low:
                errs.append(f"cell {i}: real name '{name}' found (SPEC: fictional names only)")
    return errs


def check_ai_tells(nb: dict) -> list[str]:
    """Banned typography in any cell."""
    errs = []
    for i, c in enumerate(nb["cells"]):
        src = cell_src(c)
        for char, name in AI_TELLS:
            if char in src:
                errs.append(f"cell {i}: {name}")
        if c["cell_type"] == "markdown":
            for j, line in enumerate(src.splitlines()):
                if line.strip() == "---":
                    errs.append(f"cell {i}: bare --- separator on line {j}")
    return errs


def check_outputs_cleared(nb: dict) -> list[str]:
    """SPEC: hand over notebooks with outputs cleared."""
    errs = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] == "code" and (c.get("outputs") or c.get("execution_count")):
            errs.append(f"cell {i}: outputs not cleared")
    return errs


def notebook_pin(nb: dict) -> str | None:
    """The gradio version pinned in the notebook."""
    for c in nb["cells"]:
        m = re.search(r"gradio==([\w.]+)", cell_src(c))
        if m:
            return m.group(1)
    return None


def check_pin_matches_space(nb: dict, spec: DemoSpec) -> list[str]:
    """The same gradio pin in the notebook, requirements.txt and README sdk_version."""
    space = ROOT / spec.space
    if not space.exists():
        return []
    pin = notebook_pin(nb)
    errs = []
    req = space / "requirements.txt"
    readme = space / "README.md"
    if req.exists():
        m = re.search(r"gradio==([\w.]+)", req.read_text())
        if not m or m.group(1) != pin:
            errs.append(f"{req.relative_to(ROOT)}: gradio pin differs from notebook ({pin})")
    else:
        errs.append(f"{spec.space}/requirements.txt missing")
    if readme.exists():
        m = re.search(r"^sdk_version:\s*([\w.]+)", readme.read_text(), re.M)
        if not m or m.group(1) != pin:
            errs.append(f"{readme.relative_to(ROOT)}: sdk_version differs from notebook ({pin})")
    else:
        errs.append(f"{spec.space}/README.md missing")
    return errs


def _string_constants(src: str) -> dict[str, str]:
    """Module-level NAME = "string" assignments in a code cell."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    found = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            found[node.targets[0].id] = node.value.value
    return found


def check_deploy_cell(nb: dict, spec: DemoSpec) -> list[str]:
    """Optional deploy cell: off by default, embeds files identical to spaces/<demo>/."""
    cells = nb["cells"]
    if len(cells) <= spec.deploy_cell:
        return []
    src = cell_src(cells[spec.deploy_cell])
    errs = []
    if not re.search(r"^DEPLOY_TO_SPACES\s*=\s*False\b", src, re.M):
        errs.append(f"cell {spec.deploy_cell}: deploy cell must set DEPLOY_TO_SPACES = False")
    consts = _string_constants(src)
    space = ROOT / spec.space
    for name, filename in DEPLOY_CONSTANTS.items():
        if name not in consts:
            errs.append(f"cell {spec.deploy_cell}: missing string constant {name}")
            continue
        path = space / filename
        if path.exists() and consts[name].strip() != path.read_text().strip():
            errs.append(
                f"cell {spec.deploy_cell}: {name} differs from {spec.space}/{filename}; "
                f"rerun /build-space {spec.number}"
            )
    return errs


def run_selfcheck(nb: dict, spec: DemoSpec) -> list[str]:
    """Execute code cells 2..self-check locally and require the PASS line."""
    cells = nb["cells"]
    if len(cells) <= spec.selfcheck_cell:
        return [f"selfcheck: notebook has no cell {spec.selfcheck_cell} yet"]
    code = "\n\n".join(
        strip_ipython(cell_src(cells[i]))
        for i in range(2, spec.selfcheck_cell + 1)
        if cells[i]["cell_type"] == "code"
    )
    env = dict(os.environ, ADMIN_KEY=os.environ.get("ADMIN_KEY", "selfcheck-admin-key"))
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        script = f.name
    try:
        proc = subprocess.run(
            [sys.executable, script], capture_output=True, text=True, timeout=180, env=env,
        )
    finally:
        os.unlink(script)
    print(proc.stdout.rstrip())
    want = f"All Demo {spec.number} checks passed"
    if proc.returncode != 0 or want not in proc.stdout:
        tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
        return [f"selfcheck failed (exit {proc.returncode}):\n{tail}"]
    return []


def _significant_lines(src: str) -> list[str]:
    """Non-blank, non-magic lines that must survive into app.py."""
    out = []
    for line in src.splitlines():
        s = line.strip()
        if not s or s.startswith(("%", "!")) or any(tok in s for tok in PARITY_SKIP):
            continue
        out.append(s)
    return out


def check_parity(nb: dict, spec: DemoSpec) -> list[str]:
    """Every notebook line in the app range appears, in order, in app.py."""
    app = ROOT / spec.space / "app.py"
    if not app.exists():
        return [f"parity: {spec.space}/app.py missing"]
    app_lines = [ln.strip() for ln in app.read_text().splitlines() if ln.strip()]
    pos = 0
    cells = nb["cells"]
    for i in range(spec.app_first, min(spec.app_last, len(cells) - 1) + 1):
        for line in _significant_lines(cell_src(cells[i])):
            try:
                pos = app_lines.index(line, pos) + 1
            except ValueError:
                return [f"parity: cell {i} line not found in app.py (or out of order): {line[:70]}"]
    if "share=True" in app.read_text():
        return ["parity: app.py must launch without share=True"]
    return []


def validate(path: Path, selfcheck: bool, parity: bool) -> list[str]:
    """Run every check that applies to one notebook."""
    nb = load_nb(path)
    spec = demo_for(path)
    errs: list[str] = []
    if spec:
        errs += check_shape(nb, spec)
        errs += check_selfcheck_and_launch(nb, spec)
        errs += check_pin_matches_space(nb, spec)
        errs += check_deploy_cell(nb, spec)
    else:
        errs.append("filename does not match demoN_*.ipynb; SPEC shape checks skipped")
    errs += check_top_comment(nb)
    errs += check_syntax(nb)
    errs += check_pyflakes(nb)
    errs += check_imports(nb)
    errs += check_no_uploads(nb)
    errs += check_analytics_first(nb)
    errs += check_admin_key_private(nb)
    errs += check_denylist(nb)
    errs += check_ai_tells(nb)
    errs += check_outputs_cleared(nb)
    if spec and selfcheck:
        errs += run_selfcheck(nb, spec)
    if spec and parity:
        errs += check_parity(nb, spec)
    return errs


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Validate the webinar demo notebooks.")
    ap.add_argument("notebook", nargs="?", help="Path to one notebook.")
    ap.add_argument("--all", action="store_true", help="Validate every built demo notebook.")
    ap.add_argument("--selfcheck", action="store_true", help="Run the self-check cells locally.")
    ap.add_argument("--parity", action="store_true", help="Compare spaces app.py with the notebook.")
    args = ap.parse_args()

    if args.all:
        paths = [ROOT / d.notebook for d in DEMOS.values() if (ROOT / d.notebook).exists()]
    elif args.notebook:
        paths = [Path(args.notebook)]
    else:
        ap.error("give a notebook path or --all")

    if not paths:
        print("No demo notebooks built yet.")
        return 0

    failed = 0
    for path in paths:
        print(f"\n== {path}")
        errs = validate(path, args.selfcheck, args.parity)
        if errs:
            failed += 1
            for e in errs:
                print(f"  FAIL  {e}")
        else:
            print("  PASS  all checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
