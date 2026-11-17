"""Pipeline steps. Each step reads the previous step's files, so steps can be rerun independently.

build     census + RWI + satellite features  -> data/processed/*.parquet
audit     RWI audit + label choice + RWI allocation  -> results/<mode>/tables
simulate  survey simulation + challenger models      -> results/<mode>/tables
report    figures + markdown pages                   -> results/<mode>/figures, docs/
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from mapaudit import audit as audit_mod
from mapaudit.allocation import (
    allocation_gap,
    formula_allocation,
    shift_by_indigenous_share,
    targeting_errors,
)
from mapaudit.census import (
    add_indigenous_flags,
    add_remoteness,
    clean_iter,
    derive_indicators,
    municipality_table,
    read_iter,
)
from mapaudit.config import get_paths, load_config
from mapaudit.embeddings import EMBEDDING_COLUMNS, embedding_norm_check, read_embeddings
from mapaudit.labels import build_labels, label_agreement, label_choice_table, weighted_percentile_rank
from mapaudit.metrics import allocation_errors, evaluation_coverage, holm, paired_contrast
from mapaudit.rwi import attach_rwi, build_tiles, quadkey_consistency, read_rwi, rwi_to_deprivation
from mapaudit.simulate import run_challengers, summarize_reps
from mapaudit.synthetic import generate

KEEP_COLUMNS = [
    "cvegeo", "cve_mun", "cve_ent", "NOM_ENT", "NOM_MUN", "NOM_LOC", "lat", "lon", "altitude_m",
    "POBTOT", "VIVPARH_CV", "has_dwelling_data", "in_scope", "urban", "log_pop", "dist_city_km",
    "log_dist_city",
    "ind_hh_share", "ind_lang_share", "ind_share", "indigenous",
    "no_elec", "no_water", "no_drain", "dirt_floor", "has_fridge", "has_internet", "illiterate",
    "no_basic_ed", "crowding", "wealth_dhs_like", "dep_infra", "marg_index",
    "wealth_pct", "dep_infra_pct", "marg_pct",
    "quadkey", "rwi", "rwi_error", "rwi_covered",
]  # fmt: skip


def _json_default(obj):
    if isinstance(obj, np.integer | np.floating):
        return obj.item()
    if isinstance(obj, np.bool_):
        return bool(obj)
    return str(obj)


def _write_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, default=_json_default))


def assemble(raw_dir: Path, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame, dict]:
    """Build the locality table, RWI tiles and municipality table from raw files (no writing)."""
    src = cfg["sources"]
    share_col = cfg["indigenous"]["share_column"]
    threshold = cfg["indigenous"]["majority_threshold"]
    summary: dict = {}

    loc = clean_iter(read_iter(raw_dir / src["iter_2020"]["filename"]))
    summary["localities"] = len(loc)
    loc = derive_indicators(loc, cfg["geography"]["urban_min_population"])
    loc = add_remoteness(loc, cfg["geography"]["city_min_population"])
    loc = add_indigenous_flags(loc, share_col, threshold)
    max_pop = cfg["scope"]["max_locality_population"]
    loc["in_scope"] = loc["lat"].notna() & (loc["POBTOT"] <= max_pop if max_pop else True)
    summary["localities_in_scope"] = int(loc["in_scope"].sum())
    loc, loadings = build_labels(loc)
    summary["localities_with_dwelling_data"] = int(loc["has_dwelling_data"].sum())
    summary["population"] = float(loc["POBTOT"].sum())
    summary["indigenous_localities"] = int((loc["indigenous"] == 1).sum())
    summary["label_loadings"] = {k: v.round(3).to_dict() for k, v in loadings.items()}

    # Optional official CONAPO index: merged before the tiles so the audit can use it as ground truth.
    official = src.get("conapo_iml_2020", {})
    official_path = raw_dir / official.get("filename", "missing")
    if official.get("enabled") and official_path.exists():
        off = pd.read_csv(official_path, dtype={official["key_column"]: str})
        off = off.rename(
            columns={official["key_column"]: "cvegeo", official["index_column"]: "official_marg"}
        )
        off["cvegeo"] = off["cvegeo"].str.zfill(9)
        if not official.get("higher_is_more_marginalized", True):
            off["official_marg"] = -off["official_marg"]
        loc = loc.merge(off[["cvegeo", "official_marg"]], on="cvegeo", how="left")
        summary["official_marg_spearman_with_rebuilt"] = float(
            loc[["official_marg", "marg_index"]].corr("spearman").iloc[0, 1]
        )

    tiles = None
    rwi_path = raw_dir / src["rwi"]["filename"]
    if rwi_path.exists():
        rwi = read_rwi(rwi_path)
        summary["rwi_tiles_in_file"] = len(rwi)
        summary["rwi_quadkey_consistency"] = quadkey_consistency(rwi)
        loc = attach_rwi(loc, rwi)
        tiles = build_tiles(loc, threshold)
        summary["rwi_tiles_matched"] = len(tiles)
    else:
        loc["quadkey"], loc["rwi"], loc["rwi_error"], loc["rwi_covered"] = pd.NA, np.nan, np.nan, 0
        summary["rwi_tiles_in_file"] = 0

    keep = [c for c in [*KEEP_COLUMNS, "official_marg"] if c in loc.columns]
    try:
        emb = read_embeddings(raw_dir, src["alphaearth"]["file_glob"])
        loc = loc.merge(
            emb[["cvegeo", *EMBEDDING_COLUMNS, *[c for c in ("ntl_avg", "ntl_log") if c in emb]]],
            on="cvegeo",
            how="left",
        )
        summary["localities_with_embeddings"] = int(loc["A00"].notna().sum())
        summary["embedding_median_norm"] = embedding_norm_check(emb)
        keep += [c for c in [*EMBEDDING_COLUMNS, "ntl_avg", "ntl_log"] if c in loc.columns]
    except FileNotFoundError as err:
        summary["localities_with_embeddings"] = 0
        summary["embeddings_note"] = str(err)

    # Allocation summaries refer to the in-scope (rural) population of each municipality.
    municipalities = municipality_table(loc[loc["in_scope"]], share_col, threshold)
    return loc[keep], tiles, municipalities, summary


def build(mode: str = "real", root: Path | None = None) -> dict:
    cfg, paths = load_config(mode, root), get_paths(mode, root)
    if mode == "demo" and not (paths.raw / cfg["sources"]["iter_2020"]["filename"]).exists():
        generate(paths.raw, cfg["synthetic"], cfg["seed"])
    loc, tiles, municipalities, summary = assemble(paths.raw, cfg)
    loc.to_parquet(paths.localities, index=False)
    municipalities.to_parquet(paths.processed / "municipalities.parquet")
    if tiles is not None:
        tiles.to_parquet(paths.tiles, index=False)
    _write_json(summary, paths.tables / "build_summary.json")
    return summary


def _rwi_allocation(loc: pd.DataFrame, municipalities: pd.DataFrame, cfg: dict) -> dict[str, pd.DataFrame]:
    scope = loc[loc["in_scope"]]
    base = scope[scope["has_dwelling_data"] & scope["indigenous"].notna()]
    est = rwi_to_deprivation(scope).loc[base.index].to_numpy()
    truth = base["dep_infra"].to_numpy()
    pop = base["POBTOT"].to_numpy()
    groups = np.where(base["indigenous"].astype(float) == 1, "Indigenous", "Non-Indigenous")
    alloc = cfg["allocation"]
    true_alloc = formula_allocation(truth, pop, base["cve_mun"], alloc["budget_mxn"])
    est_alloc = formula_allocation(est, pop, base["cve_mun"], alloc["budget_mxn"])
    return {
        "rwi_targeting": targeting_errors(truth, est, pop, groups, alloc["target_population_share"]),
        "rwi_allocation": allocation_gap(true_alloc, est_alloc, municipalities),
        "rwi_allocation_by_share": shift_by_indigenous_share(true_alloc, est_alloc, municipalities),
        "rwi_allocation_errors": allocation_errors(true_alloc, est_alloc, municipalities),
    }


def _decile_gap(decile: pd.DataFrame, by: str = "truth_decile") -> float:
    """Indigenous minus non-Indigenous mean rank error within deciles (of ``by``), averaged with
    weights equal to the Indigenous population in each decile."""
    wide = decile.pivot(index=by, columns="group", values="mean_error").dropna()
    if wide.empty or "Indigenous" not in wide:
        return float("nan")
    weights = decile[decile["group"] == "Indigenous"].set_index(by)["pop"].reindex(wide.index)
    return float(np.average(wide["Indigenous"] - wide["Non-Indigenous"], weights=weights))


def confirmatory_tests(coverage_reg: pd.DataFrame, audit_regs: pd.DataFrame) -> pd.DataFrame:
    """H1 (two-sided) and H2 (one-sided, coefficient > 0) with Holm's correction, as pre-registered."""
    h1, h2 = coverage_reg.iloc[0], audit_regs.iloc[-1]
    rows = [
        {"hypothesis": "H1 coverage", "estimate": h1["coef"], "ci_low": h1["ci_low"],
         "ci_high": h1["ci_high"], "test": "two-sided", "p_value": h1["p_value"]},
        {"hypothesis": "H2 rank bias", "estimate": h2["coef"], "ci_low": h2["ci_low"],
         "ci_high": h2["ci_high"], "test": "one-sided (> 0)", "p_value": h2["p_one_sided"]},
    ]  # fmt: skip
    table = pd.DataFrame(rows)
    table["p_holm"] = holm(table["p_value"])
    table["supported_at_5pct"] = table["p_holm"] < 0.05
    return table


