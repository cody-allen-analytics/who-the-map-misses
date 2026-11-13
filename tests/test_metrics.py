"""Tests for the evaluation metrics and the pre-registered tests."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mapaudit import audit as audit_mod
from mapaudit.config import load_config
from mapaudit.metrics import (
    allocation_errors,
    calibration_slope,
    decile_bias,
    evaluation_coverage,
    holm,
    interval_score,
    misallocation_share,
    one_sided_p,
    paired_contrast,
    variance_ratio,
    weighted_metrics,
)
from mapaudit.pipeline import _decile_gap, assemble, confirmatory_tests
from mapaudit.synthetic import generate


def test_weighted_metrics_known_values():
    m = weighted_metrics(np.array([1.0, -1.0, 2.0]), np.array([1.0, 1.0, 2.0]))
    assert m["bias"] == pytest.approx(1.0)
    assert m["mae"] == pytest.approx(1.5)
    assert m["rmse"] == pytest.approx(np.sqrt(2.5))


def test_compression_is_detected():
    rng = np.random.default_rng(0)
    truth = rng.uniform(0, 1, 5000)
    compressed = truth.mean() + 0.5 * (truth - truth.mean())  # predictions pulled halfway to the average
    assert calibration_slope(truth, compressed) == pytest.approx(2.0)
    assert variance_ratio(truth, compressed) == pytest.approx(0.25)
    assert calibration_slope(truth, truth) == pytest.approx(1.0)


def test_interval_score_rewards_honest_narrow_intervals():
    y = np.array([0.5, 0.5])
    assert interval_score(y, y - 0.1, y + 0.1, alpha=0.1) == pytest.approx(0.2)  # covered: score = width
    # a miss by 0.1 adds 2/alpha * 0.1 = 2.0
    assert interval_score(np.array([0.7]), np.array([0.4]), np.array([0.6]), alpha=0.1) == pytest.approx(2.2)


def test_misallocation_share_bounds():
    a = pd.Series({"m1": 50.0, "m2": 50.0})
    assert misallocation_share(a, a) == pytest.approx(0.0)
    assert misallocation_share(a, pd.Series({"m1": 100.0, "m2": 0.0})) == pytest.approx(0.5)
    munis = pd.DataFrame({"pop": [1, 1], "indigenous": [1, 0]}, index=["m1", "m2"])
    errs = allocation_errors(a, pd.Series({"m1": 75.0, "m2": 25.0}), munis).set_index("group")
    assert errs.loc["All", "misallocation_share"] == pytest.approx(0.25)
    assert errs.loc["Indigenous-majority municipalities", "ape_median"] == pytest.approx(0.5)


def test_one_sided_p_and_holm():
    assert one_sided_p(2.0, 0.04, "greater") == pytest.approx(0.02)
    assert one_sided_p(-2.0, 0.04, "greater") == pytest.approx(0.98)
    assert holm([0.01, 0.04]) == pytest.approx([0.02, 0.04])


def test_paired_contrast_uses_same_replications():
    metrics = pd.DataFrame({
        "rep": [0, 0, 1, 1],
        "model": ["A", "B"] * 2,
        "group": "Indigenous",
        "weighting": "people",
        "bias": [-0.03, 0.01, -0.05, -0.02],
    })  # fmt: skip
    out = paired_contrast(metrics, "bias", "A", "B", "Indigenous", absolute=True)
    assert out["mean_difference"] == pytest.approx(((0.03 - 0.01) + (0.05 - 0.02)) / 2)
    assert out["share_a_worse"] == 1.0


def test_decile_bias_and_evaluation_coverage():
    out = decile_bias(
        np.array([0.1, 0.9]), np.array([0.2, 0.7]), np.ones(2), np.array(["x", "x"]), np.array([1, 10])
    )
    assert out.set_index("decile").loc[10, "bias"] == pytest.approx(-0.2)
    scope = pd.DataFrame({"indigenous": [1, 0, np.nan], "POBTOT": [10.0, 30.0, 5.0]})
    cov = evaluation_coverage(scope, pd.Series([True, False, False]), "test").set_index("group")
    assert cov.loc["Indigenous", "share_evaluated"] == 1.0
    assert cov.loc["Unknown (suppressed data)", "population_in_scope"] == 5.0


def test_confirmatory_tests_apply_holm():
    coverage_reg = pd.DataFrame([{"coef": -0.05, "ci_low": -0.08, "ci_high": -0.02, "p_value": 0.01}])
    audit_regs = pd.DataFrame(
        [{"coef": 3.0, "ci_low": 0.5, "ci_high": 5.5, "p_value": 0.06, "p_one_sided": 0.03}]
    )
    table = confirmatory_tests(coverage_reg, audit_regs).set_index("hypothesis")
    assert table.loc["H1 coverage", "p_holm"] == pytest.approx(0.02)
    assert table.loc["H2 rank bias", "p_holm"] == pytest.approx(0.03)
    assert bool(table.loc["H2 rank bias", "supported_at_5pct"])


def test_calibration_view_shows_gap_without_group_bias(tmp_path, small_settings):
    """With group-blind map errors, the separation view finds ~no gap but the calibration view does,
    because the groups differ in average wealth (the base-rate effect the methods page explains)."""
    settings = {**small_settings, "n_municipalities": 100, "rwi_indigenous_bias_sd": 0.0}
    generate(Path(tmp_path), settings, seed=12)
    _, tiles, _, _ = assemble(Path(tmp_path), load_config("demo"))
    gaps = {}
    for by in ("truth_decile", "map_decile"):
        means = audit_mod._weighted_group_means(tiles, by).reset_index()
        means["group"] = np.where(means["indigenous"] == 1, "Indigenous", "Non-Indigenous")
        gaps[by] = _decile_gap(means, by=by)
    assert gaps["map_decile"] > gaps["truth_decile"] + 2
