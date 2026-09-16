# -*- coding: utf-8 -*-
"""
07_build_routes.py  --  STEP 6 of the NGPL dataset build.

Builds reconstructed route geometry for the 27 LINEAR Common Carrier pipelines
from the 56 named nodes produced in STEP 2b.

Writes:
  gis/pipeline_routes.geojson            one feature per pipeline that has >=1 drawable segment
  data_processed/route_segments.csv      one row per consecutive waypoint pair (47 rows)
  data_processed/route_status.csv        one row per in-scope pipeline (37 rows) -- nothing disappears

WHAT THIS GEOMETRY IS, AND WHAT IT IS NOT
  It is a straight geodesic segment between two gazetteer points that the PNGRB
  register names in the pipeline's own title. That is all it is.
  It is NOT the pipeline's alignment. It does not follow the right of way, it
  does not know about rivers, ghats, forest diversions or the actual corridor.
  Every feature carries geometry_type = "reconstructed_straight_segment" and
  NOT_AN_ALIGNMENT = true so that no downstream consumer can mistake it.
  Section 8.1 of the README stands unchanged after this step.

THE GAP RULE (the reason this script exists rather than a three-line shapely call)
  5 of the 56 node names have no coordinate. A LineString drawn through the
  remaining waypoints would silently bridge the gap and produce a route that
  looks complete and is wrong. So:
    - geometry is MultiLineString, one part per DRAWABLE consecutive pair
    - a gapped pair contributes NO part, and is recorded as a row in
      route_segments.csv with segment_status naming which end failed
    - route_geometry_status is complete / partial / none_all_nodes_unresolved /
      not_applicable_areal -- never blank, never 0
  A partial route is therefore visibly discontinuous in the file itself, not
  only in an attribute a reader might not open.

TWO-VERTEX SEGMENTS, DELIBERATELY
  Each part has exactly 2 vertices, both of which are node coordinates taken
  verbatim from pipeline_nodes.csv. No vertex in this file was computed by this
  script. That is what makes the anti-fabrication check in 12_validate_routes.py
  exact: the vertex set must be a subset of the node coordinate set.
  CONSEQUENCE FOR STEP 7: a 2-vertex segment in EPSG:4326 reprojected to
  EPSG:7755 is a straight line in the projected plane, which cuts the corner
  against the true geodesic -- up to ~1.5 km at the middle of a 900 km segment.
  The buffer step MUST densify along the geodesic before projecting. Do not
  buffer this file as it stands.

LENGTHS
  straight_line_km is the GEODESIC distance on the WGS 84 ellipsoid
  (pyproj.Geod.inv), not a projected distance. It is exact and CRS-free, so it
  cannot inherit the EPSG:3395 latitude error that was rejected earlier.
"""
import os, json, math
import pandas as pd, numpy as np

try:
    from pyproj import Geod
    GEOD = Geod(ellps="WGS84")
except ImportError:
    GEOD = None

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
DP   = os.path.join(ROOT, "data_processed")
GIS  = os.path.join(ROOT, "gis")
os.makedirs(GIS, exist_ok=True)

def need(path, what):
    if not os.path.exists(path):
        raise SystemExit(f"MISSING INPUT: {path}\n  {what}\n"
                         f"  This script will not guess around a missing input.")
    return path

MASTER = need(os.path.join(DP, "pipeline_master.csv"), "run 01_build_pipeline_master.py")
TOPO   = need(os.path.join(DP, "pipeline_topology.csv"), "run 03_build_node_candidates.py")
CAND   = need(os.path.join(DP, "node_candidates.csv"),   "run 03_build_node_candidates.py")
NODES  = need(os.path.join(DP, "pipeline_nodes.csv"),    "run 04_geocode_nodes.py")

m     = pd.read_csv(MASTER)
topo  = pd.read_csv(TOPO)
cand  = pd.read_csv(CAND)
nodes = pd.read_csv(NODES)

