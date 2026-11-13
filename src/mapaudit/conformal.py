"""Split conformal prediction intervals, marginal and group-conditional ("Mondrian").

A marginal 90% interval covers the truth 90% of the time *on average*, which can hide 75%
coverage for a minority group offset by 93% for the majority. Mondrian conformal prediction
calibrates a separate quantile within each group, so the guarantee holds group by group
(under exchangeability within groups).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mapaudit.metrics import interval_score


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    scores = np.sort(np.asarray(scores, dtype=float)[~np.isnan(scores)])
    n = scores.size
    if n == 0:
        return np.inf
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return float(scores[k - 1]) if k <= n else np.inf


def fit_quantiles(scores: np.ndarray, groups, alpha: float) -> dict:
    """Marginal quantile under key '__all__' plus one quantile per group."""
    scores = np.asarray(scores, dtype=float)
    groups = pd.Series(groups).to_numpy()
    out = {"__all__": conformal_quantile(scores, alpha)}
    for g in pd.unique(groups):
        if pd.isna(g):
            continue
        out[g] = conformal_quantile(scores[groups == g], alpha)
    return out


def quantiles_for(keys, quantiles: dict, fallback_keys=None) -> np.ndarray:
    """Per-row quantile: the row's own cell, else its fallback cell, else the marginal quantile."""
    q = pd.Series(keys).map(quantiles)
    if fallback_keys is not None:
        q = q.fillna(pd.Series(fallback_keys).map(quantiles))
    return q.fillna(quantiles["__all__"]).to_numpy(dtype=float)


def coverage_by_group(
    y_true: np.ndarray, pred: np.ndarray, q: np.ndarray, groups, alpha: float | None = None
) -> pd.DataFrame:
    """Coverage, mean width and (if ``alpha`` is given) interval score of pred +/- q, by group."""
    groups = pd.Series(groups).to_numpy()
    y_true, pred, q = (np.asarray(v, dtype=float) for v in (y_true, pred, q))
    covered = np.abs(y_true - pred) <= q
    width = 2 * q
    rows = []
    keys = [g for g in pd.unique(groups) if not pd.isna(g)]
    for g in [*keys, "All"]:
        m = np.ones(len(y_true), bool) if g == "All" else groups == g
        row = {"group": g, "coverage": covered[m].mean(), "width": width[m].mean(), "n": int(m.sum())}
        if alpha is not None:
            row["interval_score"] = interval_score(y_true[m], pred[m] - q[m], pred[m] + q[m], alpha)
        rows.append(row)
    return pd.DataFrame(rows)
