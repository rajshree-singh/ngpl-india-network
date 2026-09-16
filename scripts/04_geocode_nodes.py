# -*- coding: utf-8 -*-
"""
04_geocode_nodes.py  --  STEP 2b. Attach coordinates to the sourced node names.

Writes:
  data_processed/pipeline_nodes.csv        nodes that resolved unambiguously
  data_processed/node_geocode_review.csv   EVERY candidate, resolved or not, for eyeballing

METHOD, and why it is defensible
  A node name alone is not geocodable: "Dwarka" is a town in Gujarat and a
  district of Delhi; "Maharajganj" exists in UP, Bihar and Tripura. Guessing
  between them is exactly the fabrication this project forbids.

  So every lookup is CONSTRAINED BY THE REGISTER: a node may only match a
  gazetteer entry inside one of the states its own pipeline is recorded as
  passing through (pipeline_master.states_covered_verbatim -- Category A).
  A name with no match inside those states is left UNRESOLVED and reported.
  Nothing is geocoded outside that constraint, ever.

  Coordinates are populated-place CENTROIDS. They are NOT pipeline facility
  locations and every row says so in coordinate_accuracy.

GAZETTEER  (download once, then this script is fully offline and reproducible)
  TWO files, both into data_raw/external/gazetteer/ :
    https://download.geonames.org/export/dump/IN.zip                -> unzip -> IN.txt
    https://download.geonames.org/export/dump/admin1CodesASCII.txt
  The second is NOT optional. IN.txt stores admin1 as a numeric CODE ("24"),
  not a state name, so without the code table the state constraint can never
  match and every node returns UNRESOLVED -- a code failure that looks
  exactly like a data failure. (Found by fixture-testing this script.)
  Licence CC-BY 4.0. Record the file's date in data_raw/external/SOURCES.md.
"""
import pandas as pd, numpy as np, os, sys, math

# Notebook-safe abort: sys.exit() inside a Colab cell raises SystemExit and
# prints a traceback that looks like a crash. Same fix as 10_validate_master.py --
# it should have been here from the start.
IN_NB = ("get_ipython" in dir(__builtins__)) or ("IPython" in sys.modules)
def abort(msg):
    print(msg)
    if IN_NB: raise SystemExit  # bare: Colab shows this quietly
    sys.exit(1)

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
DP   = os.path.join(ROOT, "data_processed")
GAZ  = os.path.join(ROOT, "data_raw", "external", "gazetteer", "IN.txt")
ADM1 = os.path.join(ROOT, "data_raw", "external", "gazetteer", "admin1CodesASCII.txt")

