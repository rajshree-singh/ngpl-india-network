# -*- coding: utf-8 -*-
"""
09_build_edges.py  --  STEP 7c.

Writes:
  data_processed/pipeline_edges.csv   the graph edge list

WHAT AN EDGE IS HERE
  One consecutive pair of route points stated in a pipeline's own name. 5.05 is
  "Shahdol-Phulpur", so it contributes one edge N0xx -> N0yy. 17.15 is
  "Kochi-Koottanad-Bangalore-Mangalore", so it contributes three.
  Ordering is source-derived: the register printed the places in that order.

EVERY STATED EDGE IS PUBLISHED, INCLUDING THE ONES WITH NO GEOMETRY.
  Eight edges join a node that has no coordinate. They are still edges -- the
  pipeline really does connect those two places; we simply cannot draw the line.
  Dropping them would silently shrink the network and would make the graph
  falsely well-connected: 17.03 would appear to run Hazira straight to
  Jagdishpur, and Vijaipur, an interconnection on three pipelines, would vanish
  from the topology altogether. So `geometry_available` and `length_km` carry
  the gap, and no row is omitted.

DIRECTED OR UNDIRECTED?
  Recorded as printed (from -> to), and `directed` is set FALSE with a reason.
  Gas flow direction is not stated anywhere in the register and reverses on
  several of these lines in real operation. Publishing a direction we cannot
  source would be a fabricated attribute, so the order is documented as
  presentation order only.

BRANCHING
  Two pipelines are not simple paths: 17.03 is a merged authorization
  (HVJ + GREP + DVPL/VDPL) and 17.20 is a known branching trunk. Their printed
  order is not a traversal. Their edges are published with
  `sequence_is_traversal = FALSE` so that a graph algorithm treating them as a
  simple path is at least doing so knowingly.
"""
import os
import pandas as pd

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON, require

DP = os.path.join(ROOT, "data_processed")
RD = dict(keep_default_na=False, na_values=[], dtype=str)

segs  = pd.read_csv(require("data_processed/route_segments.csv"), **RD)
nodes = pd.read_csv(require("data_processed/pipeline_nodes.csv"), **RD)
m     = pd.read_csv(require("data_processed/pipeline_master.csv"), **RD)
topo  = pd.read_csv(require("data_processed/pipeline_topology.csv"), **RD)

NON_TRAVERSAL = {
 "17.03.NGPL": "merged authorization (HVJ + GREP + DVPL/VDPL); the printed order "
               "of places is not a single traversal",
 "17.20.NGPL": "known branching trunk (JHBDPL / Urja Ganga); the printed order is "
               "not a single traversal",
}

NAME  = dict(zip(m.pipeline_id, m.pipeline_name))
OPER  = dict(zip(m.pipeline_id, m.operator_code))
CAT   = dict(zip(m.pipeline_id, m.pipeline_category))
STAT  = dict(zip(m.pipeline_id, m.status))
CLASS = dict(zip(nodes.node_id, nodes.node_class))

rows = []
for i, (_, s) in enumerate(segs.iterrows(), 1):
    pid = s.pipeline_id
    drawable = s.segment_status == "drawable"
    rows.append(dict(
        edge_id=f"E{i:03d}",
        pipeline_id=pid,
        pipeline_name=NAME.get(pid, ""),
        operator_code=OPER.get(pid, ""),
        pipeline_category=CAT.get(pid, ""),
        status=STAT.get(pid, ""),
        segment_order=int(s.seq_from),
        from_node_id=s.from_node_id, from_node_name=s.from_node_name,
        to_node_id=s.to_node_id,     to_node_name=s.to_node_name,
        from_node_class=CLASS.get(s.from_node_id, ""),
        to_node_class=CLASS.get(s.to_node_id, ""),
        directed="FALSE",
        direction_note="order as printed in the pipeline name; the register "
                       "states no flow direction, and several of these lines "
                       "reverse in operation",
        sequence_is_traversal="FALSE" if pid in NON_TRAVERSAL else "TRUE",
        traversal_note=NON_TRAVERSAL.get(pid, ""),
        geometry_available="TRUE" if drawable else "FALSE",
        length_km=s.straight_line_km if drawable else "NA",
        length_method=("geodesic between two gazetteer settlement centroids, "
                       "WGS 84 ellipsoid; NOT the routed length")
                      if drawable else "NA",
        edge_status=s.segment_status,
        gap_reason="" if drawable else
                   f"no coordinate for {s.from_node_name if s.from_status!='resolved' else ''}"
                   f"{' and ' if s.from_status!='resolved' and s.to_status!='resolved' else ''}"
                   f"{s.to_node_name if s.to_status!='resolved' else ''}".strip(),
        edge_source="pipeline name, PNGRB register 20251231_NGPL.pdf",
        provenance_category="A (topology) + B (length)"))

