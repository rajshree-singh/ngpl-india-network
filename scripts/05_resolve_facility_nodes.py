# -*- coding: utf-8 -*-
"""
05_resolve_facility_nodes.py  --  STEP 2c. Evidence for FACILITY nodes.

Proposes nothing. Writes data_processed/facility_candidates.csv for review.

WHY THIS STEP EXISTS
  GeoNames is a gazetteer of POPULATED PLACES. Several nodes in this register
  are not settlements at all -- they are compressor stations, LNG terminals and
  ports that happen to share a name with a nearby town, or in Vijaipur's case
  with nothing at all. A populated-place gazetteer structurally cannot contain
  them, so "not found" there is a statement about the gazetteer, not about the
  world. OpenStreetMap does carry industrial and plant features.

  Two distinct questions:
    (a) Vijaipur -- unresolved. GeoNames' three exact matches are 158, 500 and
        633 km away and are different places. The GAIL Vijaipur complex is a
        facility.
    (b) Hazira, Dahej, Paradip, Ennore, Dabhol, Trombay -- RESOLVED, but to a
        settlement centroid. Is the register naming the town or the terminal?
        If a mapped terminal sits several km from the town, the current
        coordinate is defensible but imprecise, and the README should say which.

!!  LICENCE -- READ BEFORE ACCEPTING ANY RESULT  !!
  OpenStreetMap is ODbL, which carries share-alike obligations for a derived
  database. Taking coordinates from OSM into this dataset may require the node
  table -- possibly the package -- to be released under ODbL, which is a
  different licence from the CC-BY assumed for the GeoNames-derived values.
  This is a publication decision, not a technical one. Resolve it BEFORE
  adopting any coordinate this script surfaces. Leaving Vijaipur unresolved and
  documenting it as a limitation remains a perfectly defensible alternative.
"""
import pandas as pd, numpy as np, os, sys, json, math, time, urllib.request, urllib.parse, datetime

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
DP   = os.path.join(ROOT, "data_processed")
OVERPASS = "https://overpass-api.de/api/interpreter"
RADIUS_M = 25000

IN_NB = ("get_ipython" in dir(__builtins__)) or ("IPython" in sys.modules)
def abort(m):
    print(m); raise SystemExit if IN_NB else sys.exit(1)

# Which nodes to investigate, and around which point.
#   "legacy"  -> search around the legacy coordinate (for unresolved nodes)
#   "current" -> search around the coordinate already assigned (for the audit)
TARGETS = [("Vijaipur","legacy"), ("Hazira","current"), ("Dahej","current"),
           ("Paradip","current"), ("Ennore","current"), ("Dabhol","current"),
           ("Trombay","current")]

# Tags that indicate gas-transport infrastructure rather than a settlement.
QUERY_CLAUSES = [
 'nwr(around:{r},{lat},{lon})["man_made"~"works|pumping_station|storage_tank|gasometer|petroleum_well"];',
 'nwr(around:{r},{lat},{lon})["pipeline"];',
 'nwr(around:{r},{lat},{lon})["substance"~"gas|natural_gas"];',
 'nwr(around:{r},{lat},{lon})["landuse"="industrial"]["name"];',
 'nwr(around:{r},{lat},{lon})["industrial"];',
 'nwr(around:{r},{lat},{lon})["operator"~"GAIL|ONGC|GSPL|IOCL|Petronet",i];',
 'nwr(around:{r},{lat},{lon})["plant:source"~"gas"];',
 'nwr(around:{r},{lat},{lon})["harbour"]["name"];',
]

def hav(a,b,c,d):
    R=6371.0088; p=math.radians
    return 2*R*math.asin(math.sqrt(math.sin(p(c-a)/2)**2 +
           math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2))

