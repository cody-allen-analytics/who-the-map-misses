from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]

SMALL_SYNTHETIC = {
    "n_states": 4,
    "n_municipalities": 60,
    "mean_localities_per_municipality": 30,
    "rwi_indigenous_bias_sd": 0.6,
    "rwi_coverage_indigenous_logit": -0.8,
    "embedding_indigenous_shift": 0.6,
}


@pytest.fixture
def small_settings() -> dict:
    return dict(SMALL_SYNTHETIC)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A throwaway repository root with a shrunken demo configuration."""
    shutil.copytree(REPO / "config", tmp_path / "config")
    (tmp_path / "docs").mkdir()
    cfg_path = tmp_path / "config" / "analysis.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["demo"]["synthetic"] = dict(SMALL_SYNTHETIC)
    cfg["demo"]["audit"] = {"bootstrap_reps": 20}
    cfg["demo"]["survey"] = {"n_municipalities": 30, "localities_per_municipality": 5, "replications": 2}
    cfg["demo"]["models"] = {"cv_folds": 3, "sae_n_components": 8, "gbm": {"max_iter": 40}}
    cfg_path.write_text(yaml.safe_dump(cfg))
    return tmp_path
