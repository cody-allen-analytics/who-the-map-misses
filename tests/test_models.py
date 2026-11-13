import numpy as np
import pandas as pd
import pytest

from mapaudit.conformal import conformal_quantile, coverage_by_group, fit_quantiles, quantiles_for
from mapaudit.ml import GBMWithEB, eb_group_effects
from mapaudit.sae import NestedFayHerriot
from mapaudit.survey import draw_survey


def _nested_data(seed=0, n_groups=300):
    rng = np.random.default_rng(seed)
    sizes = rng.integers(2, 10, n_groups)
    g = np.repeat(np.arange(n_groups), sizes)
    X = rng.normal(size=(len(g), 3))
    beta = np.array([0.3, 0.1, -0.05, 0.02])
    u = rng.normal(0, np.sqrt(0.004), n_groups)
    theta = beta[0] + X @ beta[1:] + u[g] + rng.normal(0, np.sqrt(0.002), len(g))
    psi = rng.uniform(0.0005, 0.004, len(g))
    y = theta + rng.normal(0, np.sqrt(psi))
    return X, y, psi, g, theta, beta


def test_fay_herriot_recovers_parameters_and_beats_alternatives():
    X, y, psi, g, theta, beta = _nested_data()
    fh = NestedFayHerriot().fit(X, y, psi, g)
    assert fh.converged
    assert fh.sigma2_u == pytest.approx(0.004, rel=0.35)
    assert fh.sigma2_v == pytest.approx(0.002, rel=0.35)
    np.testing.assert_allclose(fh.beta, beta, atol=0.01)
    mse_eblup = np.mean((fh.fitted_ - theta) ** 2)
    assert mse_eblup < np.mean((y - theta) ** 2)  # beats the direct estimate
    assert mse_eblup < np.mean((fh.predict(X) - theta) ** 2)  # beats the synthetic estimate


def test_unsampled_locality_inherits_municipality_effect():
    X, y, psi, g, *_ = _nested_data(seed=1)
    fh = NestedFayHerriot().fit(X, y, psi, g)
    x_new = np.zeros((2, 3))
    pred = fh.predict(x_new, groups=[g[0], "never-sampled"])
    assert pred[0] == pytest.approx(fh.beta[0] + fh.group_effects[g[0]])
    assert pred[1] == pytest.approx(fh.beta[0])


def test_eb_effects_shrink_toward_zero():
    rng = np.random.default_rng(2)
    groups = np.repeat(np.arange(50), 4)
    true = rng.normal(0, 0.5, 50)
    resid = true[groups] + rng.normal(0, 1, len(groups))
    effects = eb_group_effects(resid, groups)
    raw_means = pd.Series(resid).groupby(groups).mean()
    assert np.abs(pd.Series(effects)).sum() < np.abs(raw_means).sum()


def test_gbm_with_eb_runs():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(300, 4))
    groups = np.repeat(np.arange(30), 10)
    y = X[:, 0] + rng.normal(0, 0.1, 300)
    model = GBMWithEB({"max_iter": 30}, seed=0, n_folds=3).fit(X, y, groups, rng)
    assert model.oof_.shape == (300,) and not np.isnan(model.oof_).any()
    assert model.predict(X, groups).shape == (300,)


def test_conformal_quantile_definition():
    assert conformal_quantile(np.arange(1.0, 10.0), alpha=0.1) == 9.0
    assert conformal_quantile(np.arange(1.0, 5.0), alpha=0.1) == np.inf  # too few points for 90%


def test_mondrian_restores_coverage_for_noisy_group():
    rng = np.random.default_rng(4)
    n = 6000
    groups = np.where(rng.random(n) < 0.2, "minority", "majority")
    noise = np.where(groups == "minority", 3.0, 1.0)
    y = rng.normal(0, noise)
    pred = np.zeros(n)
    calib, test = np.arange(n) < n // 2, np.arange(n) >= n // 2
    q = fit_quantiles(np.abs(y[calib]), groups[calib], alpha=0.1)
    marginal = coverage_by_group(
        y[test], pred[test], np.full(test.sum(), q["__all__"]), groups[test]
    ).set_index("group")
    mondrian = coverage_by_group(y[test], pred[test], quantiles_for(groups[test], q), groups[test]).set_index(
        "group"
    )
    assert marginal.loc["All", "coverage"] == pytest.approx(0.9, abs=0.02)
    assert marginal.loc["minority", "coverage"] < 0.8
    assert mondrian.loc["minority", "coverage"] == pytest.approx(0.9, abs=0.03)


def test_survey_draw_shapes():
    rng = np.random.default_rng(5)
    n = 2000
    loc = pd.DataFrame(
        {
            "cvegeo": [f"{i:09d}" for i in range(n)],
            "cve_mun": [f"{i % 100:05d}" for i in range(n)],
            "POBTOT": rng.integers(50, 3000, n).astype(float),
            "VIVPARH_CV": rng.integers(5, 600, n).astype(float),
            **{c: rng.uniform(0, 1, n) for c in ["no_elec", "no_water", "no_drain", "dirt_floor"]},
        }
    )
    draw = draw_survey(
        loc,
        rng,
        n_municipalities=20,
        localities_per_municipality=4,
        dwellings_per_locality=20,
        min_dwellings=10,
    )
    s = draw.sample
    assert s["cve_mun"].nunique() <= 20 and s.groupby("cve_mun").size().max() <= 4
    assert s["y_obs"].between(0, 1).all() and (s["psi"] >= 0).all()
