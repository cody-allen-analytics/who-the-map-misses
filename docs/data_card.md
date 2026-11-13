# Data card

## Sources

| Source | What is used | Unit | Year | Access | License |
|---|---|---|---|---|---|
| INEGI, Censo de Población y Vivienda 2020, results by locality (ITER) | Population, Indigenous household and language counts, dwelling services and assets, education | Locality (about 190,000) | 2020 | Open download | INEGI free-use terms |
| Meta Data for Good, Relative Wealth Index | Relative wealth estimate and its error per tile | Bing tile, zoom 14 (~2.4 km) | Published 2021 | Humanitarian Data Exchange | Record the license shown on the HDX page here |
| Google DeepMind, AlphaEarth Foundations Satellite Embedding V1 | 64-d annual embedding, mean within 500 m of each locality | 10 m pixels | 2020 | Earth Engine (free for noncommercial use, registration) | CC-BY 4.0 |
| NOAA/EOG VIIRS annual night lights V2.1 | `average_masked` radiance, mean within 500 m | ~460 m pixels | 2020 | Earth Engine | See catalog page |
| CONAPO, Índice de marginación por localidad 2020 (optional) | Official index, used only to validate the rebuilt index | Locality | 2020 | gob.mx | Government open data |

Required attribution for AlphaEarth: *"The AlphaEarth Foundations Satellite Embedding dataset is
produced by Google and Google DeepMind."*

## Processing

1. ITER: drop aggregate rows (municipal totals `0000`, pooled one- and two-dwelling localities
   `9998`/`9999`, state and national totals), convert `*` and `N/D` to missing, parse
   degrees-minutes-seconds coordinates, build the 9-digit `cvegeo` key.
2. Shares use occupied private dwellings with recorded characteristics (`VIVPARH_CV`) as denominator.
3. Labels: see [Methods](methods.md#ground-truth-labels).
4. RWI: quadkeys read as text; if leading zeros were stripped (spreadsheets do this, and every
   Mexican quadkey starts with 0), the zoom is recovered by checking quadkeys against tile coordinates.
5. Localities are joined to RWI tiles by computing their own quadkey at the RWI zoom.

## Known issues

- **Suppression:** localities with fewer than three dwellings show only total population and
  dwellings; they cannot have labels and are excluded from label-based analyses.
- **Point coordinates:** one point per locality; see the rural scope in [Methods](methods.md#units-and-scope).
- **Vintage mismatch:** the RWI was built from 2010s surveys and imagery; the census is from 2020.
- **Coverage:** the RWI only covers populated tiles as Meta's population layers saw them.
  Unmatched localities are a finding (H1), not just missing data.
- **Indigenous identification:** household-based and language-based census measures differ, and both
  differ from self-identification. The pipeline reports both measures.

## If the RWI does not cover Mexico

Meta's public release describes 93 to 135 low- and middle-income countries depending on the source.
If the Mexico file is missing:

1. Audit NASA SEDAC's Global Gridded Relative Deprivation Index (GRDI), which is global, with the same
   code: aggregate GRDI to the same tiles and replace `rwi` with `-grdi`.
2. Treat the AlphaEarth-based challenger as the audited system.

Record which path was taken in the deviations log of the [pre-analysis plan](pre_analysis_plan.md#deviations-log).

## What is committed

Only aggregated outputs: tables in `results/real/tables` and figures. No raw files and no
locality-level rows are committed.
