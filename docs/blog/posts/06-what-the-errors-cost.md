---
date: 2026-12-22
draft: true
categories:
  - Findings
---

# What the errors cost

An error in a map is abstract until money moves because of it. The last step plugs each map into two
simple allocation rules and measures who gains and who loses.

<!-- more -->

## Two rules

- **Targeting:** fund the localities the map says are poorest until 20% of the rural population is covered.
- **Formula:** split a budget across municipalities in proportion to the estimated number of
  deprived people, the logic behind Mexico's FAIS social-infrastructure fund. (A stylized rule, not
  the legal formula.)

![Allocation shifts](../../assets/figures/real/allocation.png#only-light)
![Allocation shifts](../../assets/figures/real/allocation-dark.png#only-dark)

[[FILL from rwi_allocation.csv: "Per billion pesos, using the RWI instead of the census moves X million
pesos away from / toward Indigenous-majority municipalities (Y%)." Then the misallocation share from
rwi_allocation_errors.csv ("Z% of the whole budget would go to the wrong municipalities"), and the
targeting exclusion rates by group.]]

## What I'd tell a program designer

[[FILL: three bullets. Candidate themes, only if the results support them: report map accuracy by group;
use small area estimation with survey-based municipality effects instead of feature-only models;
sample very small localities so that uncertainty estimates mean something there.]]

## Limitations

Rural scope only; census labels describe dwellings, not income; one country and one year. See
[Methods](../../methods.md#limitations).

## What's next

[[FILL: cities with block-level census data, another country, or a newer map.]]
