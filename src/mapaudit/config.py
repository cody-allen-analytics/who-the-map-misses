"""Configuration and filesystem layout.

Two modes share one code path:

* ``real`` reads downloaded data from ``data/raw`` and writes to ``results/real``.
* ``demo`` generates synthetic data in ``data/demo`` and writes to ``results/demo``. CI runs this
  mode end to end, so every commit proves the pipeline still works.
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

MODES = ("real", "demo")


def repo_root() -> Path:
    """Repository root; override with the MAPAUDIT_ROOT environment variable."""
    env = os.environ.get("MAPAUDIT_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _deep_update(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_update(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_config(mode: str = "real", root: Path | None = None) -> dict[str, Any]:
    """Load analysis + source settings; in demo mode apply the ``demo`` overrides."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    root = root or repo_root()
    with open(root / "config" / "analysis.yaml", encoding="utf-8") as fh:
        analysis = yaml.safe_load(fh)
    with open(root / "config" / "sources.yaml", encoding="utf-8") as fh:
        sources = yaml.safe_load(fh)
    demo_overrides = analysis.pop("demo", {}) or {}
    if mode == "demo":
        analysis = _deep_update(analysis, demo_overrides)
    analysis["sources"] = sources
    analysis["mode"] = mode
    return analysis


@dataclass(frozen=True)
class Paths:
    """Every file location used by the pipeline."""

    root: Path
    mode: str = "real"

    @property
    def data(self) -> Path:
        return self.root / "data" if self.mode == "real" else self.root / "data" / "demo"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def processed(self) -> Path:
        return self.data / "processed"

    @property
    def results(self) -> Path:
        return self.root / "results" / self.mode

    @property
    def tables(self) -> Path:
        return self.results / "tables"

    @property
    def figures(self) -> Path:
        return self.results / "figures"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    # processed artifacts
    @property
    def localities(self) -> Path:
        return self.processed / "localities.parquet"

    @property
    def tiles(self) -> Path:
        return self.processed / "rwi_tiles.parquet"

    def ensure(self) -> Paths:
        for path in (self.raw, self.processed, self.tables, self.figures):
            path.mkdir(parents=True, exist_ok=True)
        return self


def get_paths(mode: str = "real", root: Path | None = None) -> Paths:
    return Paths(root=root or repo_root(), mode=mode).ensure()
