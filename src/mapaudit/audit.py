"""Audit of a deployed map (Meta's RWI) against census ground truth.

Three questions, each with its own table:

1. Representation: are Indigenous localities less likely to be covered by the map at all?
2. Rank error by true wealth decile ("separation" view): among places that are equally wealthy in
   the census, does the map rank Indigenous tiles as wealthier? Conditioning on the true decile
   separates an Indigenous-specific blind spot from the known tendency of ML maps to compress the
   poorest areas toward the middle.
3. Rank error by map decile ("calibration" view): among places the map ranks the same, are the
   Indigenous ones actually poorer? This is what a program using the map experiences. When groups
   differ in average wealth, a map with group-blind noise passes the first test and fails this one,
   so the two views are reported side by side (see docs/methods.md), and the calibration gap is read
   against a no-bias benchmark computed from the data themselves (``calibration_benchmark``).
4. Regressions: does the Indigenous coefficient survive controls for rurality, remoteness, true
   wealth, and state? Standard errors are clustered by municipality; H2 is tested one-sided.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from mapaudit.metrics import one_sided_p

SIZE_BINS = [0, 99, 499, 2499, np.inf]
SIZE_LABELS = ["<100", "100-499", "500-2,499", "2,500+"]


def _group_name(value) -> str:
    return "Indigenous" if int(value) == 1 else "Non-Indigenous"


def coverage_table(loc: pd.DataFrame) -> pd.DataFrame:
    """Share of in-scope localities and population inside an RWI tile, by group and size."""
    base = loc[loc["in_scope"] & loc["indigenous"].notna() & loc["POBTOT"].notna()].copy()
    base["size_class"] = pd.cut(base["POBTOT"], SIZE_BINS, labels=SIZE_LABELS, include_lowest=True)
    base["_covered_pop"] = base["POBTOT"] * base["rwi_covered"]
    rows = []
    for (grp, size), part in base.groupby(["indigenous", "size_class"], observed=True):
        rows.append(
            {
                "group": _group_name(grp),
                "size_class": str(size),
                "localities": len(part),
                "share_localities_covered": part["rwi_covered"].mean(),
                "share_population_covered": part["_covered_pop"].sum() / part["POBTOT"].sum(),
            }
        )
    for grp, part in base.groupby("indigenous"):
        rows.append(
            {
                "group": _group_name(grp),
                "size_class": "All",
                "localities": len(part),
                "share_localities_covered": part["rwi_covered"].mean(),
                "share_population_covered": part["_covered_pop"].sum() / part["POBTOT"].sum(),
            }
        )
    return pd.DataFrame(rows)


def coverage_regression(loc: pd.DataFrame) -> pd.DataFrame:
    """Linear probability model: covered ~ Indigenous share, holding locality size fixed."""
    base = loc[loc["in_scope"] & loc["ind_share"].notna() & loc["log_dist_city"].notna()].copy()
    fit = smf.ols("rwi_covered ~ ind_share + log_pop + log_dist_city", data=base).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(base["cve_mun"])[0]}
    )
    return _tidy(fit, "ind_share", "coverage ~ ind_share + log_pop + log_dist_city")


def _weighted_group_means(df: pd.DataFrame, by: str = "truth_decile") -> pd.DataFrame:
    tmp = df.assign(_wx=df["rank_error"] * df["pop"])
    agg = tmp.groupby([by, "indigenous"]).agg(wx=("_wx", "sum"), pop=("pop", "sum"), n=("pop", "size"))
    agg["mean_error"] = agg["wx"] / agg["pop"]
    return agg


def group_gap(tiles: pd.DataFrame, by: str = "truth_decile") -> float:
    """Indigenous minus non-Indigenous mean rank error within deciles of ``by``, averaged with weights
    equal to the Indigenous population in each decile."""
    agg = _weighted_group_means(tiles, by)
    wide = agg["mean_error"].unstack("indigenous")
    if 0 not in wide or 1 not in wide:
        return float("nan")
    weights = agg["pop"].unstack("indigenous")[1]
    ok = wide[0].notna() & wide[1].notna() & weights.notna()
    if not ok.any():
        return float("nan")
    return float(np.average(wide.loc[ok, 1] - wide.loc[ok, 0], weights=weights[ok]))


def calibration_benchmark(
    tiles: pd.DataFrame, n_perm: int, rng: np.random.Generator, bins: int = 100
) -> dict[str, float]:
    """The calibration gap a map with group-blind errors would show on these same data.

    If the map treats groups alike given the truth (separation), its values are exchangeable among
    tiles at the same census percentile. Shuffling them within percentile bins keeps the real truth,
    groups, population weights and map noise, and removes only a group-specific error, so the
    calibration gap of each shuffled map is a draw from its no-bias distribution. Unlike a gap taken
    from a synthetic world, this benchmark reflects the real difference in wealth between groups and
    the real map's accuracy.
    """
    truth_pct = tiles["truth_pct"].to_numpy(dtype=float)
    rwi_pct = tiles["rwi_pct"].to_numpy(dtype=float)
    truth_bin = np.clip(np.floor(truth_pct * bins).astype(int), 0, bins - 1)
    slots = np.lexsort((np.arange(len(tiles)), truth_bin))  # tile positions, grouped by bin
    base = pd.DataFrame({"pop": tiles["pop"].to_numpy(), "indigenous": tiles["indigenous"].to_numpy()})
    gaps = np.empty(n_perm)
    for b in range(n_perm):
        shuffled = np.empty(len(tiles))
        shuffled[slots] = rwi_pct[np.lexsort((rng.random(len(tiles)), truth_bin))]
        sim = base.assign(
            rank_error=100 * (shuffled - truth_pct),
            map_decile=np.clip(np.floor(shuffled * 10).astype(int) + 1, 1, 10),
        )
        gaps[b] = group_gap(sim, "map_decile")
    return {
        "mean": float(np.nanmean(gaps)),
        "p025": float(np.nanpercentile(gaps, 2.5)),
        "p975": float(np.nanpercentile(gaps, 97.5)),
    }


def decile_errors(
    tiles: pd.DataFrame, n_boot: int, rng: np.random.Generator, by: str = "truth_decile"
) -> pd.DataFrame:
    """Population-weighted mean rank error by decile and group, with cluster-bootstrap CIs.

    ``by="truth_decile"`` gives the separation view (deciles of census wealth); ``by="map_decile"``
    gives the calibration view (deciles of the map's own ranking).

    The municipality-cluster bootstrap is vectorized: per-municipality sums of (error x population)
    and population are computed once for every (decile, group) cell, and each bootstrap replicate is
    a vector of multinomial resampling counts over municipalities, so a replicate is a matrix product.
    """
    point = _weighted_group_means(tiles, by)
    cell = pd.MultiIndex.from_frame(tiles[[by, "indigenous"]])
    tmp = pd.DataFrame(
        {
            "mun": tiles["cve_mun"].to_numpy(),
            "wx": (tiles["rank_error"] * tiles["pop"]).to_numpy(dtype=float),
            "w": tiles["pop"].to_numpy(dtype=float),
        },
        index=cell,
    )
    wx = tmp.pivot_table(index="mun", columns=tmp.index, values="wx", aggfunc="sum", fill_value=0.0)
    w = tmp.pivot_table(index="mun", columns=tmp.index, values="w", aggfunc="sum", fill_value=0.0)
    w = w.reindex(columns=wx.columns, fill_value=0.0)
    n_mun = len(wx)
    counts = rng.multinomial(n_mun, np.full(n_mun, 1 / n_mun), size=n_boot)  # (B, municipalities)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = (counts @ wx.to_numpy()) / (counts @ w.to_numpy())  # (B, cells)
    boot_df = pd.DataFrame(boot, columns=pd.MultiIndex.from_tuples(wx.columns, names=[by, "indigenous"]))
    out = point[["mean_error", "n", "pop"]].copy()
    out["ci_low"] = boot_df.quantile(0.025).reindex(out.index)
    out["ci_high"] = boot_df.quantile(0.975).reindex(out.index)
    out = out.reset_index()
    out["group"] = out["indigenous"].map(_group_name)
    return out


CONTROL_BLOCKS = {
    "1 none": [],
    "2 + rurality": ["log_pop", "urban_share"],
    "3 + remoteness": ["log_pop", "urban_share", "log_dist_city", "altitude_km"],
    "4 + true decile": ["log_pop", "urban_share", "log_dist_city", "altitude_km", "C(truth_decile)"],
    "5 + state FE": [
        "log_pop",
        "urban_share",
        "log_dist_city",
        "altitude_km",
        "C(truth_decile)",
        "C(cve_ent)",
    ],
}


def _formula(data: pd.DataFrame, controls: list[str]) -> str:
    """rank_error ~ ind_share + controls, dropping numeric controls that do not vary
    (e.g. urban_share is always 0 when the scope is rural localities)."""
    kept = [c for c in controls if c.startswith("C(") or data[c].std() > 0]
    return " + ".join(["rank_error ~ ind_share", *kept])


def _tidy(fit, term: str, spec: str, one_sided: str | None = None) -> pd.DataFrame:
    """One row per fitted term; ``one_sided`` ("greater"/"less") adds the directional p-value."""
    ci = fit.conf_int().loc[term]
    coef, p = fit.params[term], fit.pvalues[term]
    row = {
        "spec": spec,
        "term": term,
        "coef": coef,
        "se": fit.bse[term],
        "ci_low": ci.iloc[0],
        "ci_high": ci.iloc[1],
        "p_value": p,
    }
    if one_sided:
        row["p_one_sided"] = one_sided_p(coef, p, one_sided)
    row["n"] = int(fit.nobs)
    return pd.DataFrame([row])


def audit_regressions(tiles: pd.DataFrame, weighted: bool = True) -> pd.DataFrame:
    """Coefficient on Indigenous share (0 to 1) in percentile points of rank error."""
    data = tiles.dropna(subset=["rank_error", "ind_share", "log_dist_city", "altitude_km"]).copy()
    groups = pd.factorize(data["cve_mun"])[0]
    weights = data["pop"] if weighted else np.ones(len(data))
    rows = []
    for name, controls in CONTROL_BLOCKS.items():
        fit = smf.wls(_formula(data, controls), data=data, weights=weights).fit(
            cov_type="cluster", cov_kwds={"groups": groups}
        )
        rows.append(_tidy(fit, "ind_share", name, one_sided="greater"))  # H2 predicts coef > 0
    return pd.concat(rows, ignore_index=True)


def compression_check(tiles: pd.DataFrame) -> dict:
    """Slope of map percentile on true percentile; < 1 means the map compresses toward the middle."""
    fit = smf.wls("rwi_pct ~ truth_pct", data=tiles, weights=tiles["pop"]).fit()
    return {
        "slope": float(fit.params["truth_pct"]),
        "spearman": float(tiles[["rwi", "wealth"]].corr("spearman").iloc[0, 1]),
    }
