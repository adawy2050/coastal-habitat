# Seasonal outlook review — 1 November 2026

Reviewed the saved October 2026 issue for December 2026–February 2027, the generation code, browser input routing and archived-forecast validation. Scientific probabilities were not changed by this review.

## Findings

The seasonal probability is fitted independently to each native SST cell. Habitat locations sharing a source cell share its result. The model learns multivariate ridge-logistic coefficients, not weights copied from the annual correlation or Shapley charts. Its outcome is whether seasonal MHW days exceed the greater of 10 days and the training-record same-season 80th percentile; it does not predict all six selectable heatwave metrics.

Six observed climate indices enter the reference model: Niño-3.4, NAO, AO, EAWR, North Atlantic SST anomaly and PDO. The October issue uses June–August means. Index detrending, standardisation, thresholds and chronological penalty selection use earlier training data. The current seasonal model has no explicit warming, recent local SST or recent local MHW predictor. Removing index trends does not account for the warming trend in the outcome.

An alternative adds the already-issued October IRI DJF Niño-3.4 forecast, trained with matching archived October issues beginning in 2004. A chronological gate chooses a zero, one-half or full candidate-model weight. JAMSTEC Niño-3.4 and IOD forecasts are displayed but are not inputs to this model. Forecast ensemble uncertainty is not propagated into cell probabilities. The annual 2026–2027 scenario curves are separate regressions with held inputs, not this seasonal forecast.

## Saved-array results

| Product | Native cells | Post-baseline test seasons | Cells using issued ENSO | Cells with positive Brier skill | Median Brier skill |
|---|---:|---:|---:|---:|---:|
| MUR | 166,771 | 3 | 0 | 33.82% | -0.0289 |
| OISST | 2,264 | 10 | 1,484 (65.55%) | 45.01% | -0.00845 |

Positive Brier skill means lower squared probability error than the historical-frequency baseline. These are descriptive counts, not statistically significant skill claims. Adjacent cells are spatially dependent. The external candidate improving on the reference does not guarantee improvement over climatology. Three MUR seasons are inadequate to establish probability reliability. The adaptive OISST promotion gate has only two evaluated seasons after eight earlier comparison seasons become available; its ten-season score mostly evaluates the reference model.

At the currently selected Philippines point (9.89 N, 118.04 E), MUR gives 21.48% against a 23.91% historical baseline, with Brier skill -0.475. OISST gives 41.63% against a 21.59% baseline, with Brier skill -0.0186. Neither selected forecast uses the issued ENSO candidate. These results do not demonstrate a reliable alert at this point.

## Calculation checks

The independent verifier passed 23 archived October forecast issues and 18 separately optimised point fits, with maximum probability difference 2.5e-8. Stored blend probabilities and chronological policy scores reproduce. Numerical correctness is distinct from predictive skill. Historical monthly observations are current archive versions, not guaranteed original release vintages.

## Improvements to test before changing published probabilities

1. Compare climatology, warming-only and local SST-persistence models with observed-index and issued-index candidates on identical forward-held-out seasons. Include recent local SST anomaly and MHW exposure only when available at each issue date.
2. Add IOD or other forecast indices only with matched historical issue/lead archives. Current future curves alone cannot validate a forecast predictor.
3. Evaluate the whole selection policy, calibration, reliability and uncertainty using chronological tests and year-block resampling. Avoid selecting and reporting performance on the same years. Report native-cell support and actual test counts.
4. Consider spatially pooled or partially pooled coefficients while retaining local outcomes and thresholds; a separate fit at every fine cell is not inherently more skilful.
5. If ensemble index members are used, calibrate their distributions from hindcasts and propagate them through the model. Do not label raw member spread as a calibrated interval.
6. Compare seasonal SST ensemble forecasts as an additional candidate. Published ECMWF assessments show strongly location-dependent MHW skill; global or tropical skill cannot establish coastal-cell skill here.
7. Keep research probabilities visible with historical baseline and held-out skill; do not upgrade their alert status solely because forecast indices are available.

Source: https://os.copernicus.org/articles/20/265/2024/
Issued ENSO archive: https://forecast.ccsr.columbia.edu/forecasts/enso/plumes
JAMSTEC source: https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html

Audit values: qa/outlook_review_20261101.json. Code inspected: scripts/pixel_outlook.py, forecast_index_models.py, external_index_forecasts.py, verify_forecast_indices.py, update_climate.py and dist/app.js.
