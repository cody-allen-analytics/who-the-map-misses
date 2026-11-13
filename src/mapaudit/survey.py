"""Simulate the household survey a real poverty-mapping exercise would have.

The census gives the true deprivation rate everywhere, so it can act as a "pseudo-census" in the
style of Corral, Henderson & Segovia (2025): draw a realistic survey from it, train models on the
survey only, and score their predictions against the full census.

Design: (1) municipalities drawn with probability proportional to population, (2) localities drawn
at random within each selected municipality, (3) dwellings drawn without replacement within each
locality. Each housing deprivation is drawn independently (hypergeometric), so the sampling
variance of the composite rate has a closed form that the Fay-Herriot model can use.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mapaudit.labels import HOUSING_DEPRIVATIONS


@dataclass
class SurveyDraw:
    sample: pd.DataFrame  # one row per sampled locality: cvegeo, cve_mun, y_obs, psi, n
    municipalities: np.ndarray  # sampled municipality codes


def draw_survey(
    loc: pd.DataFrame,
    rng: np.random.Generator,
    n_municipalities: int,
    localities_per_municipality: int,
    dwellings_per_locality: int,
    min_dwellings: int,
    eligible: pd.Series | None = None,
) -> SurveyDraw:
    frame = loc if eligible is None else loc[eligible]
    frame = frame[frame["VIVPARH_CV"] >= min_dwellings]
    frame = frame.dropna(subset=HOUSING_DEPRIVATIONS)

    mun_pop = frame.groupby("cve_mun")["POBTOT"].sum()
    n_mun = min(n_municipalities, len(mun_pop))
    chosen = rng.choice(
        mun_pop.index.to_numpy(), size=n_mun, replace=False, p=(mun_pop / mun_pop.sum()).to_numpy()
    )
    pool = frame[frame["cve_mun"].isin(chosen)].copy()
    pool["_key"] = rng.random(len(pool))
    pool["_rank"] = pool.groupby("cve_mun")["_key"].rank(method="first")
    sample = pool[pool["_rank"] <= localities_per_municipality].copy()

    N = sample["VIVPARH_CV"].round().astype(int).to_numpy()
    n = np.minimum(dwellings_per_locality, N)
    fpc = np.where(N > 1, (N - n) / np.maximum(N - 1, 1), 0.0)
    p_hat = np.zeros((len(sample), len(HOUSING_DEPRIVATIONS)))
    var = np.zeros_like(p_hat)
    for k, col in enumerate(HOUSING_DEPRIVATIONS):
        K = np.clip(np.round(sample[col].to_numpy() * N), 0, N).astype(int)
        x = rng.hypergeometric(K, N - K, n)
        p_hat[:, k] = x / n
        p_smooth = (x + 0.5) / (n + 1)  # avoids zero variance when x is 0 or n
        var[:, k] = p_smooth * (1 - p_smooth) / n * fpc
    m = len(HOUSING_DEPRIVATIONS)
    sample["y_obs"] = p_hat.mean(axis=1)
    sample["psi"] = var.sum(axis=1) / m**2
    sample["n_dwellings_sampled"] = n
    keep = ["cvegeo", "cve_mun", "y_obs", "psi", "n_dwellings_sampled"]
    return SurveyDraw(sample=sample[keep].reset_index(drop=True), municipalities=np.asarray(chosen))
