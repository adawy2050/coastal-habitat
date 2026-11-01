# Outlook combination tests — November 2026

This comparison retains the October 2026 issue and December 2026–February 2027 target, so its results can be compared directly with the existing outlook. It does not silently roll an October fit into another issue month.

## Inputs and candidates

Twelve predefined candidates compare historical frequency; linear long-term change; recent local SST and MHW days; six observed climate indices; observed ENSO/PDO; and the issued IRI combined, dynamical and statistical ENSO forecasts, alone or together with local conditions and observed indices. The full list and native-cell results are in `dist/forecasts/combinations/{product}/summary.json`.

Local SST is the June–August mean at the nearest retained OISST source; its source index and distance accompany every cell. Recent MHW exposure uses June–August monthly counts from the selected native product. Outcomes use each native cell's own DJF MHW-day record. Complete DJF 2025/26 incorporates the certified January–February extension and December boundary correction. No current-year future MHW outcome is invented. The long-term term is year, not causal attribution of anthropogenic warming.

Every continuous predictor is centred and scaled using that origin's training years. Ridge logistic regression uses a fixed penalty of 10, set before scoring; the intercept penalty is 1e-6. This comparison does not detrend climate indices: trend, local temperature and indices are competing predictors under shrinkage. Consequently a change relative to the previous detrended model cannot be attributed solely to the extra forecast input. Constant outcome histories use smoothed prevalence.

Thresholds at each origin are the greater of 10 days and the prior same-season 80th percentile. Issued-forecast candidates train only on years with matching historical October forecasts; other candidates can use the longer earlier outcome record. No realised target-season climate index substitutes for an issued forecast.

## Evaluation

All candidates are evaluated on the same 2016–2025 target years. Primary scores use only years after the MHW baseline was available: 2023–2025 for MUR, 2016–2025 for OISST. Earlier MUR scores are retrospective. Candidate selection is itself evaluated: use climatology for the first four comparison origins, then choose the candidate with the smallest mean squared probability error in earlier origins only. The future selection uses all earlier comparison losses. This policy score is distinct from the best candidate's score on the same evaluated years.

Paired year-bootstrap bounds compare that selection policy with the saved published policy. These are descriptive pointwise bounds with 1,000 resamples, not spatially adjusted significance tests or proof of calibrated alerts. They do not account for serial dependence between years. Native-cell counts are not independent sample sizes. This release preserves the published probabilities and exposes the candidate comparisons separately. The short MUR evaluation and the limited selection-policy test record should not be hidden by a finer map resolution.

## Other available forecasts

Nine JAMSTEC SINTEX-F feeds were downloaded with source URLs, hashes, modification dates and ensemble members: Niño-3.4, DMI, EMI, ATL3, SIOD, SASD, NNI, CNI and DNI. Their current monthly predictions extend through August 2027. Each feed's historical values are observations, not archived historical forecast issues. Those observations cannot be used as though the model had predicted them. These nine forecast curves are available in the portal; only matched issued ENSO archives enter the forward-tested forecast combinations.

The IRI IOD browser archive begins in September 2025, too short for the requested multiyear test. The older JAMSTEC F1 page provides archived raster plots with an earlier model and baseline; these have not been silently mixed with current F2 numerical forecasts. Additional indices can enter the candidate framework when matched historical issue/lead records are obtained.

## Reproduction

From the repository directory:

```powershell
python scripts/collect_forecast_combinations.py
python scripts/test_outlook_combinations.py --product oisst
python scripts/test_outlook_combinations.py --product mur
python scripts/verify_outlook_combinations.py
python scripts/package_outlook_combinations.py
python scripts/build_assets.py
python scripts/verify_assets.py
```

The model script fails closed outside the supported October 2026 comparison. The browser continues to show its issue explicitly after later main-outlook refreshes. Full arrays are retained locally under `_cache/outlook_combinations`; public point-sized compressed records avoid downloading all cells for one location. The original study arrays and published outlook probabilities are unchanged.

Sources: [IRI ENSO](https://forecast.ccsr.columbia.edu/forecasts/enso/plumes), [IRI IOD archive](https://forecast.ccsr.columbia.edu/forecasts/iod?month=9&year=2025), [JAMSTEC index definitions and downloads](https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html).

## Results of this run

| Product | Native cells | Qualifying test seasons | Median selection-policy Brier skill | Cells with positive policy skill |
|---|---:|---:|---:|---:|
| OISST | 2,264 | 10 | 0.175 | 80.8% |
| MUR | 166,771 | 3 | 0.021 | 52.4% |

These are held-out scores of the earlier-test selection procedure, not the maximum of the candidate scores. The archived published policy had median skill -0.00845 for OISST and -0.0289 for MUR on matching years and binary outcomes. The new OISST local-plus-observed candidate had median skill 0.234; adding the combined issued ENSO forecast gave 0.223. More forecast inputs therefore did not always improve the result. The new MUR local-plus-observed-plus-both-ENSO candidate had median skill 0.141, but only three qualifying seasons support that summary.

At 9.89 N, 118.04 E, the OISST selection procedure proposes 59.8% with skill 0.004; MUR proposes 22.4% with skill -0.158. The basin-wide improvement does not establish a reliable alert at this example cell. Default published probabilities remain unchanged.

Independent optimiser checks passed 18 synthetic fits and six real-cell warming fits (maximum differences below 5e-9 for the real cells). Every native-cell historical label and climatological probability matches the original comparison on the same years. Six browser checks cover both products in all three study areas; all nine forecast selectors and the point CSV passed.
