# Who the Map Misses

**Machine-learning poverty maps are increasingly used to decide where aid goes. This project tests
whether they understate deprivation in Indigenous communities, and what that error would cost in a
real budget formula.**

Mexico is the test bed because its 2020 census reports, for every locality, how many people live in
Indigenous households and what infrastructure their dwellings have. That turns the census into
ground truth everywhere, so a map's errors can be measured across the whole country instead of at a
few survey clusters.

## What this project does

1. **Audits a deployed model.** Meta's Relative Wealth Index (RWI) is scored against census ground
   truth on the same 2.4 km tiles. Errors are compared *within the same true wealth decile*, which
   separates an Indigenous-specific blind spot from the known tendency of these maps to pull the
   poorest places toward the middle, and *within the same map decile*, which is what someone using
   the map experiences.
2. **Builds challengers.** Models trained on a realistic simulated survey use Google DeepMind's
   AlphaEarth satellite embeddings (or night lights) and are benchmarked against small area
   estimation, the statistical method these maps aim to replace.
3. **Tests the label.** Asset-based wealth, infrastructure deprivation and a marginalization index
   are built from the same census to show how the definition of poverty changes who counts as poorest.
4. **Prices the error.** Each map is plugged into a stylized version of Mexico's FAIS
   social-infrastructure formula and a "poorest 20%" targeting rule.
5. **Checks uncertainty for each group.** Conformal prediction intervals are evaluated for Indigenous
   and non-Indigenous localities separately, with and without group-conditional calibration.
6. **Scores each result by the decision it informs.** Error measures were fixed in advance: RMSE and
   signed bias rather than MAPE, compression diagnostics, and paired model comparisons
   ([why](methods.md#evaluation-metrics)).

The hypotheses were [written down before the analysis](pre_analysis_plan.md), and the pipeline is
[validated on synthetic data](validation.md) with biases of known size.

## Start here

- [Results](results.md): the findings, with every figure next to its table.
- [Methods](methods.md): definitions, models and design decisions.
- [Lab notebook](blog/index.md): how the project developed, one milestone at a time.
- [Reproduce](reproduce.md): run everything from raw data.
- [Notebooks](https://github.com/cody-allen-analytics/who-the-map-misses/tree/main/notebooks): the analysis
  step by step, from a two-minute synthetic demo to the real-data results.

!!! info "Scope"
    Map comparisons cover rural localities (fewer than 2,500 people), which INEGI records as points
    and which contain most Indigenous-majority communities. Cities need block-level census data;
    see [Methods → Extensions](methods.md#extensions).
