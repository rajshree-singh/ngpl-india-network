# -*- coding: utf-8 -*-
"""
13_validate_tables.py  --  validation for STEP 7 (states, coverage, offtakes, edges).

Run:
  python 13_validate_tables.py            normal validation
  python 13_validate_tables.py --mutate   self-test: corrupt the output and
                                          confirm every corruption FAILS

SKIPS ARE NOT PASSES. Any group that cannot run makes this print INCOMPLETE and
exit non-zero.

THE TWO CHECKS THAT CARRY THIS STEP

  S-12 recomputes the coverage verdict from pipeline_master, node_candidates and
  pipeline_nodes, and refuses the stored value if it disagrees. A finding that
  says "the register contradicts itself" has to be reproducible from the inputs,
  not taken on trust from the file that asserts it.

  S-14 is the FALSE-POSITIVE GUARD. A pipeline with any unlocated node must never
  carry the verdict `incomplete_route_points_unnamed`, because an unlocated node
  and an unnamed route point look identical from the outside. 17.03 appears to
  miss Madhya Pradesh only because Vijaipur has no coordinate -- and Vijaipur is
  in Madhya Pradesh. Publishing that as a finding would be presenting our own
  missing data as a discovery about the source.

  O-02 is the closure proof for the offtake table: our transcription must
  reproduce the register's own printed total of 558 km, for each of the two
  tables, to within 0.5 km. A reader can check that against the public PDF
  without running any code.
"""
import os, sys, copy
import pandas as pd

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON, normalise_states

DP = os.path.join(ROOT, "data_processed")
FAILS, SKIPS, NPASS = [], [], 0

def ok(tag, cond, msg):
    global NPASS
    if cond: NPASS += 1
    else:    FAILS.append(f"{tag}: {msg}")
def skip(group, why, fix): SKIPS.append((group, why, fix))

def _read(path):
    """Read exactly what is on disk. See 12_validate_routes.py for why
    keep_default_na=False is load-bearing and not a style choice."""
    return pd.read_csv(path, keep_default_na=False, na_values=[], dtype=str)

TRUE = {"true", "TRUE", "True", "1"}
PRINTED_TOTAL = {"Operational": 558.0, "Under Construction": 558.0}
VERDICTS = {"complete", "incomplete_route_points_unnamed",
            "inconclusive_unresolved_node", "not_applicable_areal"}


