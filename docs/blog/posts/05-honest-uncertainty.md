---
date: 2026-12-15
draft: true
categories:
  - Statistics
---

# When a 90% interval isn't 90% for everyone

Conformal prediction gives intervals with a coverage guarantee, but the guarantee is *on average*
over the calibration population. Averages can hide a lot.

<!-- more -->

## Three ways to calibrate

1. **Marginal:** one quantile for everyone.
2. **Mondrian by group:** a separate quantile for Indigenous and non-Indigenous localities.
3. **Mondrian by group × size:** separate quantiles within size terciles too.

![Coverage by method and group](../../assets/figures/real/conformal_coverage.png#only-light)
![Coverage by method and group](../../assets/figures/real/conformal_coverage-dark.png#only-dark)

[[FILL: coverage of marginal intervals for Indigenous vs non-Indigenous localities; how much
group-conditional calibration recovers inside the survey frame, and what it costs in width. The
interval score (width plus a penalty for each miss) says whether the trade is worth it.]]

## The part calibration can't fix

The survey never visits localities with fewer than 10 dwellings, so no calibration set looks like them.
[[FILL: coverage outside the frame.]] When coverage collapses there regardless of method, the remedy
is in survey design (sample some tiny localities), not in a cleverer interval.