# --- documented name variants. Category A name -> gazetteer spelling. ----------
# Official renamings and transliteration variants only. Each is a documented
# equivalence, not a guess; anything not listed here is looked up verbatim.
ALIASES = {
 "Bangalore":"Bengaluru", "Mangalore":"Mangaluru", "Bhatinda":"Bathinda",
 "Hissar":"Hisar", "Tuticorin":"Thoothukudi", "Trombay":"Trombay",
 "Kochi":"Kochi", "Panvel":"Panvel", "Bhopal":"Bhopal",
 "Vijayawada":"Vijayawada", "Nellore":"Nellore", "Jharsuguda":"Jharsuguda",
 # --- accepted 2026-09-06 from 04b evidence. Each is a transliteration variant
 #     confirmed by BOTH high name similarity AND close spatial agreement with
 #     the legacy node table -- two independent signals, not one.
 "Mehsana":"Mahesana",     # 1.99 km, sim 0.80, pop 190,753
 "Taloja":"Taloje",        # 1.74 km, sim 0.83, pop 14,318
 "Dhamra":"Dhamara",       # 5.59 km, sim 0.92, Odisha
 "Ennore":"Ennur",         # 3.76 km, sim 0.73, Tamil Nadu
}
ALIAS_NOTE = {
 "Bangalore":"official renaming 2014 (Bengaluru)",
 "Mangalore":"official renaming 2014 (Mangaluru)",
 "Tuticorin":"official renaming 2018 (Thoothukudi)",
 "Bhatinda":"register spelling; gazetteer uses Bathinda",
 "Hissar":"register spelling; gazetteer uses Hisar",
 "Mehsana":"official spelling Mahesana; 1.99 km from the legacy node table",
 "Taloja":"gazetteer spells the settlement Taloje; 1.74 km from the legacy node table. "
          "The register means Taloja MIDC industrial estate, Raigad district",
 "Dhamra":"gazetteer spells it Dhamara; 5.59 km from the legacy node table. "
          "The register means Dhamra port, Bhadrak district, Odisha",
 "Ennore":"gazetteer spells it Ennur; 3.76 km from the legacy node table. Ennore is now "
          "administratively part of Chennai and its port was renamed Kamarajar Port. "
          "A railway station 'Ennur' (geonameid 1272038) lies 0.21 km from the legacy point "
          "and corroborates; the POPULATED PLACE is used instead, so that every node in "
          "this dataset remains the same kind of object",
}
# GeoNames state (admin1) names as they appear, mapped from register wording.
STATE_FIX = {
 "MP":"Madhya Pradesh", "UT of Puducherry":"Puducherry",
 "UT of Jammu & Kashmir":"Jammu and Kashmir", "Jammu & Kashmir":"Jammu and Kashmir",
 "UT of Dadra & Nagar Haveli and Daman & Diu":"Dadra and Nagar Haveli and Daman and Diu",
 "Agartala":"Tripura",           # register prints a city in the States column for 17.18
 "Orissa":"Odisha", "Odisha":"Odisha", "Uttaranchal":"Uttarakhand",
 "NCT of Delhi":"Delhi", "Delhi":"Delhi",
}
# Tier 1: populated places. Tier 2: infrastructure a pipeline actually terminates
# at -- ports, terminals, industrial estates. "Paradip" exists in GeoNames as a
# PORT (feature_class S), so a populated-places-only filter could never find it.
# Tier 2 is used ONLY when tier 1 yields nothing in-state, and the row is marked.
LEGACY_TOL_KM = 25.0     # two sources within this distance are taken to concur
TIER1_CLASS = {"P"}
TIER2_CODES = {"PRT","HBR","FCL","INSM","MFG","MFGPET","MNMT","RSTN","MAR","OILW","OILF"}
# Within tier 2, prefer the feature a pipeline actually terminates at. "Paradip"
# exists as both a PORT and a RAILWAY STATION; the port is the referent for a gas
# pipeline, the station is not. Lower number = preferred.
TIER2_RANK = {"PRT":0,"HBR":0,"MAR":0,"OILT":1,"FCL":1,"INSM":1,"MFGPET":1,
              "MFG":2,"OILW":2,"OILF":2,"MNMT":3,"RSTN":4}

COMPOUND = [  # multi-word names containing "and"/"&" -- removed before splitting
 ("UT of Dadra & Nagar Haveli and Daman & Diu","Dadra and Nagar Haveli and Daman and Diu"),
 ("Dadra & Nagar Haveli and Daman & Diu","Dadra and Nagar Haveli and Daman and Diu"),
 ("UT of Jammu & Kashmir","Jammu and Kashmir"),
 ("Jammu & Kashmir","Jammu and Kashmir"),
 ("Meghalaya & Sikkim","Meghalaya|Sikkim"),          # genuinely two states
 ("UT of Puducherry","Puducherry"),
]
def norm_states(s):
    if pd.isna(s): return set()
    txt = str(s); out=set()
    for pat, repl in COMPOUND:                  # consume compounds first
        if pat in txt:
            out |= set(repl.split("|")); txt = txt.replace(pat, "")
    txt = txt.replace(" and ", ",")
    for p in txt.split(","):
        p = p.strip(" ,&")
        if p: out.add(STATE_FIX.get(p, p))
    return out

def hav(a,b,c,d):
    R=6371.0088; p=math.radians
    return 2*R*math.asin(math.sqrt(math.sin(p(c-a)/2)**2 +
           math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2))

# --- load ---------------------------------------------------------------------
cand = pd.read_csv(os.path.join(DP,"node_candidates.csv"))
mast = pd.read_csv(os.path.join(DP,"pipeline_master.csv")).set_index("pipeline_id")

if not os.path.exists(GAZ):
    abort(f"gazetteer not found: {GAZ}\n"
          "  run 00b_fetch_gazetteer.py first -- it downloads both GeoNames files\n"
          "  and writes their provenance into data_raw/external/SOURCES.md.\n"
          "  Nothing is geocoded without it.")

COLS=["geonameid","name","asciiname","alternatenames","latitude","longitude",
      "feature_class","feature_code","country","cc2","admin1","admin2","admin3",
      "admin4","population","elevation","dem","timezone","moddate"]
