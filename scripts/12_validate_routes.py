# -*- coding: utf-8 -*-
"""
12_validate_routes.py  --  validation for STEP 6.

Run:
  python 12_validate_routes.py            normal validation
  python 12_validate_routes.py --mutate   self-test: corrupt the output 12 ways
                                          and confirm every corruption FAILS

SKIPS ARE NOT PASSES. If any group cannot run, this prints INCOMPLETE and
exits non-zero. That rule is here because the first master validator printed
"ALL CHECKS PASSED" having executed 34 of 43 checks, and because 04 once
reported "0 nodes disagree with legacy" when zero comparisons had run.

GROUP 2 IS THE ONE THAT MATTERS. It re-reads pipeline_nodes.csv and asserts
that the set of vertices in the GeoJSON is a SUBSET of the set of resolved node
coordinates. If that holds, no coordinate in the route file was invented, moved
or interpolated -- which is the single claim this step has to survive review.

GROUP 4 RECOMPUTES geodesic lengths from the GeoJSON geometry rather than
trusting straight_line_km in route_segments.csv. A stored number cannot check
the geometry it was supposedly derived from.
"""
import os, sys, json, math, itertools, copy
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

FAILS, SKIPS, NPASS = [], [], 0
def ok(tag, cond, msg):
    global NPASS
    if cond: NPASS += 1
    else:    FAILS.append(f"{tag}: {msg}")
def skip(group, why, fix):
    SKIPS.append((group, why, fix))

def geo_km(lon1, lat1, lon2, lat2):
    if GEOD is not None:
        return GEOD.inv(lon1, lat1, lon2, lat2)[2] / 1000.0
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2-p1)/2)**2 +
         math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2)
    return 2*R*math.asin(math.sqrt(a))


