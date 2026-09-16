# -*- coding: utf-8 -*-
"""
03_build_node_candidates.py   --  STEP 2a of the NGPL dataset build.

Writes:
  data_processed/pipeline_topology.csv        one row per in-scope pipeline
  data_processed/node_candidates.csv          one row per (pipeline, ordered waypoint)
  data_processed/unsourced_locations.csv      names used earlier that the PDF does NOT support

PROVENANCE RULE (the whole point of this step)
  The ONLY place the PNGRB register states route points is a pipeline's own NAME.
  "Kochi-Koottanad-Bangalore-Mangalore" is the source stating that this pipeline
  runs Kochi -> Koottanad -> Bangalore -> Mangalore, in that order. Nothing else
  in the PDF gives a route point for a Common Carrier pipeline.
  Therefore every node here is Category A, cited to pipeline_name, and the
  sequence is source-derived too -- which also gives edge ordering for STEP 3.

  This script deliberately produces NO coordinates. Coordinate sourcing is STEP 2b
  and uses a citable gazetteer. Nothing is geocoded by guesswork here.
"""
import pandas as pd, numpy as np, os, re

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
DP   = os.path.join(ROOT, "data_processed")
m    = pd.read_csv(os.path.join(DP, "pipeline_master.csv"))

# ---------------------------------------------------------------------------
# 1. AREAL vs LINEAR.
#    An areal pipeline is a regional / basin / grid network: the register names
#    a service area, not a route. It has no endpoints even in principle, so it
#    cannot be given nodes without inventing them. Listed explicitly rather than
#    inferred, because a keyword rule on "Network|Grid" is a judgement that
#    should be visible and auditable, not buried in a regex.
AREAL = {
 "17.01.NGPL":"Assam Regional Network -- service area, no route stated",
 "17.02.NGPL":"Cauvery Basin Network -- basin network, no route stated",
 "17.06.NGPL":"KG Basin Network -- basin network, no route stated",
 "17.07.NGPL":"Gujarat Regional Network -- service area, no route stated",
 "17.08.NGPL":"Agartala Regional Network -- service area, no route stated",
 "17.13.NGPL":"Mumbai Regional Network -- service area, no route stated",
 "17.17.NGPL":"Assam Regional Network (AGCL) -- service area, no route stated",
 "18.01.NGPL":"High Pressure Gujarat Gas Grid -- state-wide grid, no route stated",
 "18.03.NGPL":"Low Pressure Gujarat Gas Grid -- state-wide grid, no route stated",
 "42.01.NGPL":"North-East Natural Gas Pipeline Grid -- multi-state grid, no route stated",
}

# ---------------------------------------------------------------------------
# 2. Waypoint sequence per linear pipeline, transcribed from the pipeline NAME.
#    Given explicitly instead of regex-split, because the register's names carry
#    four separate irregularities that no splitter handles correctly. Each is
#    recorded in NAME_NOTE below so a reviewer can see the reading applied.
WAYPOINTS = {
 "17.03.NGPL": ["Hazira","Vijaipur","Jagdishpur","Dahej"],
 "17.11.NGPL": ["Dahej","Vijaipur","Dadri"],
 "17.04.NGPL": ["Kakinada","Hyderabad","Uran","Ahmedabad"],
 "17.05.NGPL": ["Dahej","Uran","Panvel","Dabhol"],
 "17.10.NGPL": ["Dadri","Panipat"],
 "17.14.NGPL": ["Uran","Trombay"],
 "18.02.NGPL": ["Hazira","Ankleshwar"],
 "5.05.NGPL" : ["Shahdol","Phulpur"],
 "17.18.NGPL": ["Dukli","Maharajganj"],
 "17.19.NGPL": ["Uran","Taloja"],
 "17.09.NGPL": ["Chainsa","Jhajjar","Hissar"],
 "17.12.NGPL": ["Dadri","Bawana","Nangal"],
 "5.01.NGPL" : ["Mehsana","Bhatinda"],
 "5.02.NGPL" : ["Bhatinda","Gurdaspur"],
 "5.03.NGPL" : ["Mallavaram","Bhopal","Bhilwara","Vijaipur"],
 "17.16.NGPL": ["Dabhol","Bangalore"],
 "17.15.NGPL": ["Kochi","Koottanad","Bangalore","Mangalore"],
 "5.08.NGPL" : ["Ennore","Tuticorin"],
 "17.20.NGPL": ["Jagdishpur","Haldia","Bokaro","Dhamra","Paradip","Barauni","Guwahati"],
 "5.13.NGPL" : ["Mumbai","Nagpur","Jharsuguda"],
 "5.12.NGPL" : ["Srikakulam","Angul"],
 "5.07.NGPL" : ["Ennore","Nellore"],
 "5.10.NGPL" : ["Kakinada","Vijayawada","Nellore"],
 "5.11.NGPL" : ["Kanai Chhata","Panitar"],
 "21.17.NGPL": ["Jamnagar","Dwarka"],
 "5.14.NGPL" : ["Hazaribagh","Ranchi"],
 "5.15.NGPL" : ["Gurdaspur","Jammu"],
}
NAME_NOTE = {
 "17.03.NGPL":"Name is a merged authorization covering HVJ + GREP + DVPL/VDPL. Waypoints taken in the order printed; 'Vijaipur' appears twice in the name and is kept once. Sequence is NOT a simple path -- see topology_note.",
 "17.11.NGPL":"Name states two segments (Dahej-Vijaipur, Vijaipur-Dadri). Shares its length/capacity cell with 17.03.",
 "17.20.NGPL":"The PDF prints 'Bokaro Dhamra' with no separator between two distinct places; read as Bokaro and Dhamra. Known branching line -- order here is the printed order, not a single path.",
 "5.11.NGPL" :"RESOLVED 2026-09-04. The register prints 'Kanai - Chhata - Panitar', which reads as three waypoints; it is two. 'Kanai Chhata' is a single locality near Contai, Purba Medinipur district, West Bengal. Source: Global Energy Monitor, Kanai Chhata-Shrirampur Gas Pipeline, https://www.gem.wiki/Kanai_Chhata-Shrirampur_Gas_Pipeline -- gives the route as 'from Kanai Chhata near Contai, West Bengal to Panitar, West Bengal' at 317 km, matching the register's 317 km, and records that PNGRB amended the termination point from Shrirampur to Panitar in 2022. The register cannot settle this reading on its own; provenance for the SPLIT is therefore external and cited, while both place names remain source-derived.",
 "21.17.NGPL":"'(Gujarat)' is a state qualifier in the name, not a waypoint; dropped.",
 "18.02.NGPL":"'(HAPi)' is the pipeline's acronym, not a waypoint; dropped.",
 "17.09.NGPL":"Register spells it 'Hissar'; the same place is 'Hisar' elsewhere. Spelling kept verbatim, alias recorded in STEP 2b.",
}