def run_audit(
    loc: pd.DataFrame, tiles: pd.DataFrame, municipalities: pd.DataFrame, cfg: dict
) -> tuple[dict, dict]:
    rng = np.random.default_rng(cfg["seed"])
    tables = {
        "coverage": audit_mod.coverage_table(loc),
        "coverage_regression": audit_mod.coverage_regression(loc),
        "decile_errors": audit_mod.decile_errors(tiles, cfg["audit"]["bootstrap_reps"], rng),
        "map_decile_errors": audit_mod.decile_errors(
            tiles, cfg["audit"]["bootstrap_reps"], rng, by="map_decile"
        ),
        "audit_regressions": audit_mod.audit_regressions(tiles, weighted=True),
        "audit_regressions_unweighted": audit_mod.audit_regressions(tiles, weighted=False),
        "label_choice": label_choice_table(loc),
        "label_agreement": label_agreement(loc),
        **_rwi_allocation(loc, municipalities, cfg),
    }
    tables["confirmatory_tests"] = confirmatory_tests(
        tables["coverage_regression"], tables["audit_regressions"]
    )
    scope = loc[loc["in_scope"]]
    evaluated = scope["has_dwelling_data"] & scope["quadkey"].isin(tiles["quadkey"])
    tables["evaluation_coverage"] = evaluation_coverage(scope, evaluated, "RWI rank-error audit")
    cov = tables["coverage"].query("size_class == 'All'").set_index("group")
    main = tables["audit_regressions"].iloc[-1]
    alloc = tables["rwi_allocation"].set_index("group")
    tgt = tables["rwi_targeting"].set_index("group")
    no_bias = audit_mod.calibration_benchmark(tiles, cfg["audit"]["calibration_permutations"], rng)
    summary = {
        "population_covered_indigenous": cov.loc["Indigenous", "share_population_covered"],
        "population_covered_non_indigenous": cov.loc["Non-Indigenous", "share_population_covered"],
        "coverage_coef_ind_share": tables["coverage_regression"]["coef"].iloc[0],
        "rank_error_coef_full_spec": main["coef"],
        "rank_error_ci_full_spec": [main["ci_low"], main["ci_high"]],
        "rank_error_p_one_sided": main["p_one_sided"],
        "rank_error_p_holm": float(tables["confirmatory_tests"]["p_holm"].iloc[1]),
        "coverage_p_holm": float(tables["confirmatory_tests"]["p_holm"].iloc[0]),
        "decile_conditional_gap_pp": _decile_gap(tables["decile_errors"]),
        "calibration_gap_pp": _decile_gap(tables["map_decile_errors"], by="map_decile"),
        # What a map with group-blind errors would show on these data (see audit.calibration_benchmark).
        "calibration_gap_no_bias_pp": no_bias["mean"],
        "calibration_gap_no_bias_range_pp": [no_bias["p025"], no_bias["p975"]],
        "rwi_misallocation_share": float(tables["rwi_allocation_errors"]["misallocation_share"].iloc[0]),
        **{f"compression_{k}": v for k, v in audit_mod.compression_check(tiles).items()},
        "rwi_exclusion_indigenous": tgt.loc["Indigenous", "exclusion_rate"],
        "rwi_exclusion_non_indigenous": tgt.loc["Non-Indigenous", "exclusion_rate"],
        "rwi_net_shift_indigenous_mxn": alloc.loc["Indigenous-majority municipalities", "net_shift"]
        if "Indigenous-majority municipalities" in alloc.index
        else float("nan"),
        "rwi_net_shift_indigenous_pct": alloc.loc["Indigenous-majority municipalities", "net_shift_pct"]
        if "Indigenous-majority municipalities" in alloc.index
        else float("nan"),
    }
    return tables, summary