def validate(gj, segs, stat, nodes, topo, master, quiet=False):
    """Returns (n_fail, n_skip). Pure -- takes objects, so --mutate can reuse it."""
    global FAILS, SKIPS, NPASS
    FAILS, SKIPS, NPASS = [], [], 0

    feats = gj.get("features", [])
    lin   = stat[stat.topology_class == "linear"]
    ares  = stat[stat.topology_class == "areal"]

    # ---------- GROUP 1: structure and coverage -------------------------------
    n_linear_expected = int((topo.in_graph_v1 == True).sum())
    ok("R-01", len(stat) == len(topo),
       f"route_status has {len(stat)} rows, topology has {len(topo)}")
    ok("R-02", len(lin) == n_linear_expected,
       f"{len(lin)} linear rows, expected {n_linear_expected}")
    ok("R-03", set(stat.pipeline_id) == set(topo.pipeline_id),
       "route_status pipeline_ids differ from pipeline_topology")
    exp_segs = int(lin.n_segments_stated.sum())
    ok("R-04", len(segs) == exp_segs,
       f"route_segments has {len(segs)} rows, sum of n_segments_stated is {exp_segs}")
    ok("R-05", set(segs.pipeline_id) <= set(lin.pipeline_id),
       "route_segments contains a pipeline that is not linear/in-scope")
    ok("R-06", ares.route_geometry_status.eq("not_applicable_areal").all(),
       "an areal pipeline does not carry route_geometry_status=not_applicable_areal")
    ok("R-07", set(f["properties"]["pipeline_id"] for f in feats) <= set(lin.pipeline_id),
       "GeoJSON contains a pipeline_id that is not a linear in-scope pipeline")
    ok("R-08", len(feats) == len(set(f["properties"]["pipeline_id"] for f in feats)),
       "duplicate pipeline_id in the GeoJSON")
    # every pipeline with >=1 drawable segment must have a feature, and vice versa
    with_geom = set(lin[lin.n_segments_drawable > 0].pipeline_id)
    ok("R-09", set(f["properties"]["pipeline_id"] for f in feats) == with_geom,
       "GeoJSON feature set does not match the pipelines route_status says are drawable")

    # ---------- GROUP 2: ANTI-FABRICATION -------------------------------------
    res = nodes[nodes.coordinate_status.astype(str).str.strip() == "resolved"]
    if not len(res):
        skip("2 (anti-fabrication)",
             "pipeline_nodes.csv has no resolved nodes",
             "re-run 04_geocode_nodes.py")
    else:
        allowed = set()
        for _, r in res.iterrows():
            if pd.isna(r.longitude) or pd.isna(r.latitude):
                continue
            allowed.add((round(float(r.longitude), 6), round(float(r.latitude), 6)))
        # Geometry type is checked FIRST and the malformed features are excluded
        # from the coordinate walk. A validator that raises on bad input has not
        # validated it -- a traceback is not a verdict, and a reviewer running
        # this on a corrupted file must get a FAIL line, not a stack trace.
        wrong_type = [f["properties"].get("pipeline_id") for f in feats
                      if f.get("geometry", {}).get("type") != "MultiLineString"]
        ok("R-15", not wrong_type,
           f"feature(s) not MultiLineString -- a LineString can silently bridge a "
           f"gap: {wrong_type}")
        verts, nbad2, nnull, nrange, malformed = [], 0, 0, 0, 0
        for f in feats:
            if f.get("geometry", {}).get("type") != "MultiLineString":
                continue
            for part in f["geometry"]["coordinates"]:
                if (not isinstance(part, list) or len(part) != 2
                        or not all(isinstance(p, list) and len(p) == 2 for p in part)):
                    nbad2 += 1
                    if not all(isinstance(p, list) and len(p) == 2 for p in part):
                        malformed += 1
                        continue
                for lon, lat in part:
                    verts.append((round(lon, 6), round(lat, 6)))
                    if abs(lon) < 1e-9 and abs(lat) < 1e-9: nnull += 1
                    if not (6.0 <= lat <= 37.6 and 68.0 <= lon <= 97.5): nrange += 1
        vset = set(verts)
        orphan = sorted(vset - allowed)
        ok("R-10", not orphan,
           f"{len(orphan)} vertex coordinate(s) in the GeoJSON are NOT in "
           f"pipeline_nodes.csv -- i.e. invented or moved. First: {orphan[:3]}")
        ok("R-11", nbad2 == 0, f"{nbad2} MultiLineString part(s) do not have exactly 2 vertices")
        ok("R-12", nnull == 0, f"{nnull} vertex at (0,0) -- zero-fill leak")
        ok("R-13", nrange == 0, f"{nrange} vertex outside the India bounding box")
        ok("R-14", malformed == 0 and len(verts) == 2 * sum(
               len(f["geometry"]["coordinates"]) for f in feats
               if f.get("geometry", {}).get("type") == "MultiLineString"),
           f"vertex count does not equal 2 x part count ({malformed} malformed part(s))")

    # ---------- GROUP 3: gap integrity ----------------------------------------
    nseg_by_pid = segs.groupby("pipeline_id").size().to_dict()
    draw_by_pid = segs[segs.segment_status == "drawable"].groupby("pipeline_id").size().to_dict()
    parts_by_pid = {f["properties"]["pipeline_id"]:
                    (len(f["geometry"]["coordinates"])
                     if f.get("geometry", {}).get("type") == "MultiLineString" else -1)
                    for f in feats}
    g3 = []
    for _, r in lin.iterrows():
        pid = r.pipeline_id
        g3.append((pid, nseg_by_pid.get(pid, 0) == r.n_segments_stated,
                   draw_by_pid.get(pid, 0) == r.n_segments_drawable,
                   parts_by_pid.get(pid, 0) == r.n_segments_drawable))
    ok("R-16", all(a for _, a, _, _ in g3), "n_segments_stated disagrees with route_segments row count")
    ok("R-17", all(b for _, _, b, _ in g3), "n_segments_drawable disagrees with route_segments")
    ok("R-18", all(c for _, _, _, c in g3),
       "number of GeoJSON parts != n_segments_drawable -- a gap has been bridged "
       "or a segment dropped: " + str([p for p, _, _, c in g3 if not c]))
    # a drawable segment must have two resolved endpoints
    d = segs[segs.segment_status == "drawable"]
    ok("R-19", (d.from_status == "resolved").all() and (d.to_status == "resolved").all(),
       "a segment marked drawable has an endpoint that is not resolved")
    nd = segs[segs.segment_status != "drawable"]
    ok("R-20", ((nd.from_status != "resolved") | (nd.to_status != "resolved")).all(),
       "a segment marked gapped has two resolved endpoints -- geometry withheld without cause")
    ok("R-21", (nd.straight_line_km.astype(str) == "NA").all(),
       "a gapped segment carries a length instead of NA")
    ok("R-22", (nd.geometry_type.astype(str) == "NONE").all(),
       "a gapped segment carries a geometry_type")
    # status field must be exhaustive -- never blank
    VALID = {"complete", "partial", "none_all_segments_gapped", "not_applicable_areal"}
    ok("R-23", set(stat.route_geometry_status) <= VALID,
       f"unexpected route_geometry_status: {set(stat.route_geometry_status)-VALID}")
    ok("R-24", stat.route_geometry_status.notna().all() and
               (stat.route_geometry_status.astype(str).str.strip() != "").all(),
       "a pipeline has a blank route_geometry_status")

    # ---------- GROUP 4: lengths, RECOMPUTED from geometry ---------------------
    if GEOD is None:
        skip("4 (geodesic length)", "pyproj not installed -- haversine fallback in use",
             "pip install pyproj, then re-run")
    recomputed, worst = {}, 0.0
    for f in feats:
        if f.get("geometry", {}).get("type") != "MultiLineString":
            continue
        tot = 0.0
        try:
            for (lon1, lat1), (lon2, lat2) in f["geometry"]["coordinates"]:
                tot += geo_km(lon1, lat1, lon2, lat2)
        except (TypeError, ValueError):
            ok("R-24b", False,
               f"{f['properties'].get('pipeline_id')}: geometry is malformed and "
               f"its length cannot be recomputed")
            continue
        recomputed[f["properties"]["pipeline_id"]] = tot
        stored = f["properties"].get("straight_line_drawn_km")
        if stored: worst = max(worst, abs(tot - float(stored)))
    ok("R-25", worst < 0.01,
       f"stored straight_line_drawn_km disagrees with geometry recomputed from "
       f"the GeoJSON by up to {worst:.3f} km")
    # cross-check route_segments against the same recompute
    dr = segs[segs.segment_status == "drawable"].copy()
    dr["km"] = pd.to_numeric(dr.straight_line_km, errors="coerce")
    unnum = dr[dr.km.isna()]
    ok("R-26a", not len(unnum),
       f"{len(unnum)} segment(s) marked drawable carry a non-numeric length "
       f"(e.g. NA): {list(unnum.pipeline_id)[:3]}")
    ssum = dr.dropna(subset=["km"]).groupby("pipeline_id").km.sum().to_dict()
    pids = set(ssum) | set(recomputed)
    w2 = max([abs(ssum.get(p, 0.0) - recomputed.get(p, 0.0)) for p in pids] or [0])
    ok("R-26", w2 < 0.01, f"route_segments lengths disagree with geometry by up to {w2:.3f} km")

    COMPARABLE = ["ok", "FAIL_shorter_than_geodesic",
                  "REVIEW_marginally_shorter_within_centroid_tolerance",
                  "REVIEW_high_ratio_length_unexplained_by_named_points"]
    comparable = lin[lin.sinuosity_flag.isin(COMPARABLE)]
    if not len(comparable):
        skip("4b (length plausibility)",
             "no pipeline has complete geometry AND a usable authorized length, "
             "so the authorized-vs-straight-line test compared nothing",
             "resolve the remaining node coordinates (STEP 2b follow-up), then re-run")
    else:
        viol = []
        for _, r in comparable.iterrows():
            a  = float(r.authorized_length_km)
            sk = recomputed.get(r.pipeline_id, float("nan"))
            allow = float(r.centroid_allowance_km)
            if sk - a > allow and r.sinuosity_flag != "FAIL_shorter_than_geodesic":
                viol.append(f"{r.pipeline_id} short by {sk-a:.2f} km "
                            f"(allowance {allow}) but not flagged FAIL")
        ok("R-27", not viol,
           "a pipeline is shorter than the geodesic through its own named points by "
           "more than the centroid allowance and is not flagged: " + "; ".join(viol))
        # the recomputed excess must match the stored one
        ex = [f"{r.pipeline_id}" for _, r in comparable.iterrows()
              if abs((recomputed.get(r.pipeline_id, 0) - float(r.authorized_length_km))
                     - float(r.length_excess_km)) > 0.01]
        ok("R-27b", not ex, f"length_excess_km disagrees with recomputed geometry: {ex}")
        ok("R-28", (comparable.sinuosity_ratio.astype(float) > 0).all(),
           "a comparable pipeline has a non-positive sinuosity ratio")
        # the flag must agree with the number, not be set independently
        mism = []
        for _, r in comparable.iterrows():
            e, v, al = float(r.length_excess_km), float(r.sinuosity_ratio), float(r.centroid_allowance_km)
            want = ("FAIL_shorter_than_geodesic" if e > al else
                    "REVIEW_marginally_shorter_within_centroid_tolerance" if e > 0 else
                    "REVIEW_high_ratio_length_unexplained_by_named_points" if v > 1.6 else "ok")
            if r.sinuosity_flag != want: mism.append(f"{r.pipeline_id}:{r.sinuosity_flag}->{want}")
        ok("R-29", not mism, "sinuosity_flag disagrees with the numbers it claims to describe: "
           + "; ".join(mism))

    # NA discipline: nothing incomparable may carry a number
    inc = lin[~lin.sinuosity_flag.isin(COMPARABLE)]
    ok("R-30", (inc.sinuosity_ratio.astype(str) == "NA").all(),
       "a pipeline with no usable comparison carries a sinuosity ratio instead of NA")
    ok("R-31", (stat[stat.route_geometry_status != "complete"]
                .straight_line_total_km.astype(str) == "NA").all(),
       "a pipeline without complete geometry reports a total length")
    ok("R-32", (inc.length_excess_km.astype(str) == "NA").all(),
       "a pipeline with no usable comparison carries a length_excess_km instead of NA")
    zero_leak = []
    for c in ["straight_line_total_km", "straight_line_drawn_km", "sinuosity_ratio"]:
        z = stat[stat[c].astype(str).isin(["0", "0.0", "0.00"])]
        if len(z): zero_leak += [f"{c}:{p}" for p in z.pipeline_id]
    ok("R-33", not zero_leak, "zero used where NA is meant: " + "; ".join(zero_leak))
    # An empty cell is ambiguous (missing? zero? not applicable?). The sentinel
    # must be written out. This is checkable only because _read() above does not
    # let pandas reinterpret it.
    blankcols = []
    for df, nm, cols in [(stat, "route_status.csv",
                          ["straight_line_total_km", "straight_line_drawn_km",
                           "sinuosity_ratio", "length_excess_km", "sinuosity_flag",
                           "route_geometry_status", "path_assumption"]),
                         (segs, "route_segments.csv",
                          ["straight_line_km", "geometry_type", "length_basis",
                           "segment_status", "from_status", "to_status"])]:
        for c in cols:
            if c in df.columns and (df[c].astype(str).str.strip() == "").any():
                blankcols.append(f"{nm}:{c}")
    ok("R-33b", not blankcols,
       "blank cell where an explicit value or NA is required: " + "; ".join(blankcols))

    # ---------- GROUP 5: labelling and provenance ------------------------------
    ok("R-34", all(f["properties"].get("geometry_type") == "reconstructed_straight_segment"
                   for f in feats), "a feature is missing geometry_type=reconstructed_straight_segment")
    ok("R-35", all(f["properties"].get("NOT_AN_ALIGNMENT") is True for f in feats),
       "a feature is missing NOT_AN_ALIGNMENT=true")
    ok("R-36", all("warning" in f["properties"] and len(f["properties"]["warning"]) > 40
                   for f in feats), "a feature is missing the alignment warning")
    ok("R-37", all(f["properties"].get("provenance_category") == "B" for f in feats),
       "a feature is not labelled Category B")
    ok("R-38", gj.get("metadata", {}).get("densify_before_buffering") is True,
       "the file does not carry the densify-before-buffering instruction")
    ok("R-39", "7755" in str(gj.get("metadata", {}).get("metric_crs_for_downstream_use", "")),
       "metadata does not name EPSG:7755 as the metric CRS")
    ok("R-40", "CRS84" in json.dumps(gj.get("crs", {})),
       "GeoJSON does not declare CRS84 / EPSG:4326")
    ok("R-41", not any(c.startswith(("n_states", "pct_", "score", "norm_"))
                       for c in segs.columns),
       "a Category-C column has appeared in a Category-A/B table")
    ok("R-42", all("node_ids" in f["properties"] and f["properties"]["node_ids"]
                   for f in feats), "a feature does not cite its node_ids")

    # ---------- GROUP 6: cross-check against the master ------------------------
    if "authorized_length_km" not in master.columns:
        skip("6 (master cross-check)", "pipeline_master.csv lacks authorized_length_km",
             "re-run 01_build_pipeline_master.py")
    else:
        A = dict(zip(master.pipeline_id, master.authorized_length_km))
        bad = [r.pipeline_id for _, r in stat.iterrows()
               if pd.notna(r.authorized_length_km) and pd.notna(A.get(r.pipeline_id))
               and abs(float(r.authorized_length_km) - float(A[r.pipeline_id])) > 1e-6]
        ok("R-43", not bad, f"authorized_length_km in route_status differs from the master: {bad}")
        ok("R-44", set(stat.pipeline_id) <= set(master[master.in_graph_scope == True].pipeline_id),
           "route_status contains a pipeline that is not in_graph_scope in the master")

    return len(FAILS), len(SKIPS)


