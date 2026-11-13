"""The audit's own validity checks: it must find a planted bias and must not invent one."""

import pytest

from mapaudit.audit import audit_regressions, coverage_regression
from mapaudit.config import load_config
from mapaudit.pipeline import assemble
from mapaudit.synthetic import generate


@pytest.mark.parametrize("bias, should_detect", [(0.6, True), (0.0, False)])
def test_audit_detects_planted_bias_only_when_present(tmp_path, small_settings, bias, should_detect):
    settings = {**small_settings, "n_municipalities": 100, "rwi_indigenous_bias_sd": bias}
    generate(tmp_path, settings, seed=11)
    cfg = load_config("demo")
    _, tiles, _, _ = assemble(tmp_path, cfg)
    main = audit_regressions(tiles).iloc[-1]
    excludes_zero = main["ci_low"] > 0 or main["ci_high"] < 0
    assert excludes_zero == should_detect
    if should_detect:
        assert main["coef"] > 0


def test_coverage_gap_is_detected(tmp_path, small_settings):
    settings = {**small_settings, "n_municipalities": 100, "rwi_coverage_indigenous_logit": -1.5}
    generate(tmp_path, settings, seed=12)
    loc, _, _, _ = assemble(tmp_path, load_config("demo"))
    assert coverage_regression(loc)["ci_high"].iloc[0] < 0
