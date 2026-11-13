"""Challenger models trained on a simulated survey and scored against the full census.

Each replication draws a new survey, fits every model on the survey only, then measures on
localities the survey did not visit:

* signed bias, RMSE and MAE by group, per person and per place, plus compression diagnostics
  (calibration slope, variance ratio, bias by true deprivation decile),
* coverage, width and interval score of 90% conformal intervals, marginal vs. group-conditional,
* exclusion errors under "target the poorest 20%", pesos shifted under a FAIS-like formula, and the
  share of the budget misallocated.

Metric choices are explained in mapaudit/metrics.py and docs/methods.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from mapaudit.allocation import allocation_gap, formula_allocation, targeting_errors
from mapaudit.conformal import coverage_by_group, fit_quantiles, quantiles_for
from mapaudit.embeddings import EMBEDDING_COLUMNS
from mapaudit.labels import weighted_percentile_rank
from mapaudit.metrics import allocation_errors, decile_bias, error_profile, evaluation_coverage
from mapaudit.ml import GBMWithEB, crossfit, group_folds
from mapaudit.sae import NestedFayHerriot
from mapaudit.survey import draw_survey

TARGET = "dep_infra"

MODELS = {
    "Nightlights (GBM)": {"kind": "gbm", "features": ["ntl_log"], "eb": False},
    "Embeddings (GBM)": {"kind": "gbm", "features": EMBEDDING_COLUMNS, "eb": False},
    "Embeddings (GBM + EB)": {"kind": "gbm", "features": EMBEDDING_COLUMNS, "eb": True},
    "Embeddings (Fay-Herriot)": {"kind": "fh", "features": "pcs"},
}


def _group_label(values: pd.Series) -> np.ndarray:
    return np.where(values.astype(float) == 1, "Indigenous", "Non-Indigenous")


def _fit_predict(name, spec, X, P, sample_idx, y_obs, psi, mun, cfg, rng, seed):
    """Return (predictions for every locality, out-of-fold predictions for sampled localities)."""
    mun_s = mun[sample_idx]
    if spec["kind"] == "gbm":
        Xs = X[spec["features"]] if isinstance(spec["features"], list) else X
        X_all = Xs.to_numpy(dtype=float)
        model = GBMWithEB(
            cfg["models"]["gbm"], seed=seed, n_folds=cfg["models"]["cv_folds"], use_eb=spec["eb"]
        )
        model.fit(X_all[sample_idx], y_obs, mun_s, rng)
        return model.predict(X_all, mun), model.oof_

    folds = group_folds(mun_s, cfg["models"]["cv_folds"], rng)
    P_s = P[sample_idx]

    def fit_predict(train, test):
        fh = NestedFayHerriot().fit(P_s[train], y_obs[train], psi[train], mun_s[train])
        return fh.predict(P_s[test], mun_s[test])

    oof = crossfit(fit_predict, len(y_obs), folds)
    fh = NestedFayHerriot().fit(P_s, y_obs, psi, mun_s)
    pred = fh.predict(P, mun)
    pred[sample_idx] = fh.fitted_
    return pred, oof


def run_challengers(
    loc: pd.DataFrame, municipalities: pd.DataFrame, cfg: dict, seed: int
) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    needed = [TARGET, "POBTOT", "indigenous", "ntl_log", *EMBEDDING_COLUMNS]
    scope = loc[loc["in_scope"]]
    evaluable = scope["has_dwelling_data"] & scope[needed].notna().all(axis=1)
    coverage_table = evaluation_coverage(scope, evaluable, "Challenger models (rural localities)")
    universe = loc[loc["has_dwelling_data"] & loc["in_scope"]].dropna(subset=needed).reset_index(drop=True)
    if universe.empty:
        raise ValueError("No localities have both census labels and satellite features.")

    P = PCA(n_components=cfg["models"]["sae_n_components"], random_state=seed).fit_transform(
        universe[EMBEDDING_COLUMNS].to_numpy(dtype=float)
    )
    truth = universe[TARGET].to_numpy(dtype=float)
    pop = universe["POBTOT"].to_numpy(dtype=float)
    mun = universe["cve_mun"].to_numpy()
    groups = _group_label(universe["indigenous"])
    ones = np.ones(len(universe))
    # National deciles of true deprivation (1 = least deprived), population-weighted.
    dep_decile = np.clip(np.floor(weighted_percentile_rank(truth, pop) * 10).astype(int) + 1, 1, 10)
    # Locality size terciles: sampled localities are larger than unsampled ones, so calibrating
    # within group x size is the natural refinement when group-only calibration falls short.
    size = (
        pd.qcut(np.log(universe["VIVPARH_CV"]), 3, labels=["small", "medium", "large"]).astype(str).to_numpy()
    )
    cells = np.char.add(np.char.add(groups.astype(str), " | "), size)
    # Conformal guarantees need calibration and deployment points to be exchangeable. The survey
    # never visits localities below min_dwellings, so coverage is reported separately for them.
    in_frame = (universe["VIVPARH_CV"] >= cfg["survey"]["min_dwellings"]).to_numpy()
    alpha = cfg["conformal"]["alpha"]
    survey_cfg = cfg["survey"]
    alloc_cfg = cfg["allocation"]
    true_alloc = formula_allocation(truth, pop, mun, alloc_cfg["budget_mxn"])

    metric_rows, cover_rows, target_rows, alloc_rows, decile_rows, mun_rows = [], [], [], [], [], []
    for rep in range(survey_cfg["replications"]):
        draw = draw_survey(
            universe,
            rng,
            n_municipalities=survey_cfg["n_municipalities"],
            localities_per_municipality=survey_cfg["localities_per_municipality"],
            dwellings_per_locality=survey_cfg["dwellings_per_locality"],
            min_dwellings=survey_cfg["min_dwellings"],
        )
        position = pd.Series(np.arange(len(universe)), index=universe["cvegeo"])
        sample_idx = position.loc[draw.sample["cvegeo"]].to_numpy()
        y_obs = draw.sample["y_obs"].to_numpy()
        psi = draw.sample["psi"].to_numpy()
        unsampled = np.ones(len(universe), bool)
        unsampled[sample_idx] = False

        for name, spec in MODELS.items():
            pred, oof = _fit_predict(
                name, spec, universe, P, sample_idx, y_obs, psi, mun, cfg, rng, seed + rep
            )
            pred = np.clip(pred, 0, 1)
            for g in ["Indigenous", "Non-Indigenous", "All"]:
                m = unsampled & ((groups == g) if g != "All" else True)
                if m.sum() < 2:
                    continue
                for weighting, w in (("people", pop), ("places", ones)):
                    metric_rows.append(
                        {
                            "rep": rep,
                            "model": name,
                            "group": g,
                            "weighting": weighting,
                            **error_profile(truth[m], pred[m], w[m]),
                        }
                    )
            u = unsampled
            decile_rows.append(
                decile_bias(truth[u], pred[u], pop[u], groups[u], dep_decile[u]).assign(rep=rep, model=name)
            )

            scores = np.abs(y_obs - oof)
            q_group = fit_quantiles(scores, groups[sample_idx], alpha)
            q_cell = fit_quantiles(scores, cells[sample_idx], alpha) | {
                k: v for k, v in q_group.items() if k != "__all__"
            }
            q_cell["__all__"] = q_group["__all__"]
            methods = {
                "Marginal": np.full(u.sum(), q_group["__all__"]),
                "Mondrian: group": quantiles_for(groups[u], q_group),
                "Mondrian: group x size": quantiles_for(cells[u], q_cell, fallback_keys=groups[u]),
            }
            calib_n = pd.Series(groups[sample_idx]).value_counts()
            frames = {
                "All unsampled": np.ones(u.sum(), bool),
                "In survey frame": in_frame[u],
                "Outside survey frame": ~in_frame[u],
            }
            for method, q in methods.items():
                for frame, f in frames.items():
                    if f.sum() == 0:
                        continue
                    cov = coverage_by_group(truth[u][f], pred[u][f], q[f], groups[u][f], alpha=alpha)
                    cov["method"], cov["frame"] = method, frame
                    cov["calibration_n"] = cov["group"].map(calib_n).fillna(len(sample_idx))
                    cover_rows.append(cov.assign(rep=rep, model=name))

            tgt = targeting_errors(truth, pred, pop, groups, alloc_cfg["target_population_share"])
            target_rows.append(tgt.assign(rep=rep, model=name))
            est_alloc = formula_allocation(pred, pop, mun, alloc_cfg["budget_mxn"])
            alloc_rows.append(
                allocation_gap(true_alloc, est_alloc, municipalities).assign(rep=rep, model=name)
            )
            mun_rows.append(
                allocation_errors(true_alloc, est_alloc, municipalities).assign(rep=rep, model=name)
            )

    return {
        "challenger_metrics": pd.DataFrame(metric_rows),
        "challenger_coverage": pd.concat(cover_rows, ignore_index=True),
        "challenger_targeting": pd.concat(target_rows, ignore_index=True),
        "challenger_allocation": pd.concat(alloc_rows, ignore_index=True),
        "challenger_decile_bias": pd.concat(decile_rows, ignore_index=True),
        "challenger_municipal": pd.concat(mun_rows, ignore_index=True),
        "challenger_evaluation_coverage": coverage_table,
    }


def summarize_reps(df: pd.DataFrame, by: list[str], value_cols: list[str]) -> pd.DataFrame:
    """Mean and 2.5/97.5 percentiles across survey replications."""
    grouped = df.groupby(by)[value_cols]
    mean = grouped.mean().add_suffix("_mean")
    lo = grouped.quantile(0.025).add_suffix("_p025")
    hi = grouped.quantile(0.975).add_suffix("_p975")
    return pd.concat([mean, lo, hi], axis=1).reset_index()