# ------------------------------------------------------------------ load & run
# NUMERIC COLUMNS, declared. Everything else is read as the literal text on disk.
NUMCOLS = ["n_waypoints_stated", "n_segments_stated", "n_segments_drawable",
           "n_segments_gap", "authorized_length_km", "seq_from", "seq_to",
           "latitude", "longitude", "n_pipelines", "legacy_delta_km",
           "operating_length_km", "under_construction_km", "capacity_mmscmd"]

def _read(path):
    """Read a published CSV EXACTLY as it sits on disk.

    keep_default_na=False matters and is not a style choice. pandas' default
    na_values list contains the literal string "NA", so a column written as the
    explicit sentinel NA comes back as NaN and `.astype(str)` yields "nan".
    A validator that read it that way would be checking pandas' interpretation
    of the file rather than the file, and every NA-discipline check below --
    the ones that exist to stop a missing value being written as 0 -- would
    silently test nothing. Numeric columns are coerced afterwards, by name.
    """
    df = pd.read_csv(path, keep_default_na=False, na_values=[], dtype=str)
    for c in df.columns:
        if c in NUMCOLS:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        elif c == "in_graph_v1" or c == "in_graph_scope":
            df[c] = df[c].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
    return df

def load():
    p = os.path.join(GIS, "pipeline_routes.geojson")
    for f in [p, os.path.join(DP, "route_segments.csv"), os.path.join(DP, "route_status.csv"),
              os.path.join(DP, "pipeline_nodes.csv"), os.path.join(DP, "pipeline_topology.csv"),
              os.path.join(DP, "pipeline_master.csv")]:
        if not os.path.exists(f):
            raise SystemExit(f"MISSING: {f}\n  Run 07_build_routes.py first.")
    return (json.load(open(p, encoding="utf-8")),
            _read(os.path.join(DP, "route_segments.csv")),
            _read(os.path.join(DP, "route_status.csv")),
            _read(os.path.join(DP, "pipeline_nodes.csv")),
            _read(os.path.join(DP, "pipeline_topology.csv")),
            _read(os.path.join(DP, "pipeline_master.csv")))