# --- schema guard: fail loudly rather than KeyError halfway through ------------
REQ = {
 "pipeline_nodes.csv":   (nodes, ["node_id","node_name","latitude","longitude",
                                  "coordinate_status","coordinate_source",
                                  "coordinate_accuracy","state_ut"]),
 "node_candidates.csv":  (cand,  ["pipeline_id","seq","node_name","role"]),
 "pipeline_topology.csv":(topo,  ["pipeline_id","pipeline_name","topology_class",
                                  "in_graph_v1","n_waypoints_stated","topology_note"]),
 "pipeline_master.csv":  (m,     ["pipeline_id","authorized_length_km","in_graph_scope"]),
}
for fname,(df,cols) in REQ.items():
    miss = [c for c in cols if c not in df.columns]
    if miss:
        raise SystemExit(f"{fname} is missing required columns: {miss}\n"
                         f"  Present: {list(df.columns)}\n"
                         f"  Regenerate it; do not hand-edit.")

# Placement allowance per node, in km. A node here is a settlement centroid, not
# the pipeline terminal inside that settlement; 05_resolve_facility_nodes.py
# measured the real offset at 0.08-3.6 km for the seven facilities it could test,
# so 10 km per node is generous and is the number that has to be defended, not
# hidden. Raising it weakens the test; lowering it turns centroid error into
# false findings.
CENTROID_TOL_KM = 10.0

# --- pipelines whose printed waypoint order is NOT a simple path --------------
# Stated explicitly. 17.03 is a merged authorization (HVJ + GREP + DVPL/VDPL) and
# 17.20 is a known branching trunk; for both, the register prints places in an
# order that is not a traversal. Their geometry is still built -- a reader asked
# for "the places this pipeline touches, joined in printed order" gets exactly
# that -- but the sinuosity test below cannot be applied to them and is not.
NON_PATH = {
 "17.03.NGPL":"Merged authorization covering HVJ + GREP + DVPL/VDPL. The printed "
              "order is not a single traversal; the drawn chain is a reading aid, "
              "not a route. Length comparison is not meaningful.",
 "17.20.NGPL":"Known branching trunk (JHBDPL / Urja Ganga). The printed order is "
              "not a single traversal. Length comparison is not meaningful.",
 "17.11.NGPL":"The register states two segments (Dahej-Vijaipur, Vijaipur-Dadri) "
              "and shares its length cell with 17.03, so authorized_length_km "
              "cannot be attributed to this chain alone.",
}

# --- node lookup --------------------------------------------------------------
nodes["_res"] = nodes.coordinate_status.astype(str).str.strip().eq("resolved")
NODE = {}
for _, r in nodes.iterrows():
    NODE[str(r.node_name).strip()] = dict(
        node_id=r.node_id, status=str(r.coordinate_status).strip(),
        lat=float(r.latitude) if pd.notna(r.latitude) else None,
        lon=float(r.longitude) if pd.notna(r.longitude) else None,
        accuracy=r.coordinate_accuracy, source=r.coordinate_source, state=r.state_ut)

# A resolved node with no coordinate is a contradiction -- catch it here, not later.
bad = [k for k,v in NODE.items() if v["status"]=="resolved" and (v["lat"] is None or v["lon"] is None)]
if bad:
    raise SystemExit(f"pipeline_nodes.csv is internally inconsistent: "
                     f"coordinate_status='resolved' but no coordinate for {bad}")
# And the reverse: an unresolved node carrying a coordinate would be a zero-fill leak.
leak = [k for k,v in NODE.items() if v["status"]!="resolved" and (v["lat"] is not None or v["lon"] is not None)]
if leak:
    raise SystemExit(f"pipeline_nodes.csv carries coordinates on non-resolved nodes: {leak}")

def geodesic_km(lon1, lat1, lon2, lat2):
    if GEOD is not None:
        _, _, d = GEOD.inv(lon1, lat1, lon2, lat2)
        return d / 1000.0
    # haversine fallback, mean Earth radius -- only if pyproj is absent
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

AUTH = dict(zip(m.pipeline_id, m.authorized_length_km))
NAME = dict(zip(topo.pipeline_id, topo.pipeline_name))
NOTE = dict(zip(topo.pipeline_id, topo.topology_note))