def audit(mode: str = "real", root: Path | None = None) -> dict:
    cfg, paths = load_config(mode, root), get_paths(mode, root)
    if not paths.tiles.exists():
        raise FileNotFoundError("No RWI tiles found. Run `mapaudit build` with the RWI file in data/raw.")
    loc = pd.read_parquet(paths.localities)
    tiles = pd.read_parquet(paths.tiles)
    municipalities = pd.read_parquet(paths.processed / "municipalities.parquet")
    tables, summary = run_audit(loc, tiles, municipalities, cfg)
    for name, table in tables.items():
        table.to_csv(paths.tables / f"{name}.csv", index=False)
    _write_json(summary, paths.tables / "audit_summary.json")
    return summary


REFERENCE_MODEL = "Embeddings (Fay-Herriot)"
H4_MODEL = "Embeddings (GBM)"


def paired_contrasts(metrics: pd.DataFrame) -> pd.DataFrame:
    """Paired, replication-by-replication model comparisons against the small area estimation model.

    The first row is H4 as pre-registered: |bias| for Indigenous localities, gradient boosting on
    embeddings minus Fay-Herriot; supported if the 95% replication range lies above zero.
    """
    rows = [
        {
            "hypothesis": "H4",
            **paired_contrast(metrics, "bias", H4_MODEL, REFERENCE_MODEL, "Indigenous", absolute=True),
        }
    ]
    for model in sorted(set(metrics["model"]) - {REFERENCE_MODEL}):
        for group in ("Indigenous", "Non-Indigenous", "All"):
            rows.append({"hypothesis": "", **paired_contrast(metrics, "rmse", model, REFERENCE_MODEL, group)})
    table = pd.DataFrame([r for r in rows if len(r) > 1])
    table["supported"] = np.where(table["hypothesis"] == "H4", np.where(table["p025"] > 0, "yes", "no"), "")
    return table