g = pd.read_csv(GAZ, sep="\t", names=COLS, dtype=str, quoting=3, low_memory=False)
# Keep populated places AND the infrastructure codes a pipeline can terminate at.
# Filtering to feature_class "P" here is what hid "Paradip" (a PORT) from the
# tier-2 fallback -- the row was discarded before the fallback could see it.
g = g[(g.feature_class=="P") | (g.feature_code.isin(TIER2_CODES))]
g["latitude"]=pd.to_numeric(g.latitude,errors="coerce")
g["longitude"]=pd.to_numeric(g.longitude,errors="coerce")
g["population"]=pd.to_numeric(g.population,errors="coerce").fillna(0)
gaz_date = pd.to_datetime(os.path.getmtime(GAZ), unit="s").strftime("%Y-%m-%d")

# admin1 -> state name, from GeoNames' own code table. Never inferred.
if not os.path.exists(ADM1):
    abort(f"admin1 code table not found: {ADM1}\n"
          "  run 00b_fetch_gazetteer.py. IN.txt stores admin1 as a numeric code,\n"
          "  so without this table the state constraint cannot match and every\n"
          "  node would return UNRESOLVED -- a code failure that looks like a\n"
          "  data failure.")
a1 = pd.read_csv(ADM1, sep="\t", names=["code","name","ascii","geonameid"],
                 dtype=str, quoting=3)
a1 = a1[a1.code.str.startswith("IN.")]
A1 = dict(zip(a1.code.str.split(".").str[1], a1["name"]))
print(f"admin1 code table    {len(A1)} Indian states/UTs")

# --- legacy coordinates, used ONLY as a cross-check ---------------------------
# Accept the old node tables under any name they plausibly have. The first
# version looked for exactly two filenames, found neither, and silently did
# ZERO comparisons -- while the summary still printed "disagree with legacy by
# >25 km: 0", which reads as reassurance. Same failure as S-05: a check that
# did not run must never look like a check that passed.
LEGACY_CANDIDATES = [
 ("data_raw","legacy_v0","pipeline_nodes_42.csv"),
 ("data_raw","legacy_v0","pipeline_nodes_148.csv"),
 ("data_raw","legacy_v0","pipeline_nodes.csv"),
 ("data_raw","legacy_v0","Dataset_pipeline_nodes.csv"),
 ("data_raw","legacy_v0","pipeline_nodes_v0.csv"),
 ("data_raw","pipeline_nodes.csv"),
 ("data_raw","legacy_v0","legacy_node_coordinates.csv"),
]
legacy={}; legacy_files=[]
for c in LEGACY_CANDIDATES:
    p=os.path.join(ROOT,*c)
    if not os.path.exists(p): continue
    d=pd.read_csv(p)
    nm = next((x for x in ("Node Name","node_name","name") if x in d.columns), None)
    la = next((x for x in ("Latitude","latitude","lat") if x in d.columns), None)
    lo = next((x for x in ("Longitude","longitude","lon") if x in d.columns), None)
    if not (nm and la and lo):
        print(f"  legacy file skipped (columns not recognised): {os.path.relpath(p,ROOT)}")
        continue
    n0=len(legacy)
    for _,r in d.iterrows():
        try: legacy.setdefault(str(r[nm]).strip(), (float(r[la]), float(r[lo])))
        except (TypeError, ValueError): pass
    legacy_files.append(f"{os.path.relpath(p,ROOT)} (+{len(legacy)-n0})")
if legacy_files:
    print("legacy cross-check     " + "; ".join(legacy_files))
else:
    print("legacy cross-check     NO legacy node table found -- cross-check will NOT run")

# --- resolve ------------------------------------------------------------------
names = (cand.groupby("node_name")
             .agg(pipelines=("pipeline_id", lambda s: sorted(set(s))),
                  roles=("role", lambda s: sorted(set(s)))).reset_index())

