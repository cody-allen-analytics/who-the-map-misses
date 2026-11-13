"""Decision-centered evaluation: what a map's errors do to real allocation rules.

Two stylized rules:

* Targeting: select the localities predicted to be poorest until 20% of the population is
  covered; measure who among the truly poorest is left out (exclusion error), by group.
* Formula: split a fixed budget across municipalities in proportion to the estimated number of
  deprived people (population x deprivation rate). This mirrors the logic of Mexico's FAIS
  social-infrastructure fund, which allocates by extreme poverty weighted by deprivations; it is a
  simplification, not a reproduction of the legal formula.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def select_poorest(deprivation: np.ndarray, population: np.ndarray, share: float) -> np.ndarray:
    """Boolean mask of the most deprived units covering ``share`` of the population."""
    dep = np.asarray(deprivation, dtype=float)
    pop = np.asarray(population, dtype=float)
    order = np.argsort(-dep, kind="mergesort")
    cum = np.cumsum(pop[order])
    n_take = int(np.searchsorted(cum, share * pop.sum(), side="left")) + 1
    mask = np.zeros(dep.size, dtype=bool)
    mask[order[:n_take]] = True
    return mask


def targeting_errors(
    true_dep: np.ndarray, est_dep: np.ndarray, population: np.ndarray, groups, share: float
) -> pd.DataFrame:
    truly_poor = select_poorest(true_dep, population, share)
    selected = select_poorest(est_dep, population, share)
    pop = np.asarray(population, dtype=float)
    groups = pd.Series(groups).to_numpy()
    rows = []
    for g in [*pd.unique(groups[~pd.isna(groups)]), "All"]:
        m = np.ones(len(pop), bool) if g == "All" else groups == g
        poor_pop = pop[m & truly_poor].sum()
        rows.append(
            {
                "group": g,
                "truly_poorest_population": poor_pop,
                "exclusion_rate": pop[m & truly_poor & ~selected].sum() / poor_pop if poor_pop else np.nan,
                "selected_population": pop[m & selected].sum(),
            }
        )
    return pd.DataFrame(rows)


def formula_allocation(
    deprivation: np.ndarray, population: np.ndarray, municipality, budget: float
) -> pd.Series:
    deprived = (
        pd.Series(np.asarray(deprivation) * np.asarray(population))
        .groupby(pd.Series(municipality).to_numpy())
        .sum()
    )
    return budget * deprived / deprived.sum()


def allocation_gap(true_alloc: pd.Series, est_alloc: pd.Series, municipalities: pd.DataFrame) -> pd.DataFrame:
    """Pesos gained (+) or lost (-) by switching from census truth to the map, by group."""
    df = municipalities.join(true_alloc.rename("true"), how="inner").join(
        est_alloc.rename("est"), how="inner"
    )
    df["gap"] = df["est"] - df["true"]
    rows = []
    for g, part in df.groupby("indigenous"):
        rows.append(
            {
                "group": "Indigenous-majority municipalities" if g == 1 else "Other municipalities",
                "municipalities": len(part),
                "true_allocation": part["true"].sum(),
                "map_allocation": part["est"].sum(),
                "net_shift": part["gap"].sum(),
                "net_shift_pct": part["gap"].sum() / part["true"].sum() if part["true"].sum() else np.nan,
                "shift_per_capita": part["gap"].sum() / part["pop"].sum(),
            }
        )
    return pd.DataFrame(rows)


def shift_by_indigenous_share(
    true_alloc: pd.Series, est_alloc: pd.Series, municipalities: pd.DataFrame
) -> pd.DataFrame:
    """Net shift as % of true allocation, by quintile of municipal Indigenous share."""
    df = municipalities.join(true_alloc.rename("true"), how="inner").join(
        est_alloc.rename("est"), how="inner"
    )
    bins = [-0.001, 0.05, 0.2, 0.4, 0.7, 1.0]
    labels = ["<5%", "5-20%", "20-40%", "40-70%", "70%+"]
    df["ind_bin"] = pd.cut(df["ind_share"], bins=bins, labels=labels)
    out = df.groupby("ind_bin", observed=True).agg(
        municipalities=("true", "size"), true=("true", "sum"), est=("est", "sum"), pop=("pop", "sum")
    )
    out["net_shift_pct"] = (out["est"] - out["true"]) / out["true"]
    return out.reset_index()
