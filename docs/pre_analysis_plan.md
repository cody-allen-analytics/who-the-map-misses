# Pre-analysis plan

!!! abstract "Status"
    **Version 1. Upload this file and create the tag `pap-v1` before running any real-data step past the
    build** (GitHub → Releases → Draft a new release → Choose a tag → type `pap-v1` → Create new tag on
    publish). The tag's timestamp is the record that hypotheses and specifications came first. Later
    changes go in the [deviations log](#deviations-log) with a reason, never by editing the text above it.

## 1. Motivation

Poverty maps built from satellite imagery and machine learning are used to target cash transfers and
infrastructure where surveys are thin. Two strands of evidence motivate this audit:

- Aiken, Rolf & Blumenstock (IJCAI 2023) find urban-rural bias in satellite poverty maps, using Mexican
  data among others, and show the bias distorts allocations.
- Corral, Henderson & Segovia (*Journal of Development Economics*, 2025) find that machine-learning
  poverty maps of Mexico are less accurate than small area estimation and most biased for the poorest areas.

Neither examines Indigenous status. Indigenous communities in Mexico are disproportionately poor,
rural and remote, so a map can misrank them for reasons that have nothing to do with Indigeneity.
The design below separates those reasons.

## 2. Hypotheses

All hypotheses are about rural localities (fewer than 2,500 inhabitants; see §3). "Indigenous share" is
the share of the population living in Indigenous census households (PHOG_IND / POBTOT). An
"Indigenous locality" or "Indigenous tile" has a share of at least 40%.

| ID | Hypothesis | Primary metric | Test |
|---|---|---|---|
| **H1** Representation | Indigenous localities are less likely to fall inside an RWI tile, holding size and remoteness fixed. | Coefficient on Indigenous share in a linear probability model of coverage | Two-sided, municipality-clustered SEs; Holm-adjusted p < 0.05 |
| **H2** Rank bias | Within the same true wealth decile, the RWI ranks Indigenous tiles as wealthier than the census does. | Coefficient on Indigenous share in specification 5 of §5 (percentile points) | One-sided (coefficient > 0), municipality-clustered SEs; Holm-adjusted p < 0.05 |
| **H3** Label choice | The share of the Indigenous population counted among the nation's poorest 20% differs across the three labels by at least 5 percentage points. | Max − min across labels | Descriptive; the census is a full count, so there is no sampling test |
| **H4** Challengers | In simulated surveys, satellite-embedding gradient boosting has larger absolute bias for Indigenous localities than small area estimation with municipality effects. | Paired difference \|bias(GBM)\| − \|bias(Fay-Herriot)\|, population-weighted, Indigenous localities, computed within each replication | Supported if the 95% range of the paired differences across replications lies above 0 |
| **H5** Uncertainty | Marginal 90% conformal intervals cover Indigenous localities less than 87% of the time; group-conditional intervals cover them within ±3 points of 90% inside the survey frame. | Empirical coverage, unsampled localities | Mean over replications with 95% replication range; interval score reported alongside |
| **H6** Money | Replacing census data with the RWI in the FAIS-style formula lowers the allocation to Indigenous-majority municipalities. | Net change in pesos and percent | Descriptive (full census); misallocation share reported alongside |

**Multiple testing.** H1 and H2 are the confirmatory hypotheses; their p-values are adjusted together with
Holm's method and each is supported if its adjusted p-value is below 0.05. H3 to H6 are reported as
estimates with uncertainty ranges, not as tests.

**Directional caveat.** H2 is stated in the direction suggested by prior work, but a negative
coefficient (the map *overstates* Indigenous deprivation) would be reported with equal prominence.

## 3. Data and sample

- **Ground truth:** INEGI 2020 census, results by locality (ITER). Localities with fewer than three
  dwellings have suppressed characteristics and are excluded from label construction.
- **Scope:** rural localities (fewer than 2,500 people). ITER provides one coordinate per locality, so
  a city would fall into a single 2.4 km tile; RWI tiles that contain any urban locality are dropped
  from the tile-level audit.
- **Map under audit:** Meta's Relative Wealth Index for Mexico, joined by quadkey.
- **Satellite features:** AlphaEarth Foundations embeddings for 2020 (mean within 500 m of each
  locality) and VIIRS 2020 night lights.

## 4. Variables

| Variable | Definition |
|---|---|
| `wealth_dhs_like` | First principal component of 8 durable goods and 4 housing services (primary label for the RWI audit) |
| `dep_infra` | Mean share of dwellings without electricity, piped water, drainage, or with a dirt floor (target for challengers and allocation) |
| `marg_index` | First principal component of 8 CONAPO-style marginalization indicators |
| `rank_error` | 100 × (RWI percentile − census wealth percentile) among tiles, population-weighted. Positive = map ranks the tile wealthier than the census |
| Controls | log tile population, urban share (dropped if constant), log km to the nearest city of 50,000+, altitude, true wealth decile, state |

## 5. Primary specification (H2)

Weighted least squares on tiles, weights = tile population, standard errors clustered by municipality:

\[
\text{rank\_error}_t = \beta \,\text{IndShare}_t + \gamma' X_t + \delta_{\text{decile}(t)} + \alpha_{\text{state}(t)} + \varepsilon_t
\]

Specifications 1-4 add controls cumulatively and are reported to show how much of the raw gap is
explained by rurality, remoteness and true wealth. Specification 5 is the confirmatory one.

## 6. Evaluation metrics

Each metric matches the decision the map feeds. Full rationale: [Methods → Evaluation metrics](methods.md#evaluation-metrics).

| Question | Primary metric | Also reported |
|---|---|---|
| Does the map misrank Indigenous places? (H2) | Indigenous minus non-Indigenous rank error among equally poor tiles (the §5 coefficient) | The same gap among tiles the map ranks the same (by map decile) |
| How accurate is a challenger? (H4) | RMSE of the predicted deprivation rate | MAE |
| Is a challenger fair? (H4) | Signed bias for Indigenous localities | Bias by true deprivation decile, calibration slope, variance ratio |
| Are the intervals honest? (H5) | Coverage by group | Interval (Winkler) score, width |
| Where does the money go? (H6) | Net change for Indigenous-majority municipalities | Misallocation share (half the sum of absolute differences in budget shares); median absolute percentage error by municipality |

- **RMSE first.** The budget formula sums predicted rates, so predictions must get the mean right, and squared
  error is the loss whose best prediction is the mean. MAE is secondary.
- **No MAPE or MSLE on rates.** Many localities have a deprivation rate of zero, where MAPE is undefined, and
  both measures discount errors in the most deprived places. Percentage errors are used only for municipal
  allocations, which are never zero.
- **People and places.** Every challenger metric is reported population-weighted (primary) and unweighted.
- **Compression.** The calibration slope (truth regressed on prediction) and the ratio of prediction to truth
  variance are reported for every model and group, because a model can lower its RMSE by pulling predictions
  toward the average.
- **Two views of rank error.** The separation view (by true decile) is confirmatory. The calibration view
  (by map decile) is secondary. Groups that differ in average wealth show a gap in this view even when the
  map's errors ignore group, so the gap is compared with a no-bias benchmark computed from the same data:
  its mean and 95% range over 200 shuffles of the map's values among tiles at the same census percentile
  ([Methods](methods.md#two-views-of-fairness)).
- **Paired comparisons.** Models are compared on the same simulated survey within each replication.
- **Denominators.** Each analysis reports the share of the in-scope population it covers, by group, with
  localities whose census data are suppressed as a separate group.

## 7. Robustness (reported regardless of outcome)

1. Unweighted regressions.
2. Language-based Indigenous share (P3YM_HLI / P_3YMAS) instead of the household measure.
3. Thresholds of 30% and 50% for "Indigenous".
4. Excluding tiles with fewer than 50 people.
5. The same audit with each of the other ground truths: infrastructure deprivation, the rebuilt
   marginalization index, and the official CONAPO marginalization index if the file is available.

Each check re-estimates specification 5; `mapaudit robustness` (notebook 03) writes them to
`results/real/tables/robustness.csv`.

## 8. Simulation design (H4, H5)

20 replications. Each draws 400 municipalities with probability proportional to rural population,
8 localities per municipality, and 20 dwellings per locality, among localities with at least 10
dwellings. Models: night lights (GBM), embeddings (GBM), embeddings (GBM + empirical-Bayes municipality
effects), embeddings (Fay-Herriot with municipality random effect, 20 principal components). Metrics
are computed on localities the survey did not visit, for each replication, and summarized by their mean
and 2.5th-97.5th percentiles across replications.

## 9. What would change the conclusions

- If the H2 coefficient shrinks to zero once the true decile is controlled for, the gap is a "poorest
  places get compressed" problem, not an Indigenous-specific one. That is still a finding, with a
  different remedy.
- If the gap appears among places the map ranks the same but not among equally poor places, the map's errors
  are not group-specific, yet its ranking still cannot be taken at face value for Indigenous places. The
  remedy is then group-aware calibration or small area estimation, not a better map.
- If the RWI's quadkey join fails for more than 5% of tiles, the audit stops until the cause is found.

## 10. Publication and data governance

Fixed before the real-data analysis; the reasons are on the [ethics page](ethics.md).

- Only aggregated results are published. No table carries a locality or map-tile identifier or
  coordinates; the pipeline's end-to-end test and the release check fail if one does.
- Maps are aggregated to hexagons about 40 km across, each the population-weighted mean of at least
  five map tiles; hexagons with fewer tiles are not drawn.
- No locality is named in published results, and the challenger models' locality-level predictions are
  not published.
- Requests from affected Indigenous communities to correct, contextualize or withdraw a result take
  precedence over this plan. They are logged on the ethics page, and any resulting change is recorded in
  the deviations log below.

## Deviations log

| Date | Section | Change | Reason |
|---|---|---|---|
| | | | |
