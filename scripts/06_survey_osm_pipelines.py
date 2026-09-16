# -*- coding: utf-8 -*-
"""
06_survey_osm_pipelines.py  --  does OSM contain mapped gas pipeline ALIGNMENTS
                                for India, and how complete are they?

This is a SURVEY. It adopts nothing and writes nothing into the published
dataset. It answers one question: is limitation 8.1 -- "there are no route
alignments" -- actually true, or only true of the sources checked so far?

  05_resolve_facility_nodes.py returned exactly one feature near Vijaipur:
      man_made=pipeline; substance=gas   name="HVJ Gas Pipeline"
  If OSM carries the HVJ alignment as a mapped way, it may carry others, and
  reconstructed straight-line geometry could be replaced by mapped geometry --
  the single largest improvement available to this dataset.

  It may equally turn out that OSM has three fragments totalling 200 km, in
  which case the honest answer is that 8.1 stands. Either result is worth
  knowing before Steps 6-9 are built on reconstructed lines.

OUTPUT
  data_processed/osm_pipeline_survey.csv   one row per mapped way
  gis/osm_pipelines_raw.geojson            geometry, for inspection ONLY

LICENCE -- unchanged from 05: OpenStreetMap is ODbL and share-alike. Nothing
here may enter the published dataset until that question is settled. Inspect
freely; adopt deliberately.
"""
import os, sys, json, math, urllib.request, urllib.parse, datetime
import pandas as pd

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
DP   = os.path.join(ROOT, "data_processed"); GD = os.path.join(ROOT, "gis")
os.makedirs(DP, exist_ok=True); os.makedirs(GD, exist_ok=True)
OVERPASS = "https://overpass-api.de/api/interpreter"

# India, split into four so a single national query cannot time out the public
# endpoint. Overlap is harmless -- ways are de-duplicated by OSM id.
BOXES = {"NW":(20.0,68.0,37.6,80.0), "NE":(20.0,80.0,37.6,97.5),
         "SW":( 6.5,68.0,20.0,80.0), "SE":( 6.5,80.0,20.0,97.5)}

def hav(a,b,c,d):
    R=6371.0088; p=math.radians
    return 2*R*math.asin(math.sqrt(math.sin(p(c-a)/2)**2 +
           math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2))

def length_km(geom):
    return sum(hav(geom[i]["lat"],geom[i]["lon"],geom[i+1]["lat"],geom[i+1]["lon"])
               for i in range(len(geom)-1))

def fetch(box):
    s,w,n,e = box
    q = (f'[out:json][timeout:300];('
         f'way["man_made"="pipeline"]["substance"~"gas|natural_gas",i]({s},{w},{n},{e});'
         f'way["man_made"="pipeline"]["type"~"gas",i]({s},{w},{n},{e});'
         f');out geom tags;')
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data":q}).encode(),
            headers={"User-Agent":"ngpl-india-network/1.0 (research dataset survey)"})
    return json.loads(urllib.request.urlopen(req, timeout=330).read())

seen, rows, feats = set(), [], []
today = datetime.date.today().isoformat()
for name, box in BOXES.items():
    print(f"querying {name} {box} ...", end=" ", flush=True)
    try:
        js = fetch(box)
    except Exception as e:
        print(f"FAILED: {e}"); continue
    got = 0
    for el in js.get("elements", []):
        if el.get("type")!="way" or el["id"] in seen: continue
        g = el.get("geometry") or []
        if len(g) < 2: continue
        seen.add(el["id"]); got += 1
        t = el.get("tags", {}) or {}
        L = length_km(g)
        rows.append(dict(osm_id=el["id"], name=t.get("name",""), operator=t.get("operator",""),
            substance=t.get("substance",""), diameter=t.get("diameter",""),
            usage=t.get("usage",""), location=t.get("location",""),
            length_km=round(L,2), n_vertices=len(g),
            start_lat=g[0]["lat"], start_lon=g[0]["lon"],
            end_lat=g[-1]["lat"], end_lon=g[-1]["lon"],
            citation=f"OSM way/{el['id']}, extracted {today}",
            licence="ODbL 1.0 -- share-alike; NOT yet cleared for the published dataset"))
        feats.append({"type":"Feature",
            "properties":{"osm_id":el["id"],"name":t.get("name",""),
                          "operator":t.get("operator",""),"length_km":round(L,2)},
            "geometry":{"type":"LineString","coordinates":[[p["lon"],p["lat"]] for p in g]}})
    print(f"{got} ways")

if not rows:
    print("\nNo mapped gas pipeline ways returned. Limitation 8.1 stands: there are no")
    print("alignments available, and reconstructed geometry remains the only option.")
    sys.exit(0)

d = pd.DataFrame(rows).sort_values("length_km", ascending=False)
d.to_csv(os.path.join(DP,"osm_pipeline_survey.csv"), index=False)
json.dump({"type":"FeatureCollection","name":"osm_pipelines_raw",
           "crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}},
           "features":feats}, open(os.path.join(GD,"osm_pipelines_raw.geojson"),"w"))

named = d[d.name.str.len()>0]
print(f"\n{'='*70}")
print(f"mapped gas pipeline ways ...... {len(d)}")
print(f"  with a name ................. {len(named)}")
print(f"  total mapped length ......... {d.length_km.sum():,.0f} km")
print(f"  longest single way .......... {d.length_km.max():,.0f} km")
print(f"\nfor scale: the register's 37 Common Carrier pipelines total 32,702 km authorized.")
print(f"\nlongest named ways:")
for _,r in named.head(20).iterrows():
    print(f"  {r.length_km:9,.1f} km  {r['name'][:44]:44s} {r.operator[:22]}")

# crude name overlap with our scope -- indicative only, not a join
mp = os.path.join(DP,"pipeline_master.csv")
if os.path.exists(mp):
    m = pd.read_csv(mp); m = m[m.in_graph_scope]
    keys = ["HVJ","Dahej","Vijaipur","Jagdishpur","Kochi","Mangalore","Dabhol","Bangalore",
            "Ennore","Tuticorin","Mehsana","Bhatinda","Gurdaspur","Mallavaram","Bhopal",
            "Kakinada","Uran","Haldia","Bokaro","Barauni","Guwahati","Nagpur","Jharsuguda",
            "Srikakulam","Angul","Shahdol","Phulpur","Dadri","Panipat","Trombay"]
    hits = {k: named[named.name.str.contains(k, case=False, na=False)].length_km.sum()
            for k in keys}
    hits = {k:v for k,v in hits.items() if v > 0}
    print(f"\nnames mentioning one of our node/pipeline names ({len(hits)} of {len(keys)} probed):")
    for k,v in sorted(hits.items(), key=lambda x:-x[1]):
        print(f"  {v:9,.1f} km  matches '{k}'")

print(f"\n{'='*70}")
print("Wrote osm_pipeline_survey.csv and gis/osm_pipelines_raw.geojson.")
print("Open the GeoJSON in QGIS against pipeline_nodes.csv before drawing any")
print("conclusion: coverage in OSM is uneven, and a named way may be a short")
print("fragment rather than a full alignment. Nothing here is adopted.")