def report(nf, ns, n_ok):
    print(f"\nchecks passed  {n_ok}")
    if FAILS:
        print(f"FAILURES       {nf}")
        for f in FAILS: print("   " + f)
    if SKIPS:
        print(f"SKIPPED        {ns}   <-- these are NOT passes")
        for g, why, fix in SKIPS:
            print(f"   group {g}\n      why: {why}\n      fix: {fix}")
    if nf == 0 and ns == 0:
        print("\nSTEP 6 VALIDATION PASSED  -- all checks ran, all checks passed")
        return 0
    print("\nSTEP 6 VALIDATION INCOMPLETE" if ns and not nf else "\nSTEP 6 VALIDATION FAILED")
    return 1


def mutate():
    """Corrupt the output 12 ways. Every one must FAIL. A validator that has
    never failed is not a validator."""
    gj0, sg0, st0, nd, tp, ms = load()
    muts = []

    def m(name, fn): muts.append((name, fn))

    m("move a vertex 0.5 deg east (fabricated coordinate)",
      lambda g, s, t: (_mv(g, 0.5), s, t))
    m("nudge a vertex 0.001 deg (small fabrication)",
      lambda g, s, t: (_mv(g, 0.001), s, t))
    m("zero-fill a vertex to (0,0)",
      lambda g, s, t: (_null(g), s, t))
    m("bridge a gap: add a part joining two ends of a gapped route",
      lambda g, s, t: (_bridge(g), s, t))
    m("drop a part from a complete route",
      lambda g, s, t: (_drop(g), s, t))
    m("convert a MultiLineString to a LineString",
      lambda g, s, t: (_flatten(g), s, t))
    m("inflate stored straight_line_drawn_km by 10%",
      lambda g, s, t: (_inflate(g), s, t))
    m("set a gapped segment's length to 0 instead of NA",
      lambda g, s, t: (g, _seg0(s), t))
    m("mark a gapped segment drawable",
      lambda g, s, t: (g, _segdraw(s), t))
    m("blank a route_geometry_status",
      lambda g, s, t: (g, s, _blank(t)))
    m("flip a sinuosity_flag to ok while the numbers say otherwise",
      lambda g, s, t: (g, s, _flip(t)))
    m("strip NOT_AN_ALIGNMENT from a feature",
      lambda g, s, t: (_strip(g), s, t))
    m("silently widen the centroid allowance to hide a shortfall",
      lambda g, s, t: (g, s, _widen(t)))
    m("overwrite length_excess_km with a value the geometry does not support",
      lambda g, s, t: (g, s, _fudge(t)))

    print("MUTATION SELF-TEST -- every mutation must FAIL\n")
    missed = []
    for name, fn in muts:
        g, s, t = fn(copy.deepcopy(gj0), sg0.copy(), st0.copy())
        nf, ns = validate(g, s, t, nd, tp, ms)
        status = "caught" if nf else "*** MISSED ***"
        if not nf: missed.append(name)
        print(f"  {status:16s} {name}"
              + ("" if not nf else f"   [{FAILS[0].split(':')[0]}]"))
    print(f"\n{len(muts)-len(missed)}/{len(muts)} mutations caught")
    if missed:
        print("MUTATIONS NOT CAUGHT -- the validator is not yet trustworthy:")
        for x in missed: print("   " + x)
        return 1
    print("Mutation self-test passed.")
    return 0

