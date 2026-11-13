"""Evaluation metrics, chosen to match the decisions the maps feed.

The rules (documented in docs/methods.md, "Evaluation metrics"):

* **Decision first.** The budget formula adds up predicted rates, so predictions must get the *mean*
  right. Squared error is the loss whose best prediction is the mean, so RMSE is the primary accuracy
  loss and signed bias the primary fairness measure. MAE (best prediction: the median) is secondary.
* **No MAPE or MSLE on rates.** MAPE divides by deprivation rates that are often zero and weights the
  least-deprived places most; on a 0-1 rate, MSLE counts an error at 100% deprivation a quarter as much
  as the same error at 0%. Relative errors are used only for municipal allocations, which are never zero.
* **People and places.** Every error is reported population-weighted (per person) and unweighted
  (per community).
* **Compression is measured, not assumed away.** RMSE rewards predictions pulled toward the average, so
  the calibration slope, the variance ratio and bias by true decile are reported alongside it.
* **Honest denominators.** Metrics exist only where the truth is known; who is left out is reported.
* **Paired comparisons.** Models are compared on the same survey draws, replication by replication.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests


def _weights(weights, n: int) -> np.ndarray:
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    return w / w.sum()


def weighted_metrics(err: np.ndarray, weights=None) -> dict:
    """Signed bias, MAE and RMSE of prediction errors (prediction minus truth)."""
    err = np.asarray(err, dtype=float)
    w = _weights(weights, err.size)
    return {
        "bias": float(np.sum(w * err)),
        "mae": float(np.sum(w * np.abs(err))),
        "rmse": float(np.sqrt(np.sum(w * err**2))),
    }


def _wmean(x: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(w * x))


def calibration_slope(truth: np.ndarray, pred: np.ndarray, weights=None) -> float:
    """Slope of truth regressed on prediction (weighted least squares).

    1 = calibrated; above 1 = predictions are compressed toward the average (the truth varies more than
    the predictions do); below 1 = predictions exaggerate differences between places.
    """
    truth, pred = np.asarray(truth, dtype=float), np.asarray(pred, dtype=float)
    w = _weights(weights, truth.size)
    pc = pred - _wmean(pred, w)
    var_p = _wmean(pc**2, w)
    if var_p <= 0:
        return float("nan")
    return float(_wmean(pc * (truth - _wmean(truth, w)), w) / var_p)


def variance_ratio(truth: np.ndarray, pred: np.ndarray, weights=None) -> float:
    """Variance of predictions over variance of the truth; below 1 means compressed predictions."""
    truth, pred = np.asarray(truth, dtype=float), np.asarray(pred, dtype=float)
    w = _weights(weights, truth.size)
    var_t = _wmean((truth - _wmean(truth, w)) ** 2, w)
    var_p = _wmean((pred - _wmean(pred, w)) ** 2, w)
    return float(var_p / var_t) if var_t > 0 else float("nan")


def error_profile(truth: np.ndarray, pred: np.ndarray, weights=None) -> dict:
    """Everything reported for one model, group and weighting."""
    truth, pred = np.asarray(truth, dtype=float), np.asarray(pred, dtype=float)
    return {
        **weighted_metrics(pred - truth, weights),
        "calibration_slope": calibration_slope(truth, pred, weights),
        "variance_ratio": variance_ratio(truth, pred, weights),
        "n": int(truth.size),
    }


def interval_score(y: np.ndarray, lo: np.ndarray, hi: np.ndarray, alpha: float) -> float:
    """Mean interval (Winkler) score: width plus 2/alpha times the distance by which the truth misses.

    Lower is better. Unlike coverage and width reported separately, it rewards intervals that are
    narrow *and* honest, and it is a proper scoring rule for central (1 - alpha) intervals.
    """
    y, lo, hi = (np.asarray(v, dtype=float) for v in (y, lo, hi))
    width = hi - lo
    below = (2 / alpha) * np.clip(lo - y, 0, None)
    above = (2 / alpha) * np.clip(y - hi, 0, None)
    return float(np.mean(width + below + above))


def misallocation_share(true_alloc: pd.Series, est_alloc: pd.Series) -> float:
    """Share of the budget that goes to the wrong municipalities: half the sum of |share differences|."""
    true_s = true_alloc / true_alloc.sum()
    est_s = (est_alloc / est_alloc.sum()).reindex(true_s.index).fillna(0.0)
    return float(0.5 * np.abs(est_s - true_s).sum())


def allocation_errors(
    true_alloc: pd.Series, est_alloc: pd.Series, municipalities: pd.DataFrame
) -> pd.DataFrame:
    """Misallocated share of the budget, and each municipality's relative error, by municipality group.

    Relative (percentage) error is appropriate here, unlike for locality rates, because municipal
    allocations are never close to zero.
    """
    df = municipalities.join(true_alloc.rename("true"), how="inner").join(
        est_alloc.rename("est"), how="inner"
    )
    df = df[df["true"] > 0]
    df["ape"] = (df["est"] - df["true"]).abs() / df["true"]
    rows = [
        {
            "group": "All",
            "misallocation_share": misallocation_share(true_alloc, est_alloc),
            "ape_median": df["ape"].median(),
            "ape_mean": df["ape"].mean(),
            "municipalities": len(df),
        }
    ]
    for flag, name in ((1, "Indigenous-majority municipalities"), (0, "Other municipalities")):
        part = df[df["indigenous"] == flag]
        rows.append(
            {
                "group": name,
                "misallocation_share": np.nan,
                "ape_median": part["ape"].median(),
                "ape_mean": part["ape"].mean(),
                "municipalities": len(part),
            }
        )
    return pd.DataFrame(rows)


def decile_bias(
    truth: np.ndarray, pred: np.ndarray, weights: np.ndarray, groups: np.ndarray, deciles: np.ndarray
) -> pd.DataFrame:
    """Weighted mean error (prediction minus truth) by true decile and group: the compression profile."""
    df = pd.DataFrame(
        {"err": np.asarray(pred) - np.asarray(truth), "w": weights, "group": groups, "decile": deciles}
    )
    df["wx"] = df["err"] * df["w"]
    out = df.groupby(["decile", "group"]).agg(wx=("wx", "sum"), w=("w", "sum"), n=("w", "size")).reset_index()
    out["bias"] = out["wx"] / out["w"]
    return out[["decile", "group", "bias", "n"]]


def one_sided_p(coef: float, p_two_sided: float, direction: str = "greater") -> float:
    """One-sided p-value from a symmetric two-sided test."""
    if direction not in ("greater", "less"):
        raise ValueError("direction must be 'greater' or 'less'")
    agrees = coef > 0 if direction == "greater" else coef < 0
    return p_two_sided / 2 if agrees else 1 - p_two_sided / 2


def holm(pvalues) -> np.ndarray:
    """Holm-adjusted p-values (controls the family-wise error rate)."""
    return multipletests(np.asarray(pvalues, dtype=float), method="holm")[1]


def paired_contrast(
    metrics: pd.DataFrame,
    value: str,
    model_a: str,
    model_b: str,
    group: str,
    weighting: str = "people",
    absolute: bool = False,
) -> dict:
    """Replication-by-replication difference (model_a minus model_b) in one metric, with its 95% range.

    Both models are scored on the same survey draws, so the paired difference removes the noise that
    comes from the draw itself.
    """
    sub = metrics[(metrics["group"] == group) & (metrics["weighting"] == weighting)]
    wide = sub.pivot(index="rep", columns="model", values=value)
    if model_a not in wide or model_b not in wide:
        return {}
    a, b = wide[model_a], wide[model_b]
    diff = (a.abs() - b.abs()) if absolute else (a - b)
    return {
        "metric": f"|{value}|" if absolute else value,
        "group": group,
        "weighting": weighting,
        "model_a": model_a,
        "model_b": model_b,
        "mean_difference": float(diff.mean()),
        "p025": float(diff.quantile(0.025)),
        "p975": float(diff.quantile(0.975)),
        "share_a_worse": float((diff > 0).mean()),
        "replications": int(diff.size),
    }


def evaluation_coverage(scope: pd.DataFrame, evaluated: pd.Series, label: str) -> pd.DataFrame:
    """Share of the in-scope population that a metric actually covers, by group.

    Localities whose census data are suppressed have no known Indigenous status either; they get their
    own row instead of silently dropping out of the denominator.
    """
    status = pd.to_numeric(scope["indigenous"], errors="coerce").to_numpy(dtype=float)
    names = np.where(
        np.isnan(status), "Unknown (suppressed data)", np.where(status == 1, "Indigenous", "Non-Indigenous")
    )
    rows = []
    for name in ("Indigenous", "Non-Indigenous", "Unknown (suppressed data)"):
        mask = names == name
        if not mask.any():
            continue
        part = scope.loc[mask]
        rows.append(
            {
                "analysis": label,
                "group": name,
                "population_in_scope": float(part["POBTOT"].sum()),
                "population_evaluated": float(part.loc[evaluated.loc[part.index], "POBTOT"].sum()),
            }
        )
    out = pd.DataFrame(rows)
    out["share_evaluated"] = out["population_evaluated"] / out["population_in_scope"]
    return out
