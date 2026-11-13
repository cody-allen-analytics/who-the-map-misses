# Methods

## Units and scope

The census reports one row per locality (about 190,000). Meta's Relative Wealth Index (RWI)
reports one value per Bing tile at zoom 14 (about 2.4 km). Every locality is assigned to the tile
containing its census coordinate, and census quantities are aggregated to tiles with population weights.

ITER gives a single point per locality. That is accurate for rural localities but not for a city
spread over dozens of tiles, so map comparisons are restricted to **rural localities** (fewer than
2,500 people) and to tiles that contain no urban locality.

## Ground-truth labels

All three labels come from the same census table, so differences between them are differences in
*definition*, not in data.

| Label | Construction | Why it matters |
|---|---|---|
| Asset wealth (DHS-style) | First principal component of shares of dwellings with a fridge, washer, car, computer, cell phone, internet, TV, microwave, electricity, piped water, drainage and a finished floor | What the RWI was trained to predict |
| Infrastructure deprivation | Mean share of dwellings lacking electricity, piped water, drainage, or with a dirt floor | A rate with a direct policy reading; target of FAIS-type spending |
| Marginalization (CONAPO-style) | First principal component of illiteracy, incomplete basic education, the four housing deprivations, crowding, and lacking a fridge | Mirrors the official index's ingredients |

Percentile ranks are population-weighted, so "the poorest 20%" means 20% of people, not of places.

## Audit of the RWI

**Rank error.** For tile \(t\), \( e_t = 100\,(\text{RWI percentile}_t - \text{census percentile}_t) \).
A positive error means the map ranks the tile as wealthier than the census does.

**Within-decile comparison.** Machine-learning maps compress the extremes: the poorest places look
less poor. Comparing Indigenous and non-Indigenous tiles *within the same true decile* removes that
mechanism from the comparison. Confidence bands come from a municipality-cluster bootstrap.

**Regressions.** Weighted least squares of \(e_t\) on Indigenous share with cumulative controls (size,
remoteness, altitude, true decile, state), weights equal to tile population, standard errors
clustered by municipality. Constant controls are dropped automatically.

**Coverage.** A linear probability model of whether a locality falls inside any RWI tile, on
Indigenous share, log population and log distance to the nearest city.

### Two views of fairness

The same rank errors can be grouped in two ways, and they answer different questions.

| View | Groups tiles by | Question | Holds when |
|---|---|---|---|
| Separation | true (census) decile | Among equally poor places, does the map rank Indigenous ones as wealthier? | Errors are independent of group, given the truth |
| Calibration | map decile | Among places the map ranks the same, are Indigenous ones poorer? | The truth is independent of group, given the map |

When groups differ in average wealth, an imperfect map generally cannot satisfy both (Kleinberg,
Mullainathan & Raghavan 2017; Chouldechova 2017). A map whose errors ignore group passes the separation view and still
fails the calibration view. If true wealth in group \(g\) is normal with mean \(\mu_g\) and variance
\(\sigma^2\), and the map adds noise of variance \(\tau^2\) regardless of group, then among places the
map scores \(m\)

\[
E[\text{truth} \mid \text{map} = m,\ g] = \mu_g + k\,(m - \mu_g), \qquad k = \frac{\sigma^2}{\sigma^2 + \tau^2} < 1,
\]

so the group with the lower average is poorer at every map value. The audit therefore uses the separation
view for the confirmatory test (H2), because it isolates how the map treats a place given its true
condition, and reports the calibration view as what someone who sees only the map experiences. The
calibration gap is read against its value in a synthetic world with no planted bias
([validation](validation.md)), not against zero.

## Challenger models

The census is used as a *pseudo-census*: a realistic household survey is drawn from it (municipalities
with probability proportional to population, then localities, then dwellings without replacement),
models are trained on the survey only, and predictions are scored against the full census in
localities the survey never visited. This mirrors Corral, Henderson & Segovia (2025).