def simulate(mode: str = "real", root: Path | None = None) -> dict:
    cfg, paths = load_config(mode, root), get_paths(mode, root)
    loc = pd.read_parquet(paths.localities)
    if "A00" not in loc.columns:
        raise FileNotFoundError("No satellite features in the locality table; export them and rerun build.")
    municipalities = pd.read_parquet(paths.processed / "municipalities.parquet")
    out = run_challengers(loc, municipalities, cfg, cfg["seed"])
    for name, table in out.items():
        table.to_csv(paths.tables / f"{name}.csv", index=False)
    metric_cols = ["bias", "mae", "rmse", "calibration_slope", "variance_ratio"]
    summaries = {
        "challenger_metrics_summary": summarize_reps(
            out["challenger_metrics"], ["model", "group", "weighting"], metric_cols
        ),
        "challenger_coverage_summary": summarize_reps(
            out["challenger_coverage"],
            ["model", "method", "frame", "group"],
            ["coverage", "width", "interval_score"],
        ),
        "challenger_targeting_summary": summarize_reps(
            out["challenger_targeting"], ["model", "group"], ["exclusion_rate"]
        ),
        "challenger_allocation_summary": summarize_reps(
            out["challenger_allocation"], ["model", "group"], ["net_shift", "net_shift_pct"]
        ),
        "challenger_decile_bias_summary": summarize_reps(
            out["challenger_decile_bias"], ["model", "group", "decile"], ["bias"]
        ),
        "challenger_municipal_summary": summarize_reps(
            out["challenger_municipal"], ["model", "group"], ["misallocation_share", "ape_median"]
        ),
        "challenger_paired": paired_contrasts(out["challenger_metrics"]),
    }
    for name, table in summaries.items():
        table.to_csv(paths.tables / f"{name}.csv", index=False)
    return {
        "replications": cfg["survey"]["replications"],
        "models": sorted(out["challenger_metrics"]["model"].unique()),
    }