# --- build segments -----------------------------------------------------------
seg_rows, feats, stat_rows = [], [], []
linear = topo[topo.in_graph_v1 == True].pipeline_id.tolist()

for pid in linear:
    wp = cand[cand.pipeline_id == pid].sort_values("seq")
    names = [str(x).strip() for x in wp.node_name.tolist()]
    parts, n_draw, n_gap, total = [], 0, 0, 0.0
    for i in range(len(names) - 1):
        a, b = names[i], names[i+1]
        na, nb = NODE.get(a), NODE.get(b)
        if na is None or nb is None:
            raise SystemExit(f"{pid}: waypoint '{a if na is None else b}' is in "
                             f"node_candidates.csv but not in pipeline_nodes.csv. "
                             f"Re-run 04_geocode_nodes.py.")
        ga = na["status"] != "resolved"
        gb = nb["status"] != "resolved"
        if ga and gb:   st = f"gap_both_unresolved ({na['status']}/{nb['status']})"
        elif ga:        st = f"gap_from_{na['status']}"
        elif gb:        st = f"gap_to_{nb['status']}"
        else:           st = "drawable"
        km = np.nan
        if st == "drawable":
            km = geodesic_km(na["lon"], na["lat"], nb["lon"], nb["lat"])
            parts.append([[na["lon"], na["lat"]], [nb["lon"], nb["lat"]]])
            n_draw += 1; total += km
        else:
            n_gap += 1
        seg_rows.append(dict(
            pipeline_id=pid, seq_from=i+1, seq_to=i+2,
            from_node_id=na["node_id"], to_node_id=nb["node_id"],
            from_node_name=a, to_node_name=b,
            from_status=na["status"], to_status=nb["status"],
            segment_status=st,
            straight_line_km=round(km, 3) if st == "drawable" else "NA",
            geometry_type="reconstructed_straight_segment" if st == "drawable" else "NONE",
            length_basis="geodesic, WGS 84 ellipsoid" if st == "drawable" else "NA",
            provenance_category="B -- computed from two Category-B node coordinates"))

    n_seg = len(names) - 1
    if   n_draw == n_seg: gstat = "complete"
    elif n_draw == 0:     gstat = "none_all_segments_gapped"
    else:                 gstat = "partial"

    auth = AUTH.get(pid, np.nan)
    ratio, flag, excess = "NA", "", "NA"
    if pid in NON_PATH:
        flag = "NOT_COMPARABLE_non_path"
    elif gstat != "complete":
        flag = "NA_incomplete_geometry"
    elif pd.isna(auth) or float(auth) <= 0 or total <= 0:
        flag = "NA_no_authorized_length"
    else:
        r = float(auth) / total
        ratio = round(r, 3)
        excess = round(total - float(auth), 3)          # km the straight line exceeds the register
        # A physical pipeline cannot be shorter than the geodesic through its own
        # named points -- but our points are SETTLEMENT CENTROIDS, not terminals,
        # so each node carries a placement error. Allowance is CENTROID_TOL_KM per
        # node; a shortfall inside that allowance is a measurement limitation, a
        # shortfall outside it is a data error. Distinguishing the two is the
        # whole point (see README 8.2).
        allow = CENTROID_TOL_KM * len(names)
        if   excess > allow: flag = "FAIL_shorter_than_geodesic"
        elif excess > 0:     flag = "REVIEW_marginally_shorter_within_centroid_tolerance"
        elif r > 1.6:        flag = "REVIEW_high_ratio_length_unexplained_by_named_points"
        else:                flag = "ok"

    stat_rows.append(dict(
        pipeline_id=pid, pipeline_name=NAME.get(pid, ""), topology_class="linear",
        n_waypoints_stated=len(names), n_segments_stated=n_seg,
        n_segments_drawable=n_draw, n_segments_gap=n_gap,
        route_geometry_status=gstat,
        straight_line_total_km=round(total, 3) if gstat == "complete" else "NA",
        straight_line_drawn_km=round(total, 3) if n_draw else "NA",
        authorized_length_km=auth,
        sinuosity_ratio=ratio, length_excess_km=excess, sinuosity_flag=flag,
        centroid_allowance_km=round(CENTROID_TOL_KM*len(names),1),
        path_assumption="printed order is NOT a traversal" if pid in NON_PATH
                        else "printed order read as a traversal",
        geometry_note=NON_PATH.get(pid, NOTE.get(pid, "")) or ""))

    if parts:
        feats.append(dict(type="Feature", properties=dict(
            pipeline_id=pid, pipeline_name=NAME.get(pid, ""),
            geometry_type="reconstructed_straight_segment",
            NOT_AN_ALIGNMENT=True,
            warning="Straight geodesic segments between gazetteer settlement "
                    "centroids named in the pipeline title. NOT the surveyed "
                    "right of way. Do not use for routing, land acquisition, "
                    "encroachment or any distance-to-pipeline calculation "
                    "presented as fact.",
            route_geometry_status=gstat,
            n_segments_stated=n_seg, n_segments_drawable=n_draw, n_segments_gap=n_gap,
            straight_line_drawn_km=round(total, 3),
            authorized_length_km=None if pd.isna(auth) else float(auth),
            sinuosity_ratio=None if ratio == "NA" else ratio,
            length_excess_km=None if excess == "NA" else excess,
            sinuosity_flag=flag,
            waypoint_sequence=" -> ".join(names),
            node_ids=";".join(NODE[n]["node_id"] for n in names),
            vertex_provenance="every vertex is a coordinate copied verbatim from "
                              "pipeline_nodes.csv; no vertex was computed here",
            coordinate_accuracy="settlement centroid (or named infrastructure "
                                "feature); NOT a facility location",
            source_document="PNGRB NGPL register 20251231_NGPL.pdf (names) + "
                            "GeoNames IN.txt (coordinates)",
            provenance_category="B"),
            geometry=dict(type="MultiLineString", coordinates=parts)))

