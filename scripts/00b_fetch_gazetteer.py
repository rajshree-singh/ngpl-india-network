# -*- coding: utf-8 -*-
"""
00b_fetch_gazetteer.py  --  download the GeoNames gazetteer and record its provenance.

Run once. Downloads BOTH files 04_geocode_nodes.py needs, verifies them, and
appends a dated, licensed entry to data_raw/external/SOURCES.md so the coordinate
provenance is written down at the moment of acquisition rather than reconstructed
later from memory.

  IN.zip                 -> IN.txt                 all populated places in India
  admin1CodesASCII.txt   -> state code -> state name

The second is NOT optional: IN.txt stores admin1 as a numeric code ("24"), so
without the code table the state constraint cannot match and every node returns
UNRESOLVED -- a code failure that looks exactly like a data failure.
"""
import os, sys, io, zipfile, urllib.request, hashlib, datetime

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
GDIR = os.path.join(ROOT, "data_raw", "external", "gazetteer")
SRC  = os.path.join(ROOT, "data_raw", "external", "SOURCES.md")
os.makedirs(GDIR, exist_ok=True)
os.makedirs(os.path.dirname(SRC), exist_ok=True)

URLS = {
  "IN.zip":                "https://download.geonames.org/export/dump/IN.zip",
  "admin1CodesASCII.txt":  "https://download.geonames.org/export/dump/admin1CodesASCII.txt",
}
today = datetime.date.today().isoformat()
notes = []

for fname, url in URLS.items():
    dest = os.path.join(GDIR, fname)
    print(f"downloading {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ngpl-india-network/1.0"})
        blob = urllib.request.urlopen(req, timeout=180).read()
    except Exception as e:
        sys.stderr.write(f"FAILED {url}\n  {e}\n"
                         f"  If Colab has no outbound access, download it in a browser\n"
                         f"  and upload to {GDIR}\n")
        continue
    sha = hashlib.sha256(blob).hexdigest()[:16]
    if fname.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            z.extract("IN.txt", GDIR)
        out, size = "IN.txt", os.path.getsize(os.path.join(GDIR, "IN.txt"))
    else:
        open(dest, "wb").write(blob)
        out, size = fname, len(blob)
    print(f"  -> {out}  {size:,} bytes  sha256:{sha}")
    notes.append((out, url, size, sha))

# verify what 04 actually needs
need = ["IN.txt", "admin1CodesASCII.txt"]
missing = [n for n in need if not os.path.exists(os.path.join(GDIR, n))]
if missing:
    print(f"\nSTILL MISSING: {missing}  -- 04_geocode_nodes.py will refuse to run.")
else:
    n_places = sum(1 for _ in open(os.path.join(GDIR,"IN.txt"), encoding="utf-8"))
    n_states = sum(1 for l in open(os.path.join(GDIR,"admin1CodesASCII.txt"), encoding="utf-8")
                   if l.startswith("IN."))
    print(f"\nOK  IN.txt {n_places:,} rows   admin1CodesASCII.txt {n_states} Indian states/UTs")

# --- provenance, written at acquisition time ---------------------------------
entry = [f"\n## GeoNames gazetteer (accessed {today})\n",
         "Used by `scripts/04_geocode_nodes.py` to assign node coordinates.\n",
         "Publisher: GeoNames (https://www.geonames.org/)\n",
         "Licence: Creative Commons Attribution 4.0 (CC-BY 4.0)\n",
         "Coordinates taken from this source are POPULATED-PLACE CENTROIDS.\n",
         "They are approximations of a town's location and are NOT pipeline\n",
         "facility locations. Every node row records this in `coordinate_accuracy`.\n\n"]
for out, url, size, sha in notes:
    entry.append(f"- `{out}` — {url} — {size:,} bytes — sha256 prefix `{sha}` — accessed {today}\n")
with open(SRC, "a", encoding="utf-8") as f:
    f.writelines(entry)
print(f"provenance appended to {os.path.relpath(SRC, ROOT)}")