def validate(st, cov, off, edg, m, topo, cand, nodes, segs):
    global FAILS, SKIPS, NPASS
    FAILS, SKIPS, NPASS = [], [], 0

    # ================= GROUP 1: pipeline_states.csv, Category-A purity ========
    ok("S-01", set(st.pipeline_id) == set(m.pipeline_id),
       "pipeline_states does not cover exactly the master's pipelines")
    bad = [c for c in st.columns
           if c.startswith(("n_", "pct_", "score", "norm_", "count_"))]
    ok("S-02", not bad, f"derived column inside a Category-A table: {bad}")
    ok("S-03", (st.provenance_category == "A").all(),
       "a pipeline_states row is not labelled Category A")
    # recompute the split from the verbatim cell -- the file must not disagree
    VERB = dict(zip(m.pipeline_id, m.states_covered_verbatim))
    mism = []
    for pid, grp in st.groupby("pipeline_id"):
        want = normalise_states(VERB[pid]) or {"NOT_STATED"}
        got = set(grp.state_ut)
        if want != got:
            mism.append(f"{pid}: file {sorted(got)} vs recomputed {sorted(want)}")
    ok("S-04", not mism, "state split disagrees with the register's verbatim cell: "
       + "; ".join(mism[:3]))
    ok("S-05", not st.duplicated(["pipeline_id", "state_ut"]).any(),
       "duplicate (pipeline, state) row")
    ok("S-06", (st.state_ut.str.strip() != "").all(), "blank state_ut")
    ok("S-07", not st.state_ut.str.contains("&").any(),
       "an unsplit compound state name survived normalisation")
    ok("S-08", not st.state_ut.str.startswith("UT of").any(),
       "'UT of' prefix survived normalisation")

    # ================= GROUP 2: pipeline_state_coverage.csv ==================
    ok("S-09", len(cov) == len(topo),
       f"coverage has {len(cov)} rows, topology has {len(topo)}")
    ok("S-10", set(cov.pipeline_id) == set(topo.pipeline_id),
       "coverage pipeline_ids differ from topology")
    ok("S-11", set(cov.coverage_verdict) <= VERDICTS,
       f"unexpected verdict: {set(cov.coverage_verdict) - VERDICTS}")

    NODE_STATE, UNRES = {}, set()
    for _, r in nodes.iterrows():
        nm = str(r.node_name).strip()
        (NODE_STATE.__setitem__(nm, str(r.state_ut).strip())
         if str(r.coordinate_status).strip() == "resolved" else UNRES.add(nm))
    if not NODE_STATE:
        skip("2 (coverage recompute)", "no resolved nodes in pipeline_nodes.csv",
             "re-run 04_geocode_nodes.py")
    else:
        wrong, fp, leak = [], [], []
        for _, r in cov.iterrows():
            pid = r.pipeline_id
            reg = normalise_states(VERB[pid])
            linear = str(topo.loc[topo.pipeline_id == pid, "in_graph_v1"].iloc[0]) in TRUE
            if not linear:
                if r.coverage_verdict != "not_applicable_areal":
                    wrong.append(f"{pid} areal but verdict {r.coverage_verdict}")
                continue
            names = [str(x).strip() for x in cand[cand.pipeline_id == pid].node_name]
            unres = [n for n in names if n in UNRES]
            reached = {NODE_STATE[n] for n in names if n in NODE_STATE}
            missing = reg - reached
            want = ("complete" if not missing else
                    "inconclusive_unresolved_node" if unres else
                    "incomplete_route_points_unnamed")
            if r.coverage_verdict != want:
                wrong.append(f"{pid}: file '{r.coverage_verdict}' vs recomputed '{want}'")
            # the false-positive guard, stated as its own condition
            if r.coverage_verdict == "incomplete_route_points_unnamed" and unres:
                fp.append(f"{pid} ({len(unres)} unlocated: {', '.join(unres)})")
            # states_not_reached must be a subset of what the register records
            snr = set(x.strip() for x in str(r.states_not_reached).split(";")
                      if x.strip() and x.strip() != "NONE")
            if not snr <= reg:
                leak.append(f"{pid}: {sorted(snr - reg)} not in the register's list")
        ok("S-12", not wrong,
           "coverage verdict disagrees with a recompute from the inputs: "
           + "; ".join(wrong[:4]))
        ok("S-13", not leak,
           "states_not_reached contains a state the register never recorded: "
           + "; ".join(leak[:3]))
        ok("S-14", not fp,
           "FALSE POSITIVE: a pipeline with an unlocated node is reported as a "
           "finding about the register. An unlocated node and an unnamed route "
           "point are indistinguishable; this must be inconclusive. "
           + "; ".join(fp))
        ok("S-15", (cov[cov.coverage_verdict == "incomplete_route_points_unnamed"]
                    .all_nodes_located.str.lower() == "true").all(),
           "a finding row does not assert all_nodes_located")
        ok("S-16", (cov[cov.coverage_verdict == "not_applicable_areal"]
                    .n_states_reached.astype(str) == "NA").all(),
           "an areal pipeline reports a reached-state count instead of NA")
        ok("S-17", (cov.evidence_note.str.strip() != "").all(),
           "a coverage row carries no evidence note")

    # ================= GROUP 3: pipeline_offtakes.csv ========================
    km = pd.to_numeric(off.stpl_length_km, errors="coerce")
    ok("O-01", not km.isna().any(),
       f"{int(km.isna().sum())} offtake row(s) have a non-numeric length")
    closure = []
    for status, printed in PRINTED_TOTAL.items():
        got = km[off.status == status].sum()
        if abs(got - printed) > 0.5:
            closure.append(f"{status}: transcribed {got:.3f} vs printed {printed}")
    ok("O-02", not closure,
       "CLOSURE PROOF FAILED -- the transcription does not reproduce the "
       "register's own printed total: " + "; ".join(closure))
    ok("O-03", (km > 0).all(), "an offtake has a zero or negative length")
    ok("O-04", off.offtake_id.is_unique, "duplicate offtake_id")
    pages = pd.to_numeric(off.pdf_page, errors="coerce")
    ok("O-05", pages.between(9, 18).all(),
       "an offtake cites a PDF page outside the STPL tables (9-13, 17-18)")
    ok("O-06", set(off.status) == set(PRINTED_TOTAL),
       f"unexpected status values: {set(off.status) - set(PRINTED_TOTAL)}")
    # S.No coverage: no row silently lost between the PDF and the file
    for status, last in [("Operational", 73), ("Under Construction", 23)]:
        sn = set(pd.to_numeric(off[off.status == status].pdf_s_no, errors="coerce").dropna().astype(int))
        ok(f"O-07-{status[:2]}", sn == set(range(1, last + 1)),
           f"{status}: S.No coverage is not 1..{last}; missing "
           f"{sorted(set(range(1, last+1)) - sn)}")
    mapped = off[off.pipeline_id != "UNKNOWN"]
    ok("O-08", set(mapped.pipeline_id) <= set(m.pipeline_id),
       f"offtake maps to a pipeline_id not in the master: "
       f"{sorted(set(mapped.pipeline_id) - set(m.pipeline_id))}")
    OPER = dict(zip(m.pipeline_id, m.operator_code))
    badop = [f"{r.offtake_id} {r.pipeline_id} reg-entity {r.transmission_entity} "
             f"vs operator {OPER.get(r.pipeline_id)}"
             for _, r in mapped.iterrows()
             if OPER.get(r.pipeline_id) != r.transmission_entity]
    ok("O-09", not badop,
       "a mapped offtake's transmission entity disagrees with that pipeline's "
       "operator in the master: " + "; ".join(badop[:3]))
    ok("O-10", (off[off.pipeline_id == "UNKNOWN"].link_basis.str.strip() != "").all(),
       "an UNKNOWN mapping carries no reason")
    ok("O-11", (off[off.pipeline_id == "UNKNOWN"].pipeline_name_matched == "UNKNOWN").all(),
       "an UNKNOWN pipeline_id carries a matched name")
    ok("O-12", (off.ga_id.str.strip() != "").all(), "blank GA ID")
    # O-13 is what catches a tap-off silently re-pointed at the wrong trunk line.
    # pipeline_name_matched is copied from the master, so id and name must agree
    # exactly; a changed id leaves a name that no longer belongs to it.
    NAME = dict(zip(m.pipeline_id, m.pipeline_name))
    wrongname = [f"{r.offtake_id}: {r.pipeline_id} carries name "
                 f"'{r.pipeline_name_matched[:30]}' but the master says "
                 f"'{str(NAME.get(r.pipeline_id,''))[:30]}'"
                 for _, r in mapped.iterrows()
                 if r.pipeline_name_matched != NAME.get(r.pipeline_id)]
    ok("O-13", not wrongname,
       "offtake pipeline_id and pipeline_name_matched disagree with the master: "
       + "; ".join(wrongname[:3]))
    # O-14: one acronym, one pipeline. The register uses a fixed shorthand; if the
    # same shorthand mapped two ways, one of them is wrong.
    # UNKNOWN is not a competing mapping, it is the absence of one, so it is
    # excluded here. Two DIFFERENT pipeline ids for one acronym would mean one is
    # wrong; an acronym that is mapped on some rows and withheld on others is a
    # separate situation, checked by O-15.
    inc = [f"{a} -> {sorted(set(g.pipeline_id))}"
           for a, g in off.groupby("tap_from_verbatim")
           if len(set(g.pipeline_id) - {"UNKNOWN"}) > 1]
    ok("O-14", not inc, "the same tap-off acronym maps to two different pipelines: "
       + "; ".join(inc[:3]))
    # O-15: where one acronym is mapped on some rows and withheld on others, the
    # withheld row must say why. That pattern is not an error -- it is how the
    # register's own inconsistencies surface -- but an unexplained one is.
    mixed = []
    for a, g in off.groupby("tap_from_verbatim"):
        ids = set(g.pipeline_id)
        if "UNKNOWN" in ids and len(ids) > 1:
            w = g[g.pipeline_id == "UNKNOWN"]
            if not w.link_basis.str.contains("WITHHELD|UNMAPPED|NOT A TRANSMISSION",
                                             regex=True).all():
                mixed.append(f"{a}: withheld without a stated reason")
    ok("O-15", not mixed,
       "an acronym is mapped on some rows and silently unmapped on others: "
       + "; ".join(mixed[:3]))

    # ================= GROUP 4: pipeline_edges.csv ===========================
    ok("E-01", len(edg) == len(segs),
       f"edges has {len(edg)} rows, route_segments has {len(segs)}")
    ok("E-02", edg.edge_id.is_unique, "duplicate edge_id")
    ids = set(nodes.node_id)
    orph = sorted((set(edg.from_node_id) | set(edg.to_node_id)) - ids)
    ok("E-03", not orph, f"edge references a node_id not in pipeline_nodes: {orph}")
    ok("E-04", set(edg.pipeline_id) <= set(m.pipeline_id),
       "edge references a pipeline not in the master")
    key_e = set(zip(edg.pipeline_id, edg.segment_order.astype(str)))
    key_s = set(zip(segs.pipeline_id, segs.seq_from.astype(str)))
    ok("E-05", key_e == key_s,
       f"edge (pipeline, order) set differs from route_segments: "
       f"{sorted(key_e ^ key_s)[:3]}")
    gap = edg[edg.geometry_available == "FALSE"]
    ok("E-06", (gap.length_km.astype(str) == "NA").all(),
       "a gapped edge carries a length instead of NA")
    ok("E-07", (gap.gap_reason.str.strip() != "").all(),
       "a gapped edge carries no reason")
    drw = edg[edg.geometry_available == "TRUE"]
    ok("E-08", (drw.length_km.astype(str) != "NA").all(),
       "a drawable edge has length NA")
    # lengths must equal route_segments, not merely look plausible
    SEG = {(r.pipeline_id, str(r.seq_from)): r.straight_line_km for _, r in segs.iterrows()}
    dl, nonnum = [], []
    for _, r in drw.iterrows():
        a = pd.to_numeric(pd.Series([r.length_km]), errors="coerce").iloc[0]
        b = pd.to_numeric(pd.Series([SEG.get((r.pipeline_id, str(r.segment_order)))]),
                          errors="coerce").iloc[0]
        # A non-numeric length on a drawable edge is a failure, never a crash.
        if pd.isna(a) or pd.isna(b): nonnum.append(r.edge_id); continue
        if abs(a - b) > 1e-6: dl.append(r.edge_id)
    ok("E-09", not dl, f"edge length disagrees with route_segments: {dl[:3]}")
    ok("E-09b", not nonnum,
       f"a drawable edge has a non-numeric length, or none in route_segments: "
       f"{nonnum[:3]}")
    # geometry_available must follow node status, not be asserted independently
    RES = {str(r.node_name).strip(): str(r.coordinate_status).strip() == "resolved"
           for _, r in nodes.iterrows()}
    bad = [r.edge_id for _, r in edg.iterrows()
           if (RES.get(str(r.from_node_name).strip(), False) and
               RES.get(str(r.to_node_name).strip(), False))
              != (r.geometry_available == "TRUE")]
    ok("E-10", not bad,
       f"geometry_available disagrees with the endpoints' coordinate_status: {bad[:3]}")
    ok("E-11", (edg.directed.str.upper() == "FALSE").all(),
       "an edge claims a direction; the register states no flow direction")
    ok("E-12", set(edg.sequence_is_traversal) <= {"TRUE", "FALSE"},
       "sequence_is_traversal is not a clean boolean")
    nt = edg[edg.sequence_is_traversal == "FALSE"]
    ok("E-13", (nt.traversal_note.str.strip() != "").all(),
       "a non-traversal edge carries no explanation")
    ok("E-14", (edg[edg.sequence_is_traversal == "TRUE"].traversal_note.str.strip() == "").all(),
       "a traversal edge carries a non-traversal note")

    # ================= GROUP 5: cross-table integrity ========================
    ok("X-01", set(cov.pipeline_id) <= set(st.pipeline_id),
       "a coverage row names a pipeline absent from pipeline_states")
    scope = set(m[m.in_graph_scope.astype(str).isin(TRUE)].pipeline_id)
    ok("X-02", set(edg.pipeline_id) <= scope,
       "an edge belongs to a pipeline that is not in analytical scope")
    ok("X-03", set(cov.pipeline_id) <= scope,
       "a coverage row belongs to a pipeline that is not in analytical scope")
    ok("X-04", not off.empty and not edg.empty and not cov.empty and not st.empty,
       "one of the STEP 7 tables is empty")
    return len(FAILS), len(SKIPS)


