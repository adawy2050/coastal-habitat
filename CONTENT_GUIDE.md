# Updating photos, papers and news

The portal is a research preview. The contact link is
`ahmed.eladawy@jamstec.go.jp`. Scientific observations and editorial sources have
separate dates; refreshing this catalogue does not refresh the SST analysis.

## Source catalogues

- Edit `dist/content/papers.json` and `dist/content/news.json`.
- Paper links use their DOI. Preserve the publisher's title and publication-date
  precision: a source dated `2026-10` does not imply a specific October day.
- News can be an institutional announcement or a clearly attributed research
  update linking to the paper. Keep the original publication date.
- `coverage` contains named study areas and approximate search bounds in
  `[west, south, east, north]` order. These are not sampled sites. Do not infer
  study geography from an author's affiliation.
- `basins` uses `redsea`, `gulf` or `eastasia`. An empty list denotes a general
  reference, available through **All sources** rather than as local news.
- Include an Arabic title and summary where applicable. English publisher and
  photographer names remain as credited by the source.

The default view ranks studies covering the selected point, nearby study areas,
then basin context. Sources mapped to another part of the basin can be reached
through **Study basin**. Paper pages contain ten entries. The point window and
downloaded PDF use the same source selection.

`scripts/refresh_area_catalogue.py` reproduces the reviewed 1 November 2026
edition. Add reviewed DOI entries and source geography there for a later
edition, and change its explicit review date. It reuses already checked
metadata. Optional `--check-all` checks older DOI records sequentially and stops
if the provider rate-limits access, retaining earlier verification dates.
The existing weekly workflow checks source metadata without inventing new
articles or changing their publication dates.

## Photographs

`dist/images/credits.json` holds provenance, coordinates, habitat classes and
licences. Automatic point context prefers matching habitat photographs within
300 km, with distances displayed. Where these are absent it uses other local
collection photographs from the same basin. A photograph is not a measurement
at the habitat cell.

`contextQuality: false` retains an image in the collection while excluding it
from automatic point context. Full originals remain available from their source;
local previews keep the viewer usable when an original server is slow.

## Checks and publication

Run `python scripts/build_assets.py`, `python scripts/verify_assets.py` and
`python scripts/browser_light_coasts_qa.py` after source or design changes.
Inspect the preview and exported PDFs, then publish through the existing
GitHub Pages workflow. Scientific files retain their separate study manifest.