# --- areal pipelines are listed, not dropped ----------------------------------
for _, r in topo[topo.in_graph_v1 != True].iterrows():
    stat_rows.append(dict(
        pipeline_id=r.pipeline_id, pipeline_name=r.pipeline_name, topology_class="areal",
        n_waypoints_stated=0, n_segments_stated=0, n_segments_drawable=0, n_segments_gap=0,
        route_geometry_status="not_applicable_areal",
        straight_line_total_km="NA", straight_line_drawn_km="NA",
        authorized_length_km=AUTH.get(r.pipeline_id, np.nan),
        sinuosity_ratio="NA", length_excess_km="NA", centroid_allowance_km="NA",
        sinuosity_flag="NA_areal",
        path_assumption="no route stated by the register",
        geometry_note=r.topology_note))

segs = pd.DataFrame(seg_rows)
stat = pd.DataFrame(stat_rows).sort_values("pipeline_id").reset_index(drop=True)

fc = dict(type="FeatureCollection",
          crs=dict(type="name", properties=dict(name="urn:ogc:def:crs:OGC:1.3:CRS84")),
          metadata=dict(
            title="Reconstructed route geometry, Indian natural gas Common Carrier pipelines",
            crs="EPSG:4326 (CRS84 axis order, lon lat)",
            metric_crs_for_downstream_use="EPSG:7755 (WGS 84 / India NSF LCC)",
            geometry_type="reconstructed_straight_segment",
            NOT_AN_ALIGNMENT=True,
            densify_before_buffering=True,
            densify_note="Parts have 2 vertices. Projecting a 2-vertex segment to "
                         "EPSG:7755 draws a straight line in the projected plane, "
                         "which departs from the geodesic by up to ~1.5 km near the "
                         "middle of a 900 km segment. Densify along the geodesic "
                         "before buffering.",
            provenance_category="B",
            source_document="20251231_NGPL.pdf",
            generated_by="07_build_routes.py"),
          features=feats)

segs.to_csv(os.path.join(DP, "route_segments.csv"), index=False)
stat.to_csv(os.path.join(DP, "route_status.csv"), index=False)
with open(os.path.join(GIS, "pipeline_routes.geojson"), "w", encoding="utf-8") as f:
    json.dump(fc, f, ensure_ascii=False, indent=1)

