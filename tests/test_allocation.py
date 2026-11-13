import numpy as np
import pandas as pd
import pytest

from mapaudit.allocation import allocation_gap, formula_allocation, select_poorest, targeting_errors


def test_select_poorest_covers_requested_share():
    dep = np.array([0.9, 0.1, 0.5, 0.7])
    pop = np.array([10, 40, 30, 20])
    mask = select_poorest(dep, pop, share=0.25)
    assert mask.tolist() == [True, False, False, True]  # 10 + 20 people >= 25% of 100
    assert pop[mask].sum() >= 25


def test_perfect_prediction_has_no_exclusion():
    rng = np.random.default_rng(0)
    dep, pop = rng.uniform(size=200), rng.integers(1, 100, 200)
    groups = np.where(rng.random(200) < 0.3, "Indigenous", "Non-Indigenous")
    out = targeting_errors(dep, dep, pop, groups, share=0.2).set_index("group")
    assert (out["exclusion_rate"] == 0).all()


def test_formula_allocation_sums_to_budget_and_gap_nets_to_zero():
    rng = np.random.default_rng(1)
    mun = np.repeat(["01001", "01002", "01003"], 10)
    pop = rng.integers(10, 500, 30)
    true = formula_allocation(rng.uniform(size=30), pop, mun, budget=1e6)
    est = formula_allocation(rng.uniform(size=30), pop, mun, budget=1e6)
    assert true.sum() == pytest.approx(1e6)
    munis = pd.DataFrame(
        {"pop": [100, 200, 300], "ind_share": [0.6, 0.1, 0.0], "indigenous": [1, 0, 0]},
        index=["01001", "01002", "01003"],
    )
    gap = allocation_gap(true, est, munis)
    assert gap["net_shift"].sum() == pytest.approx(0, abs=1e-6)
