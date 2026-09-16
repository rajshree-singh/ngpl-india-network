# -*- coding: utf-8 -*-
"""
11_validate_nodes.py  --  gate for STEP 2.

Same contract as 10_validate_master.py: a valid gate needs every check to pass
AND no group to be skipped. Group 4 is the only one that checks the node table
against a source independent of itself (node_candidates + pipeline_master);
groups 1-3 are internal consistency and would pass on a silently moved coordinate.
"""
import pandas as pd, numpy as np, os, re, sys

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
DP   = os.path.join(ROOT, "data_processed")
n    = pd.read_csv(os.path.join(DP, "pipeline_nodes.csv"))

ok=[]; skipped=[]
def check(label, cond, detail=""):
    ok.append(bool(cond)); print(f"{'PASS' if cond else 'FAIL'}  {label}  {detail}")
def skip(g, reason, fix):
    skipped.append((g,reason,fix)); print(f"SKIP  {g}  --  {reason}")

RESOLVED = n.coordinate_status.eq("resolved")

# --- 1. identifiers -----------------------------------------------------------
check("56 rows -- every node the register names", len(n)==56, f"got {len(n)}")
check("node_id unique", n.node_id.is_unique)
check("node_id format N###", n.node_id.str.fullmatch(r"N\d{3}").all())
# Stability is the whole point: ids must span ALL nodes, not just resolved ones,
# so that resolving one later renumbers nothing. Contiguous N001..N0NN over the
# alphabetically sorted full list is what makes that true and checkable.
check("node_id contiguous N001..N%03d" % len(n),
      list(n.node_id)==[f"N{i:03d}" for i in range(1,len(n)+1)])
check("node_id follows alphabetical node_name order",
      list(n.node_name)==sorted(n.node_name),
      "ids must not depend on which nodes happen to be resolved")
check("node_name unique", n.node_name.is_unique)

# --- 2. status accounting -----------------------------------------------------
check("coordinate_status vocabulary closed",
      set(n.coordinate_status) <= {"resolved","ambiguous","unresolved"},
      str(sorted(set(n.coordinate_status))))
check("51 resolved", int(RESOLVED.sum())==51, f"got {int(RESOLVED.sum())}")
check("5 without coordinates", int((~RESOLVED).sum())==5,
      f"got {int((~RESOLVED).sum())}: {sorted(n.loc[~RESOLVED,'node_name'])}")
check("every resolved row has a coordinate",
      n.loc[RESOLVED,["latitude","longitude"]].notna().all().all())
check("every UNresolved row has NO coordinate -- never zero-filled",
      n.loc[~RESOLVED,["latitude","longitude"]].isna().all().all())
check("every resolved row cites a geonameid",
      n.loc[RESOLVED,"coordinate_source"].str.contains("geonameid").all())
check("every unresolved row carries a reason",
      n.loc[~RESOLVED,"status"].fillna("").str.len().gt(10).all())

# --- 3. coordinate sanity -----------------------------------------------------
r = n[RESOLVED]
check("all coordinates inside India's bounding box",
      r.latitude.between(6.5,37.6).all() and r.longitude.between(68.0,97.5).all(),
      str(r.loc[~(r.latitude.between(6.5,37.6) & r.longitude.between(68.0,97.5)),
                ["node_name","latitude","longitude"]].values.tolist()))
# The accuracy label must describe what was actually matched. A tier-2 match is
# a port or station, not a settlement; labelling it a city centroid understates
# the caveat in the one field whose job is to carry it.
t1 = r.coordinate_method.str.startswith("populated-place centroid")
check("accuracy label agrees with the match type",
      (r.loc[t1,"coordinate_accuracy"].str.startswith("approximate_city_centroid").all() and
       r.loc[~t1,"coordinate_accuracy"].str.startswith("approximate_infrastructure_feature").all()),
      str(r.loc[t1 != r.coordinate_accuracy.str.startswith("approximate_city_centroid"),
                "node_name"].tolist()))
