"""Render figures and write the results pages of the documentation site.

real mode -> docs/results.md and docs/assets/figures/real/
demo mode -> docs/validation.md and docs/assets/figures/demo/

Numbers in the pages are generated from results/<mode>/tables, never typed by hand.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from mapaudit import plots
from mapaudit.config import get_paths, load_config

FOCUS_MODEL = "Embeddings (GBM)"


_FORMATS = {
    "pct": "{:.1%}", "pct0": "{:.0%}", "pp": "{:+.1f}", "num": "{:,.0f}", "f3": "{:.3f}",
}  # fmt: skip


def _fmt(value, kind: str) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "–"
    if kind == "str":
        return str(value).replace("|", "\\|")  # a pipe inside a cell would split it
    if kind == "yesno":
        return "yes" if str(value).strip().lower() in {"true", "1", "yes"} else "no"
    if kind == "int":
        return f"{int(value):,}"
    if kind == "mxn":
        return f"{value / 1e6:+,.1f}M"
    if kind == "p":
        return f"{value:.3f}" if value >= 0.001 else f"{value:.1e}"
    out = _FORMATS[kind].format(value)
    if out.startswith("-") and not any(ch in "123456789" for ch in out):
        out = _FORMATS[kind].format(abs(value))  # no "-0.000"
    return out


def md_table(df: pd.DataFrame, columns: dict[str, tuple[str, str]]) -> str:
    """Markdown table; ``columns`` maps column -> (header, format kind)."""
    head = "| " + " | ".join(h for h, _ in columns.values()) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    rows = [
        "| " + " | ".join(_fmt(r[c], k) for c, (_, k) in columns.items()) + " |" for _, r in df.iterrows()
    ]
    return "\n".join([head, sep, *rows])


def _figure(rel_dir: str, name: str, alt: str) -> str:
    return f"![{alt}]({rel_dir}/{name}.png#only-light)\n![{alt}]({rel_dir}/{name}-dark.png#only-dark)\n"


def _load(tables: Path, name: str) -> pd.DataFrame | None:
    path = tables / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else None


def _allocation_by_model(tables: Path) -> pd.DataFrame | None:
    rwi = _load(tables, "rwi_allocation")
    ch = _load(tables, "challenger_allocation_summary")
    rows = []
    if rwi is not None:
        r = rwi[rwi["group"].str.startswith("Indigenous")]
        if not r.empty:
            v = float(r["net_shift_pct"].iloc[0])
            rows.append({"model": "Relative Wealth Index", "mean": v, "low": v, "high": v})
    if ch is not None:
        for _, r in ch[ch["group"].str.startswith("Indigenous")].iterrows():
            rows.append(
                {
                    "model": r["model"],
                    "mean": r["net_shift_pct_mean"],
                    "low": r["net_shift_pct_p025"],
                    "high": r["net_shift_pct_p975"],
                }
            )
    return pd.DataFrame(rows) if rows else None


def render_figures(mode: str, root: Path | None = None) -> list[str]:
    cfg, paths = load_config(mode, root), get_paths(mode, root)
    t = paths.tables
    made = []
    jobs = []
    if (decile := _load(t, "decile_errors")) is not None:
        jobs.append(("decile_errors", plots.fig_decile_errors, decile))
    if (map_decile := _load(t, "map_decile_errors")) is not None:
        jobs.append(("map_decile_errors", plots.fig_map_decile_errors, map_decile))
    if (cov := _load(t, "coverage")) is not None:
        jobs.append(("rwi_coverage", plots.fig_coverage, cov))
    if (regs := _load(t, "audit_regressions")) is not None:
        jobs.append(("audit_specs", plots.fig_audit_specs, regs))
    if (lab := _load(t, "label_choice")) is not None:
        jobs.append(("label_choice", plots.fig_label_choice, lab))
    if (met := _load(t, "challenger_metrics_summary")) is not None:
        jobs.append(("challenger_bias", plots.fig_challengers, met))
    if (dec := _load(t, "challenger_decile_bias_summary")) is not None:
        jobs.append(("challenger_deciles", plots.fig_challenger_deciles, dec))
    if (cs := _load(t, "challenger_coverage_summary")) is not None:
        model = FOCUS_MODEL if FOCUS_MODEL in set(cs["model"]) else cs["model"].iloc[0]
        jobs.append(
            (
                "conformal_coverage",
                lambda d, th: plots.fig_conformal(d, model, cfg["conformal"]["alpha"], th),
                cs,
            )
        )
    by_share, by_model = _load(t, "rwi_allocation_by_share"), _allocation_by_model(t)
    if by_share is not None and by_model is not None:
        jobs.append(("allocation", lambda a, th: plots.fig_allocation(a, by_model, th), by_share))
    if paths.tiles.exists():
        jobs.append(("map", plots.fig_map, pd.read_parquet(paths.tiles)))
    if mode == "demo" and (val := _load(t, "validation")) is not None:
        jobs.append(("validation", plots.fig_validation, val))
    for name, builder, data in jobs:
        plots.render(name, builder, paths.figures, data)
        made.append(name)
    target = paths.docs / "assets" / "figures" / mode
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(paths.figures, target)
    return made


def _headline(summary: dict) -> list[str]:
    s = summary
    lines = []
    if "rank_error_coef_full_spec" in s:
        lo, hi = s["rank_error_ci_full_spec"]
        lines.append(
            f"- **Rank bias.** Holding true wealth decile, settlement size, remoteness, altitude, and state fixed, "
            f"the map ranks an all-Indigenous tile **{s['rank_error_coef_full_spec']:+.1f} percentile points** "
            f"higher than a non-Indigenous tile relative to the census (95% CI {lo:+.1f} to {hi:+.1f}; "
            f"one-sided p = {s.get('rank_error_p_one_sided', float('nan')):.3g}, "
            f"Holm-adjusted p = {s.get('rank_error_p_holm', float('nan')):.3g})."
        )
        lines.append(
            f"- **Within the same true decile**, Indigenous tiles' average rank error exceeds non-Indigenous tiles' "
            f"by {s['decile_conditional_gap_pp']:+.1f} points (weighted by Indigenous population)."
        )
    if "calibration_gap_pp" in s:
        line = (
            f"- **Among places the map ranks the same**, Indigenous tiles' rank error is "
            f"{s['calibration_gap_pp']:+.1f} points higher, i.e. they are poorer than the map says."
        )
        if "calibration_gap_no_bias_pp" in s:
            lo, hi = s["calibration_gap_no_bias_range_pp"]
            line += (
                f" A map with group-blind errors would show {s['calibration_gap_no_bias_pp']:+.1f} points on these "
                f"data (95% range {lo:+.1f} to {hi:+.1f}), because groups differ in average wealth; only a gap "
                f"beyond that range points to errors specific to Indigenous places."
            )
        lines.append(line)
    if "population_covered_indigenous" in s:
        lines.append(
            f"- **Coverage.** {s['population_covered_indigenous']:.1%} of the Indigenous rural population lies inside a "
            f"map tile, vs. {s['population_covered_non_indigenous']:.1%} of the non-Indigenous rural population."
        )
    if "rwi_net_shift_indigenous_pct" in s:
        lines.append(
            f"- **Money.** Using the map instead of the census in a FAIS-style formula changes the allocation to "
            f"Indigenous-majority municipalities by **{s['rwi_net_shift_indigenous_pct']:+.1%}** "
            f"({s['rwi_net_shift_indigenous_mxn'] / 1e6:+,.1f} million pesos per billion allocated); "
            f"{s.get('rwi_misallocation_share', float('nan')):.1%} of the whole budget goes to the wrong municipalities."
        )
        lines.append(
            f"- **Targeting.** Selecting the poorest 20% by the map leaves out "
            f"{s['rwi_exclusion_indigenous']:.0%} of the truly poorest Indigenous population vs. "
            f"{s['rwi_exclusion_non_indigenous']:.0%} of the truly poorest non-Indigenous population."
        )
    return lines


def write_page(mode: str, root: Path | None = None) -> Path:
    paths = get_paths(mode, root)
    t = paths.tables
    rel = f"assets/figures/{mode}"
    audit_summary = (
        json.loads((t / "audit_summary.json").read_text()) if (t / "audit_summary.json").exists() else {}
    )
    build_summary = (
        json.loads((t / "build_summary.json").read_text()) if (t / "build_summary.json").exists() else {}
    )
    out: list[str] = []

    if mode == "demo":
        out += [
            "# Validation on synthetic data",
            "",
            '!!! warning "Synthetic data"',
            "    Everything on this page comes from **synthetic** data with biases planted on purpose. It shows that the",
            "    pipeline runs end to end and that the audit can detect a bias of known size. It says nothing about Mexico.",
            "    Real results live on the [Results](results.md) page.",
            "",
        ]
        if (val := _load(t, "validation")) is not None:
            out += [
                "## Does the audit find a planted bias, and only when it is there?",
                "",
                "Two fresh synthetic worlds drawn with the demo settings, one with the planted bias and one "
                "without. Without it, the coefficient and the equally-poor gap should be near zero. The "
                "ranked-equally gap need not be: when groups differ in average wealth, a map whose errors "
                "ignore group still shows a gap among places it ranks the same "
                "(see [Methods](methods.md#two-views-of-fairness)). The no-bias benchmark estimates that gap "
                "from each world's own data; the ranked-equally gap should stay within its range without "
                "the planted bias and exceed it with the bias.",
                "",
                _figure(
                    rel, "validation", "Validation: estimated coefficients with and without planted bias"
                ),
                md_table(
                    val,
                    {
                        "world": ("World", "str"),
                        "planted_rwi_bias_sd": ("Planted RWI bias (SD)", "f3"),
                        "rank_error_coef": ("Rank-error coef (pp)", "pp"),
                        "rank_error_ci_low": ("CI low", "pp"),
                        "rank_error_ci_high": ("CI high", "pp"),
                        "separation_gap_pp": ("Gap: equally poor (pp)", "pp"),
                        "calibration_gap_pp": ("Gap: ranked equally (pp)", "pp"),
                        "calibration_gap_no_bias_pp": ("No-bias benchmark (pp)", "pp"),
                        "calibration_gap_no_bias_p975": ("Benchmark 97.5% (pp)", "pp"),
                        "coverage_coef": ("Coverage coef", "f3"),
                    },
                ),
                "",
            ]
    else:
        out += [
            "# Results",
            "",
            "Generated by `mapaudit report` from the tables in `results/real/tables`. "
            "Methods and hypotheses: [Methods](methods.md), [Pre-analysis plan](pre_analysis_plan.md).",
            "",
        ]

    out += [
        "## Data at a glance",
        "",
        md_table(
            pd.DataFrame([build_summary]),
            {
                "localities": ("Localities", "int"),
                "localities_in_scope": ("Rural (in scope)", "int"),
                "localities_with_dwelling_data": ("With dwelling data", "int"),
                "indigenous_localities": ("Indigenous localities", "int"),
                "rwi_tiles_matched": ("RWI tiles analyzed", "int"),
                "localities_with_embeddings": ("With satellite features", "int"),
            },
        )
        if build_summary
        else "",
        "",
    ]

    if audit_summary:
        out += ["## Headline numbers", "", *_headline(audit_summary), ""]

    def people(df):
        return df[df["weighting"] == "people"] if "weighting" in df else df

    def no_all(df):
        return df[df["group"] != "All"]

    tests_cols = {
        "hypothesis": ("Hypothesis", "str"), "estimate": ("Estimate", "f3"), "ci_low": ("CI low", "f3"),
        "ci_high": ("CI high", "f3"), "test": ("Test", "str"), "p_value": ("p", "p"),
        "p_holm": ("p (Holm)", "p"), "supported_at_5pct": ("Supported at 5%", "yesno"),
    }  # fmt: skip
    decile_cols = {
        "group": ("Group", "str"), "mean_error": ("Mean rank error (pp)", "pp"),
        "ci_low": ("CI low", "pp"), "ci_high": ("CI high", "pp"), "n": ("Tiles", "int"),
    }  # fmt: skip
    # (figure, title, intro, [(table, columns, row filter[, caption])]). Tables without a caption go in a
    # collapsible "Table view" under the figure; captioned tables are results of their own and stay visible.
    sections = [
        (None, "Confirmatory tests", "H1 and H2 as pre-registered: H2 one-sided, Holm's correction across both.",
         [("confirmatory_tests", tests_cols, None)]),
        (None, "Who each analysis covers", "Metrics exist only where the census truth is known. Share of the "
         "in-scope population each analysis actually evaluates:",
         [("evaluation_coverage", {"analysis": ("Analysis", "str"), "group": ("Group", "str"),
                                   "share_evaluated": ("Population evaluated", "pct")}, None),
          ("challenger_evaluation_coverage", {"analysis": ("Analysis", "str"), "group": ("Group", "str"),
                                              "share_evaluated": ("Population evaluated", "pct")}, None)]),
        ("decile_errors", "Rank error by true wealth decile (separation view)", None,
         [("decile_errors", {"truth_decile": ("True decile", "int"), **decile_cols}, None)]),
        ("map_decile_errors", "Places the map ranks the same (calibration view)",
         "Read with the previous figure: when groups differ in average wealth, a map whose errors ignore "
         "group can pass the separation test and still fail this one. The headline numbers therefore compare "
         "the gap with a no-bias benchmark computed from these data: the map's values shuffled among tiles at "
         "the same census percentile, which keeps the real groups and map noise but removes any "
         "group-specific error.",
         [("map_decile_errors", {"map_decile": ("Map decile", "int"), **decile_cols}, None)]),
        ("audit_specs", "Indigenous coefficient across specifications", None,
         [("audit_regressions", {"spec": ("Specification", "str"), "coef": ("Coef (pp)", "pp"),
                                 "ci_low": ("CI low", "pp"), "ci_high": ("CI high", "pp"),
                                 "p_one_sided": ("p (one-sided)", "p"), "n": ("Tiles", "int")}, None)]),
        ("rwi_coverage", "Who is on the map", None,
         [("coverage", {"group": ("Group", "str"), "size_class": ("Size", "str"),
                        "localities": ("Localities", "int"),
                        "share_population_covered": ("Population covered", "pct")}, None)]),
        ("label_choice", "Label choice", None,
         [("label_choice", {"label": ("Label", "str"), "group": ("Group", "str"),
                            "share_in_poorest": ("Share in poorest 20%", "pct")}, None)]),
        ("challenger_bias", "Challenger models",
         "Primary loss: RMSE (the budget needs means right); primary fairness measure: signed bias. "
         "Calibration slope above 1 and variance ratio below 1 mean compressed predictions.",
         [("challenger_metrics_summary", {"model": ("Model", "str"), "group": ("Group", "str"),
                                          "bias_mean": ("Bias", "f3"), "rmse_mean": ("RMSE", "f3"),
                                          "mae_mean": ("MAE", "f3"),
                                          "calibration_slope_mean": ("Calibration slope", "f3"),
                                          "variance_ratio_mean": ("Variance ratio", "f3")}, people),
          ("challenger_paired", {"hypothesis": ("Hypothesis", "str"), "metric": ("Metric", "str"),
                                 "group": ("Group", "str"), "model_a": ("Model", "str"),
                                 "model_b": ("vs.", "str"), "mean_difference": ("Difference", "f3"),
                                 "p025": ("2.5%", "f3"), "p975": ("97.5%", "f3"),
                                 "share_a_worse": ("Draws where worse", "pct0"),
                                 "supported": ("Supported", "str")}, None,
           "**Paired comparisons on the same simulated surveys.** Difference = first model minus second, "
           "computed draw by draw; positive means the first model does worse. H4 (first row) is supported "
           "if the 95% range lies above zero.")]),
        ("challenger_deciles", "Where each model's errors fall", None,
         [("challenger_decile_bias_summary", {"model": ("Model", "str"), "group": ("Group", "str"),
                                              "decile": ("Decile", "int"), "bias_mean": ("Bias", "f3")}, None)]),
        ("conformal_coverage", "Prediction intervals",
         "Interval score = width plus a penalty for each miss (lower is better).",
         [("challenger_coverage_summary", {"model": ("Model", "str"), "method": ("Method", "str"),
                                           "frame": ("Localities", "str"), "group": ("Group", "str"),
                                           "coverage_mean": ("Coverage", "pct"), "width_mean": ("Width", "f3"),
                                           "interval_score_mean": ("Interval score", "f3")}, no_all)]),
        ("allocation", "Allocation",
         "Misallocated share = half the sum of absolute differences between map-based and census-based budget shares.",
         [("rwi_allocation_by_share", {"ind_bin": ("Municipal Indigenous share", "str"),
                                       "municipalities": ("Municipalities", "int"),
                                       "net_shift_pct": ("Change vs. census", "pct")}, None),
          ("rwi_allocation_errors", {"group": ("Group", "str"),
                                     "misallocation_share": ("Budget misallocated", "pct"),
                                     "ape_median": ("Median municipal error", "pct")}, None,
           "**Relative Wealth Index instead of the census:**"),
          ("challenger_municipal_summary", {"model": ("Model", "str"), "group": ("Group", "str"),
                                            "misallocation_share_mean": ("Budget misallocated", "pct"),
                                            "ape_median_mean": ("Median municipal error", "pct")}, None,
           "**Challenger models instead of the census** (mean over survey draws):")]),
        ("map", "Map",
         f"Regional patterns only: each hexagon (about {plots.MAP_HEX_KM} km across) is the population-weighted "
         f"mean of at least {plots.MAP_MIN_TILES} map tiles, and sparser hexagons are not drawn, so no single "
         "community can be read off the map ([publication rules](ethics.md#publication-rules)).",
         []),
    ]  # fmt: skip
    if (rob := _load(t, "robustness")) is not None:
        sections_rob = md_table(
            rob,
            {
                "variant": ("Variant", "str"),
                "rank_error_coef": ("Coef (pp)", "pp"),
                "ci_low": ("CI low", "pp"),
                "ci_high": ("CI high", "pp"),
                "decile_conditional_gap_pp": ("Within-decile gap (pp)", "pp"),
                "tiles": ("Tiles", "int"),
            },
        )
    else:
        sections_rob = None
    for fig_name, title, intro, tables in sections:
        loaded = []
        for name, cols, keep, *caption in tables:
            if (df := _load(t, name)) is not None:
                loaded.append((df if keep is None else keep(df), cols, caption[0] if caption else None))
        has_figure = fig_name is not None and (paths.figures / f"{fig_name}.png").exists()
        if not has_figure and not (fig_name is None and loaded):
            continue
        out += [f"## {title}", ""]
        if intro:
            out += [intro, ""]
        if has_figure:
            out += [_figure(rel, fig_name, title)]
        for df, cols, caption in loaded:
            if caption:
                out += [caption, "", md_table(df, cols), ""]
            elif has_figure:
                out += ['??? note "Table view"', "", "    " + md_table(df, cols).replace("\n", "\n    "), ""]
            else:
                out += [md_table(df, cols), ""]
    if sections_rob:
        out += [
            "## Robustness",
            "",
            "Pre-specified in section 7 of the [pre-analysis plan](pre_analysis_plan.md): the same "
            "specification with a different weighting, Indigenous measure, threshold, sample, or definition "
            "of poverty.",
            "",
            sections_rob,
            "",
        ]
    page = paths.docs / ("validation.md" if mode == "demo" else "results.md")
    page.write_text("\n".join(out) + "\n", encoding="utf-8")
    (paths.results / "headline.md").write_text("\n".join(_headline(audit_summary)) + "\n", encoding="utf-8")
    return page


def report(mode: str = "real", root: Path | None = None) -> dict:
    figures = render_figures(mode, root)
    page = write_page(mode, root)
    return {"figures": figures, "page": str(page)}