# ------------------------------------------------------------------ load & run
FILES = ["pipeline_states.csv", "pipeline_state_coverage.csv", "pipeline_offtakes.csv",
         "pipeline_edges.csv", "pipeline_master.csv", "pipeline_topology.csv",
         "node_candidates.csv", "pipeline_nodes.csv", "route_segments.csv"]

def load():
    for f in FILES:
        if not os.path.exists(os.path.join(DP, f)):
            raise SystemExit(f"MISSING: {os.path.join(DP, f)}\n"
                             f"  ROOT resolved to {ROOT} (via {ROOT_REASON}).\n"
                             f"  Run 02_build_pipeline_states.py, 08_build_offtakes.py "
                             f"and 09_build_edges.py first.")
    return [_read(os.path.join(DP, f)) for f in FILES]

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
        print("\nSTEP 7 VALIDATION PASSED  -- all checks ran, all checks passed")
        return 0
    print("\nSTEP 7 VALIDATION INCOMPLETE" if ns and not nf else "\nSTEP 7 VALIDATION FAILED")
    return 1

# --- mutations: every one must FAIL ------------------------------------------
def _set(df, col, val, mask=None, n=1):
    d = df.copy()
    idx = d.index if mask is None else d.index[mask(d)]
    if len(idx): d.loc[idx[:n], col] = val
    return d

