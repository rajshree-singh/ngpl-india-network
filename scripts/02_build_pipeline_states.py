# -*- coding: utf-8 -*-
"""
02_build_pipeline_states.py  --  STEP 7a.

Writes:
  data_processed/pipeline_states.csv          one row per (pipeline, state). Category A.
  data_processed/pipeline_state_coverage.csv  does the named route reach every state
                                              the register says the pipeline crosses?

WHY TWO FILES AND NOT ONE
  pipeline_states.csv is pure Category A: it only splits the register's own
  "States Covered" cell into one row per state. Nothing is computed from it.
  pipeline_state_coverage.csv is Category C: it COMPARES that Category-A fact
  against where the pipeline's named route points actually are. Mixing the two
  would put a derived judgement inside a source-derived table, which is the
  defect that removed `n_states_verbatim` from the master table.

THE COMPARISON, AND WHY IT IS WORTH MAKING
  The register states a pipeline's route points only in its NAME, and states the
  states it crosses in a separate column. Those two facts must agree. Where they
  do not -- where the register lists a state that the named points cannot reach --
  the register is telling us, using nothing but itself, that the name is
  incomplete. That is a source-internal check: a reviewer can verify it from the
  public PDF without running any code and without trusting any outside source.

  Example: 5.08 is named "Ennore-Tuticorin". Both are in Tamil Nadu. The register
  also records Karnataka, Andhra Pradesh and Puducherry. A route between two
  Tamil Nadu towns cannot enter those states.

THE FALSE POSITIVE THIS SCRIPT MUST NOT PRODUCE
  A state can also look unreachable simply because one of the pipeline's nodes
  has no coordinate yet. 17.03 appears to miss Madhya Pradesh only because
  Vijaipur is unresolved -- and Vijaipur is IN Madhya Pradesh. Reporting that as
  a finding would be presenting our own missing data as a discovery.
  So a pipeline with ANY unresolved node is verdict `inconclusive_unresolved_node`
  and is never counted among the findings. Only pipelines whose every node is
  located can return `incomplete_route_points_unnamed`.
"""
import os
import pandas as pd

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON, require, normalise_states

DP = os.path.join(ROOT, "data_processed")

m     = pd.read_csv(require("data_processed/pipeline_master.csv"),
                    keep_default_na=False, na_values=[], dtype=str)
topo  = pd.read_csv(require("data_processed/pipeline_topology.csv"),
                    keep_default_na=False, na_values=[], dtype=str)
cand  = pd.read_csv(require("data_processed/node_candidates.csv"),
                    keep_default_na=False, na_values=[], dtype=str)
nodes = pd.read_csv(require("data_processed/pipeline_nodes.csv"),
                    keep_default_na=False, na_values=[], dtype=str)

TRUE = {"true", "TRUE", "True", "1"}

# =============================================================== 1. long table
rows = []
for _, r in m.iterrows():
    verbatim = r.states_covered_verbatim
    states = sorted(normalise_states(verbatim))
    if not states:
        # Never silently drop a pipeline. A pipeline with no states recorded gets
        # one row saying so, so that a count over this table still covers all 99.
        rows.append(dict(pipeline_id=r.pipeline_id, pipeline_name=r.pipeline_name,
                         pipeline_category=r.pipeline_category, status=r.status,
                         in_graph_scope=r.in_graph_scope, state_ut="NOT_STATED",
                         states_covered_verbatim=verbatim,
                         state_source="PNGRB register, States Covered column",
                         normalisation_note="register records no state for this row",
                         provenance_category="A"))
        continue
    for st in states:
        note = ""
        if st not in verbatim:
            note = ("canonical form; register prints it differently in the "
                    "verbatim cell (abbreviation, '&', 'UT of', or an older name)")
        rows.append(dict(pipeline_id=r.pipeline_id, pipeline_name=r.pipeline_name,
                         pipeline_category=r.pipeline_category, status=r.status,
                         in_graph_scope=r.in_graph_scope, state_ut=st,
                         states_covered_verbatim=verbatim,
                         state_source="PNGRB register, States Covered column",
                         normalisation_note=note, provenance_category="A"))
states_df = pd.DataFrame(rows)

# =========================================================== 2. coverage table
NODE_STATE, UNRESOLVED = {}, set()
for _, r in nodes.iterrows():
    nm = str(r.node_name).strip()
    if str(r.coordinate_status).strip() == "resolved":
        NODE_STATE[nm] = str(r.state_ut).strip()
    else:
        UNRESOLVED.add(nm)

