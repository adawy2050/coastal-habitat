# Coastal habitat observatory

The home page now links to the marine heatwave atlas and the kelp digital twin. The third entry, the seagrass digital twin, is marked under construction; no seagrass model or data are included.

- Home: https://adawy2050.github.io/redsea-habitat-mhw-atlas/
- Heatwave atlas: https://adawy2050.github.io/redsea-habitat-mhw-atlas/heatwaves.html
- Kelp digital twin: https://adawy2050.github.io/redsea-habitat-mhw-atlas/kelp/

Existing root URLs with atlas coordinates, filters or section fragments still open the heatwave atlas with their parameters preserved. The atlas HTML source is now `dist/heatwaves.html`; `dist/index.html` is the home page. Scientific atlas arrays and the weekly climate refresh retain their existing locations.

The kelp viewer includes 99 Longissima stations (1996–2020 and two 2021–2100 SSP runs) and 1,930 Japonica historical stations (1991–2020). See [KELP_PORTAL.md](KELP_PORTAL.md) for adopted source runs, acknowledgements, scope, data format and reproduction.

## Heatwave atlas


A static atlas of **210,680 habitat cells** across the Red Sea, Arabian Gulf, East Asia and western Pacific. It includes coral, seagrass, mangrove and kelp/macroalgae footprints, annual and monthly marine heatwave histories, native daily OISST temperature, climate indices and separately backtested seasonal probabilities.

**Website:** https://adawy2050.github.io/redsea-habitat-mhw-atlas/

## Explore

- Start with a map rectangle or select any of the three study areas and their MEOW ecoregions.
- Animate annual habitat-cell maps for six marine heatwave metrics.
- Distinguish solid observed series from dotted annual model fits; toggle fitted linear trends in history and climate charts.
- Blend satellite imagery with the detailed shoreline using independent opacity controls. Seagrass starts off; coral, mangrove and kelp layers start on.
- Click a cell to open a large analysis window with its history, 2026 observations, climate links, outlook and PDF report.
- Compare up to five pinned cells with the selected cell.
- Fit annual pixel histories to seven climate indices and either a time trend or local annual OISST SST.
- Inspect Shapley R² shares, observed/fitted histories and leave-one-year-out fit.
- Compare raw or detrended paired climate–heatwave histories with 0–2-year index leads.
- Plot any of the seven climate indices at annual or monthly frequency.
- Export pixel data, comparisons, climate series, fitted model data, map PNGs and chart SVGs.
- Share a selected cell using its latitude/longitude in the URL.
- View upcoming-season probabilities for each habitat overall, each habitat × ecoregion, or the selected pixel, with historical baselines and chronological backtests.
- Choose prediction probability in the map-variable dropdown to map individual source-cell forecasts.
- Create a point PDF with all six annual histories, the seasonal outlook, validation, climate associations and author contacts.
- View newly released NOAA monthly indices while preserving the manuscript's historical climate archive.
- Switch between English and Arabic at the top; Arabic uses a right-to-left layout, translated controls, chart labels and methods. The choice persists and can be shared with `?lang=ar` or `?lang=en`.
- Set the climate chart's own date range, jump to the current year, or view annual means including clearly labelled partial years. Latest-month cards retain each index's actual publication date.
- Browse 470 openly licensed photographs across all three study areas, with nearby locations, source links, photographer credits and original-resolution viewing.

GHRSST MUR is the first view (2003–2025, 0.01°, baseline 2003–2022). OISST provides the longer record (1982–2025, 0.25°, baseline 1982–2011). The map locations remain habitat grid cells; selecting OISST does not increase its native SST resolution.

## Run locally

```powershell
cd 'D:\Red Sea paper\habitat-mhw-atlas'
powershell -ExecutionPolicy Bypass -File .\preview.ps1
```

Open http://localhost:8765. No Node installation, build step, API key or database is needed. Libraries, coastline geometry and scientific display data are included. Satellite imagery loads from Esri World Imagery for the visible viewport; the coastline basemap works without that service. Coverage layers are rendered publication maps of the study inventories; original GIS polygons are not distributed.

## GitHub Pages

The included `.github/workflows/pages.yml` publishes `dist/` after pushes to `main`. In repository **Settings → Pages**, set **Source** to **GitHub Actions**. Every path supports a GitHub Pages project subdirectory.

