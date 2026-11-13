"""Small area estimation: a Fay-Herriot model with a municipality random effect.

For sampled locality i in municipality j::

    y_ij = x_ij' beta + u_j + v_ij + e_ij
    u_j ~ N(0, s2_u)   municipality effect     (borrowed by unsampled localities in sampled municipalities)
    v_ij ~ N(0, s2_v)  locality effect
    e_ij ~ N(0, psi_ij) sampling error with known variance from the survey design

The variance components are estimated by REML. Each municipality's covariance block is
s2_u * 11' + diag(s2_v + psi), whose inverse and determinant have closed forms
(Sherman-Morrison), so the likelihood is evaluated with group sums instead of matrix inverses.

EBLUP predictions:
    sampled locality:                    x'b + u_j + v_ij
    unsampled locality, sampled mun.:    x'b + u_j
    unsampled municipality:              x'b          (the "synthetic" estimator)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _add_intercept(X: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(X)), X])


@dataclass
class NestedFayHerriot:
    sigma2_u: float = np.nan
    sigma2_v: float = np.nan
    beta: np.ndarray | None = None
    converged: bool = False
    group_effects: dict = field(default_factory=dict)
    fitted_: np.ndarray | None = None

    def _pieces(self, theta, X, y, psi, g, n_groups):
        s2u, s2v = np.exp(theta)
        d = s2v + psi
        w = 1.0 / d
        s = np.bincount(g, weights=w, minlength=n_groups)
        c = s2u / (1.0 + s2u * s)
        Xw = X * w[:, None]
        a = np.zeros((n_groups, X.shape[1]))
        np.add.at(a, g, Xw)
        A = X.T @ Xw - (a.T * c) @ a
        yw = y * w
        by = np.bincount(g, weights=yw, minlength=n_groups)
        b = X.T @ yw - a.T @ (c * by)
        beta = np.linalg.solve(A, b)
        r = y - X @ beta
        br = np.bincount(g, weights=r * w, minlength=n_groups)
        quad = float(np.sum(r * r * w) - np.sum(c * br**2))
        logdet_v = float(np.sum(np.log(d)) + np.sum(np.log1p(s2u * s)))
        return beta, A, quad, logdet_v, r, br, s, c, d, s2u, s2v

    def fit(self, X: np.ndarray, y: np.ndarray, psi: np.ndarray, groups) -> NestedFayHerriot:
        X = _add_intercept(np.asarray(X, dtype=float))
        y = np.asarray(y, dtype=float)
        psi = np.asarray(psi, dtype=float)
        codes, labels = pd.factorize(pd.Series(groups), sort=False)
        n_groups = len(labels)

        def neg_reml(theta):
            _, A, quad, logdet_v, *_ = self._pieces(theta, X, y, psi, codes, n_groups)
            _, logdet_a = np.linalg.slogdet(A)
            return 0.5 * (logdet_v + quad + logdet_a)

        start = np.log(np.full(2, max(np.var(y) / 4, 1e-6)))
        result = minimize(neg_reml, start, method="L-BFGS-B", bounds=[(-25.0, 5.0)] * 2)
        self.converged = bool(result.success)
        beta, _, _, _, r, br, s, c, d, s2u, s2v = self._pieces(result.x, X, y, psi, codes, n_groups)
        self.beta, self.sigma2_u, self.sigma2_v = beta, float(s2u), float(s2v)
        u = s2u * br / (1.0 + s2u * s)
        v = s2v * (r - c[codes] * br[codes]) / d
        self.group_effects = dict(zip(labels, u, strict=True))
        self.fitted_ = X @ beta + u[codes] + v
        return self

    def predict(self, X: np.ndarray, groups=None) -> np.ndarray:
        """Synthetic part plus the municipality effect where the municipality was sampled."""
        if self.beta is None:
            raise RuntimeError("Model is not fitted.")
        pred = _add_intercept(np.asarray(X, dtype=float)) @ self.beta
        if groups is not None:
            effects = pd.Series(groups).map(self.group_effects).fillna(0.0).to_numpy()
            pred = pred + effects
        return pred