cov = []
for _, t in topo.iterrows():
    pid = t.pipeline_id
    reg = sorted(normalise_states(
        m.loc[m.pipeline_id == pid, "states_covered_verbatim"].iloc[0]))
    if str(t.in_graph_v1) not in TRUE:          # areal: no route, nothing to compare
        cov.append(dict(pipeline_id=pid, pipeline_name=t.pipeline_name,
                        topology_class="areal",
                        n_states_register=len(reg), n_states_reached="NA",
                        states_register="; ".join(reg), states_reached="NA",
                        states_not_reached="NA", n_nodes=0, n_nodes_unresolved=0,
                        all_nodes_located="NA",
                        coverage_verdict="not_applicable_areal",
                        evidence_note="the register names a service area, not a "
                                      "route, so there are no named route points "
                                      "to compare against",
                        provenance_category="C"))
        continue

    names = [str(x).strip() for x in cand[cand.pipeline_id == pid].node_name]
    unres = [n for n in names if n in UNRESOLVED]
    reached = sorted({NODE_STATE[n] for n in names if n in NODE_STATE})
    missing = sorted(set(reg) - set(reached))

    if not missing:
        verdict = "complete"
        note = ("every state the register records is entered by at least one "
                "named route point")
    elif unres:
        verdict = "inconclusive_unresolved_node"
        note = (f"cannot be judged: {len(unres)} node(s) have no coordinate "
                f"({', '.join(unres)}), so a state they would account for is "
                f"indistinguishable from a state the name omits. NOT counted as "
                f"a finding.")
    else:
        verdict = "incomplete_route_points_unnamed"
        note = (f"every named point is located, yet the register records "
                f"{len(missing)} state(s) none of them enters "
                f"({', '.join(missing)}). The register therefore states, using "
                f"only itself, that this pipeline has route points its name does "
                f"not give. Verifiable against the public PDF without code.")

    cov.append(dict(pipeline_id=pid, pipeline_name=t.pipeline_name,
                    topology_class="linear",
                    n_states_register=len(reg), n_states_reached=len(reached),
                    states_register="; ".join(reg),
                    states_reached="; ".join(reached) if reached else "NONE",
                    states_not_reached="; ".join(missing) if missing else "NONE",
                    n_nodes=len(names), n_nodes_unresolved=len(unres),
                    all_nodes_located=str(not unres),
                    coverage_verdict=verdict, evidence_note=note,
                    provenance_category="C"))
cov_df = pd.DataFrame(cov)

os.makedirs(DP, exist_ok=True)
states_df.to_csv(os.path.join(DP, "pipeline_states.csv"), index=False)
cov_df.to_csv(os.path.join(DP, "pipeline_state_coverage.csv"), index=False)

# ------------------------------------------------------------------- report
print(f"pipeline_states.csv           {len(states_df)} rows "
      f"({states_df.pipeline_id.nunique()} pipelines x their states)")
print(f"                              {states_df.state_ut.nunique()} distinct states/UTs")
ns = states_df[states_df.state_ut != "NOT_STATED"].groupby("pipeline_id").size()
print(f"                              states per pipeline: min {ns.min()}, "
      f"max {ns.max()}, total pipeline-state pairs {int(ns.sum())}")
print(f"\npipeline_state_coverage.csv   {len(cov_df)} rows")
for k, v in cov_df.coverage_verdict.value_counts().items():
    print(f"  {k:36s} {v}")

found = cov_df[cov_df.coverage_verdict == "incomplete_route_points_unnamed"]
print(f"\nFINDING -- the register's own two columns disagree for {len(found)} pipelines")
print("  (every node located, yet states recorded that no named point enters)")
for _, r in found.sort_values("states_not_reached",
                              key=lambda s: s.str.count(";"), ascending=False).iterrows():
    print(f"  {r.pipeline_id:12s} {r.pipeline_name[:42]:42s} -> {r.states_not_reached}")

inc = cov_df[cov_df.coverage_verdict == "inconclusive_unresolved_node"]
print(f"\nNOT COUNTED -- {len(inc)} pipelines cannot be judged, a node is unlocated")
for _, r in inc.iterrows():
    print(f"  {r.pipeline_id:12s} {r.n_nodes_unresolved} unlocated node(s); "
          f"apparent gap {r.states_not_reached}")
print("\nNEXT: python 08_build_offtakes.py")