The same workflow refreshes NOAA climate observations and seasonal models at habitat, ecoregion and individual source-cell scales each Monday at 00:20 UTC (09:20 JST), and on manual dispatch. It commits the updated feed, forecast arrays, outlook and checksum files before deploying. Failed downloads leave the previous successful published version intact. Complete-year study arrays end in 2025; the separate 2026 observation extension uses the server download and QC pipeline.

The current IOD archive is delayed. A fixed six-index panel (Niño-3.4, NAO, AO, EAWR, North Atlantic SST anomaly and PDO) supplies the dated seasonal outlook, with its own nested chronological backtest. The seventh index remains available in the historical analysis and latest-feed charts. Model probabilities are shown with a historical baseline and Brier skill, rather than validated alert categories.

The climate panel also shows the selected point's next-season forecast with its dates, historical probability and backtest. Its climate date range is independent of the MHW analysis years. Current-year monthly data stop at the latest available observations; annual means for incomplete years use available months only, with month counts included in CSV exports. The downloadable point PDFs remain in English, as labelled in the Arabic interface.

## Data and statistics

See [DATA_METHODS.md](DATA_METHODS.md). Browser data are in `dist/data/`. `metadata.json` describes native cell coordinates and periods; `pixels.json` links habitat coordinates to those native SST cells. Binary `.f32` files are little-endian float32 arrays. Annual and seasonal histories are ordered **year × native source cell**. Forecast probabilities and scores have one value per native cell; backtests are **test year × native cell**, and coefficients are **native cell × seven coefficients**. Missing intensity/duration values are NaNs.

`validation.json` records the 108 Red Sea annual-summary checks. `gulf_validation.json` records Gulf source-summary comparisons, duplicate-row checks, marine attachment, native seasonal/annual consistency and source completeness. `scripts/test_multibasin.py` also compares matching Gulf source values and checks that Red Sea annual histories, pixel coefficients, backtests and probabilities remain unchanged. `manifest.json` includes asset checksums and hashes of the corrected habitat attachment and climate inputs.

Each pixel forecast is fitted to its own source-cell seasonal MHW history, threshold and training-only choice of regularisation. Habitat-wide and regional forecasts instead use their corresponding mean exposure histories. Whole-habitat forecasts are fitted separately for each basin; choosing all study areas shows each set. Repeated habitat attachments to one SST cell share that cell's forecast. Pixel skill is tested independently; finer spatial support does not guarantee higher skill.

The selected-cell multivariate model is calculated by `dist/stats.js`. It is a full-record statistical fit, separate from the manuscript's chronological seasonal warning analysis. Model output changes when the selected pixel, outcome, years, reference or lead changes. The paired detrending switch affects only the paired plot.

## Rebuild from the original study workspace

```powershell
python .\scripts\build_multibasin.py
python .\scripts\update_climate.py
python .\scripts\verify.py
node .\scripts\test_stats.cjs
python .\scripts\test_outlook.py
python .\scripts\test_pixel_outlook.py
python .\scripts\test_multibasin.py
```

The combined builder reads `_cache/redsea_atlas_base` (the preserved original display package) and `_cache/gulf_extracted` (the compact remote extraction), plus the Gulf annual source tables in `_cache/gulf_source`. These private rebuild inputs are excluded from Git. The public website and scheduled climate refresh work directly from the included static files. The original Red Sea package is also recoverable from Git commit `8381735`; `build_data.py` and `build_seasonal_pixels.py` remain the original Red Sea-only source builders.

`scripts/extract_gulf_remote.py --root STUDY_ROOT --output NEW_ATLAS_CACHE` runs on the Gulf study server and reads its native annual metrics, full native event catalogues and daily SST. It writes only a separate atlas transfer cache. The Gulf extraction retains 15,940 of 15,996 known-ecoregion locations within the 5 km MUR marine-attachment limit, reattaches 1,715 coastal locations and excludes four unknown-ecoregion records. Repeated identical annual rows are counted once. No seagrass records occur in the source Gulf of Oman inventory.

`scripts/build_coverage.py` renders both original local habitat inventories to transparent map tiles. It requires GeoPandas, Rasterio and Pillow. `scripts/build_seasonal_pixels.py` reconstructs native-cell seasonal histories from the saved events and checks annual totals and monthly habitat summaries. `scripts/update_climate.py` requires NumPy, pandas and SciPy and works from the included seasonal histories and training cases; scheduled refreshes never need the large original event or SST archives. `scripts/test_pixel_outlook.py` compares batched forecasts with independent scalar fits and sampled nested backtests.

