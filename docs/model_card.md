# Model card: challenger poverty maps

## Overview

Four models predict the **infrastructure-deprivation rate** of a rural locality (the share of
dwellings lacking electricity, piped water, drainage, or with a dirt floor) from satellite data,
trained on a simulated household survey. They exist to study how mapping methods distribute their
errors, **not** to be used for targeting.

| Model | Inputs | Method |
|---|---|---|
| Night lights (GBM) | VIIRS 2020 radiance | Histogram gradient boosting |
| Embeddings (GBM) | AlphaEarth 2020 embedding (64-d) | Histogram gradient boosting |
| Embeddings (GBM + EB) | same | Boosting plus empirical-Bayes municipality effects from cross-fitted residuals |
| Embeddings (Fay-Herriot) | 20 principal components of the embedding | Small area estimation with municipality and locality random effects (REML) |

## Intended use

- Research on the accuracy and fairness of poverty maps.
- Teaching example of small area estimation versus machine learning under a realistic survey design.

## Out of scope

- Selecting beneficiaries or ranking specific communities for programs.
- Publishing or sharing locality-level predictions: they would be a deprivation map of Indigenous
  communities made without their participation ([publication rules](ethics.md#publication-rules)).
- Any use that affects specific Indigenous communities without their free, prior and informed consent.
- Urban areas (see the scope note in [Methods](methods.md#units-and-scope)).
- Years other than 2020 without revalidation.

## Training data

A survey simulated from the 2020 census: 400 municipalities drawn with probability proportional to
rural population, 8 localities per municipality, 20 dwellings per locality, localities with at least
10 dwellings only. 50 replications.

## Evaluation

Scored on localities the survey did not visit, in each of 50 replications, for Indigenous and
non-Indigenous localities separately, per person (population-weighted, primary) and per community
(unweighted). Metrics were fixed in advance; the reasons are in
[Methods → Evaluation metrics](methods.md#evaluation-metrics).

| Aspect | Metric |
|---|---|
| Accuracy | RMSE (primary: the budget formula needs the mean right), MAE |
| Fairness | Signed bias by group (H4: paired difference in absolute bias, boosting minus Fay-Herriot) |
| Compression | Calibration slope, variance ratio, bias by true deprivation decile |
| Uncertainty | Coverage, width and interval score of 90% conformal intervals (marginal and group-conditional), inside and outside the survey frame |
| Decisions | Exclusion error under "poorest 20%" targeting; net shift, misallocation share and municipal percentage error in a FAIS-style budget |

MAPE and MSLE are not used: deprivation rates are often zero, and both discount errors in the most
deprived places. See [Results](results.md).

## Ethical considerations

Errors are not evenly distributed: the project exists to measure that. Any reuse of these models
should report group-level performance and should involve the communities affected. See
[Ethics & Indigenous data sovereignty](ethics.md).

## Caveats

- Ground truth describes dwellings, not income.
- Embeddings are averaged within a fixed 500 m buffer.
- Performance outside the survey frame (localities with fewer than 10 dwellings) is extrapolation.