# --- report -------------------------------------------------------------------
lin = stat[stat.topology_class == "linear"]
print(f"pipeline_routes.geojson    {len(feats)} features "
      f"({int(segs.segment_status.eq('drawable').sum())} drawable segments)")
print(f"route_segments.csv         {len(segs)} rows")
print(f"route_status.csv           {len(stat)} rows "
      f"({len(lin)} linear + {len(stat)-len(lin)} areal)")
print("\nROUTE GEOMETRY STATUS")
for k, v in lin.route_geometry_status.value_counts().items():
    print(f"  {k:28s} {v}")
print(f"  {'not_applicable_areal':28s} {len(stat)-len(lin)}")

gapped = segs[segs.segment_status != "drawable"]
print(f"\nGAPPED SEGMENTS            {len(gapped)}")
for _, r in gapped.iterrows():
    print(f"  {r.pipeline_id:12s} {r.from_node_name} -> {r.to_node_name:18s} {r.segment_status}")
if not len(gapped):
    print("  none")

print("\nLENGTH CROSS-CHECK  (register length vs geodesic through the named points)")
COMPARABLE = ["ok", "FAIL_shorter_than_geodesic",
              "REVIEW_marginally_shorter_within_centroid_tolerance",
              "REVIEW_high_ratio_length_unexplained_by_named_points"]
shown = lin[lin.sinuosity_flag.isin(COMPARABLE)]
if not len(shown):
    print("  DID NOT RUN -- no pipeline has complete geometry AND a usable "
          "authorized length. This is NOT a pass.")
else:
    MARK = {"ok": "  ", "FAIL_shorter_than_geodesic": "!!",
            "REVIEW_marginally_shorter_within_centroid_tolerance": " -",
            "REVIEW_high_ratio_length_unexplained_by_named_points": " ?"}
    for _, r in shown.sort_values("sinuosity_ratio").iterrows():
        print(f" {MARK[r.sinuosity_flag]} {r.pipeline_id:12s} "
              f"register {float(r.authorized_length_km):8.2f} km   "
              f"geodesic {float(r.straight_line_total_km):8.2f} km   "
              f"ratio {float(r.sinuosity_ratio):5.3f}")
    nf = int((shown.sinuosity_flag == "FAIL_shorter_than_geodesic").sum())
    nm = int((shown.sinuosity_flag.str.startswith("REVIEW_marginally")).sum())
    nh = int((shown.sinuosity_flag.str.startswith("REVIEW_high")).sum())
    print(f"    compared {len(shown)} of {len(lin)} linear pipelines "
          f"({nf} FAIL, {nm} marginally short, {nh} high ratio)")
    print(f"    not compared: {len(lin)-len(shown)} "
          f"(incomplete geometry, non-path, or no register length) -- NOT passes")
    if nm:
        print("\n -  MARGINALLY SHORTER than the geodesic, inside the centroid "
              "allowance.\n    A settlement centroid is not the terminal; this is a "
              "measurement limit,\n    not necessarily a data error. Each one still "
              "needs a named terminal to close.")
        for _, r in shown[shown.sinuosity_flag.str.startswith("REVIEW_marginally")].iterrows():
            print(f"      {r.pipeline_id:12s} short by {float(r.length_excess_km):6.2f} km "
                  f"(allowance {r.centroid_allowance_km} km)  {r.pipeline_name[:44]}")
    if nh:
        print("\n ?  REGISTER LENGTH MUCH GREATER than the geodesic through the "
              "named points.\n    Two possible causes, and this script cannot tell "
              "them apart:\n      (a) the authorized length includes spurs/branches "
              "the title does not name;\n      (b) waypoints are missing from the "
              "transcription in 03_build_node_candidates.py.\n    Each needs the PDF "
              "row re-read before the route is published. UNRESOLVED.")
        for _, r in shown[shown.sinuosity_flag.str.startswith("REVIEW_high")].sort_values(
                "sinuosity_ratio", ascending=False).iterrows():
            print(f"      {r.pipeline_id:12s} ratio {float(r.sinuosity_ratio):5.3f}  "
                  f"{r.pipeline_name[:58]}")

print("\nNEXT: python 12_validate_routes.py")
