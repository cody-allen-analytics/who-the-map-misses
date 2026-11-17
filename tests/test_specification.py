"""Why H2 conditions on the true wealth decile, and why that is safe.

Rank error is map percentile minus census percentile, and maps compress the extremes, so the error
depends on where a tile sits within its decile. If Indigenous tiles sat systematically lower within
deciles, decile fixed effects could leave some of that compression in the Indigenous coefficient.
This test builds worlds where the map's errors ignore group entirely (the true H2 effect is zero)
while Indigenous tiles are poorer, runs the real specification on them, and checks that the
coefficient is centred on zero rather than pushed toward the hypothesis.
"""

import numpy as np
import pandas as pd

from mapaudit.audit import audit_regressions
from mapaudit.labels import weighted_percentile_rank


def _group_blind_world(rng: np.random.Generator, n: int = 3000, n_mun: int = 300) -> pd.DataFrame:
    mun = rng.integers(0, n_mun, n)
    ind = np.clip(rng.beta(0.6, 2.0, n_mun)[mun] + rng.normal(0, 0.12, n), 0, 1)
    truth = -1.1 * ind + rng.normal(0, 1, n)  # Indigenous places are poorer on average
    noisy_map = truth + rng.normal(0, 0.6, n)  # same noise for every group: separation holds
    pop = np.exp(rng.normal(4.5, 1.0, n))
    tiles = pd.DataFrame(
        {
            "pop": pop,
            "ind_share": ind,
            "cve_mun": mun,
            "cve_ent": mun % 8,
            "log_pop": np.log1p(pop),
            "urban_share": 0.0,
            "log_dist_city": rng.normal(3, 1, n),
            "altitude_km": rng.uniform(0, 2.5, n),
        }
    )
    tiles["truth_pct"] = weighted_percentile_rank(truth, pop)
    tiles["rank_error"] = 100 * (weighted_percentile_rank(noisy_map, pop) - tiles["truth_pct"])
    tiles["truth_decile"] = np.clip(np.floor(tiles["truth_pct"] * 10).astype(int) + 1, 1, 10)
    return tiles


def test_decile_conditioning_does_not_manufacture_an_indigenous_effect():
    rng = np.random.default_rng(2026)
    coefs = [audit_regressions(_group_blind_world(rng)).iloc[-1]["coef"] for _ in range(30)]
    # One world's coefficient has a standard deviation of about 2 points; the mean of 30 about 0.4.
    assert abs(np.mean(coefs)) < 1.0