e = pd.DataFrame(rows)
os.makedirs(DP, exist_ok=True)
e.to_csv(os.path.join(DP, "pipeline_edges.csv"), index=False)

# ------------------------------------------------------------------ report
n_lin = int((topo.in_graph_v1.str.lower() == "true").sum())
print(f"pipeline_edges.csv          {len(e)} edges across "
      f"{e.pipeline_id.nunique()} of {n_lin} linear pipelines")
print(f"  with geometry             {int((e.geometry_available=='TRUE').sum())}")
print(f"  without geometry (gaps)   {int((e.geometry_available=='FALSE').sum())}  "
      f"-- published, not dropped")
print(f"  not a traversal           {int((e.sequence_is_traversal=='FALSE').sum())} edges "
      f"on {e[e.sequence_is_traversal=='FALSE'].pipeline_id.nunique()} pipelines")

deg = pd.concat([e.from_node_id, e.to_node_id]).value_counts()
NM = dict(zip(nodes.node_id, nodes.node_name))
print(f"\nNODE DEGREE  ({len(deg)} of {len(nodes)} nodes appear in an edge)")
print("  the busiest points in the network:")
for nid, d in deg.head(8).items():
    print(f"    {nid}  {NM.get(nid,''):14s} degree {d}")
iso = sorted(set(nodes.node_id) - set(deg.index))
if iso:
    print(f"  nodes in NO edge: {len(iso)} -> {[NM.get(x,x) for x in iso]}")
else:
    print("  every node appears in at least one edge")

# TWO component counts, because reporting only one would mislead in opposite
# directions. Counting over drawable edges alone makes the network look more
# fragmented than the register says it is -- the pipeline exists, we just cannot
# draw it. Counting over all stated edges makes it look better mapped than it is.
# The difference between the two IS the cost of the unlocated nodes, and it is
# the number worth publishing.
from collections import Counter
def components(rows_iter):
    par = {n: n for n in nodes.node_id}
    def find(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for a, b in rows_iter:
        ra, rb = find(a), find(b)
        if ra != rb: par[ra] = rb
    return par, find

def ncomp(sub):
    par, find = components(zip(sub.from_node_id, sub.to_node_id))
    return Counter(find(n) for n in deg.index), find

drawn_c, drawn_find = ncomp(e[e.geometry_available == "TRUE"])
all_c,   all_find   = ncomp(e)

print("\nCONNECTED COMPONENTS  (undirected)")
print(f"  over edges we can DRAW      {len(drawn_c):2d} components")
print(f"  over edges the register STATES {len(all_c):2d} components")
print(f"  difference                  {len(drawn_c)-len(all_c):2d}  <-- the cost of the "
      f"unlocated nodes")
print("  The register's topology is the truthful one. The drawable count is an "
      "artefact\n  of missing coordinates and must never be reported as network "
      "fragmentation.")
for label, cc, fn in [("stated", all_c, all_find), ("drawable", drawn_c, drawn_find)]:
    print(f"  largest components, {label}:")
    for root, size in cc.most_common(3):
        members = sorted(NM.get(n, n) for n in deg.index if fn(n) == root)
        print(f"    size {size:2d}: {', '.join(members[:8])}{' ...' if size>8 else ''}")

# How much of that is one node? Answer it, do not leave it as an impression.
print("\nCOST OF EACH UNLOCATED NODE  (components that merge if it is located)")
unloc = sorted({n for n in
                list(e[e.geometry_available=="FALSE"].from_node_name) +
                list(e[e.geometry_available=="FALSE"].to_node_name)}
               & set(nodes[nodes.coordinate_status!="resolved"].node_name))
for nm in unloc:
    sub = e[(e.geometry_available == "TRUE") |
            ((e.from_node_name == nm) | (e.to_node_name == nm))]
    c2, _ = ncomp(sub)
    print(f"  {nm:14s} degree {int(deg.get(nodes.loc[nodes.node_name==nm,'node_id'].iloc[0],0)):d}"
          f"   components {len(drawn_c)} -> {len(c2)}   "
          f"({len(drawn_c)-len(c2)} merge)")

print("\nGAPPED EDGES  (real connections we cannot draw)")
for _, r in e[e.geometry_available == "FALSE"].iterrows():
    print(f"  {r.edge_id}  {r.pipeline_id:12s} {r.from_node_name} -> {r.to_node_name:16s} "
          f"({r.gap_reason})")
print("\nNEXT: python 13_validate_tables.py")
