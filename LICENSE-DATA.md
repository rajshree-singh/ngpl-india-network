# Licence for the data in this repository

**Everything in `data_processed/`, `gis/` and `metadata/` is licensed under the
Creative Commons Attribution 4.0 International Licence (CC BY 4.0).**

Full text: https://creativecommons.org/licenses/by/4.0/legalcode
Summary:   https://creativecommons.org/licenses/by/4.0/

You may share and adapt this data for any purpose, including commercially,
provided you give appropriate credit. Cite it as shown in `CITATION.cff`.

**The code in `scripts/` is licensed separately**, under the MIT Licence — see
`LICENSE`. Two licences are used because code and data have different
conventions; both are permissive.

## What this licence does NOT cover

- **The source register** (`20251231_NGPL.pdf`). Published by the Petroleum and
  Natural Gas Regulatory Board. Not redistributed here; its own terms apply.
- **The GeoNames gazetteer.** Licensed CC BY 4.0 by GeoNames. Not redistributed
  here; `scripts/00b_fetch_gazetteer.py` retrieves it.
- **OpenStreetMap-derived outputs.** OSM is licensed ODbL. Those outputs are not
  included in this repository; see `.gitignore` for the reason.
- **Files in `data_raw/legacy_v0/`.** These are the authors' own superseded
  working files, retained so that the correction history can be verified. They
  are released under the same CC BY 4.0 terms as the rest of the data, but they
  are **superseded and must not be used as data**. `metadata/changelog.csv`
  records what was wrong with them.