def mutate():
    st, cov, off, edg, m, topo, cand, nodes, segs = load()
    M = [
     ("offtake: shave 5 km off a length (breaks the 558 closure proof)",
      lambda: (st, cov, _set(off, "stpl_length_km", "0.001",
               lambda d: d.stpl_length_km.astype(float) > 5), edg)),
     ("offtake: delete a row (silent loss)",
      lambda: (st, cov, off.iloc[1:].copy(), edg)),
     ("offtake: map a tap-off to the wrong trunk pipeline",
      lambda: (st, cov, _set(off, "pipeline_id", "17.20.NGPL",
               lambda d: d.pipeline_id == "17.03.NGPL"), edg)),
     ("offtake: blank the reason on an UNKNOWN mapping",
      lambda: (st, cov, _set(off, "link_basis", "",
               lambda d: d.pipeline_id == "UNKNOWN"), edg)),
     ("coverage: upgrade an inconclusive pipeline to a finding (FALSE POSITIVE)",
      lambda: (st, _set(cov, "coverage_verdict", "incomplete_route_points_unnamed",
               lambda d: d.coverage_verdict == "inconclusive_unresolved_node"), off, edg)),
     ("coverage: downgrade a real finding to complete",
      lambda: (st, _set(cov, "coverage_verdict", "complete",
               lambda d: d.coverage_verdict == "incomplete_route_points_unnamed"), off, edg)),
     ("coverage: invent a missing state the register never recorded",
      lambda: (st, _set(cov, "states_not_reached", "Kerala",
               lambda d: d.coverage_verdict == "incomplete_route_points_unnamed"), off, edg)),
     ("states: drop a state from a pipeline's split",
      lambda: (st.iloc[1:].copy(), cov, off, edg)),
     ("states: leave a compound '&' name unsplit",
      lambda: (_set(st, "state_ut", "Meghalaya & Sikkim"), cov, off, edg)),
     ("edges: drop a gapped edge (silently reconnects the network)",
      lambda: (st, cov, off, edg[edg.geometry_available != "FALSE"].copy())),
     ("edges: mark a gapped edge as having geometry",
      lambda: (st, cov, off, _set(edg, "geometry_available", "TRUE",
               lambda d: d.geometry_available == "FALSE"))),
     ("edges: give a gapped edge a length instead of NA",
      lambda: (st, cov, off, _set(edg, "length_km", "0",
               lambda d: d.geometry_available == "FALSE"))),
     ("edges: inflate a drawable edge's length",
      lambda: (st, cov, off, _set(edg, "length_km", "999",
               lambda d: d.geometry_available == "TRUE"))),
     ("edges: claim a flow direction the register never states",
      lambda: (st, cov, off, _set(edg, "directed", "TRUE"))),
     ("edges: point an edge at a node that does not exist",
      lambda: (st, cov, off, _set(edg, "to_node_id", "N999"))),
    ]
    print("MUTATION SELF-TEST -- every mutation must FAIL\n")
    missed = []
    for name, fn in M:
        a, b, c, d = fn()
        nf, _ = validate(a, b, c, d, m, topo, cand, nodes, segs)
        if nf: print(f"  caught           {name}   [{FAILS[0].split(':')[0]}]")
        else:  print(f"  *** MISSED ***   {name}"); missed.append(name)
    print(f"\n{len(M)-len(missed)}/{len(M)} mutations caught")
    if missed:
        print("NOT CAUGHT -- the validator is not yet trustworthy:")
        for x in missed: print("   " + x)
        return 1
    print("Mutation self-test passed.")
    return 0


if __name__ == "__main__":
    if "--mutate" in sys.argv:
        rc = mutate()
    else:
        dfs = load()
        nf, ns = validate(*dfs)
        rc = report(nf, ns, NPASS)
    try:
        get_ipython(); print(f"\n[exit status {rc}]")
    except NameError:
        sys.exit(rc)