## Sources and attribution

Ahmed Eladawy. Contact: ahmed.eladawy@jamstec.go.jp. SST: NASA/JPL GHRSST MUR v4.1 and NOAA OISST v2.1. Habitat inventories: UNEP-WCMC Ocean+ Habitats (coral 2021, seagrass 2021, mangroves 2010). Climate: NOAA CPC, PSL and NCEI ERSSTv5. Satellite imagery: Esri, Vantor, Earthstar Geographics and the GIS User Community. Coastline: GSHHG 2.3.7 under LGPL, with Natural Earth public-domain fallback. Detailed GSHHG vertices are retained in lazy map tiles. Leaflet 1.9.4, Plotly.js 2.35.2, jsPDF 4.2.1 and jsPDF-AutoTable 5.0.8 are vendored with their original license notices. Original data providers' use and attribution terms continue to apply. This repository contains sampled numerical habitat-cell values and rendered coverage maps, not the original habitat polygon datasets or cached satellite imagery.

The 470-photo collection includes Red Sea reefs, seagrass and Farasan mangroves; Arabian Gulf reefs, UAE and Qatar mangroves; real satellite views; and clearly labelled bleaching comparisons from other regions. Full originals are retained locally in `D:\Red Sea paper\atlas-photo-library`, with SHA-256 hashes and source download URLs. Compact previews are hosted on Pages. Sources, photographers and licences are retained in [`dist/images/credits.json`](dist/images/credits.json) and [`PHOTO_AUDIT.md`](dist/images/PHOTO_AUDIT.md). Original photos are unedited. Their licences apply independently of the portal code. The viewer supports full native pixels, pan, download and keyboard navigation. Photos illustrate habitats and do not describe the selected pixel's condition.

## Editing the research and news sections

`dist/content/papers.json` contains 29 published-paper entries, paged ten at a time. Regional papers and news follow the selected study area. A `basins` list determines which area shows each item; empty lists retain general references in the source catalogue. Each paper has a DOI, publisher title, Arabic title, journal, year and topic (`regional`, `habitats`, `methods`, `forecast`). `dist/content/news.json` contains dated source links with reviewed English/Arabic titles and short summaries. Add or edit entries using the existing structure. No API key or runtime third-party photo embed is needed.

After editing source modules locally, run in PowerShell:

```powershell
python scripts/build_assets.py
python scripts/verify_assets.py
python scripts/verify.py
python scripts/verify_detail.py
```

Commit and push changes to `main`; GitHub Pages assembles and publishes them. The Monday 00:20 UTC job refreshes monthly climate feeds, genuine daily AO/NAO observations, seasonal probabilities and the NOAA ENSO bulletin date. Existing publisher metadata is checked every 90 days. New papers/news and their Arabic translations are curated entries. SST and MHW observation histories retain their documented end date (2025).

## Interface upgrade

See [UPGRADE_NOTES.md](UPGRADE_NOTES.md) for phases, measurements and verification. Editable source modules remain in `dist/`; `scripts/build_assets.py` assembles `language.js`, `interface.js` and `interface.css`. Original scientific files and `data/manifest.json` are preserved; `asset-manifest.json` covers presentation and dense-display assets separately. The browser uses the official self-hosted Plotly 2.35.2 Cartesian partial bundle with the existing Plotly licence. Daily SVG curves retain every observation. PDF libraries load on demand.


## East Asia extension — 18 October 2026

The independent export retains 145,332 of 150,773 study sites after valid marine MUR attachment within 5 km. It adds 22 ecoregions plus 15 cells outside the mapped ecoregions. Earlier Red Sea and Gulf numerical slices are preserved and checked by `test_eastasia.py`. Native quarterly and monthly records, daily OISST and habitat/region training outcomes are appended independently.

The source `exceedance` field is an integer threshold flag, not temperature. East Asia temperature intensity is calculated from saved anomaly + climatology − p90 threshold on the saved event mask. Annual frequency follows the existing no-leap/year-boundary convention. Missing MUR dates (2021-02-20, 2021-02-21, 2022-11-09) remain absent.

East Asia seagrass footprints include modelled top-percent suitability grids for Zostera marina, Z. japonica and Z. caespitosa; kelp/macroalgae footprints are occurrence based. Coverage, reports and methods retain this distinction.