# --- mutation helpers (kept small and obvious) --------------------------------
def _mv(g, d):     g["features"][0]["geometry"]["coordinates"][0][0][0] += d; return g
def _null(g):      g["features"][0]["geometry"]["coordinates"][0][0] = [0.0, 0.0]; return g
def _drop(g):
    for f in g["features"]:
        if len(f["geometry"]["coordinates"]) > 1:
            f["geometry"]["coordinates"].pop(); return g
    return g
def _bridge(g):
    for f in g["features"]:
        if f["properties"]["route_geometry_status"] != "complete":
            c = f["geometry"]["coordinates"]
            c.append([c[-1][1], c[0][0]]); return g
    g["features"][0]["geometry"]["coordinates"].append(
        list(reversed(g["features"][0]["geometry"]["coordinates"][0]))); return g
def _flatten(g):
    f = g["features"][0]
    f["geometry"] = dict(type="LineString",
                         coordinates=[p for part in f["geometry"]["coordinates"] for p in part])
    return g
def _inflate(g):
    g["features"][0]["properties"]["straight_line_drawn_km"] = round(
        float(g["features"][0]["properties"]["straight_line_drawn_km"]) * 1.1, 3); return g
def _strip(g):     g["features"][0]["properties"].pop("NOT_AN_ALIGNMENT", None); return g
def _seg0(s):
    i = s.index[s.segment_status != "drawable"]
    if len(i): s.loc[i[0], "straight_line_km"] = "0"
    return s
