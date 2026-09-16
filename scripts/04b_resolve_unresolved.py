# -*- coding: utf-8 -*-
"""
04b_resolve_unresolved.py  --  evidence for the nodes 04 could not resolve.

Proposes NOTHING automatically. It searches the gazetteer for candidates and
prints the evidence; you decide, and any accepted alias goes into ALIASES in
04_geocode_nodes.py with a note. That keeps the decision human and recorded.

Two independent lines of evidence, both kept inside the register's state constraint:

  1. SPATIAL.  For a node that has a legacy coordinate, search the gazetteer
     within RADIUS_KM of that point. A gazetteer entry 2 km from where the old
     table put "Paradip", spelled "Paradwip", is near-conclusive -- far stronger
     than string similarity, because two independent things agree.

  2. NAME.     Fuzzy + substring match, restricted to the allowed states.

A node with neither is very likely absent from GeoNames. That is a finding to
report in the README, not a gap to fill by inventing a coordinate.
"""
import pandas as pd, numpy as np, os, sys, math, difflib

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
DP   = os.path.join(ROOT, "data_processed")
GDIR = os.path.join(ROOT, "data_raw", "external", "gazetteer")
RADIUS_KM = 20.0
TOP = 6

IN_NB = ("get_ipython" in dir(__builtins__)) or ("IPython" in sys.modules)
def abort(m):
    print(m)
    raise SystemExit if IN_NB else sys.exit(1)

rev = pd.read_csv(os.path.join(DP, "node_geocode_review.csv"))
for f in ("IN.txt", "admin1CodesASCII.txt"):
    if not os.path.exists(os.path.join(GDIR, f)):
        abort(f"missing {f} -- run 00b_fetch_gazetteer.py")

COLS=["geonameid","name","asciiname","alternatenames","latitude","longitude",
      "feature_class","feature_code","country","cc2","admin1","admin2","admin3",
      "admin4","population","elevation","dem","timezone","moddate"]
g = pd.read_csv(os.path.join(GDIR,"IN.txt"), sep="\t", names=COLS, dtype=str,
                quoting=3, low_memory=False)
g = g[g.feature_class.isin(["P","S","L"])]          # places, spots (ports/plants), areas
g["latitude"]=pd.to_numeric(g.latitude,errors="coerce")
g["longitude"]=pd.to_numeric(g.longitude,errors="coerce")
g["population"]=pd.to_numeric(g.population,errors="coerce").fillna(0)
a1 = pd.read_csv(os.path.join(GDIR,"admin1CodesASCII.txt"), sep="\t",
                 names=["code","name","ascii","geonameid"], dtype=str, quoting=3)
a1 = a1[a1.code.str.startswith("IN.")]
A1 = dict(zip(a1.code.str.split(".").str[1], a1["name"]))
g["state"] = g.admin1.map(A1)

def hav(a,b,c,d):
    R=6371.0088; p=math.radians
    return 2*R*math.asin(math.sqrt(math.sin(p(c-a)/2)**2 +
           math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2))

# --- how well did the resolved nodes agree with the legacy table? ------------
res = rev[rev.coordinate_source!="UNRESOLVED"]
withlg = res[res.legacy_delta_km.notna()]
print("="*74)
print("LEGACY AGREEMENT  (does the old coordinate table corroborate the gazetteer?)")
print(f"  resolved nodes ................ {len(res)}")
print(f"  with a legacy coordinate ...... {len(withlg)}")
if len(withlg):
    d=withlg.legacy_delta_km
    print(f"  median offset ................. {d.median():.2f} km")
    print(f"  90th percentile ............... {d.quantile(.9):.2f} km")
    print(f"  max ........................... {d.max():.2f} km  ({withlg.loc[d.idxmax(),'node_name']})")
    for lo,hi in [(0,1),(1,5),(5,15),(15,25),(25,1e9)]:
        n=((d>=lo)&(d<hi)).sum()
        if n: print(f"    {lo:>3.0f}-{hi if hi<1e9 else 'inf':>4} km  {n:3d}")
print(f"  resolved WITHOUT any legacy value (no corroboration): "
      f"{len(res)-len(withlg)}  -> {sorted(res[res.legacy_delta_km.isna()].node_name)}")

# --- candidates for each unresolved node ------------------------------------
uns = rev[rev.coordinate_source=="UNRESOLVED"]
print("\n"+"="*74)
print(f"UNRESOLVED: {len(uns)} nodes.  Evidence below -- accept nothing without checking.\n")
for _,r in uns.iterrows():
    allowed = set(str(r.get("allowed_states","")).split(";")) if "allowed_states" in rev.columns else None
    print("-"*74)
    print(f"{r.node_name}   (pipelines: {r.pipelines})")
    print(f"  04 said: {r.status}")
    sub = g[g.state.notna()]
    # restrict to the states named in the status line, parsed back out
    import re as _re
    st = _re.findall(r"'([^']+)'", str(r.status))
    if st: sub = sub[sub.state.isin(st)]

    shown=set()
    if not pd.isna(r.legacy_lat):
        near = sub[(sub.latitude.between(r.legacy_lat-0.35, r.legacy_lat+0.35)) &
                   (sub.longitude.between(r.legacy_lon-0.35, r.legacy_lon+0.35))].copy()
        if len(near):
            near["km"]=[hav(r.legacy_lat,r.legacy_lon,a,b) for a,b in zip(near.latitude,near.longitude)]
            near=near[near.km<=RADIUS_KM].nsmallest(TOP,"km")
            if len(near):
                print(f"  SPATIAL -- within {RADIUS_KM:.0f} km of the legacy point "
                      f"({r.legacy_lat}, {r.legacy_lon}):")
                for _,x in near.iterrows():
                    sim=difflib.SequenceMatcher(None,r.node_name.lower(),str(x.asciiname).lower()).ratio()
                    print(f"     {x.km:6.2f} km  {x.asciiname:28s} {x.feature_code:5s} "
                          f"pop={int(x.population):>8,}  name-sim={sim:.2f}  id={x.geonameid}")
                    shown.add(x.geonameid)
    else:
        print("  SPATIAL -- no legacy coordinate exists for this node, so no spatial evidence.")

    names = sub.asciiname.fillna("").astype(str)
    key = r.node_name.lower()
    # A prefix test cannot find a transposition: "Mehsana" -> "Mahesana" shares
    # only "M". Score EVERY in-state name instead; the gazetteer subset is small
    # once the state constraint is applied, so this is affordable.
    close = sub.copy()
    if len(close):
        close["sim"]=[difflib.SequenceMatcher(None,key,str(n).lower()).ratio()
                      for n in close.asciiname.fillna("")]
        close = close[(close.sim>=0.62) & (~close.geonameid.isin(shown))].nlargest(TOP,"sim")
        if len(close):
            print("  NAME -- closest spellings inside the allowed states:")
            for _,x in close.iterrows():
                extra=""
                if not pd.isna(r.legacy_lat):
                    extra=f"  {hav(r.legacy_lat,r.legacy_lon,x.latitude,x.longitude):7.1f} km from legacy"
                print(f"     sim={x.sim:.2f}  {x.asciiname:28s} {x.feature_code:5s} "
                      f"{x.state:22s} pop={int(x.population):>8,}{extra}  id={x.geonameid}")
    if not len(close) and not shown:
        print("  NO CANDIDATE on either line of evidence -- likely absent from GeoNames.")
print("-"*74)
print("\nTo accept one: add  \"<node_name>\": \"<gazetteer asciiname>\"  to ALIASES in")
print("04_geocode_nodes.py, with a one-line reason in ALIAS_NOTE, then re-run 04.")
