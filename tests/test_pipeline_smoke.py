"""End-to-end run of every step on a tiny synthetic world in a throwaway repository."""

import json
import warnings

from mapaudit import pipeline, report
from mapaudit.config import get_paths
from mapaudit.plots import FigureLayoutWarning


def test_demo_pipeline_end_to_end(tmp_repo):
    warnings.simplefilter("error", FigureLayoutWarning)  # clipped or overlapping text fails the test
    pipeline.build("demo", tmp_repo)
    summary = pipeline.audit("demo", tmp_repo)
    assert {"rank_error_coef_full_spec", "rwi_net_shift_indigenous_pct"} <= set(summary)
    robust = pipeline.robustness("demo", tmp_repo)
    assert {"Primary specification", "Language-based Indigenous share"} <= set(robust["variant"])
    pipeline.simulate("demo", tmp_repo)
    pipeline.validate(tmp_repo)
    out = report.report("demo", tmp_repo)

    paths = get_paths("demo", tmp_repo)
    for table in [
        "coverage",
        "decile_errors",
        "audit_regressions",
        "label_choice",
        "rwi_allocation",
        "challenger_metrics_summary",
        "challenger_coverage_summary",
        "validation",
        "robustness",
        "confirmatory_tests",
        "map_decile_errors",
        "evaluation_coverage",
        "challenger_paired",
        "challenger_decile_bias_summary",
        "challenger_municipal_summary",
        "rwi_allocation_errors",
    ]:
        assert (paths.tables / f"{table}.csv").exists(), table
    assert {"decile_errors", "map_decile_errors", "challenger_deciles", "map", "validation"} <= set(
        out["figures"]
    )
    assert (paths.figures / "decile_errors-dark.png").exists()
    page = (tmp_repo / "docs" / "validation.md").read_text()
    assert "Synthetic data" in page and "Headline numbers" in page
    assert json.loads((paths.tables / "build_summary.json").read_text())["localities"] > 0