rows=[]
for _,r in names.iterrows():
    nm  = r.node_name
    look = ALIASES.get(nm, nm)
    allowed = set()
    for pid in r.pipelines:
        allowed |= norm_states(mast.at[pid,"states_covered_verbatim"])

    exact = ((g.name.str.lower()==look.lower()) | (g.asciiname.str.lower()==look.lower()))
    hit = g[exact].copy()
    hit["state"] = hit.admin1.map(A1)
    tier = 1
    inside = hit[(hit.feature_class.isin(TIER1_CLASS)) & (hit.state.isin(allowed))]
    if not len(inside):                      # fall back to infrastructure features
        inside = hit[(hit.feature_code.isin(TIER2_CODES)) & (hit.state.isin(allowed))]
        tier = 2 if len(inside) else 1

    lat=lon=np.nan; src=meth=acc="UNRESOLVED"; state=""; gid=""; status=""
    lgc = legacy.get(nm)

    # DISAMBIGUATION.  "Choose the largest population among in-state matches" is
    # NOT a valid rule and must never be used. Measured against the legacy table:
    #    exactly one in-state match : 22 nodes,  0 wrong,   max error  13 km
    #    more than one              : 19 nodes,  4 wrong,   max error 945 km
    # It put Hazira in Haryana instead of Gujarat, because 17.03 legitimately
    # passes through Haryana so the state constraint could not reject it.
    # A homonym is resolved only by independent evidence, never by size.
    if len(inside) == 1:
        best = inside.iloc[0]
        how  = "unique match inside the register's States Covered"
    elif len(inside) > 1 and lgc is not None:
        cands = inside.copy()
        cands["km"] = [hav(lgc[0], lgc[1], a, b)
                       for a, b in zip(cands.latitude, cands.longitude)]
        cands["rank"] = cands.feature_code.map(TIER2_RANK).fillna(0 if tier==1 else 9)
        near = cands[cands.km <= LEGACY_TOL_KM].sort_values(["rank","km"]).head(1)
        if len(near):
            best = near.iloc[0]
            how  = (f"{len(inside)} in-state homonyms; resolved by agreement with the "
                    f"legacy node table ({best.km:.1f} km) -- two independent sources concur")
        else:
            best = None
            status = (f"AMBIGUOUS: {len(inside)} in-state matches, none within "
                      f"{LEGACY_TOL_KM:.0f} km of the legacy coordinate. Needs manual review.")
    elif len(inside) > 1:
        best = None
        status = (f"AMBIGUOUS: {len(inside)} in-state matches and no legacy coordinate "
                  f"to disambiguate. Needs manual review.")
    else:
        best = None
        status = (f"UNRESOLVED: {len(hit)} gazetteer match(es) for '{look}', "
                  f"none inside {sorted(allowed) or '<no states recorded>'}")

    if best is not None:
        lat,lon = float(best.latitude), float(best.longitude)
        gid, state = best.geonameid, best.state
        src  = f"GeoNames IN.txt ({gaz_date}), geonameid {gid}"
        meth = (("populated-place centroid" if tier==1
                 else f"infrastructure feature ({best.feature_code})") + ", " + how)
        acc  = ("approximate_city_centroid -- NOT a pipeline facility location"
                if tier == 1 else
                f"approximate_infrastructure_feature ({best.feature_code}) -- a nearby "
                "mapped feature of that name, NOT the pipeline facility itself")
        status = "resolved"

    dist = hav(lat,lon,lgc[0],lgc[1]) if (lgc and not np.isnan(lat)) else np.nan
    rows.append(dict(node_name=nm, gazetteer_name=look,
        alias_note=ALIAS_NOTE.get(nm,""), pipelines=";".join(r.pipelines),
        n_pipelines=len(r.pipelines), roles=";".join(r.roles),
        latitude=lat, longitude=lon, state_ut=state, geonameid=gid,
        coordinate_source=src, coordinate_method=meth, coordinate_accuracy=acc,
        coordinate_date=gaz_date if src!="UNRESOLVED" else "",
        n_matches_in_state=len(inside), n_matches_country=len(hit),
        legacy_lat=lgc[0] if lgc else np.nan, legacy_lon=lgc[1] if lgc else np.nan,
        legacy_delta_km=round(dist,2) if not np.isnan(dist) else np.nan,
        status=status))

rev = pd.DataFrame(rows).sort_values("node_name").reset_index(drop=True)

# node_class is DERIVED (Category C) and reproducible: a point named by two or
# more pipelines is an interconnection; otherwise terminal or intermediate.
def klass(r):
    if r.n_pipelines >= 2: return "Interconnection"
    return "Terminal" if set(r.roles.split(";")) <= {"origin","terminus"} else "IntermediateRoutePoint"
rev["node_class"] = rev.apply(klass, axis=1)
rev["facility_type"] = "UNKNOWN -- the register names the place, not the facility"