def overpass(lat, lon):
    q = "[out:json][timeout:90];(" + "".join(
        c.format(r=RADIUS_M, lat=lat, lon=lon) for c in QUERY_CLAUSES) + ");out center tags;"
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data":q}).encode(),
                                 headers={"User-Agent":"ngpl-india-network/1.0 (research dataset)"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

# NOTE ON DISTANCES -- a real limitation of this script.
# Distance is measured to a way's CENTER. For a compact feature (a plant, a
# port) that is the right answer. For a long linear feature it is meaningless:
# the "HVJ Gas Pipeline" was reported 36.61 km from Vijaipur despite a 25 km
# search radius, because Overpass matched the nearest point of the way while
# this function measured to the centroid of a pipeline hundreds of km long.
# Treat any man_made=pipeline row's km value as unusable. Compact facilities
# -- the actual purpose of this script -- are unaffected.
def elements(js, lat, lon):
    out=[]
    for e in js.get("elements", []):
        y = e.get("lat", (e.get("center") or {}).get("lat"))
        x = e.get("lon", (e.get("center") or {}).get("lon"))
        if y is None or x is None: continue
        t = e.get("tags", {}) or {}
        out.append(dict(osm_type=e["type"], osm_id=e["id"], name=t.get("name",""),
            operator=t.get("operator",""), latitude=y, longitude=x,
            km=round(hav(lat,lon,y,x),2),
            distance_valid = "no -- linear feature, km is to the centroid"
                             if t.get("man_made")=="pipeline" else "yes",
            tags="; ".join(f"{k}={v}" for k,v in sorted(t.items())
                           if k in ("man_made","pipeline","substance","landuse","industrial",
                                    "plant:source","harbour","power","amenity","place"))))
    return out

if not os.path.exists(os.path.join(DP,"pipeline_nodes.csv")):
    abort("pipeline_nodes.csv not found -- run 04_geocode_nodes.py first")
n = pd.read_csv(os.path.join(DP,"pipeline_nodes.csv")).set_index("node_name")
rev_p = os.path.join(DP,"node_geocode_review.csv")
rev = pd.read_csv(rev_p).set_index("node_name") if os.path.exists(rev_p) else None

today = datetime.date.today().isoformat()
rows=[]
for name, anchor in TARGETS:
    if name not in n.index:
        print(f"  {name}: not in pipeline_nodes.csv, skipped"); continue
    row = n.loc[name]
    if anchor == "current" and pd.notna(row.latitude):
        lat, lon, src = float(row.latitude), float(row.longitude), "current GeoNames coordinate"
    elif rev is not None and name in rev.index and pd.notna(rev.loc[name].get("legacy_lat")):
        lat, lon, src = float(rev.loc[name].legacy_lat), float(rev.loc[name].legacy_lon), "legacy coordinate"
    else:
        print(f"  {name}: no anchor point available, skipped"); continue

    print(f"\n{name}  ({row.coordinate_status}) -- searching {RADIUS_M/1000:.0f} km around the {src} ({lat:.4f}, {lon:.4f})")
    try:
        els = elements(overpass(lat, lon), lat, lon)
    except Exception as e:
        print(f"   Overpass failed: {e}\n   (public endpoint is rate-limited; wait a minute and retry)")
        continue
    els = [e for e in els if e["name"] or e["operator"]]
    els.sort(key=lambda e: e["km"])
    if not els:
        print("   no tagged industrial/pipeline feature found -> genuinely absent from OSM too")
    for e in els[:10]:
        print(f"   {e['km']:6.2f} km  {e['name'][:38]:38s} {e['operator'][:16]:16s} {e['tags'][:52]}")
    for e in els:
        e.update(node_name=name, anchor=src, anchor_lat=lat, anchor_lon=lon,
                 coordinate_status_now=row.coordinate_status, extracted=today,
                 source="OpenStreetMap via Overpass API",
                 licence="ODbL 1.0 -- SHARE-ALIKE, see the licence warning in this script",
                 citation=f"OSM {e['osm_type']}/{e['osm_id']}, extracted {today}")
        rows.append(e)
    time.sleep(3)   # be polite to the public endpoint

out = pd.DataFrame(rows)
if len(out):
    cols=["node_name","coordinate_status_now","anchor","km","distance_valid","name","operator","tags",
          "latitude","longitude","osm_type","osm_id","citation","licence","extracted",
          "anchor_lat","anchor_lon","source"]
    out[cols].to_csv(os.path.join(DP,"facility_candidates.csv"), index=False)
    print(f"\nwrote facility_candidates.csv  ({len(out)} candidates across "
          f"{out.node_name.nunique()} nodes)")
else:
    print("\nno candidates found for any target")
print("\nNothing has been adopted. Review the file, settle the ODbL question in the")
print("licence warning at the top of this script, then decide node by node.")
