---
date: 2026-11-17
draft: true
categories:
  - Design
---

# Why I'm auditing AI poverty maps

Governments and NGOs increasingly decide where aid goes using poverty maps built from satellite
imagery and machine learning. They are cheap, cover every square kilometre, and look authoritative.
The question I want to answer is narrow and testable: **do these maps systematically understate
deprivation in Indigenous communities?**

<!-- more -->

## Why this question

[[FILL: two or three sentences, in your own voice, connecting this to your background in political
economy, infrastructure and Indigenous communities. Why does it matter to you?]]

Two recent papers come close. Aiken, Rolf and Blumenstock (2023) showed that satellite poverty maps
carry an urban-rural bias that distorts allocations. Corral, Henderson and Segovia (2025) showed, with
Mexican data, that machine-learning maps are less accurate than classic small area estimation and most
biased for the poorest places. Neither looks at Indigenous status.

## Why Mexico

Mexico's 2020 census reports, for every one of roughly 190,000 localities, how many people live in
Indigenous households and which services their dwellings have. That turns the census into ground
truth everywhere, so a map's errors can be measured across the country instead of at a handful of
survey clusters.

## The hard part: separating Indigeneity from everything correlated with it

Indigenous communities in Mexico are, on average, poorer, smaller and more remote. A map can misrank
them for any of those reasons. The core comparison is therefore *within the same true wealth decile*,
with controls for settlement size, remoteness and state.

## Committing before looking

Before touching the real data, I wrote down my hypotheses, metrics and model specifications in a
[pre-analysis plan](../../pre_analysis_plan.md) and tagged the commit (`pap-v1`). That includes the
scorecard: which error measure decides each question, and why some popular ones are ruled out. If I
change anything later, it goes in a deviations log with a reason. I also validated the pipeline on synthetic data:
it finds a bias I planted, and finds nothing when I don't plant one ([validation](../../validation.md)).

Next: turning a census table into ground truth, which turned out to be less trivial than it sounds.