# NOT checked here: legacy_delta_km as stored. A validator must never accept a
# file's own claim about itself when it can recompute it -- mutation testing
# showed that moving Hazira back to Haryana passed, because the stale stored
# offset still read 2.05 km and the state check cannot reject Haryana (17.03
# genuinely passes through it). Recomputed in group 5 instead.
# Catches Excel/Sheets silently rewriting ISO dates to DD-MM-YYYY on a round-trip.
check("coordinate_date is ISO yyyy-mm-dd",
      r.coordinate_date.astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all(),
      f"got e.g. {r.coordinate_date.iloc[0]!r} -- did this file pass through a spreadsheet?")
check("provenance split recorded (name=A, coordinate=B)",
      n.name_provenance.str.startswith("A").all() and
      r.coordinate_provenance.str.startswith("B").all())

# --- 4. cross-check against node_candidates and pipeline_master ---------------
cp = os.path.join(DP,"node_candidates.csv"); mp = os.path.join(DP,"pipeline_master.csv")
if os.path.exists(cp) and os.path.exists(mp):
    c = pd.read_csv(cp); m = pd.read_csv(mp).set_index("pipeline_id")
    check("node set matches node_candidates exactly",
          set(n.node_name)==set(c.node_name),
          f"only in nodes: {sorted(set(n.node_name)-set(c.node_name))}; "
          f"only in candidates: {sorted(set(c.node_name)-set(n.node_name))}")
    want = c.groupby("node_name").pipeline_id.apply(lambda s: ";".join(sorted(set(s))))
    got  = n.set_index("node_name").pipelines.apply(lambda s: ";".join(sorted(s.split(";"))))
    diff = [k for k in want.index if want[k] != got.get(k)]
    check("each node's pipeline list is exactly what the candidates say",
          not diff, str(diff[:6]))
    check("n_pipelines equals the length of that list",
          (n.pipelines.str.split(";").str.len()==n.n_pipelines).all())
    # The state constraint, re-checked from the OUTPUT rather than trusting the
    # matcher: a node must sit in a state the register records for one of its
    # own pipelines.
    # State-name normalisation. Reimplemented in each script so far, and it has
    # produced a false failure every time -- it belongs in one shared module.
    # Two traps, both found by running this check:
    #   (a) a compound UT name must be REMOVED from the text once matched, not
    #       merely substituted, or the later " and " split shreds it:
    #       "UT of Jammu & Kashmir" -> {"Jammu", "Kashmir"}.
    #   (b) 17.18's States cell reads "Agartala" -- a city, not a State. That is
    #       a defect in the source, documented in pipeline_master.notes, and the
    #       normalisation to Tripura must be applied here too.
    COMPOUND = [("UT of Dadra & Nagar Haveli and Daman & Diu",["Dadra and Nagar Haveli and Daman and Diu"]),
                ("Dadra & Nagar Haveli and Daman & Diu",["Dadra and Nagar Haveli and Daman and Diu"]),
                ("UT of Jammu & Kashmir",["Jammu and Kashmir"]),
                ("Jammu & Kashmir",["Jammu and Kashmir"]),
                ("Meghalaya & Sikkim",["Meghalaya","Sikkim"]),
                ("UT of Puducherry",["Puducherry"])]
    FIX = {"MP":"Madhya Pradesh",
           "Agartala":"Tripura"}   # source defect on 17.18; see pipeline_master.notes
    def states(sv):
        if pd.isna(sv): return set()
        t=str(sv); out=set()
        for pat,vals in COMPOUND:
            if pat in t:
                out |= set(vals); t = t.replace(pat,"")     # consume, do not substitute
        t = t.replace(" and ", ",")
        for p in t.split(","):
            p = p.strip(" ,&")
            if p: out.add(FIX.get(p,p))
        return out

    viol=[]
    for _,row in r.iterrows():
        allowed=set()
        for pid in row.pipelines.split(";"):
            if pid in m.index: allowed |= states(m.at[pid,"states_covered_verbatim"])
        if row.state_ut not in allowed: viol.append((row.node_name,row.state_ut,sorted(allowed)))
    check("every node lies in a state its own pipeline passes through",
          not viol, str(viol[:4]))
else:
    skip("group 4: cross-check against node_candidates + pipeline_master (5 checks)",
         "node_candidates.csv or pipeline_master.csv not found in data_processed/",
         "re-run 01_build_pipeline_master.py and 03_build_node_candidates.py")

