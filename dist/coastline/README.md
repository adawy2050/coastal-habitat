# Detailed shoreline display

Source: **GSHHG 2.3.7**, Paul Wessel and Walter H. F. Smith. Original full-resolution ESRI shapefiles (resolution `f`, levels 1–4), obtained from the [official GMT release](https://github.com/GenericMappingTools/gshhg-gmt/releases/tag/2.3.7).

Citation: Wessel, P., and W. H. F. Smith (1996), A global, self-consistent, hierarchical, high-resolution shoreline database, *Journal of Geophysical Research*, 101(B4), 8741–8743. DOI: [10.1029/96JB00104](https://doi.org/10.1029/96JB00104).

These derived display files are released under the same **GNU Lesser General Public License, version 3 or later**. The original notices, README and LGPL text are included. The GPL v3 text referenced by LGPL is included as `COPYINGv3` from the [GCC project mirror](https://github.com/gcc-mirror/gcc/blob/master/COPYING3).

## Modifications, 22 October 2026

The atlas clips the original polygons to its three study domains and divides them into 4-degree tiles. Full-resolution tile vertices are retained without line simplification; coordinate storage is rounded to five decimal degrees. This rounding is a storage choice and does not describe source survey accuracy. The global, unclipped overview uses a 0.03-degree simplification tolerance and omits source polygons smaller than 5 km². It also includes the source L5 Antarctic ice-front polygons as land. All source islands within the three study domains are retained in the detailed tiles.

The data are for display only. They do not replace habitat footprints, SST grids or any mask used in the heatwave analysis. GSHHG is assembled from historical sources and is not a survey of the present shoreline.

## Rendering contract

Load `index.json` first. Bounds are `[west, south, east, north]` in EPSG:4326. At overview scales, load `overview.path`. At zoom 8 or above, fetch and cache only `tiles[].path` whose bounds intersect the current view. Hide the overview when detailed tiles are ready to avoid retaining simplified protrusions beneath the full-resolution coast.

Each GeoJSON feature has `properties.kind` and `properties.level`. Draw fills in increasing level order: L1 land, L2 inland water, L3 islands within lakes, L4 water within those islands. For detailed tiles use **no polygon stroke**. Then draw features with `kind: coast` as thin dark lines. These line features are clipped from the original boundaries independently: the artificial edges of a tile or study domain are not shorelines. The unclipped global overview has no separate coast features; its polygons can use a thin stroke directly.

The data contain no raster imagery and require no map-service API key. Attribute “Shoreline: GSHHG 2.3.7, Wessel & Smith (LGPL)” with the source link provided by `index.attributionHtml`.

Rebuild with `python scripts/shoreline_build.py`; check with `python scripts/shoreline_verify.py`. The scripts verify the downloaded archive checksum and record individual asset SHA-256 checksums in `index.json`.
