# -*- coding: utf-8 -*-
"""
16_missing_node_sensitivity.py  --  how much does a criticality ranking change
                                     when ONE node's location is missing?

Writes:
  data_processed/node_missingness_sensitivity.csv   one row per node
  data_processed/ranking_agreement.csv              stated vs drawable, summary

EVERYTHING HERE IS CATEGORY C.

THE QUESTION
  In this dataset five route points have no coordinate, and on the mappable
  graph their edges are absent. Vijaipur is one of them, and it happens to be
  the third most central node. Is that bad luck, or is it the kind of node
  that data gaps tend to hit hardest? And how badly does ANY one missing
  location distort a betweenness ranking?

THE EXPERIMENT (one line per node)
  Start from G_stated (all 47 edges). For each node v in turn, remove the edges
  incident to v but keep v as an isolated node -- exactly what a missing
  coordinate does to G_drawable. Recompute betweenness on the other 55 nodes and
  compare with the ranking on G_stated:
     spearman_rho       rank correlation over the 55 remaining nodes
     kendall_tau_b      same, less sensitive to ties
     top5_retained      of the 5 most central remaining nodes in G_stated,
                        how many are still in the top 5
     betweenness_mass_lost   1 - (sum of the other nodes' betweenness after)
                        / (sum before). Rank correlation measures ORDER only:
                        a gap that splits the network can cut every score
                        by the same factor and leave the order intact
                        (Dahej does exactly this). This column measures the
                        size of the change, which the ranks cannot see.
  Low rho / low top-5 retention means: losing this node's location would most
  distort any criticality ranking built from the mappable data.

WHY BETWEENNESS
  It is the measure most used to rank infrastructure nodes, and the one that
  moved most in this dataset. Same normalisation as 14_build_vulnerability.py
  (undirected, 2/((n-1)(n-2))). Computed here with NetworkX, whose agreement
  with the hand implementation is checked in 15_validate_vulnerability.py.
"""
import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngpl_paths import DP, require
import networkx as nx
from scipy.stats import spearmanr, kendalltau

require("data_processed/pipeline_edges.csv", "data_processed/pipeline_nodes.csv")

def read(name):
    with open(os.path.join(DP, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))          # everything stays text; NA stays "NA"

nodes = read("pipeline_nodes.csv")
edges = read("pipeline_edges.csv")
name = {n["node_id"]: n["node_name"] for n in nodes}
status = {n["node_id"]: n["coordinate_status"] for n in nodes}
N = sorted(name)

def graph(edge_rows, drop=None):
    G = nx.Graph(); G.add_nodes_from(N)
    for e in edge_rows:
        a, b = e["from_node_id"], e["to_node_id"]
        if drop is not None and drop in (a, b):
            continue
        G.add_edge(a, b)
    return G

def bc(G):
    return nx.betweenness_centrality(G, normalized=True)

def top(b, k, exclude=()):
    keep = [(v, n) for n, v in b.items() if n not in exclude]
    keep.sort(key=lambda t: (-t[0], name[t[1]]))
    return {n for _, n in keep[:k]}

G0 = graph(edges); B0 = bc(G0)
assert G0.number_of_nodes() == 56 and G0.number_of_edges() == 47, "unexpected stated graph"

rows = []
for v in N:
    Bv = bc(graph(edges, drop=v))
    others = [n for n in N if n != v]
    x = [B0[n] for n in others]; y = [Bv[n] for n in others]
    rho = spearmanr(x, y).statistic
    tau = kendalltau(x, y, variant="b").statistic
    t0 = top(B0, 5, exclude={v}); tv = top(Bv, 5, exclude={v})
    mass = 1 - sum(y) / sum(x) if sum(x) > 0 else 0.0
    rows.append({
        "node_id": v, "node_name": name[v], "coordinate_status": status[v],
        "degree_stated": G0.degree(v),
        "betweenness_stated": f"{B0[v]:.6f}",
        "spearman_rho_if_missing": f"{rho:.4f}",
        "kendall_tau_b_if_missing": f"{tau:.4f}",
        "top5_retained_if_missing": len(t0 & tv),
        "betweenness_mass_lost_if_missing": f"{mass:.4f}",
        "provenance_category": "C",
    })
rows.sort(key=lambda r: float(r["spearman_rho_if_missing"]))
for i, r in enumerate(rows, 1):
    r["distortion_rank"] = i          # 1 = its absence distorts the ranking most

out = os.path.join(DP, "node_missingness_sensitivity.csv")
cols = ["distortion_rank","node_id","node_name","coordinate_status","degree_stated",
        "betweenness_stated","spearman_rho_if_missing","kendall_tau_b_if_missing",
        "top5_retained_if_missing","betweenness_mass_lost_if_missing","provenance_category"]
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

# ---- the ranking that actually exists: stated vs drawable -----------------
drawable = [e for e in edges if e["geometry_available"] == "TRUE"]
Bd = bc(graph(drawable))
loc = [n for n in N if status[n] == "resolved"]
def agree(ids):
    x = [B0[n] for n in ids]; y = [Bd[n] for n in ids]
    return spearmanr(x, y).statistic, kendalltau(x, y, variant="b").statistic
r_all, t_all = agree(N); r_loc, t_loc = agree(loc)
summ = [
  {"comparison":"stated vs drawable, all 56 nodes","n_nodes":56,
   "spearman_rho":f"{r_all:.4f}","kendall_tau_b":f"{t_all:.4f}",
   "top5_retained":len(top(B0,5) & top(Bd,5)),"provenance_category":"C"},
  {"comparison":"stated vs drawable, 51 located nodes","n_nodes":len(loc),
   "spearman_rho":f"{r_loc:.4f}","kendall_tau_b":f"{t_loc:.4f}",
   "top5_retained":len(top(B0,5,exclude=set(N)-set(loc)) & top(Bd,5,exclude=set(N)-set(loc))),
   "provenance_category":"C"},
]
with open(os.path.join(DP, "ranking_agreement.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)

print(f"wrote {out}  ({len(rows)} rows)")
for r in rows[:8]:
    print(f"  {r['distortion_rank']:>2}  {r['node_name']:<14} {r['coordinate_status']:<10} "
          f"deg {r['degree_stated']}  rho {r['spearman_rho_if_missing']}  "
          f"tau {r['kendall_tau_b_if_missing']}  top5 {r['top5_retained_if_missing']}/5  "
          f"mass lost {r['betweenness_mass_lost_if_missing']}")
for s in summ: print(" ", s)
