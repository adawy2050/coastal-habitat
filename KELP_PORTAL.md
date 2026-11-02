# Coastal habitat observatory and kelp portal

The home page links to the existing heatwave atlas, the new kelp station viewer and an inactive seagrass entry marked under construction. No seagrass model, analysis or dataset was added.

## Pages

- `/` — observatory home.
- `/heatwaves.html` — existing heatwave atlas, with a Home link. Existing root URLs with atlas coordinates, filters or section fragments redirect here with their parameters intact.
- `/kelp/` — kelp station map, model results, methods, sources and acknowledgements.

The new pages share the atlas's light sea-green/slate palette, full-width map, satellite and shoreline options, large point window, CSV downloads, chart SVG exports, language controls and testing/contact labels. The home and kelp pages have English, Arabic and Japanese text. The heatwave atlas retains its existing language support and scientific files.

## Adopted sources

**Saccharina longissima:** `D:/kep model/kelp_paper_revision_20260306/ssp_model_runs_20261020/manuscript_TPM20p43_20261021`. The adopted historical run has 99 stations, 1996–2020; SSP1-2.6 and SSP5-8.5 cover 2021–2100. The 2021–2025 adjustment interval is marked. The portal uses per-thallus results, not a new bed-area or density extrapolation. It preserves the actual internal-step joint-growth-factor mean, rather than multiplying averaged factors. Historical annual means, peaks and detachment were checked against the native annual station table. The manuscript interpretation and acknowledgements follow the package checked on 26 October 2026.

**Saccharina japonica:** `D:/kep model/otherspeciesmodels/Saccharina_japonica_focus/32_Japonica_1931_model_ready_20261008/outputs_1991_2020_higher_mixedNO3`. All 1,930 completed station scenarios are included, 1991–2020. The blocked `JAP_OCC_000010` is excluded. Earlier rejected calibration branches are not substituted for this completed delivery. No completed future run was found or invented. The 2019 nutrient-source switch is marked. Individual mass, mature density, bed standing biomass, component growth factors and the mature-compartment mass budget remain distinct. Seasonal tissue loss is part of erosion and is not added twice. No unsupported joint-growth-factor reconstruction is made from the Japonica daily-average factors.

## Display data

`scripts/build_kelp_portal.py` reads only saved model outputs and source completion reports. Monthly curves are native-daily calendar-month means. Annual states/factors are means and annual fluxes are integrated sums. Annual Longissima peaks retain native internal-step maxima; Japonica peaks retain native daily maxima. No model is rerun, fitted, rescaled or smoothed by the website.

Each point/scenario is one gzip binary file with four little-endian uint32 dimensions, float64 per-field scales, and uint16 monthly/annual values. Missing entries use 65535. Decoded values are `q × scale`; the maximum absolute rounding error is `scale/2`. The source checks run before compression. CSV downloads retain each field's bound. Near-zero plotted values are display approximations, not a separate claim of bed disappearance. The 2,227 point/scenario records retain SHA-256 checksums in the catalogue. Small annual map arrays reuse the decoded point values in catalogue station order.

No raw restricted SENTAN forcing, private manuscript access links, full manuscript PDFs, or individual Habomai monitoring records are distributed. The manuscript's JST CREST acknowledgement (JPMJCR23J1), named collaborators, model authors and FORA providers are credited. Background photo author, source and CC BY-SA licence are displayed. Existing Esri and GSHHG map credits remain visible.

## Rebuild and verify

```powershell
cd 'D:\Red Sea paper\habitat-mhw-atlas'
python scripts/build_kelp_portal.py
python scripts/package_kelp_maps.py
python scripts/verify_kelp_portal.py
python scripts/build_assets.py
python scripts/verify_assets.py
python scripts/browser_kelp_qa.py
```

The extraction reads the two source folders but does not edit them. Cached station exports resume when their source size and modification time match. Remove the corresponding `_cache/kelp_export` receipt before changing the export schema. The website is a viewer of the completed simulations; it does not claim live assimilation, field validation of every station, or a climate-model ensemble. The established Monday climate-index refresh continues for the heatwave atlas only.
