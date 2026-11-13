"""Ground-truth labels built from the census.

The project's central measurement question is *which* notion of poverty a map should be judged
against. Three labels are built from the same census table:

* ``wealth_dhs_like``: first principal component of durable goods and housing quality, the
  construction used by DHS wealth indexes, which is what Meta's RWI was trained to predict.
* ``dep_infra``: average share of dwellings lacking electricity, piped water, drainage, or a
  finished floor; an infrastructure-deprivation rate with a direct policy reading.
* ``marg_index``: a CONAPO-style marginalization index (education, services, crowding,
  refrigerator), rebuilt from ITER with a first principal component.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DURABLES = [
    "has_fridge",
    "has_washer",
    "has_car",
    "has_pc",
    "has_cell",
    "has_internet",
    "has_tv",
    "has_micro",
]
HOUSING_DEPRIVATIONS = ["no_elec", "no_water", "no_drain", "dirt_floor"]
MARGINALIZATION = [
    "illiterate", "no_basic_ed", "no_drain", "no_elec", "no_water", "dirt_floor", "crowding", "no_fridge",
]  # fmt: skip

LABELS = {
    # name: (column, higher_means_poorer)
    "wealth_dhs_like": ("wealth_dhs_like", False),
    "dep_infra": ("dep_infra", True),
    "marg_index": ("marg_index", True),
}


def weighted_percentile_rank(values: np.ndarray | pd.Series, weights: np.ndarray | pd.Series) -> np.ndarray:
    """Population-weighted percentile rank in [0, 1] (midpoint convention); NaN stays NaN."""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    out = np.full(values.shape, np.nan)
    ok = ~np.isnan(values) & ~np.isnan(weights) & (weights > 0)
    if not ok.any():
        return out
    v, w = values[ok], weights[ok]
    order = np.argsort(v, kind="mergesort")
    cum = np.cumsum(w[order])
    total = cum[-1]
    mid = (cum - w[order] / 2) / total
    ranks = np.empty_like(mid)
    ranks[order] = mid
    # Ties share the average rank so identical values get identical percentiles.
    tied = pd.Series(ranks).groupby(v).transform("mean").to_numpy()
    out[ok] = tied
    return out


def first_component(df: pd.DataFrame, columns: list[str], reference: str) -> tuple[pd.Series, pd.Series]:
    """First principal component of standardized columns, signed to correlate with ``reference``.

    Returns (scores, loadings). Rows with any missing input get NaN.
    """
    complete = df[columns].dropna()
    z = (complete - complete.mean()) / complete.std(ddof=0).replace(0, 1)
    # PCA via SVD of the standardized matrix.
    _, _, vt = np.linalg.svd(z.to_numpy(), full_matrices=False)
    loadings = pd.Series(vt[0], index=columns)
    if loadings[reference] < 0:
        loadings = -loadings
    scores = pd.Series(np.nan, index=df.index)
    scores.loc[complete.index] = z.to_numpy() @ loadings.to_numpy()
    return scores, loadings


def build_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Add the three labels and their population-weighted percentile ranks."""
    out = df.copy()
    usable = out["has_dwelling_data"]
    out["has_elec"] = 1 - out["no_elec"]
    out["has_water"] = 1 - out["no_water"]
    out["has_drain"] = 1 - out["no_drain"]
    out["finished_floor"] = 1 - out["dirt_floor"]

    wealth_cols = [*DURABLES, "has_elec", "has_water", "has_drain", "finished_floor"]
    wealth, wealth_loadings = first_component(out.loc[usable], wealth_cols, reference="has_fridge")
    marg, marg_loadings = first_component(out.loc[usable], MARGINALIZATION, reference="illiterate")
    out["wealth_dhs_like"] = wealth.reindex(out.index)
    out["marg_index"] = marg.reindex(out.index)
    out["dep_infra"] = out[HOUSING_DEPRIVATIONS].mean(axis=1, skipna=False).where(usable)

    weights = out["POBTOT"]
    out["wealth_pct"] = weighted_percentile_rank(out["wealth_dhs_like"], weights)
    out["dep_infra_pct"] = weighted_percentile_rank(out["dep_infra"], weights)
    out["marg_pct"] = weighted_percentile_rank(out["marg_index"], weights)
    return out, {"wealth_dhs_like": wealth_loadings, "marg_index": marg_loadings}


def label_choice_table(
    loc: pd.DataFrame, group: str = "indigenous", poorest_share: float = 0.2
) -> pd.DataFrame:
    """Share of each group's population counted among the nation's poorest under each label."""
    rows = []
    base = loc[loc["has_dwelling_data"] & loc[group].notna()]
    labels = dict(LABELS)
    if "official_marg" in base.columns and base["official_marg"].notna().any():
        labels["official_conapo"] = ("official_marg", True)  # oriented: higher = more marginalized
        base = base[base["official_marg"].notna()]
    for label, (column, higher_is_poorer) in labels.items():
        poverty_score = base[column] if higher_is_poorer else -base[column]
        pct = weighted_percentile_rank(poverty_score, base["POBTOT"])
        poorest = pct >= 1 - poorest_share
        for value, part in base.assign(_poor=poorest).groupby(group):
            pop = part["POBTOT"].sum()
            rows.append(
                {
                    "label": label,
                    "group": "Indigenous" if int(value) == 1 else "Non-Indigenous",
                    "population": pop,
                    "share_in_poorest": (part["POBTOT"] * part["_poor"]).sum() / pop,
                }
            )
    return pd.DataFrame(rows)


def label_agreement(loc: pd.DataFrame, group: str = "indigenous") -> pd.DataFrame:
    """Spearman correlations between labels (deprivation orientation), by group."""
    base = loc[loc["has_dwelling_data"] & loc[group].notna()].copy()
    base["wealth_as_poverty"] = -base["wealth_dhs_like"]
    cols = {"wealth_as_poverty": "wealth_dhs_like", "dep_infra": "dep_infra", "marg_index": "marg_index"}
    rows = []
    for value, part in base.groupby(group):
        corr = part[list(cols)].rank().corr()
        names = list(cols)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                rows.append(
                    {
                        "group": "Indigenous" if int(value) == 1 else "Non-Indigenous",
                        "label_a": cols[a],
                        "label_b": cols[b],
                        "spearman": corr.loc[a, b],
                    }
                )
    return pd.DataFrame(rows)