def _segdraw(s):
    i = s.index[s.segment_status != "drawable"]
    if len(i): s.loc[i[0], "segment_status"] = "drawable"
    return s
def _blank(t):     t.loc[t.index[0], "route_geometry_status"] = ""; return t
def _flip(t):
    i = t.index[t.sinuosity_flag.str.startswith(("REVIEW_high", "REVIEW_marginally", "FAIL_"))]
    if len(i): t.loc[i[0], "sinuosity_flag"] = "ok"
    return t


def _widen(t):
    i = t.index[t.sinuosity_flag == "REVIEW_marginally_shorter_within_centroid_tolerance"]
    if len(i): t.loc[i[0], "centroid_allowance_km"] = "5.0"  # excess > allowance => must FAIL
    return t
def _fudge(t):
    i = t.index[t.length_excess_km.astype(str) != "NA"]
    if len(i): t.loc[i[0], "length_excess_km"] = "-999.0"
    return t


if __name__ == "__main__":
    if "--mutate" in sys.argv:
        rc = mutate()
    else:
        gj, sg, st, nd, tp, ms = load()
        nf, ns = validate(gj, sg, st, nd, tp, ms)
        rc = report(nf, ns, NPASS)
    try:
        get_ipython()                 # in Colab: no traceback
        print(f"\n[exit status {rc}]")
    except NameError:
        sys.exit(rc)
