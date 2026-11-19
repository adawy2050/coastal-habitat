# Observed 2026 habitat-cell extension

The extension downloads real SST observations for the existing habitat cells. It does not replace the archived historical arrays, change habitat footprints, or add an unfinished year to the annual forecast training.

- Verified upstream availability on 22 October 2026: NASA/JPL MUR v4.1 through 20 October; NOAA OISST v2.1 through 20 October (recent NCEI daily files are preliminary). The ERDDAP OISST mirror was behind NCEI and was not used for the latest 2026 observations.
- Downloads include December 2025 for detection across the year boundary. All new writes are isolated in a separate update workspace (`ATLAS_UPDATE_20261022`); original study archives are read only.
- Native cells and atlas mappings remain unchanged: MUR 166,771 cells and OISST 2,264 cells across the three studies.
- Fixed source climatologies and p90 thresholds remain 2003–2022 for MUR and 1982–2011 for OISST.
- Red Sea/Gulf: at least five consecutive days above the fixed threshold, without gap joining, matching their source code.
- East Asia: join threshold-crossing runs separated by at most two days, then retain segments at least five days long. Saved source flags reproduce saved event masks exactly with this order. Archived packed anomaly/threshold values can round values near the threshold, so detector verification uses the original integer exceedance flags, while intensity remains a temperature difference. Original 2025 daily SST independently checks temperature packing.
- The unfinished 2026 record is a separate observed-to-date panel. Frequency resets at 1 January; mean duration is the within-2026 day count divided by within-2026 event segments. It is not a completed-event duration estimate.
- Final four days (Red Sea/Gulf) or six days (East Asia) can gain event membership after later SST observations arrive. Observed SST itself is not a projection.
- Public binary arrays are cell-major, within 256-cell chunks, then dates. SST, anomaly and threshold-relative intensity use int16 hundredths of a degree Celsius. MHW membership uses uint8. Files use gzip; the index identifies the exact dates and cell ranges.
- Every exported file has SHA256 and byte count. Independent local checks compare daily mask sums with every monthly count and every observed-to-date total. There are no zero-filled future months.

`observed2026_sync.py --launch` starts the isolated resumable remote supervisor. `--watch` polls progress. The supervisor retries network download failures after 120 seconds and stops on scientific QC failures. `observed2026_fetch.py` transfers only ready, QC-passed products and verifies them before use.
