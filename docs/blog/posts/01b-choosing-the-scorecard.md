---
date: 2026-11-20
draft: true
categories:
  - Statistics
---

# Choosing the scorecard before the game

Before running anything on real data, I fixed how every result would be scored. The error measure
decides which mistakes count, and one of the most popular would have hidden exactly the mistake this
project looks for.

<!-- more -->

## Start from the decision

The challenger maps predict a deprivation rate for each locality: the share of dwellings without
electricity, piped water, drainage or a finished floor. A budget formula multiplies each rate by
population and adds up the results, so what moves money correctly is getting the *average* right.
Squared error is the loss whose best prediction is the average. RMSE is therefore the headline accuracy
measure, and signed bias (does a model understate deprivation for one group?) is the fairness measure.

## Why not MAPE

MAPE is the default on many forecasting dashboards. Here it fails three ways:

1. Many localities have a deprivation rate of zero, where it is undefined.
2. It divides by the truth, so a 5-point miss counts five times as much in a place with 10%
   deprivation as in a place with 50%. The poorest places count least.
3. Under-predicting can cost at most 100%; over-predicting has no ceiling. A model that understates
   deprivation, the error I am auditing, gets rewarded.

MSLE has a milder version of the second problem: on a rate between 0 and 1, an error in a fully
deprived place counts about a quarter as much as the same error in a fully served one.

## Watch for compression

A model can lower its RMSE by pulling every prediction toward the national average. The poorest places
then look less poor, and that is where programs act. So every model also gets a calibration slope (1 is
right; above 1 means its predictions are squeezed), a variance ratio, and its bias in each decile of
true deprivation.

## Per person and per community

Population-weighted metrics say how wrong a map is for the average person; unweighted ones, for the
average community. Indigenous localities are many and small, so I report both.

## Two questions that sound alike

"Is the map fair to Indigenous communities?" splits into two questions:

- Among **equally poor** places, does the map rank Indigenous ones as wealthier?
- Among places the **map ranks the same**, are Indigenous ones poorer?

When groups differ in average wealth, an imperfect map can't pass both tests. I checked on synthetic
data: a map whose errors ignore Indigenous status entirely passes the first and still fails the second
by several percentile points, because places that look alike on the map regress toward their own
group's average. So the confirmatory test asks the first question, and the second is read against
that synthetic benchmark rather than against zero.

## The rest of the scorecard

- **Intervals:** the interval score charges for width and for every miss, so neither huge intervals
  nor overconfident ones win.
- **Money:** the share of the budget that would go to the wrong municipalities.
- **Comparisons between models:** paired, on the same simulated survey in each replication, so the
  luck of the draw cancels.
- **Who is missing:** every analysis states what share of each group's population it covers. Places
  whose census data are suppressed get their own row.

All of this is in the [pre-analysis plan](../../pre_analysis_plan.md#6-evaluation-metrics), tagged
before the analysis, and in
[`metrics.py`](https://github.com/cody-allen-analytics/who-the-map-misses/blob/main/src/mapaudit/metrics.py).

[[FILL (optional): one or two sentences from your own experience of a metric that hid the mistake that
mattered.]]
