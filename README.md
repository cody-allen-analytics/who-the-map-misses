# Who the Map Misses

**Do machine-learning poverty maps understate deprivation in Indigenous communities, and what would
that cost in a real budget formula?**

[![CI](https://github.com/cody-allen-analytics/who-the-map-misses/actions/workflows/ci.yml/badge.svg)](https://github.com/cody-allen-analytics/who-the-map-misses/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-website-blue)](https://cody-allen-analytics.github.io/who-the-map-misses/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Satellite-and-ML poverty maps are used to target cash transfers and infrastructure where surveys
are thin. This project audits one widely used map, Meta's Relative Wealth Index, against Mexico's
2020 census, which reports Indigenous population and dwelling infrastructure for every locality, and
builds challengers on Google DeepMind's AlphaEarth satellite embeddings and small area estimation.

## Key findings

<!-- FINDINGS:START (notebook 06 writes the generated findings here; edit the wording afterwards) -->
**Status:** pipeline complete and validated on synthetic data ([validation](docs/validation.md));
hypotheses pre-registered before any real-data analysis ([plan](docs/pre_analysis_plan.md), tag `pap-v1`).
Real-data results in progress.
<!-- FINDINGS:END -->

<!-- FIGURE:START (notebook 06 inserts the headline figure here) -->

<!-- FIGURE:END -->

Full results with a table under every figure: **[project website](https://cody-allen-analytics.github.io/who-the-map-misses/results/)**.

## What this project shows

| Question | Approach | Code |
|---|---|---|
| Does the deployed map misrank Indigenous places? | Rank error within true wealth deciles (separation) and within map deciles (calibration), the latter read against a no-bias benchmark from within-percentile permutations of the map; weighted regressions with municipality-clustered SEs; cluster bootstrap; Holm-adjusted confirmatory tests | [`audit.py`](src/mapaudit/audit.py) |
| Is it Indigeneity or just rurality and poverty? | Cumulative controls for size, remoteness, true decile and state; pre-specified robustness | [`audit.py`](src/mapaudit/audit.py), [`pipeline.py`](src/mapaudit/pipeline.py) |
| Does the definition of poverty matter? | Three labels from one census (DHS-style assets, infrastructure deprivation, CONAPO-style marginalization) | [`labels.py`](src/mapaudit/labels.py) |
| Can a foundation model do better? | Simulated two-stage survey; gradient boosting on AlphaEarth embeddings vs. a Fay-Herriot model with municipality random effects, written from scratch (REML) | [`survey.py`](src/mapaudit/survey.py), [`sae.py`](src/mapaudit/sae.py), [`ml.py`](src/mapaudit/ml.py) |
| Are uncertainty estimates honest for everyone? | Split conformal intervals: marginal vs. group-conditional (Mondrian), inside vs. outside the survey frame | [`conformal.py`](src/mapaudit/conformal.py) |
| What do the errors cost? | Poorest-20% targeting and a FAIS-style municipal formula | [`allocation.py`](src/mapaudit/allocation.py) |
| Are these the right error measures? | Metrics matched to the decision: RMSE for a formula that sums rates, signed bias for fairness, compression diagnostics, interval scores, misallocation share, paired comparisons; no MAPE on rates that are often zero | [`metrics.py`](src/mapaudit/metrics.py) |

## Research practices

- **Pre-registered.** Hypotheses, metrics and specifications were committed and tagged before the
  analysis ([pre-analysis plan](docs/pre_analysis_plan.md)); changes go in a deviations log.
- **Metrics chosen for the decision.** Each error measure was fixed in advance for the decision it
  informs, and reported per person and per community ([evaluation metrics](docs/methods.md#evaluation-metrics)).
- **Validated.** The audit is run on synthetic worlds with and without a planted bias. It must find the
  bias when it is there and nothing when it isn't ([validation](docs/validation.md)). CI runs this on every push.
- **Design decisions are documented.** For example, map comparisons are restricted to rural localities
  because the census gives each city a single point ([methods](docs/methods.md#units-and-scope)).
- **No hand-typed numbers.** Every number on the website is generated from `results/real/tables`.
- **Indigenous data sovereignty.** The audit studies the algorithm, not the communities. Only aggregates
  are published: no table identifies a locality (a test enforces it), maps show ~40 km regions rather than
  communities, and locality-level predictions stay unpublished. Affected communities can ask for a result
  to be corrected or withdrawn, and the page states openly where the project falls short of the CARE
  principles ([ethics & Indigenous data sovereignty](docs/ethics.md), with a summary in Spanish).

## Quickstart

- **In your browser, nothing to install:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cody-allen-analytics/who-the-map-misses/blob/main/notebooks/01_demo.ipynb)
  runs the whole pipeline on synthetic data in about two minutes.
- **In JupyterLab:** run `notebooks/00_setup.ipynb`, then `01_demo.ipynb`. Notebooks 02-06 run the real-data analysis.
- **From a terminal:** `pip install -e ".[dev]"`, then `mapaudit demo` and `pytest` (40+ tests, including
  planted-bias validation; CI also executes every notebook).

Real data (INEGI census, Meta RWI, Earth Engine export): see **[Reproduce](docs/reproduce.md)**.

## Repository map

```
config/            analysis parameters and data sources (everything that affects a number)
src/mapaudit/      census.py  labels.py  rwi.py  audit.py  survey.py  sae.py  ml.py  conformal.py
                   allocation.py  simulate.py  pipeline.py  report.py  plots.py  gee.py  cli.py
                   notebook.py (notebook helpers)  publication.py (only aggregates are published)
                   upload.py (web-upload fallback, no git)
notebooks/         00_setup → 01_demo → 02_ground_truth → 03_audit → 04_satellite_features
                   → 05_challengers → 06_report_and_release (thin drivers over the package)
scripts/           gee_export_alphaearth.py (Earth Engine export), check_release.py
tests/             unit tests, planted-bias validation, end-to-end smoke test
results/real/      committed tables and figures
docs/              website: results, pre-analysis plan, methods, data/model cards, ethics & Indigenous
                   data sovereignty, lab notebook
```

## Data

| Source | Use | License |
|---|---|---|
| INEGI Censo 2020, results by locality (ITER) | Ground truth | INEGI free-use terms |
| Meta Relative Wealth Index (HDX) | Map under audit | See HDX page |
| AlphaEarth Foundations Satellite Embedding (Google DeepMind) | Challenger features | CC-BY 4.0 |
| VIIRS annual night lights | Baseline features | See catalog |

Raw data is not committed; notebook 02 downloads it. Details and known issues: [data card](docs/data_card.md).

## Limitations

Rural localities only; census labels describe dwellings and education, not income; the RWI and the
census are a year or more apart; results describe places, not households; the census's Indigenous
measures are based on language, not self-identification. See [methods](docs/methods.md#limitations)
and [who counts as Indigenous here](docs/ethics.md#who-counts-as-indigenous-here).

## Citation

See [`CITATION.cff`](CITATION.cff). Code is MIT-licensed; text and figures are CC BY 4.0.