Interface labels are available in English, Arabic, simplified/traditional Chinese, Japanese, Korean, Filipino, Indonesian, Malay, Vietnamese, Russian and Persian. Scientific source titles retain their original wording; PDF reports use English. Photos use verified open licences and geographic coordinates or explicitly approximate named areas. The nearest photo is not presented as a photograph of the selected heatwave cell.

The weekly GitHub workflow refreshes climate observations and refits seasonal models for all three study areas. Historical MHW arrays stay frozen through 2025. Future annual dotted lines are conditional on the stated climate inputs; seasonal probability lines describe the whole forecast season.

## Scientific figures — 19 October 2026

Upcoming-season probabilities are grouped into one figure per habitat. Each ecoregion has a persistent colour and line style across habitats; the legend can hide individual regions. Past chronological-test probabilities and the next whole-season probability are separate segments, without invented monthly forecasts. Figures and the native monthly calendar can be downloaded as SVG. Annual history has a selectable right axis; daily SST, monthly SST and monthly MHW days share a separate two-axis plot. Point summaries use compact text rather than large-number cards.

Verification includes exact preservation of earlier basin arrays, 12,060 original East Asia annual-day comparisons, native seasonal model refits, daily SST/annual-mean agreement, monthly/annual MHW sums, 24 language/viewport combinations and a generated point PDF.

## Observed 2026 update and layered point view

The atlas adds separately checked 2026 observations through20October2026. OISST is available for all2,264nativecells across all three study areas. MUR downloads and analysis run in a resumable server job; `status/` shows live progress from the dedicated `atlas-progress`branch. The processing chain starts analysis after downloads, checks results, transfers certified files, verifies local data and publishes. `resume_2026_update.ps1` resumes the local publishing watcher if needed. The monitor bridge runs independently on the study server; no credentials are stored in the source or on disk.

Click a habitat point to open the large analysis window, including history, daily/monthly data, climate links, seasonal outlook,2026observations and a PDF report. Satellite imagery and GSHHG shoreline have independent opacity controls. Seagrass is off by default; coral, mangroves and kelp remain enabled. GSHHG2.3.7full-resolution vertices are loaded only for visible detailed tiles; a global simplified overview is used at low zoom. Scientific analysis masks are unchanged.

2026 remains separate from complete annual model training. January–September heatwave-day comparisons use the same completed months in every year. New monthly and regional summaries are generated by `scripts/observed2026_summaries.py`. The point report retains source-grid resolution and marks preliminary observations and recent event membership.

## October 2026 update

Certified daily SST, heatwave membership and monthly counts through 20 October 2026 are delivered separately in `dist/observed2026/`. OISST is complete; MUR is downloaded and checked by an isolated server worker. The public `/status/` page follows its progress. Each product starts analysis immediately after download, and a server publisher verifies and publishes the finished update without depending on the local computer. The daily/monthly point views and PDFs include the new observations. Partial 2026 values do not replace complete-year annual-model training.

`external_index_forecasts.py` downloads forecasts already issued by Columbia/IRI and JAMSTEC. The public IRI SVG preserves plotted numerical vertices; its labelled combined-average curve is recovered to 0.01 °C, with source hashes. The matching issue-month archive begins in 2004. JAMSTEC supplies monthly Niño-3.4 and IOD forecasts and model members into 2027. Source anomalies and reference periods are retained.

`forecast_index_models.py` tests the issued ENSO forecast as an extra input to each cell's six-index ridge model. Thresholds, detrending, scaling, regularisation, blend selection and the promotion gate use earlier seasons only. Both candidates use the same target definition. At least eight earlier post-baseline test seasons and a lower past Brier score are required before adding the forecast. The gate is repeated inside historical tests. A new completed DJF season can be added from certified January–February observations. Its December 2025 tail is checked against January 2026 so events crossing the former record boundary are included; the archived study arrays remain unchanged. Current IOD forecasts are shown but are not a fitted cell-model input without a matching issue archive. `verify_forecast_indices.py` checks public-figure extraction and independent point refits.

The Monday GitHub job refreshes climate observations, published index forecasts, cell comparisons and source catalogues. Bulk SST observations use the server download/QC pipeline, not the climate-only GitHub job. Missing or failed feeds preserve the last successful files; a forecast is used only when its issue month and target season match the current outlook.
