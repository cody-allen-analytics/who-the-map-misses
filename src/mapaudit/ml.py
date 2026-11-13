"""Machine-learning challengers: gradient boosting, plus a version that borrows strength.

Plain gradient boosting predicts every locality from its own satellite features. Small area
estimation also uses the survey's information about *where* a locality is: an unsampled locality
in a sampled municipality inherits that municipality's estimated effect. ``GBMWithEB`` adds the
same idea to boosting: cross-fitted residuals give each sampled municipality an empirical-Bayes
shrunken effect that is added to predictions for every locality in it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


def make_gbm(params: dict, seed: int) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(loss="squared_error", random_state=seed, **params)


def group_folds(groups, n_folds: int, rng: np.random.Generator) -> np.ndarray:
    """Assign whole groups (municipalities) to folds so validation mimics unsampled areas."""
    labels = pd.unique(pd.Series(groups))
    fold_of = dict(zip(labels, rng.permutation(len(labels)) % n_folds, strict=True))
    return pd.Series(groups).map(fold_of).to_numpy()


def crossfit(
    fit_predict: Callable[[np.ndarray, np.ndarray], np.ndarray], n: int, folds: np.ndarray
) -> np.ndarray:
    """Out-of-fold predictions; ``fit_predict(train_idx, test_idx)`` returns predictions for test."""
    oof = np.full(n, np.nan)
    for k in np.unique(folds):
        test = np.flatnonzero(folds == k)
        train = np.flatnonzero(folds != k)
        oof[test] = fit_predict(train, test)
    return oof


def eb_group_effects(residuals: np.ndarray, groups) -> dict:
    """Empirical-Bayes municipality effects from residuals (method-of-moments variances)."""
    df = pd.DataFrame({"r": residuals, "g": pd.Series(groups).to_numpy()})
    stats = df.groupby("g")["r"].agg(["mean", "var", "size"])
    within = stats.loc[stats["size"] > 1]
    if within.empty:
        return dict.fromkeys(stats.index, 0.0)
    sigma2_w = float(((within["size"] - 1) * within["var"]).sum() / (within["size"] - 1).sum())
    tau2 = max(0.0, float(stats["mean"].var(ddof=1) - np.mean(sigma2_w / stats["size"])))
    shrink = tau2 / (tau2 + sigma2_w / stats["size"])
    return (shrink * stats["mean"]).to_dict()


@dataclass
class GBMWithEB:
    params: dict
    seed: int
    n_folds: int = 5
    use_eb: bool = True
    model: HistGradientBoostingRegressor | None = None
    effects: dict = field(default_factory=dict)
    oof_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray, groups, rng: np.random.Generator) -> GBMWithEB:
        X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
        folds = group_folds(groups, self.n_folds, rng)

        def fit_predict(train, test):
            return make_gbm(self.params, self.seed).fit(X[train], y[train]).predict(X[test])

        self.oof_ = crossfit(fit_predict, len(y), folds)
        self.model = make_gbm(self.params, self.seed).fit(X, y)
        self.effects = eb_group_effects(y - self.oof_, groups) if self.use_eb else {}
        return self

    def predict(self, X: np.ndarray, groups=None) -> np.ndarray:
        pred = self.model.predict(np.asarray(X, dtype=float))
        if self.use_eb and groups is not None:
            pred = pred + pd.Series(groups).map(self.effects).fillna(0.0).to_numpy()
        return pred
