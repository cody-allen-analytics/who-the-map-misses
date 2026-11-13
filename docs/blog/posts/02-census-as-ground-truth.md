---
date: 2026-11-24
draft: true
categories:
  - Data
---

# Turning a census into ground truth

The census was supposed to be the easy part. Four details in INEGI's locality file (ITER) each
would have silently corrupted the analysis.

<!-- more -->

## 1. The file contains its own totals

Rows with locality code `0000` are municipal totals; `9998` and `9999` pool all one- and
two-dwelling localities; rows with municipality `000` are state totals. Summing the file without
dropping them counts every person several times.

## 2. Small places are suppressed

For localities with fewer than three dwellings, every characteristic is replaced by `*`. These are
[[FILL: N]] localities and [[FILL: N]] people. They can't have labels, and they are exactly the kind of
tiny, remote settlement where a map is most likely to be wrong, so I report them rather than drop them quietly.

## 3. Coordinates are text

Latitude and longitude come as degrees-minutes-seconds strings (`102°17'44.149" W`). The parser is
vectorized and tested against hand-converted examples.

## 4. A city is a single point

This was the design decision that mattered most. ITER gives one coordinate per locality, so a city of
a million people sits in a single 2.4 km map tile while the map has dozens of tiles over it.
Comparing map and census at the tile level only makes sense where localities really are points: rural
localities (fewer than 2,500 people), which also hold most Indigenous-majority communities. Tiles
that contain any urban locality are dropped from the tile audit.

## Three definitions of poverty from one table

| Label | What it measures |
|---|---|
| Asset wealth (DHS-style) | Durable goods plus housing services; what the RWI was trained to predict |
| Infrastructure deprivation | Share of dwellings without electricity, water, drainage, or with a dirt floor |
| Marginalization (CONAPO-style) | Education, housing, crowding, refrigerator |

Under these labels, the share of the Indigenous population counted among the nation's poorest 20% is
[[FILL from label_choice.csv]]. [[FILL: one sentence on what the spread means.]]

Next: does the map see what the census sees?