# node_id is a PUBLISHED IDENTIFIER and must be stable. Assigning ids only to
# resolved nodes means that resolving one later renumbers every node after it --
# a cited N025 would stop meaning Jagdishpur. Ids are therefore assigned over
# ALL candidate names, alphabetically, and never change.
rev = rev.sort_values("node_name").reset_index(drop=True)
rev.insert(0, "node_id", [f"N{i:03d}" for i in range(1, len(rev)+1)])
rev["coordinate_status"] = np.where(rev.coordinate_source!="UNRESOLVED", "resolved",
                           np.where(rev.status.str.startswith("AMBIGUOUS"), "ambiguous", "unresolved"))
rev["name_provenance"]       = "A -- pipeline name, PNGRB register"
rev["coordinate_provenance"] = np.where(rev.coordinate_status=="resolved",
                                        "B -- GeoNames gazetteer, state-constrained", "")
# Every node the register names is published, with its status. An unresolved node
# still exists in the network; omitting it would make the edge table unable to
# express the gap.
ok = rev.copy()

os.makedirs(DP,exist_ok=True)
rev.to_csv(os.path.join(DP,"node_geocode_review.csv"),index=False)
ok[["node_id","node_name","node_class","facility_type","state_ut","latitude","longitude",
    "coordinate_status","coordinate_source","coordinate_method","coordinate_accuracy",
    "coordinate_date","name_provenance","coordinate_provenance",
    "pipelines","n_pipelines","roles","legacy_delta_km","status"]].to_csv(
    os.path.join(DP,"pipeline_nodes.csv"),index=False)

print(f"gazetteer            IN.txt dated {gaz_date}, {len(g):,} rows "
      f"({int((g.feature_class=='P').sum()):,} populated places + "
      f"{int(g.feature_code.isin(TIER2_CODES).sum()):,} infrastructure features)")
print(f"node names           {len(rev)}")
print(f"  resolved           {len(ok)}")
amb = rev[rev.status.str.startswith("AMBIGUOUS")]
uns2 = rev[rev.status.str.startswith("UNRESOLVED")]
print(f"  AMBIGUOUS          {len(amb)}   (homonyms -- NOT guessed)")
for _,r in amb.iterrows():  print(f"     {r.node_name:16s} {r.status}")
print(f"  UNRESOLVED         {len(uns2)}")
for _,r in uns2.iterrows(): print(f"     {r.node_name:16s} {r.status}")
cmp = ok[ok.legacy_delta_km.notna()]
print(f"\nLEGACY CROSS-CHECK")
if not len(cmp):
    print(f"  DID NOT RUN -- 0 of {len(ok)} resolved nodes had a legacy coordinate to")
    print( "  compare against. This is NOT agreement. Put your old node table(s) in")
    print( "  data_raw/legacy_v0/ (any of: " + ", ".join(c[-1] for c in LEGACY_CANDIDATES) + ")")
else:
    far = cmp[cmp.legacy_delta_km>25]
    print(f"  compared          {len(cmp)} of {len(ok)} resolved nodes")
    print(f"  median offset     {cmp.legacy_delta_km.median():.2f} km")
    print(f"  >25 km apart      {len(far)}")
    for _,r in far.iterrows():
        print(f"     {r.node_name:16s} {r.legacy_delta_km} km")
    if len(cmp) < len(ok):
        print(f"  NOT compared      {len(ok)-len(cmp)} -> {sorted(ok[ok.legacy_delta_km.isna()].node_name)}")
nres=(rev.coordinate_status=="resolved").sum()
print(f"\npipeline_nodes.csv    {len(rev)} rows (ALL named nodes, stable ids N001-N{len(rev):03d})")
print(f"                      {nres} with coordinates, {len(rev)-nres} without")
weak = rev[(rev.coordinate_status=="resolved") & (rev.legacy_delta_km > 10)]
if len(weak):
    print(f"\nWEAKEST ACCEPTED COORDINATES (>10 km from the independent table):")
    for _,r in weak.sort_values("legacy_delta_km",ascending=False).iterrows():
        print(f"   {r.node_name:14s} {r.legacy_delta_km:6.2f} km  "
              f"{int(r.n_matches_in_state):3d} in-state homonyms  -> {r.pipelines}")
print(f"\nreview file: node_geocode_review.csv  -- check every row before using pipeline_nodes.csv")