| Model | Features | Borrows strength across localities? |
|---|---|---|
| Night lights (GBM) | VIIRS 2020 average radiance | No |
| Embeddings (GBM) | 64-d AlphaEarth embedding | No |
| Embeddings (GBM + EB) | same | Yes: empirical-Bayes municipality effects from cross-fitted residuals |
| Embeddings (Fay-Herriot) | 20 principal components of the embedding | Yes: REML-estimated municipality and locality random effects |

**Fay-Herriot with a municipality effect.** For sampled locality \(i\) in municipality \(j\):

\[
y_{ij} = x_{ij}'\beta + u_j + v_{ij} + e_{ij},\quad u_j\sim N(0,\sigma_u^2),\; v_{ij}\sim N(0,\sigma_v^2),\; e_{ij}\sim N(0,\psi_{ij})
\]

with \(\psi_{ij}\) the known design variance of the survey estimate. Each municipality's covariance block
\(\sigma_u^2\mathbf{1}\mathbf{1}' + \operatorname{diag}(\sigma_v^2+\psi)\) is inverted in closed form
(Sherman-Morrison), so REML needs only group sums. Unsampled localities in sampled municipalities
receive \(x'\hat\beta + \hat u_j\); others receive \(x'\hat\beta\). The implementation is tested for
parameter recovery on simulated data (`tests/test_models.py`).

## Evaluation metrics

Each metric was chosen for the decision its output feeds, before any real data were seen
([pre-analysis plan §6](pre_analysis_plan.md#6-evaluation-metrics)). The code is in `metrics.py`.

**Accuracy: RMSE first.** The budget formula multiplies predicted deprivation rates by population and adds
them up, so a prediction has to get the *mean* right. Squared error is the loss whose best prediction is
the mean (it is consistent for the mean; Gneiting 2011), so RMSE is the primary accuracy measure. MAE,
whose best prediction is the median, is secondary.

**Fairness: signed bias.** RMSE and MAE say how far off a model is, not in which direction. Signed bias
(prediction minus truth) by group says whether a model systematically understates deprivation for
Indigenous localities. It is the H4 metric.

**Why not MAPE or MSLE.**

| Measure | Problem on locality deprivation rates |
|---|---|
| MAPE | Undefined where the rate is zero, which is common (every dwelling has electricity, say). It divides by the truth, so it weights the least deprived places most. An under-prediction can cost at most 100% while an over-prediction is unbounded (Hyndman & Koehler 2006), so it favors models that understate deprivation: the error under audit. |
| MSLE | Built for targets that span orders of magnitude, where relative error matters. A rate between 0 and 1 doesn't, and on that range an error at 100% deprivation counts about a quarter as much as the same error at 0%. |

Percentage errors are used only for municipal allocations, which are never close to zero.

**People and places.** Population-weighted metrics say how wrong a map is for the average person;
unweighted ones, for the average community. Indigenous localities are many and small, so a per-person
metric can hide large errors in many small places. Both are reported, per person first.

**Compression.** A model can lower its RMSE by pulling every prediction toward the average, which moves
its errors to the extremes, where programs act. Three diagnostics expose this:

- *Calibration slope*: the slope of the truth regressed on the prediction. 1 is calibrated; above 1 means
  the predictions are squeezed toward the average.
- *Variance ratio*: the variance of the predictions over the variance of the truth. Below 1 means squeezed.
- *Bias by true decile*: compression shows up as positive bias in the least deprived deciles and negative
  bias in the most deprived.

**Intervals.** Coverage alone rewards intervals that are too wide; width alone rewards intervals that
miss. The interval score (Gneiting & Raftery 2007) combines the two:

\[
S_\alpha(l, u; y) = (u - l) + \frac{2}{\alpha}(l - y)\,\mathbf{1}\{y < l\} + \frac{2}{\alpha}(y - u)\,\mathbf{1}\{y > u\}.
\]

Lower is better. It is a proper scoring rule, so a model cannot improve its score by reporting intervals
other than its honest ones.

**Money.** The misallocation share, \(\tfrac12 \sum_j |\hat s_j - s_j|\) over municipal budget shares,
is the fraction of the budget that would have to move to reproduce the census-based allocation. It is
reported with the net change for Indigenous-majority municipalities and the median absolute percentage
error by municipality.

**Comparing models.** In each replication every model is trained and scored on the same simulated survey,
so differences are taken replication by replication and the luck of the draw cancels. Tables report the
mean paired difference, its 2.5th-97.5th percentiles across replications, and the share of replications
in which a model does worse.

**Tests.** H1 (two-sided) and H2 (one-sided, as pre-registered) are adjusted together with Holm's method.
Everything else is an estimate with an uncertainty range.

**Denominators.** A metric exists only where the truth is known. Each analysis reports the share of the
in-scope population it covers, by group. Localities with suppressed census data (fewer than three
dwellings) also lack Indigenous status, so they appear as a separate "Unknown" group instead of
disappearing from the denominator.

## Prediction intervals

Split conformal intervals use cross-fitted residuals on surveyed localities as calibration scores.
Three versions: marginal (one quantile), Mondrian by group, and Mondrian by group × size tercile.
Coverage, width and interval score are reported separately for localities inside the survey frame (at
least 10 dwellings) and outside it, because conformal guarantees require calibration and test points to be
exchangeable.

## Allocation

- **Targeting:** select the localities predicted to be most deprived until 20% of the rural
  population is covered; the exclusion rate is the share of the truly poorest population left out.
- **Formula:** split a fixed budget across municipalities in proportion to the estimated number of
  deprived people (population × deprivation rate). This follows the logic of Mexico's FAIS, which
  allocates by extreme poverty weighted by average deprivations; it is a stylized rule, not the legal formula.
- The RWI is relative, so it is converted to a deprivation rate by quantile-mapping its ranks onto
  the national distribution of the census rate (as if that distribution were known from a survey).
- **Errors:** the misallocation share and municipal percentage errors (see
  [Evaluation metrics](#evaluation-metrics)).

## Validation

`mapaudit validate` generates synthetic worlds with and without a planted Indigenous bias and checks
that the audit finds it only when it is there. The same check runs in CI (`tests/test_validation.py`).
The world without bias also supplies the benchmark for the calibration view, and a test checks that this
view shows a gap the separation view does not (`tests/test_metrics.py`).

## Limitations

- Census labels describe dwellings and education, not income or consumption.
- Ecological inference: results are about places, not individual households.
- The RWI was estimated around 2021 from 2010s surveys and imagery; the census is from 2020.
- A 500 m buffer is a modelling choice for embedding features.
- Language- and household-based census measures undercount people who self-identify as Indigenous.

## Extensions

- **Cities:** use the AGEB (census tract) tables and the INEGI geostatistical framework to place urban
  population inside tiles.
- **Change over time:** compare 2020 maps with the next census or intercensal survey.
- **Other countries:** Guatemala, Peru and Bolivia publish censuses with Indigenous identifiers.
- **Other deployed maps:** NASA's Global Gridded Relative Deprivation Index (GRDI) can be audited with
  the same code.

## References

- Chouldechova, A. (2017). Fair prediction with disparate impact: a study of bias in recidivism prediction
  instruments. *Big Data*, 5(2).
- Gneiting, T. (2011). Making and evaluating point forecasts. *Journal of the American Statistical
  Association*, 106(494).
- Gneiting, T., & Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation.
  *Journal of the American Statistical Association*, 102(477).
- Hyndman, R. J., & Koehler, A. B. (2006). Another look at measures of forecast accuracy. *International
  Journal of Forecasting*, 22(4).
- Kleinberg, J., Mullainathan, S., & Raghavan, M. (2017). Inherent trade-offs in the fair determination of
  risk scores. *Innovations in Theoretical Computer Science (ITCS)*.

Studies of satellite poverty maps that motivate the audit are cited in the
[pre-analysis plan](pre_analysis_plan.md#1-motivation).