# --- 5. RECOMPUTE the offset from the independent table -----------------------
#     The single strongest check in this file. Groups 1-4 all read values the
#     node table asserts about itself; this one re-derives the distance from a
#     separate source and compares. It is what catches a coordinate that has
#     been moved without its metadata being updated.
import math
LG = [("data_raw","legacy_v0","legacy_node_coordinates.csv"),
      ("data_raw","legacy_v0","pipeline_nodes_42.csv"),
      ("data_raw","legacy_v0","pipeline_nodes.csv")]
lp = next((os.path.join(ROOT,*c) for c in LG if os.path.exists(os.path.join(ROOT,*c))), None)
if lp:
    print(f"      recomputing offsets against: {os.path.relpath(lp, ROOT)}")
    L = pd.read_csv(lp)
    nm = next(c for c in ("node_name","Node Name","name") if c in L.columns)
    la = next(c for c in ("latitude","Latitude","lat") if c in L.columns)
    lo = next(c for c in ("longitude","Longitude","lon") if c in L.columns)
    lg = {str(x).strip():(float(y),float(z)) for x,y,z in zip(L[nm],L[la],L[lo])}
    def hav(a,b,c,d):
        R=6371.0088; p=math.radians
        return 2*R*math.asin(math.sqrt(math.sin(p(c-a)/2)**2 +
               math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2))
    recomp, drift = [], []
    for _,row in r.iterrows():
        if row.node_name not in lg: continue
        d_km = hav(row.latitude,row.longitude,*lg[row.node_name])
        recomp.append((row.node_name,d_km))
        if pd.notna(row.legacy_delta_km) and abs(d_km-float(row.legacy_delta_km)) > 0.05:
            drift.append((row.node_name, round(d_km,2), float(row.legacy_delta_km)))
    far = [(k,round(v,1)) for k,v in recomp if v > 25]
    check(f"recomputed offset <=25 km for all {len(recomp)} comparable nodes",
          not far, str(far[:6]))
    check("stored legacy_delta_km matches the recomputed value",
          not drift, "coordinate moved without its metadata: " + str(drift[:6]))
    if recomp:
        v=sorted(x for _,x in recomp)
        k=len(v)
        # True median. v[k//2] alone is the UPPER middle value on an even-length
        # list, which is not a median: on the 44 comparable nodes it reports
        # 0.95 km where the median is 0.86 km. This line only prints, so no check
        # was ever wrong -- but the number was quoted in the README, which is
        # exactly how a display bug becomes a published one.
        med = v[k//2] if k % 2 else (v[k//2 - 1] + v[k//2]) / 2
        # Linear interpolation between order statistics -- the convention numpy
        # and pandas use, so a reader recomputing this gets the same number.
        _i = 0.9 * (k - 1); _lo = int(_i)
        p90 = v[_lo] + (_i - _lo) * (v[min(_lo + 1, k - 1)] - v[_lo])
        print(f"      recomputed offsets over {k} comparable nodes: "
              f"median {med:.2f} km, 90th pct {p90:.2f} km, max {v[-1]:.2f} km "
              f"({max(recomp,key=lambda t:t[1])[0]})")
else:
    skip("group 5: recomputed offset against the independent table (2 checks)",
         "no legacy node table found in data_raw/legacy_v0/",
         "run 00c_write_legacy_coords.py")

# --- summary ------------------------------------------------------------------
nf = ok.count(False)
print()
if skipped:
    print(f"{len(ok)-nf} passed, {nf} failed, {len(skipped)} GROUP(S) SKIPPED")
    for g,reason,fix in skipped:
        print(f"  skipped  {g}\n           reason: {reason}\n           fix:    {fix}")
    print("\nINCOMPLETE -- not a valid STEP 2 gate until the skipped groups run.")
elif nf:
    print(f"{nf} CHECK(S) FAILED")
else:
    print("ALL CHECKS PASSED -- valid STEP 2 gate (no groups skipped)")
status = 0 if (nf==0 and not skipped) else 1
if "get_ipython" in dir(__builtins__) or "IPython" in sys.modules:
    print(f"\n(exit status would be {status})")
else:
    sys.exit(status)
