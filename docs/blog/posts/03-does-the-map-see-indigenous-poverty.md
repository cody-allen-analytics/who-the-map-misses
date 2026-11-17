---
date: 2026-12-01
draft: true
categories:
  - Findings
---

# Does the map see Indigenous poverty?

The first audit compares Meta's Relative Wealth Index with census ground truth on [[FILL: N]] rural
map tiles. Two questions: who is on the map at all, and, for those who are, is their rank right?

<!-- more -->

## Who is on the map

[[FILL from coverage.csv: "X% of the Indigenous rural population lives inside a map tile, compared with
Y% of the non-Indigenous rural population." Then the coverage regression result, holding size and
remoteness fixed.]]

![Coverage by group and locality size](../../assets/figures/real/rwi_coverage.png#only-light)
![Coverage by group and locality size](../../assets/figures/real/rwi_coverage-dark.png#only-dark)

## Is the rank right?

The comparison that matters is within the same true wealth decile, because these maps are known to
pull the poorest places toward the middle.

![Rank error by true decile](../../assets/figures/real/decile_errors.png#only-light)
![Rank error by true decile](../../assets/figures/real/decile_errors-dark.png#only-dark)

[[FILL: describe the figure in two sentences. Then the confirmatory estimate: "Holding true decile,
size, remoteness, altitude and state fixed, an all-Indigenous tile is ranked B points higher/lower
(95% CI a to b)." Report it the same way whichever direction it goes.]]

## The same errors, seen from the map user's side

The comparison above holds the *truth* fixed. A program officer sees only the map, so the other question
is: among places the map ranks the same, are Indigenous ones poorer? Groups that differ in average
wealth produce a gap here even for a map whose errors ignore group, so I compare it with a no-bias
benchmark computed from the same data (the map's values shuffled among equally poor places), not with
zero.

![Rank error by map decile](../../assets/figures/real/map_decile_errors.png#only-light)
![Rank error by map decile](../../assets/figures/real/map_decile_errors-dark.png#only-dark)

[[FILL from map_decile_errors.csv and audit_summary.json (calibration_gap_pp against
calibration_gap_no_bias_pp and its range): is the gap beyond the no-bias range? If it is, a group-blind
targeting rule based on the map under-serves Indigenous places even where the map ranks them correctly
on average.]]

## How much does each control explain?

![Coefficient across specifications](../../assets/figures/real/audit_specs.png#only-light)
![Coefficient across specifications](../../assets/figures/real/audit_specs-dark.png#only-dark)

[[FILL: what happens to the coefficient as controls are added? If it drops when the true decile is
added, the problem is "poorest places get compressed"; if it survives, it is Indigenous-specific.]]

## Robustness

[[FILL from robustness.csv: language-based measure, other thresholds, unweighted. One sentence each,
or a short table.]]
