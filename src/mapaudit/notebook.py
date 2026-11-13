"""Helpers for the notebooks in notebooks/.

The notebooks stay short because the logic lives here and in the pipeline modules, where it is
tested. Everything here also works from a plain Python session.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

from mapaudit.config import get_paths, repo_root
from mapaudit.upload import is_excluded

PLACEHOLDER_SUFFIXES = {".md", ".toml", ".yml", ".yaml", ".cff", ".txt", ".ipynb"}
REQUIRED = ["numpy", "pandas", "scipy", "sklearn", "statsmodels", "matplotlib", "yaml", "pyarrow", "requests"]
OPTIONAL = {"pytest": "tests", "ruff": "formatting", "mkdocs": "website", "ee": "Earth Engine export"}


def notebook_mode(default: str = "real") -> str:
    """'real' unless MAPAUDIT_NOTEBOOK_MODE says otherwise (CI runs every notebook in demo mode)."""
    mode = os.environ.get("MAPAUDIT_NOTEBOOK_MODE", default)
    if mode not in ("real", "demo"):
        raise ValueError(f"MAPAUDIT_NOTEBOOK_MODE must be 'real' or 'demo', got {mode!r}")
    return mode


def check_environment() -> pd.DataFrame:
    """Versions of the packages the project needs; tells you what to install if something is missing."""
    rows = [{"package": "python", "version": sys.version.split()[0], "needed for": "everything"}]
    missing = []
    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
            rows.append(
                {"package": name, "version": getattr(module, "__version__", "?"), "needed for": "pipeline"}
            )
        except ImportError:
            rows.append({"package": name, "version": "MISSING", "needed for": "pipeline"})
            missing.append(name)
    for name, purpose in OPTIONAL.items():
        try:
            module = importlib.import_module(name)
            rows.append(
                {
                    "package": name,
                    "version": getattr(module, "__version__", "installed"),
                    "needed for": purpose,
                }
            )
        except ImportError:
            rows.append({"package": name, "version": "not installed", "needed for": purpose})
    if missing:
        print(
            f"Missing: {missing}. Run the install cell in notebooks/00_setup.ipynb, then restart the kernel."
        )
    return pd.DataFrame(rows)


def load_table(name: str, mode: str = "real") -> pd.DataFrame:
    return pd.read_csv(get_paths(mode).tables / f"{name}.csv")


def load_summary(name: str, mode: str = "real") -> dict:
    return json.loads((get_paths(mode).tables / f"{name}.json").read_text())


def show_figure(name: str, mode: str = "real", width: int = 900):
    """Display a rendered figure inline (run the report step first)."""
    from IPython.display import Image, display

    path = get_paths(mode).figures / f"{name}.png"
    if not path.exists():
        print(f"{path.name} not found: run report.render_figures({mode!r}) first.")
        return None
    return display(Image(filename=str(path), width=width))


# ----------------------------------------------------------------------------- personalization


def _text_files(root: Path):
    """Project files that may contain placeholders. Python files are skipped on purpose: the
    placeholder strings in code (this module, scripts/check_release.py, tests) must stay intact."""
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if not path.is_file() or is_excluded(rel):
            continue
        if path.suffix in PLACEHOLDER_SUFFIXES or path.name == "LICENSE":
            yield path


def personalize(
    github_username: str,
    given_name: str,
    family_name: str,
    email: str,
    orcid: str | None = None,
    root: Path | None = None,
) -> list[str]:
    """Replace the template placeholders in every project file (what `sed` would do in a terminal)."""
    root = Path(root or repo_root())
    full_name = f"{given_name} {family_name}".strip()
    changed = []
    for path in _text_files(root):
        text = path.read_text(encoding="utf-8")
        new = text
        if path.name == "CITATION.cff":
            new = new.replace('given-names: "YOUR NAME"', f'given-names: "{given_name}"')
            new = new.replace('family-names: "YOUR-FAMILY-NAME"', f'family-names: "{family_name}"')
            if orcid:
                new = new.replace("0000-0000-0000-0000", orcid)
            else:
                new = re.sub(r"\n\s*orcid: \"https://orcid.org/0000-0000-0000-0000\"", "", new)
        new = new.replace("YOUR-USERNAME", github_username).replace("YOUR NAME", full_name)
        new = new.replace("you@example.com", email)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(path.relative_to(root).as_posix())
    return changed


# ----------------------------------------------------------------------------- checks


def sanity_checks(summary: dict, mode: str = "real") -> pd.DataFrame:
    """Checks to pass before trusting the build (see the implementation guide, step 4)."""
    rows = []

    def check(name, ok, value, expected):
        rows.append(
            {"check": name, "result": "pass" if ok else "CHECK", "value": value, "expected": expected}
        )

    if mode == "real":
        n, pop = summary.get("localities", 0), summary.get("population", 0)
        check("localities", 180_000 <= n <= 200_000, f"{n:,}", "about 189,000")
        check("population", 120e6 <= pop <= 130e6, f"{pop:,.0f}", "about 126 million")
    qk = summary.get("rwi_quadkey_consistency")
    check("RWI quadkeys match tile coordinates", qk is not None and qk > 0.95, qk, "> 0.95")
    loadings = summary.get("label_loadings", {})
    wealth = loadings.get("wealth_dhs_like", {})
    marg = loadings.get("marg_index", {})
    check(
        "asset loadings all positive",
        bool(wealth) and min(wealth.values()) > 0,
        min(wealth.values(), default=None),
        "> 0",
    )
    check(
        "marginalization loadings all positive",
        bool(marg) and min(marg.values()) > 0,
        min(marg.values(), default=None),
        "> 0",
    )
    if summary.get("localities_with_embeddings"):
        norm = summary.get("embedding_median_norm", 0)
        check("embedding norms plausible", 0.3 <= norm <= 1.05, round(norm, 3), "0.3 to 1")
    return pd.DataFrame(rows)


def run_checks(fix: bool = True, release: bool = False, root: Path | None = None) -> pd.DataFrame:
    """Format, lint, test and build the website, as CI will after you push.

    With ``fix=True`` formatting problems are fixed in place. With ``release=True`` the pre-share
    check (no placeholders left, real results present) runs too.
    """
    root = Path(root or repo_root())
    py = sys.executable
    targets = ["src", "tests", "scripts"]
    steps = [
        (
            "format",
            [py, "-m", "ruff", "format", *targets]
            if fix
            else [py, "-m", "ruff", "format", "--check", *targets],
        ),
        ("lint", [py, "-m", "ruff", "check", *(["--fix"] if fix else []), *targets]),
        ("tests", [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--color=no"]),
        ("website", [py, "-m", "mkdocs", "build", "--strict", "--site-dir", str(root / "site")]),
    ]
    if release:
        steps.append(("ready to share", [py, str(root / "scripts" / "check_release.py")]))
    env = {**os.environ, "NO_MKDOCS_2_WARNING": "1", "NO_COLOR": "1", "FORCE_COLOR": "0"}
    rows = []
    for name, cmd in steps:
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=env)
        text = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + result.stderr)
        tail = text.strip().splitlines()[-2:]
        rows.append(
            {
                "check": name,
                "status": "pass" if result.returncode == 0 else "FAIL",
                "output": " | ".join(tail),
            }
        )
    table = pd.DataFrame(rows)
    if (table["status"] == "FAIL").any():
        print("Fix the failing checks before committing; CI runs the same checks on GitHub.")
    else:
        print("All checks passed.")
    return table


# ----------------------------------------------------------------------------- README


FIGURE_BLOCK = "\n".join(
    [
        "<picture>",
        '  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/figures/real/decile_errors-dark.png">',
        '  <img alt="Rank error of the Relative Wealth Index by true wealth decile, Indigenous vs non-Indigenous'
        ' tiles" src="docs/assets/figures/real/decile_errors.png">',
        "</picture>",
    ]
)


def update_readme(root: Path | None = None) -> str:
    """Write the generated findings and the headline figure into README.md (edit the wording after)."""
    root = Path(root or repo_root())
    headline = root / "results" / "real" / "headline.md"
    figure = root / "docs" / "assets" / "figures" / "real" / "decile_errors.png"
    if not headline.exists() or not figure.exists():
        raise FileNotFoundError("Run the report step on real data first (notebook 06).")
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    findings = headline.read_text(encoding="utf-8").strip()
    text = re.sub(
        r"(<!-- FINDINGS:START[^>]*-->\n).*?(\n<!-- FINDINGS:END -->)",
        lambda m: m.group(1) + findings + m.group(2),
        text,
        flags=re.S,
    )
    text = re.sub(
        r"(<!-- FIGURE:START[^>]*-->\n).*?(\n<!-- FIGURE:END -->)",
        lambda m: m.group(1) + FIGURE_BLOCK + m.group(2),
        text,
        flags=re.S,
    )
    readme.write_text(text, encoding="utf-8")
    return findings


def prepare_demo(through: str) -> None:
    """Demo mode only: run earlier pipeline steps whose outputs are missing, up to ``through``.

    Lets every notebook run on its own (CI executes each one separately on synthetic data).
    """
    from mapaudit import pipeline

    paths = get_paths("demo")
    outputs = {
        "build": paths.localities,
        "audit": paths.tables / "audit_summary.json",
        "robustness": paths.tables / "robustness.csv",
        "simulate": paths.tables / "challenger_metrics_summary.csv",
    }
    order = list(outputs)
    for step in order[: order.index(through) + 1]:
        if not outputs[step].exists():
            getattr(pipeline, step)("demo")
