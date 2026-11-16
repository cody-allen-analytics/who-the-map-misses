# Validation on synthetic data

!!! warning "Synthetic data"
    Everything on this page comes from **synthetic** data with biases planted on purpose. It shows that the
    pipeline runs end to end and that the audit can detect a bias of known size. It says nothing about Mexico.
    Real results live on the [Results](results.md) page.

## Does the audit find a planted bias, and only when it is there?

Two fresh synthetic worlds drawn with the demo settings, one with the planted bias and one without. Without it, the coefficient and the equally-poor gap should be near zero. The ranked-equally gap need not be: when groups differ in average wealth, a map whose errors ignore group still shows a gap among places it ranks the same (see [Methods](methods.md#two-views-of-fairness)).

![Validation: estimated coefficients with and without planted bias](assets/figures/demo/validation.png#only-light)
![Validation: estimated coefficients with and without planted bias](assets/figures/demo/validation-dark.png#only-dark)

| World | Planted RWI bias (SD) | Rank-error coef (pp) | CI low | CI high | Gap: equally poor (pp) | Gap: ranked equally (pp) | Coverage coef |
|---|---|---|---|---|---|---|---|
| Bias planted | 0.600 | +25.5 | +20.2 | +30.9 | +12.0 | +12.9 | -0.072 |
| No bias planted | 0.000 | +0.2 | -4.4 | +4.8 | -0.8 | +4.3 | -0.010 |

## Data at a glance

| Localities | Rural (in scope) | With dwelling data | Indigenous localities | RWI tiles analyzed | With satellite features |
|---|---|---|---|---|---|
| 6,836 | 6,733 | 5,606 | 1,695 | 4,464 | 6,836 |

## Headline numbers

- **Rank bias.** Holding true wealth decile, settlement size, remoteness, altitude, and state fixed, the map ranks an all-Indigenous tile **+20.3 percentile points** higher than a non-Indigenous tile relative to the census (95% CI +15.1 to +25.5; one-sided p = 1.14e-14, Holm-adjusted p = 2.27e-14).
- **Within the same true decile**, Indigenous tiles' average rank error exceeds non-Indigenous tiles' by +8.6 points (weighted by Indigenous population).
- **Among places the map ranks the same**, Indigenous tiles' rank error is +13.8 points higher, i.e. they are poorer than the map says. This view can show a gap even for a map with group-blind errors, because groups differ in average wealth.
- **Coverage.** 90.9% of the Indigenous rural population lies inside a map tile, vs. 92.8% of the non-Indigenous rural population.
- **Money.** Using the map instead of the census in a FAIS-style formula changes the allocation to Indigenous-majority municipalities by **-26.3%** (-102.1 million pesos per billion allocated); 11.6% of the whole budget goes to the wrong municipalities.
- **Targeting.** Selecting the poorest 20% by the map leaves out 49% of the truly poorest Indigenous population vs. 35% of the truly poorest non-Indigenous population.

## Confirmatory tests

H1 and H2 as pre-registered: H2 one-sided, Holm's correction across both.

| Hypothesis | Estimate | CI low | CI high | Test | p | p (Holm) | Supported at 5% |
|---|---|---|---|---|---|---|---|
| H1 coverage | -0.071 | -0.111 | -0.031 | two-sided | 5.4e-04 | 5.4e-04 | yes |
| H2 rank bias | 20.257 | 15.056 | 25.458 | one-sided (> 0) | 1.1e-14 | 2.3e-14 | yes |

## Who each analysis covers

Metrics exist only where the census truth is known. Share of the in-scope population each analysis actually evaluates:

| Analysis | Group | Population evaluated |
|---|---|---|
| RWI rank-error audit | Indigenous | 90.4% |
| RWI rank-error audit | Non-Indigenous | 92.4% |
| RWI rank-error audit | Unknown (suppressed data) | 0.0% |

| Analysis | Group | Population evaluated |
|---|---|---|
| Challenger models (rural localities) | Indigenous | 100.0% |
| Challenger models (rural localities) | Non-Indigenous | 100.0% |
| Challenger models (rural localities) | Unknown (suppressed data) | 0.0% |

## Rank error by true wealth decile (separation view)

![Rank error by true wealth decile (separation view)](assets/figures/demo/decile_errors.png#only-light)
![Rank error by true wealth decile (separation view)](assets/figures/demo/decile_errors-dark.png#only-dark)

??? note "Table view"

    | True decile | Group | Mean rank error (pp) | CI low | CI high | Tiles |
    |---|---|---|---|---|---|
    | 1 | Non-Indigenous | +5.2 | +3.3 | +7.6 | 529 |
    | 1 | Indigenous | +10.4 | +8.6 | +12.0 | 575 |
    | 2 | Non-Indigenous | +2.7 | +0.6 | +4.6 | 448 |
    | 2 | Indigenous | +16.7 | +10.8 | +22.0 | 213 |
    | 3 | Non-Indigenous | +2.1 | -0.1 | +4.3 | 443 |
    | 3 | Indigenous | +14.9 | +8.7 | +22.5 | 161 |
    | 4 | Non-Indigenous | -0.6 | -4.5 | +2.7 | 342 |
    | 4 | Indigenous | +10.6 | +5.1 | +16.0 | 90 |
    | 5 | Non-Indigenous | +1.1 | -2.0 | +4.2 | 378 |
    | 5 | Indigenous | +10.6 | +5.3 | +17.2 | 91 |
    | 6 | Non-Indigenous | -1.2 | -4.5 | +2.5 | 271 |
    | 6 | Indigenous | +5.4 | -2.2 | +13.0 | 43 |
    | 7 | Non-Indigenous | -3.7 | -8.6 | +1.8 | 223 |
    | 7 | Indigenous | -2.2 | -14.5 | +7.4 | 40 |
    | 8 | Non-Indigenous | -11.7 | -16.6 | -6.8 | 207 |
    | 8 | Indigenous | +3.1 | -6.4 | +8.1 | 40 |
    | 9 | Non-Indigenous | -7.3 | -12.0 | -3.3 | 153 |
    | 9 | Indigenous | -11.0 | -23.2 | +1.5 | 28 |
    | 10 | Non-Indigenous | -8.8 | -12.7 | -5.6 | 168 |
    | 10 | Indigenous | -6.4 | -10.5 | -3.5 | 21 |

## Places the map ranks the same (calibration view)

Read with the previous figure: when groups differ in average wealth, a map whose errors ignore group can pass the separation test and still fail this one.

![Places the map ranks the same (calibration view)](assets/figures/demo/map_decile_errors.png#only-light)
![Places the map ranks the same (calibration view)](assets/figures/demo/map_decile_errors-dark.png#only-dark)

??? note "Table view"

    | Map decile | Group | Mean rank error (pp) | CI low | CI high | Tiles |
    |---|---|---|---|---|---|
    | 1 | Non-Indigenous | -10.6 | -12.3 | -9.3 | 687 |
    | 1 | Indigenous | -2.6 | -4.2 | -0.7 | 370 |
    | 2 | Non-Indigenous | -14.6 | -18.4 | -10.3 | 436 |
    | 2 | Indigenous | +2.2 | -0.7 | +4.6 | 210 |
    | 3 | Non-Indigenous | -8.8 | -12.7 | -4.9 | 399 |
    | 3 | Indigenous | +4.8 | -0.1 | +9.8 | 188 |
    | 4 | Non-Indigenous | -8.9 | -14.3 | -4.8 | 344 |
    | 4 | Indigenous | +7.0 | -1.0 | +12.9 | 127 |
    | 5 | Non-Indigenous | -6.7 | -11.5 | -0.9 | 281 |
    | 5 | Indigenous | +11.8 | +7.0 | +16.2 | 113 |
    | 6 | Non-Indigenous | -5.6 | -8.9 | -2.7 | 260 |
    | 6 | Indigenous | +10.8 | +3.8 | +17.3 | 66 |
    | 7 | Non-Indigenous | +1.4 | -3.2 | +4.7 | 243 |
    | 7 | Indigenous | +16.0 | +6.9 | +28.0 | 60 |
    | 8 | Non-Indigenous | +4.8 | -0.6 | +10.7 | 177 |
    | 8 | Indigenous | +15.7 | +9.1 | +23.5 | 81 |
    | 9 | Non-Indigenous | +7.1 | +3.1 | +11.2 | 201 |
    | 9 | Indigenous | +22.7 | +14.4 | +33.0 | 56 |
    | 10 | Non-Indigenous | +6.2 | +3.9 | +10.1 | 134 |
    | 10 | Indigenous | +11.3 | +4.3 | +20.2 | 31 |

## Indigenous coefficient across specifications

![Indigenous coefficient across specifications](assets/figures/demo/audit_specs.png#only-light)
![Indigenous coefficient across specifications](assets/figures/demo/audit_specs-dark.png#only-dark)

??? note "Table view"

    | Specification | Coef (pp) | CI low | CI high | p (one-sided) | Tiles |
    |---|---|---|---|---|---|
    | 1 none | +27.0 | +22.7 | +31.2 | 4.2e-35 | 4,452 |
    | 2 + rurality | +26.6 | +22.3 | +30.8 | 3.2e-35 | 4,452 |
    | 3 + remoteness | +26.2 | +21.7 | +30.7 | 1.9e-30 | 4,452 |
    | 4 + true decile | +20.7 | +16.3 | +25.1 | 1.1e-20 | 4,452 |
    | 5 + state FE | +20.3 | +15.1 | +25.5 | 1.1e-14 | 4,452 |

## Who is on the map

![Who is on the map](assets/figures/demo/rwi_coverage.png#only-light)
![Who is on the map](assets/figures/demo/rwi_coverage-dark.png#only-dark)

??? note "Table view"

    | Group | Size | Localities | Population covered |
    |---|---|---|---|
    | Non-Indigenous | <100 | 2,547 | 87.9% |
    | Non-Indigenous | 100-499 | 1,019 | 92.3% |
    | Non-Indigenous | 500-2,499 | 246 | 95.0% |
    | Indigenous | <100 | 1,220 | 84.3% |
    | Indigenous | 100-499 | 390 | 88.8% |
    | Indigenous | 500-2,499 | 81 | 96.9% |
    | Non-Indigenous | All | 3,812 | 92.8% |
    | Indigenous | All | 1,691 | 90.9% |

## Label choice

![Label choice](assets/figures/demo/label_choice.png#only-light)
![Label choice](assets/figures/demo/label_choice-dark.png#only-dark)

??? note "Table view"

    | Label | Group | Share in poorest 20% |
    |---|---|---|
    | wealth_dhs_like | Non-Indigenous | 15.7% |
    | wealth_dhs_like | Indigenous | 87.4% |
    | dep_infra | Non-Indigenous | 15.3% |
    | dep_infra | Indigenous | 92.7% |
    | marg_index | Non-Indigenous | 15.2% |
    | marg_index | Indigenous | 94.3% |

## Challenger models

Primary loss: RMSE (the budget needs means right); primary fairness measure: signed bias. Calibration slope above 1 and variance ratio below 1 mean compressed predictions.

![Challenger models](assets/figures/demo/challenger_bias.png#only-light)
![Challenger models](assets/figures/demo/challenger_bias-dark.png#only-dark)

??? note "Table view"

    | Model | Group | Bias | RMSE | MAE | Calibration slope | Variance ratio |
    |---|---|---|---|---|---|---|
    | Embeddings (Fay-Herriot) | All | 0.003 | 0.036 | 0.026 | 1.001 | 0.804 |
    | Embeddings (Fay-Herriot) | Indigenous | -0.007 | 0.047 | 0.033 | 1.195 | 0.570 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 0.007 | 0.031 | 0.024 | 0.849 | 1.094 |
    | Embeddings (GBM + EB) | All | 0.004 | 0.040 | 0.028 | 1.013 | 0.739 |
    | Embeddings (GBM + EB) | Indigenous | -0.013 | 0.055 | 0.040 | 1.127 | 0.581 |
    | Embeddings (GBM + EB) | Non-Indigenous | 0.009 | 0.033 | 0.024 | 0.872 | 0.989 |
    | Embeddings (GBM) | All | 0.003 | 0.040 | 0.028 | 1.057 | 0.675 |
    | Embeddings (GBM) | Indigenous | -0.018 | 0.056 | 0.039 | 1.204 | 0.517 |
    | Embeddings (GBM) | Non-Indigenous | 0.011 | 0.033 | 0.024 | 0.892 | 0.952 |
    | Nightlights (GBM) | All | -0.001 | 0.068 | 0.049 | 0.920 | 0.325 |
    | Nightlights (GBM) | Indigenous | -0.040 | 0.095 | 0.070 | 1.063 | 0.222 |
    | Nightlights (GBM) | Non-Indigenous | 0.013 | 0.055 | 0.041 | 0.720 | 0.522 |

**Paired comparisons on the same simulated surveys.** Difference = first model minus second, computed draw by draw; positive means the first model does worse. H4 (first row) is supported if the 95% range lies above zero.

| Hypothesis | Metric | Group | Model | vs. | Difference | 2.5% | 97.5% | Draws where worse | Supported |
|---|---|---|---|---|---|---|---|---|---|
| H4 | \|bias\| | Indigenous | Embeddings (GBM) | Embeddings (Fay-Herriot) | 0.011 | 0.009 | 0.013 | 100% | yes |
| – | rmse | Indigenous | Embeddings (GBM + EB) | Embeddings (Fay-Herriot) | 0.008 | 0.005 | 0.011 | 100% | – |
| – | rmse | Non-Indigenous | Embeddings (GBM + EB) | Embeddings (Fay-Herriot) | 0.002 | 0.002 | 0.003 | 100% | – |
| – | rmse | All | Embeddings (GBM + EB) | Embeddings (Fay-Herriot) | 0.004 | 0.003 | 0.005 | 100% | – |
| – | rmse | Indigenous | Embeddings (GBM) | Embeddings (Fay-Herriot) | 0.009 | 0.006 | 0.012 | 100% | – |
| – | rmse | Non-Indigenous | Embeddings (GBM) | Embeddings (Fay-Herriot) | 0.002 | 0.001 | 0.003 | 100% | – |
| – | rmse | All | Embeddings (GBM) | Embeddings (Fay-Herriot) | 0.005 | 0.004 | 0.005 | 100% | – |
| – | rmse | Indigenous | Nightlights (GBM) | Embeddings (Fay-Herriot) | 0.048 | 0.046 | 0.051 | 100% | – |
| – | rmse | Non-Indigenous | Nightlights (GBM) | Embeddings (Fay-Herriot) | 0.025 | 0.023 | 0.026 | 100% | – |
| – | rmse | All | Nightlights (GBM) | Embeddings (Fay-Herriot) | 0.033 | 0.031 | 0.033 | 100% | – |

## Where each model's errors fall

![Where each model's errors fall](assets/figures/demo/challenger_deciles.png#only-light)
![Where each model's errors fall](assets/figures/demo/challenger_deciles-dark.png#only-dark)

??? note "Table view"

    | Model | Group | Decile | Bias |
    |---|---|---|---|
    | Embeddings (Fay-Herriot) | Indigenous | 1 | 0.014 |
    | Embeddings (Fay-Herriot) | Indigenous | 2 | 0.005 |
    | Embeddings (Fay-Herriot) | Indigenous | 3 | 0.011 |
    | Embeddings (Fay-Herriot) | Indigenous | 4 | 0.003 |
    | Embeddings (Fay-Herriot) | Indigenous | 5 | 0.010 |
    | Embeddings (Fay-Herriot) | Indigenous | 6 | 0.014 |
    | Embeddings (Fay-Herriot) | Indigenous | 7 | 0.014 |
    | Embeddings (Fay-Herriot) | Indigenous | 8 | 0.011 |
    | Embeddings (Fay-Herriot) | Indigenous | 9 | 0.004 |
    | Embeddings (Fay-Herriot) | Indigenous | 10 | -0.056 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 1 | -0.002 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 2 | 0.000 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 3 | 0.010 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 4 | 0.007 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 5 | 0.009 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 6 | 0.018 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 7 | 0.020 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 8 | 0.018 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 9 | 0.010 |
    | Embeddings (Fay-Herriot) | Non-Indigenous | 10 | -0.032 |
    | Embeddings (GBM + EB) | Indigenous | 1 | 0.018 |
    | Embeddings (GBM + EB) | Indigenous | 2 | 0.018 |
    | Embeddings (GBM + EB) | Indigenous | 3 | 0.012 |
    | Embeddings (GBM + EB) | Indigenous | 4 | 0.007 |
    | Embeddings (GBM + EB) | Indigenous | 5 | 0.013 |
    | Embeddings (GBM + EB) | Indigenous | 6 | 0.018 |
    | Embeddings (GBM + EB) | Indigenous | 7 | 0.007 |
    | Embeddings (GBM + EB) | Indigenous | 8 | 0.001 |
    | Embeddings (GBM + EB) | Indigenous | 9 | -0.010 |
    | Embeddings (GBM + EB) | Indigenous | 10 | -0.065 |
    | Embeddings (GBM + EB) | Non-Indigenous | 1 | 0.014 |
    | Embeddings (GBM + EB) | Non-Indigenous | 2 | 0.012 |
    | Embeddings (GBM + EB) | Non-Indigenous | 3 | 0.015 |
    | Embeddings (GBM + EB) | Non-Indigenous | 4 | 0.010 |
    | Embeddings (GBM + EB) | Non-Indigenous | 5 | 0.010 |
    | Embeddings (GBM + EB) | Non-Indigenous | 6 | 0.013 |
    | Embeddings (GBM + EB) | Non-Indigenous | 7 | 0.010 |
    | Embeddings (GBM + EB) | Non-Indigenous | 8 | 0.011 |
    | Embeddings (GBM + EB) | Non-Indigenous | 9 | 0.004 |
    | Embeddings (GBM + EB) | Non-Indigenous | 10 | -0.028 |
    | Embeddings (GBM) | Indigenous | 1 | 0.020 |
    | Embeddings (GBM) | Indigenous | 2 | 0.017 |
    | Embeddings (GBM) | Indigenous | 3 | 0.012 |
    | Embeddings (GBM) | Indigenous | 4 | 0.007 |
    | Embeddings (GBM) | Indigenous | 5 | 0.011 |
    | Embeddings (GBM) | Indigenous | 6 | 0.013 |
    | Embeddings (GBM) | Indigenous | 7 | 0.002 |
    | Embeddings (GBM) | Indigenous | 8 | -0.005 |
    | Embeddings (GBM) | Indigenous | 9 | -0.018 |
    | Embeddings (GBM) | Indigenous | 10 | -0.074 |
    | Embeddings (GBM) | Non-Indigenous | 1 | 0.017 |
    | Embeddings (GBM) | Non-Indigenous | 2 | 0.014 |
    | Embeddings (GBM) | Non-Indigenous | 3 | 0.017 |
    | Embeddings (GBM) | Non-Indigenous | 4 | 0.013 |
    | Embeddings (GBM) | Non-Indigenous | 5 | 0.013 |
    | Embeddings (GBM) | Non-Indigenous | 6 | 0.015 |
    | Embeddings (GBM) | Non-Indigenous | 7 | 0.011 |
    | Embeddings (GBM) | Non-Indigenous | 8 | 0.012 |
    | Embeddings (GBM) | Non-Indigenous | 9 | 0.006 |
    | Embeddings (GBM) | Non-Indigenous | 10 | -0.028 |
    | Nightlights (GBM) | Indigenous | 1 | 0.064 |
    | Nightlights (GBM) | Indigenous | 2 | 0.053 |
    | Nightlights (GBM) | Indigenous | 3 | 0.037 |
    | Nightlights (GBM) | Indigenous | 4 | 0.041 |
    | Nightlights (GBM) | Indigenous | 5 | 0.022 |
    | Nightlights (GBM) | Indigenous | 6 | 0.007 |
    | Nightlights (GBM) | Indigenous | 7 | 0.009 |
    | Nightlights (GBM) | Indigenous | 8 | -0.029 |
    | Nightlights (GBM) | Indigenous | 9 | -0.054 |
    | Nightlights (GBM) | Indigenous | 10 | -0.148 |
    | Nightlights (GBM) | Non-Indigenous | 1 | 0.048 |
    | Nightlights (GBM) | Non-Indigenous | 2 | 0.035 |
    | Nightlights (GBM) | Non-Indigenous | 3 | 0.031 |
    | Nightlights (GBM) | Non-Indigenous | 4 | 0.028 |
    | Nightlights (GBM) | Non-Indigenous | 5 | 0.031 |
    | Nightlights (GBM) | Non-Indigenous | 6 | 0.017 |
    | Nightlights (GBM) | Non-Indigenous | 7 | 0.004 |
    | Nightlights (GBM) | Non-Indigenous | 8 | -0.011 |
    | Nightlights (GBM) | Non-Indigenous | 9 | -0.045 |
    | Nightlights (GBM) | Non-Indigenous | 10 | -0.108 |

## Prediction intervals

Interval score = width plus a penalty for each miss (lower is better).

![Prediction intervals](assets/figures/demo/conformal_coverage.png#only-light)
![Prediction intervals](assets/figures/demo/conformal_coverage-dark.png#only-dark)

??? note "Table view"

    | Model | Method | Localities | Group | Coverage | Width | Interval score |
    |---|---|---|---|---|---|---|
    | Embeddings (Fay-Herriot) | Marginal | All unsampled | Indigenous | 78.4% | 0.145 | 0.366 |
    | Embeddings (Fay-Herriot) | Marginal | All unsampled | Non-Indigenous | 90.7% | 0.145 | 0.197 |
    | Embeddings (Fay-Herriot) | Marginal | In survey frame | Indigenous | 87.5% | 0.145 | 0.240 |
    | Embeddings (Fay-Herriot) | Marginal | In survey frame | Non-Indigenous | 96.5% | 0.145 | 0.164 |
    | Embeddings (Fay-Herriot) | Marginal | Outside survey frame | Indigenous | 65.8% | 0.145 | 0.538 |
    | Embeddings (Fay-Herriot) | Marginal | Outside survey frame | Non-Indigenous | 82.0% | 0.145 | 0.247 |
    | Embeddings (Fay-Herriot) | Mondrian: group | All unsampled | Indigenous | 84.9% | 0.187 | 0.341 |
    | Embeddings (Fay-Herriot) | Mondrian: group | All unsampled | Non-Indigenous | 88.2% | 0.132 | 0.197 |
    | Embeddings (Fay-Herriot) | Mondrian: group | In survey frame | Indigenous | 92.2% | 0.187 | 0.248 |
    | Embeddings (Fay-Herriot) | Mondrian: group | In survey frame | Non-Indigenous | 95.1% | 0.132 | 0.155 |
    | Embeddings (Fay-Herriot) | Mondrian: group | Outside survey frame | Indigenous | 74.9% | 0.187 | 0.468 |
    | Embeddings (Fay-Herriot) | Mondrian: group | Outside survey frame | Non-Indigenous | 77.7% | 0.132 | 0.259 |
    | Embeddings (Fay-Herriot) | Mondrian: group x size | All unsampled | Indigenous | 84.6% | 0.187 | 0.343 |
    | Embeddings (Fay-Herriot) | Mondrian: group x size | All unsampled | Non-Indigenous | 88.0% | 0.132 | 0.198 |
    | Embeddings (Fay-Herriot) | Mondrian: group x size | In survey frame | Indigenous | 91.7% | 0.187 | 0.251 |
    | Embeddings (Fay-Herriot) | Mondrian: group x size | In survey frame | Non-Indigenous | 94.9% | 0.132 | 0.157 |
    | Embeddings (Fay-Herriot) | Mondrian: group x size | Outside survey frame | Indigenous | 74.9% | 0.187 | 0.469 |
    | Embeddings (Fay-Herriot) | Mondrian: group x size | Outside survey frame | Non-Indigenous | 77.6% | 0.131 | 0.259 |
    | Embeddings (GBM + EB) | Marginal | All unsampled | Indigenous | 78.9% | 0.167 | 0.397 |
    | Embeddings (GBM + EB) | Marginal | All unsampled | Non-Indigenous | 92.3% | 0.167 | 0.209 |
    | Embeddings (GBM + EB) | Marginal | In survey frame | Indigenous | 87.0% | 0.167 | 0.263 |
    | Embeddings (GBM + EB) | Marginal | In survey frame | Non-Indigenous | 95.8% | 0.167 | 0.188 |
    | Embeddings (GBM + EB) | Marginal | Outside survey frame | Indigenous | 67.8% | 0.167 | 0.579 |
    | Embeddings (GBM + EB) | Marginal | Outside survey frame | Non-Indigenous | 87.1% | 0.167 | 0.242 |
    | Embeddings (GBM + EB) | Mondrian: group | All unsampled | Indigenous | 84.9% | 0.210 | 0.372 |
    | Embeddings (GBM + EB) | Mondrian: group | All unsampled | Non-Indigenous | 89.5% | 0.150 | 0.208 |
    | Embeddings (GBM + EB) | Mondrian: group | In survey frame | Indigenous | 91.9% | 0.210 | 0.270 |
    | Embeddings (GBM + EB) | Mondrian: group | In survey frame | Non-Indigenous | 94.0% | 0.150 | 0.180 |
    | Embeddings (GBM + EB) | Mondrian: group | Outside survey frame | Indigenous | 75.3% | 0.210 | 0.511 |
    | Embeddings (GBM + EB) | Mondrian: group | Outside survey frame | Non-Indigenous | 82.7% | 0.150 | 0.251 |
    | Embeddings (GBM + EB) | Mondrian: group x size | All unsampled | Indigenous | 85.3% | 0.216 | 0.374 |
    | Embeddings (GBM + EB) | Mondrian: group x size | All unsampled | Non-Indigenous | 89.5% | 0.150 | 0.208 |
    | Embeddings (GBM + EB) | Mondrian: group x size | In survey frame | Indigenous | 92.3% | 0.218 | 0.274 |
    | Embeddings (GBM + EB) | Mondrian: group x size | In survey frame | Non-Indigenous | 94.0% | 0.150 | 0.180 |
    | Embeddings (GBM + EB) | Mondrian: group x size | Outside survey frame | Indigenous | 75.9% | 0.213 | 0.510 |
    | Embeddings (GBM + EB) | Mondrian: group x size | Outside survey frame | Non-Indigenous | 82.7% | 0.150 | 0.251 |
    | Embeddings (GBM) | Marginal | All unsampled | Indigenous | 76.7% | 0.166 | 0.428 |
    | Embeddings (GBM) | Marginal | All unsampled | Non-Indigenous | 91.7% | 0.166 | 0.210 |
    | Embeddings (GBM) | Marginal | In survey frame | Indigenous | 85.6% | 0.166 | 0.276 |
    | Embeddings (GBM) | Marginal | In survey frame | Non-Indigenous | 95.5% | 0.166 | 0.187 |
    | Embeddings (GBM) | Marginal | Outside survey frame | Indigenous | 64.5% | 0.166 | 0.636 |
    | Embeddings (GBM) | Marginal | Outside survey frame | Non-Indigenous | 85.9% | 0.166 | 0.245 |
    | Embeddings (GBM) | Mondrian: group | All unsampled | Indigenous | 83.8% | 0.214 | 0.392 |
    | Embeddings (GBM) | Mondrian: group | All unsampled | Non-Indigenous | 87.8% | 0.142 | 0.210 |
    | Embeddings (GBM) | Mondrian: group | In survey frame | Indigenous | 91.4% | 0.214 | 0.280 |
    | Embeddings (GBM) | Mondrian: group | In survey frame | Non-Indigenous | 93.4% | 0.142 | 0.177 |
    | Embeddings (GBM) | Mondrian: group | Outside survey frame | Indigenous | 73.5% | 0.214 | 0.546 |
    | Embeddings (GBM) | Mondrian: group | Outside survey frame | Non-Indigenous | 79.5% | 0.142 | 0.261 |
    | Embeddings (GBM) | Mondrian: group x size | All unsampled | Indigenous | 84.2% | 0.217 | 0.391 |
    | Embeddings (GBM) | Mondrian: group x size | All unsampled | Non-Indigenous | 87.8% | 0.143 | 0.210 |
    | Embeddings (GBM) | Mondrian: group x size | In survey frame | Indigenous | 91.8% | 0.218 | 0.279 |
    | Embeddings (GBM) | Mondrian: group x size | In survey frame | Non-Indigenous | 93.3% | 0.143 | 0.177 |
    | Embeddings (GBM) | Mondrian: group x size | Outside survey frame | Indigenous | 73.8% | 0.216 | 0.544 |
    | Embeddings (GBM) | Mondrian: group x size | Outside survey frame | Non-Indigenous | 79.4% | 0.142 | 0.261 |
    | Nightlights (GBM) | Marginal | All unsampled | Indigenous | 70.3% | 0.250 | 0.704 |
    | Nightlights (GBM) | Marginal | All unsampled | Non-Indigenous | 88.1% | 0.250 | 0.339 |
    | Nightlights (GBM) | Marginal | In survey frame | Indigenous | 79.7% | 0.250 | 0.491 |
    | Nightlights (GBM) | Marginal | In survey frame | Non-Indigenous | 94.0% | 0.250 | 0.285 |
    | Nightlights (GBM) | Marginal | Outside survey frame | Indigenous | 57.6% | 0.250 | 0.995 |
    | Nightlights (GBM) | Marginal | Outside survey frame | Non-Indigenous | 79.0% | 0.250 | 0.421 |
    | Nightlights (GBM) | Mondrian: group | All unsampled | Indigenous | 81.0% | 0.340 | 0.612 |
    | Nightlights (GBM) | Mondrian: group | All unsampled | Non-Indigenous | 83.5% | 0.223 | 0.348 |
    | Nightlights (GBM) | Mondrian: group | In survey frame | Indigenous | 88.6% | 0.340 | 0.471 |
    | Nightlights (GBM) | Mondrian: group | In survey frame | Non-Indigenous | 91.0% | 0.223 | 0.277 |
    | Nightlights (GBM) | Mondrian: group | Outside survey frame | Indigenous | 70.5% | 0.340 | 0.806 |
    | Nightlights (GBM) | Mondrian: group | Outside survey frame | Non-Indigenous | 72.2% | 0.223 | 0.456 |
    | Nightlights (GBM) | Mondrian: group x size | All unsampled | Indigenous | 81.4% | 0.344 | 0.612 |
    | Nightlights (GBM) | Mondrian: group x size | All unsampled | Non-Indigenous | 84.4% | 0.225 | 0.344 |
    | Nightlights (GBM) | Mondrian: group x size | In survey frame | Indigenous | 89.1% | 0.346 | 0.470 |
    | Nightlights (GBM) | Mondrian: group x size | In survey frame | Non-Indigenous | 92.0% | 0.224 | 0.271 |
    | Nightlights (GBM) | Mondrian: group x size | Outside survey frame | Indigenous | 70.7% | 0.341 | 0.806 |
    | Nightlights (GBM) | Mondrian: group x size | Outside survey frame | Non-Indigenous | 72.9% | 0.226 | 0.454 |

## Allocation

Misallocated share = half the sum of absolute differences between map-based and census-based budget shares.

![Allocation](assets/figures/demo/allocation.png#only-light)
![Allocation](assets/figures/demo/allocation-dark.png#only-dark)

??? note "Table view"

    | Municipal Indigenous share | Municipalities | Change vs. census |
    |---|---|---|
    | <5% | 6 | 40.5% |
    | 5-20% | 70 | 20.8% |
    | 20-40% | 40 | 6.3% |
    | 40-70% | 28 | -21.8% |
    | 70%+ | 6 | -40.3% |

**Relative Wealth Index instead of the census:**

| Group | Budget misallocated | Median municipal error |
|---|---|---|
| All | 11.6% | 23.0% |
| Indigenous-majority municipalities | – | 25.5% |
| Other municipalities | – | 20.7% |

**Challenger models instead of the census** (mean over survey draws):

| Model | Group | Budget misallocated | Median municipal error |
|---|---|---|---|
| Embeddings (Fay-Herriot) | All | 5.3% | 8.5% |
| Embeddings (Fay-Herriot) | Indigenous-majority municipalities | – | 8.8% |
| Embeddings (Fay-Herriot) | Other municipalities | – | 8.5% |
| Embeddings (GBM + EB) | All | 7.6% | 13.0% |
| Embeddings (GBM + EB) | Indigenous-majority municipalities | – | 13.5% |
| Embeddings (GBM + EB) | Other municipalities | – | 12.7% |
| Embeddings (GBM) | All | 7.4% | 12.3% |
| Embeddings (GBM) | Indigenous-majority municipalities | – | 12.1% |
| Embeddings (GBM) | Other municipalities | – | 12.7% |
| Nightlights (GBM) | All | 19.5% | 34.2% |
| Nightlights (GBM) | Indigenous-majority municipalities | – | 30.3% |
| Nightlights (GBM) | Other municipalities | – | 36.4% |

## Map

Regional patterns only: each hexagon (about 40 km across) is the population-weighted mean of at least 5 map tiles, and sparser hexagons are not drawn, so no single community can be read off the map ([publication rules](ethics.md#publication-rules)).

![Map](assets/figures/demo/map.png#only-light)
![Map](assets/figures/demo/map-dark.png#only-dark)

## Robustness

Pre-specified in section 7 of the [pre-analysis plan](pre_analysis_plan.md): the same specification with a different weighting, Indigenous measure, threshold, sample, or definition of poverty.

| Variant | Coef (pp) | CI low | CI high | Within-decile gap (pp) | Tiles |
|---|---|---|---|---|---|
| Primary specification | +20.3 | +15.1 | +25.5 | +8.6 | 4,452 |
| Unweighted | +19.8 | +17.2 | +22.4 | +8.6 | 4,452 |
| Tiles with 50+ people | +20.3 | +14.5 | +26.0 | +8.6 | 2,488 |
| Indigenous threshold 30% | +20.3 | +15.1 | +25.5 | +7.9 | 4,452 |
| Indigenous threshold 50% | +20.3 | +15.1 | +25.5 | +10.1 | 4,452 |
| Ground truth: infrastructure deprivation | +29.2 | +23.8 | +34.6 | +12.0 | 4,452 |
| Ground truth: marginalization index | +34.6 | +29.3 | +40.0 | +14.1 | 4,452 |
| Language-based Indigenous share | +23.8 | +17.7 | +29.9 | +8.9 | 4,452 |

