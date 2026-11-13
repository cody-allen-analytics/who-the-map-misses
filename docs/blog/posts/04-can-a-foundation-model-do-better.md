---
date: 2026-12-08
draft: true
categories:
  - Models
---

# Can a satellite foundation model do better?

If the deployed map has a blind spot, would a newer model fix it? I trained challengers on Google
DeepMind's AlphaEarth embeddings and compared them with classic small area estimation, under the
conditions a real statistical office faces: a limited survey, and predictions needed everywhere else.

<!-- more -->

## Setting up a fair fight

The census acts as a pseudo-census. Each of 20 replications draws a realistic survey (municipalities
with probability proportional to population, then localities, then 20 dwellings each), trains every
model on the survey only, and scores it on the localities the survey never visited.

| Model | Idea |
|---|---|
| Night lights (GBM) | The classic baseline |
| Embeddings (GBM) | A 64-d foundation-model summary of each place |
| Embeddings (GBM + EB) | The same, plus municipality effects estimated from the survey |
| Embeddings (Fay-Herriot) | Small area estimation: random effects for municipality and locality |

Writing the Fay-Herriot estimator myself was the most instructive part: the covariance of each
municipality's block has a closed-form inverse, so REML needs only group sums. A unit test checks that
it recovers known variance components on simulated data.

## How they're scored

RMSE, because the budget formula needs each place's rate right on average; signed bias by group,
because the question is whether a model understates deprivation for Indigenous localities; and a
calibration slope, because a model can lower its RMSE by squeezing every prediction toward the average.
Models are compared on the same simulated survey in each replication, so the luck of the draw cancels.

## Results

![Bias and RMSE by group](../../assets/figures/real/challenger_bias.png#only-light)
![Bias and RMSE by group](../../assets/figures/real/challenger_bias-dark.png#only-dark)

[[FILL: which model wins overall, and does the Indigenous / non-Indigenous gap in bias shrink when the
model borrows strength from the survey's municipalities? Quote numbers with replication ranges, and the
H4 paired difference from challenger_paired.csv.]]

![Bias by true deprivation decile](../../assets/figures/real/challenger_deciles.png#only-light)
![Bias by true deprivation decile](../../assets/figures/real/challenger_deciles-dark.png#only-dark)

[[FILL: where do the errors fall? Compression looks like positive bias in the least deprived deciles and
negative bias in the most deprived. Does any model buy its RMSE that way (calibration slope well above 1)?]]

## Takeaway

[[FILL: one paragraph. Expected shape: features matter less than whether the method uses what the survey
says about each municipality, but write what the data show.]]
