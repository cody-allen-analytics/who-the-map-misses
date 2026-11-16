"""Pre-share checklist: fails if placeholders remain, real results are missing, or a result table
identifies a locality or map tile (the publication rules in docs/ethics.md).

python scripts/check_release.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDERS = [
    r"\[\[FILL",
    r"YOUR-USERNAME",
    r"YOUR NAME",
    r"YOUR-FAMILY-NAME",
    r"0000-0000-0000-0000",
    r"you@example\.com",
    r"Delete this note",
    r"Real-data results in progress",
]
SKIP_DIRS = {".git", "data", "site", "upload", ".venv", "venv", "__pycache__", "node_modules"}
REQUIRED = [
    "results/real/tables/audit_summary.json",
    "results/real/tables/robustness.csv",
    "results/real/tables/challenger_metrics_summary.csv",
    "docs/assets/figures/real/decile_errors.png",
]


def main() -> int:
    problems = []
    for path in ROOT.rglob("*"):
        if path.is_dir() or any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix not in {".md", ".yml", ".yaml", ".toml", ".cff", ".txt"} and path.name != "LICENSE":
            continue
        rel = path.relative_to(ROOT)
        # Draft posts may keep placeholders until they are published.
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "draft: true" in text and "blog/posts" in str(rel):
            continue
        for pattern in PLACEHOLDERS:
            for match in re.finditer(pattern, text):
                line = text[: match.start()].count("\n") + 1
                problems.append(f"{rel}:{line}: placeholder {match.group(0)!r}")
    for req in REQUIRED:
        if not (ROOT / req).exists():
            problems.append(f"missing real-data output: {req} (run notebooks 02-06)")
    sys.path.insert(0, str(ROOT / "src"))
    from mapaudit.publication import identifier_columns

    real = ROOT / "results" / "real"
    if real.exists():
        problems += [
            f"results/real/{hit}: locality- or tile-level column (only aggregates may be published)"
            for hit in identifier_columns(real)
        ]
    if problems:
        print("Not ready to share:\n  " + "\n  ".join(problems))
        return 1
    print("Ready to share.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