NAME_SOURCE = {  # where a reading needed a source beyond the Dec-2025 name itself
 "5.11.NGPL":"pipeline_name (PNGRB register), disambiguated by PNGRB NGPL register, 2 December 2022 release (https://www.pngrb.gov.in/data-bank/NGPL-02122022.pdf)",
}

scope = m[m.in_graph_scope].copy()
assert len(scope) == 37, len(scope)

# --- topology table ---------------------------------------------------------
rows=[]
for _,r in scope.iterrows():
    pid=r.pipeline_id
    areal = pid in AREAL
    wp = WAYPOINTS.get(pid, [])
    rows.append(dict(pipeline_id=pid, pipeline_name=r.pipeline_name,
        topology_class="areal" if areal else "linear",
        n_waypoints_stated=0 if areal else len(wp),
        in_graph_v1=(not areal),
        waypoint_sequence="" if areal else " -> ".join(wp),
        waypoint_source="" if areal else "pipeline_name (PNGRB register)",
        topology_note=AREAL.get(pid, NAME_NOTE.get(pid,"")) ))
topo=pd.DataFrame(rows)

# --- node candidates --------------------------------------------------------
cand=[]
for _,r in topo[topo.in_graph_v1].iterrows():
    wp=WAYPOINTS[r.pipeline_id]
    for i,name in enumerate(wp,1):
        cand.append(dict(pipeline_id=r.pipeline_id, seq=i, node_name=name,
            role="origin" if i==1 else ("terminus" if i==len(wp) else "intermediate"),
            node_type="TBD_step2b", state_ut="TBD_step2b",
            latitude=np.nan, longitude=np.nan,
            coordinate_source="NOT_SOURCED", coordinate_method="NOT_SOURCED",
            coordinate_accuracy="NOT_SOURCED", coordinate_date="",
            name_source=NAME_SOURCE.get(r.pipeline_id,"pipeline_name (PNGRB register)"),
            provenance_category="A"))
cand=pd.DataFrame(cand)

# --- locations used in the old inventory that the PDF does NOT support -------
LEGACY = os.path.join(ROOT,"data_raw","legacy_v0","pipeline_inventory_21.csv")
uns=pd.DataFrame(columns=["location","used_by","status","action"])
if os.path.exists(LEGACY):
    old=pd.read_csv(LEGACY)
    seen={}
    for _,r in old.iterrows():
        vals=[str(r.get("Start Point","")),str(r.get("End Point",""))]
        vals+=[p.strip() for p in str(r.get("Intermediate Points","")).split(";")]
        for v in vals:
            v=v.strip()
            if v and v not in ("nan","—",""): seen.setdefault(v,set()).add(r["Pipeline ID"])
    sourced=set(cand.node_name)
    uns=pd.DataFrame([dict(location=k, used_by=",".join(sorted(v)),
                           status="UNSOURCED -- not stated as a route point anywhere in the PDF",
                           action="excluded from the graph; retained here for transparency")
                      for k,v in sorted(seen.items()) if k not in sourced])

os.makedirs(DP, exist_ok=True)
topo.to_csv(os.path.join(DP,"pipeline_topology.csv"), index=False)
cand.to_csv(os.path.join(DP,"node_candidates.csv"), index=False)
uns.to_csv(os.path.join(DP,"unsourced_locations.csv"), index=False)

print(f"pipeline_topology.csv      {len(topo)} rows  ({int(topo.in_graph_v1.sum())} linear / {int((~topo.in_graph_v1).sum())} areal)")
print(f"node_candidates.csv        {len(cand)} waypoint rows, {cand.node_name.nunique()} distinct node names")
print(f"unsourced_locations.csv    {len(uns)} locations excluded")
