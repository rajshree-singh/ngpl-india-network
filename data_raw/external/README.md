# External sources

`SOURCES.md` records the publisher, URL, size, checksum, licence and access
date of every external file this dataset uses.

The files themselves are **not** stored here:

- **GeoNames gazetteer** (`IN.txt`, `admin1CodesASCII.txt`) — 69.6 MB, above
  what GitHub handles comfortably. `scripts/00b_fetch_gazetteer.py` downloads
  both and rewrites `SOURCES.md` with a fresh checksum and access date.

Folders for the seismic, population, flood and boundary layers are not present
because that work is not part of this release. `scripts/00_colab_setup.py`
creates them when needed.