def validate(root: Path | None = None) -> pd.DataFrame:
    """Planted-bias check: the audit must detect planted effects and stay quiet without them."""
    cfg, paths = load_config("demo", root), get_paths("demo", root)
    rng = np.random.default_rng(cfg["seed"])
    rows = []
    worlds = {
        "Bias planted": cfg["synthetic"],
        "No bias planted": {
            **cfg["synthetic"],
            "rwi_indigenous_bias_sd": 0.0,
            "rwi_coverage_indigenous_logit": 0.0,
        },
    }
    for i, (world, settings) in enumerate(worlds.items()):
        raw = paths.data / "validation" / f"world_{i}"
        if raw.exists():
            shutil.rmtree(raw)
        generate(raw, settings, cfg["seed"] + 1000 + i)
        loc, tiles, _, _ = assemble(raw, cfg)
        reg = audit_mod.audit_regressions(tiles).iloc[-1]
        cov = audit_mod.coverage_regression(loc).iloc[0]
        gaps = {}
        for by in ("truth_decile", "map_decile"):
            means = audit_mod._weighted_group_means(tiles, by).reset_index()
            means["group"] = np.where(means["indigenous"] == 1, "Indigenous", "Non-Indigenous")
            gaps[by] = _decile_gap(means, by=by)
        no_bias = audit_mod.calibration_benchmark(tiles, cfg["audit"]["calibration_permutations"], rng)
        rows.append(
            {
                "world": world,
                "planted_rwi_bias_sd": settings["rwi_indigenous_bias_sd"],
                "planted_coverage_logit": settings["rwi_coverage_indigenous_logit"],
                "rank_error_coef": reg["coef"],
                "rank_error_ci_low": reg["ci_low"],
                "rank_error_ci_high": reg["ci_high"],
                "separation_gap_pp": gaps["truth_decile"],
                "calibration_gap_pp": gaps["map_decile"],
                "calibration_gap_no_bias_pp": no_bias["mean"],
                "calibration_gap_no_bias_p975": no_bias["p975"],
                "coverage_coef": cov["coef"],
                "coverage_ci_low": cov["ci_low"],
                "coverage_ci_high": cov["ci_high"],
            }
        )
    table = pd.DataFrame(rows)
    table.to_csv(paths.tables / "validation.csv", index=False)
    return table


def _robustness_row(name: str, tiles: pd.DataFrame, weighted: bool = True) -> dict:
    reg = audit_mod.audit_regressions(tiles, weighted=weighted).iloc[-1]
    means = audit_mod._weighted_group_means(tiles).reset_index()
    means["group"] = np.where(means["indigenous"] == 1, "Indigenous", "Non-Indigenous")
    return {
        "variant": name,
        "rank_error_coef": reg["coef"],
        "ci_low": reg["ci_low"],
        "ci_high": reg["ci_high"],
        "p_value": reg["p_value"],
        "decile_conditional_gap_pp": _decile_gap(means),
        "tiles": int(reg["n"]),
    }


def _retruth(tiles: pd.DataFrame, wealth: pd.Series) -> pd.DataFrame:
    """Recompute rank error and true deciles against another ground truth (higher = wealthier)."""
    out = tiles.loc[wealth.notna()].copy()
    out["wealth"] = wealth.loc[out.index]
    # Re-rank both sides on the same set of tiles (the official index may not cover them all).
    out["rwi_pct"] = weighted_percentile_rank(out["rwi"], out["pop"])
    out["truth_pct"] = weighted_percentile_rank(out["wealth"], out["pop"])
    out["rank_error"] = 100 * (out["rwi_pct"] - out["truth_pct"])
    out["truth_decile"] = np.clip(np.floor(out["truth_pct"] * 10).astype(int) + 1, 1, 10)
    return out


def robustness(mode: str = "real", root: Path | None = None) -> pd.DataFrame:
    """Robustness checks promised in the pre-analysis plan (section 6)."""
    cfg, paths = load_config(mode, root), get_paths(mode, root)
    tiles = pd.read_parquet(paths.tiles)
    rows = [
        _robustness_row("Primary specification", tiles),
        _robustness_row("Unweighted", tiles, weighted=False),
        _robustness_row("Tiles with 50+ people", tiles[tiles["pop"] >= 50]),
    ]
    for threshold in (0.3, 0.5):
        alt = tiles.assign(indigenous=(tiles["ind_share"] >= threshold).astype(int))
        rows.append(_robustness_row(f"Indigenous threshold {threshold:.0%}", alt))
    # The same audit judged against the other definitions of poverty (and the official index, if loaded).
    truths = {"Ground truth: infrastructure deprivation": -tiles["dep_infra"],
              "Ground truth: marginalization index": -tiles["marg"]}  # fmt: skip
    if "official_marg" in tiles.columns and tiles["official_marg"].notna().any():
        truths["Ground truth: official CONAPO index"] = -tiles["official_marg"]
    for name, wealth in truths.items():
        rows.append(_robustness_row(name, _retruth(tiles, wealth)))
    lang_cfg = copy.deepcopy(cfg)
    lang_cfg["indigenous"]["share_column"] = "ind_lang_share"
    _, lang_tiles, _, _ = assemble(paths.raw, lang_cfg)
    if lang_tiles is not None:
        rows.append(_robustness_row("Language-based Indigenous share", lang_tiles))
    table = pd.DataFrame(rows)
    table.to_csv(paths.tables / "robustness.csv", index=False)
    return table
