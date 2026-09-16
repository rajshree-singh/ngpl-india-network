# -*- coding: utf-8 -*-
"""10_validate_master.py  --  gate for STEP 1.

A run is a valid gate only if every check passes AND no group is skipped.
Groups 6 and 7 are the only ones that verify the master against a source
independent of itself; without them this proves internal consistency only.
"""
import pandas as pd, numpy as np, os, re, sys
# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
m = pd.read_csv(os.path.join(ROOT,"data_processed","pipeline_master.csv"))
ok=[]; skipped=[]
def check(label, cond, detail=""):
    ok.append(bool(cond)); print(f"{'PASS' if cond else 'FAIL'}  {label}  {detail}")
def skip(group, reason, fix):
    skipped.append((group, reason, fix)); print(f"SKIP  {group}  --  {reason}")

# --- 1. shape & keys
check("99 rows", len(m)==99, f"got {len(m)}")
check("pipeline_id unique", m.pipeline_id.is_unique)
check("no whitespace/case drift in ids", (m.pipeline_id==m.pipeline_id.str.strip()).all()
      and m.pipeline_id.str.endswith(".NGPL").all())
check("37 in graph scope", int(m.in_graph_scope.sum())==37, f"got {int(m.in_graph_scope.sum())}")
check("scope == Common Carrier exactly",
      set(m[m.in_graph_scope].pipeline_category)=={"Common Carrier"} and
      m[m.pipeline_category=="Common Carrier"].in_graph_scope.all())
# 21.17.NGPL carries a 21.xx (tie-in) prefix but sits in the p.14 Common Carrier
# table, so the count of 37 once rested on an inference from the p.1 total.
# RESOLVED 2026-09-04: the PNGRB release of 2 December 2022
# (https://www.pngrb.gov.in/data-bank/NGPL-02122022.pdf) lists this pipeline under
# the explicit heading "Under Construction Common Carrier Natural Gas Pipelines".
# The classification is now stated by the source. The pair of checks below keeps
# it that way: the first fails if any OTHER tie-in-prefixed ID enters Common
# Carrier, the second fails if the citation is ever dropped from the notes.
check("21.17 is the only tie-in-prefixed ID inside Common Carrier",
      set(m[(m.pipeline_category=="Common Carrier") &
            m.pipeline_id.str.startswith("21.")].pipeline_id)=={"21.17.NGPL"})
check("21.17's Common Carrier classification cites a source, not an inference",
      "VERIFIED" in str(m.loc[m.pipeline_id=="21.17.NGPL","notes"].iloc[0]))

# --- 2. PDF page-1 category totals  (the closure proof)
tot = m.groupby("pipeline_category").authorized_length_km.sum()
check("Common Carrier = 32,702 km", abs(tot["Common Carrier"]-32702)<=1, f"{tot['Common Carrier']:.1f}")
check("Tie-in         =    792 km", abs(tot["Tie-in"]-792)<=1,          f"{tot['Tie-in']:.2f}")
check("Dedicated      =    779 km", abs(tot["Dedicated"]-779)<=1,       f"{tot['Dedicated']:.3f}")
check("grand total    = 34,273 km", abs(m.authorized_length_km.sum()-34273)<=2,
      f"{m.authorized_length_km.sum():.2f}")

# --- 3. per-table subtotals printed in the PDF
SUB = {"T1_p3_4_Op_CC":(15454.2,15978), "T2_p5_Op_TieIn":(284.4,290.85),
       "T3_p6_8_Op_Ded":(658,653), "T4_p19_UC_CC":(15713,9947),
       "T5_p14_UC_CC_S42":(1535,None), "T6_p15_UC_TieIn":(507.91,None),
       "T7_p16_UC_Ded":(121.6,None)}
for t,(a,o) in SUB.items():
    s=m[m.pdf_table==t]
    check(f"{t} authorized subtotal", abs(s.authorized_length_km.sum()-a)<=1.0,
          f"{s.authorized_length_km.sum():.2f} vs {a}")
    if o is not None:
        check(f"{t} operating subtotal", abs(s.operating_length_km.sum()-o)<=1.0,
              f"{s.operating_length_km.sum():.2f} vs {o}")
check("UC CC under-construction subtotal = 5,766",
      abs(m[m.pdf_table=="T4_p19_UC_CC"].under_construction_km.sum()-5766)<=1)

# --- 4. no fabricated values
check("17.11 lengths are NA",
      m.loc[m.pipeline_id=="17.11.NGPL",["authorized_length_km","operating_length_km","capacity_mmscmd"]].isna().all().all())
check("operational rows have NA (not 0) under_construction_km",
      m.loc[m.status=="Operational","under_construction_km"].isna().all())
check("p14/p15/p16 rows have NA operating_length_km",
      m.loc[m.pdf_table.isin(["T5_p14_UC_CC_S42","T6_p15_UC_TieIn","T7_p16_UC_Ded"]),
            "operating_length_km"].isna().all())
check("no zero-filled lengths", not ((m.authorized_length_km==0) & m.authorized_length_km.notna()).any())
# A note must SPECIFICALLY explain the NA. Merely being non-empty is not enough:
# most rows carry a generic operator-glossary note, which would make a
# "notes is non-empty" test pass for the wrong reason.
KEYS = ("reported jointly", "no operating/under-construction split",
        "two values", "NA rather than")
narows = m[m[["authorized_length_km","operating_length_km","capacity_mmscmd"]].isna().any(axis=1)]
unexplained = narows[~narows.notes.fillna("").str.contains("|".join(KEYS), case=False)]
check("every length/capacity NA carries a SPECIFIC explanation", len(unexplained)==0,
      "" if len(unexplained)==0 else list(unexplained.pipeline_id))
check("the one true zero (17.18 operating length) is labelled as measured, not missing",
      "TRUE measured zero" in str(m.loc[m.pipeline_id=="17.18.NGPL","notes"].iloc[0]))
check("no derived/Category-C column present in this Category-A table",
      not any(c.startswith(("n_","pct_","score","norm")) for c in m.columns),
      f"{[c for c in m.columns if c.startswith(('n_','pct_','score','norm'))]}")
check("19.28 capacity kept verbatim",
      m.loc[m.pipeline_id=="19.28.NGPL","capacity_verbatim"].iloc[0]=="0.075 / 0.108")

# --- 5. provenance completeness
check("every row cites a pdf_table", m.pdf_table.notna().all() and m.pdf_table.str.len().gt(0).all())
check("pdf_row unique within each pdf_table", not m.duplicated(["pdf_table","pdf_row"]).any())
check("dates parse to ISO", m.authorization_date.str.match(r"^\d{4}-\d{2}-\d{2}$").all())
check("no operator_name silently invented",
      m.loc[m.operator_name.isna(),"operator_code"].isin(["GAIL","GTIL","PEPL"]).all())

# --- 6. independent cross-check against the earlier hand transcription
#     Expected known delta: the prior transcription omitted the two PDF rows
#     marked "*" (latest data not submitted/available). Their omission is provably
#     wrong -- without them the p.6-8 subtotal is 633.7, not the printed 658.
# Accept the file under any of the names it plausibly has. It is YOUR earlier
# transcription of the PDF's operational tables -- in the original project
# folder it is called "PDF Data.xlsx". No renaming required.
CANDIDATES = [
    ("data_raw","legacy_v0","pdf_tables_operational.xlsx"),
    ("data_raw","legacy_v0","PDF Data.xlsx"),
    ("data_raw","PDF Data.xlsx"),
    ("data_raw","external","PDF Data.xlsx"),
    ("PDF Data.xlsx",),
]
xp = next((os.path.join(ROOT,*c) for c in CANDIDATES
           if os.path.exists(os.path.join(ROOT,*c))), None)
if xp:
    print(f"      cross-check source: {os.path.relpath(xp, ROOT)}")
    prior = pd.read_excel(xp, sheet_name=None, header=1)
    fr=[]
    for sh,df in prior.items():
        if len(df.columns) < 8: continue
        d = df.iloc[:,[1,5,7]].copy(); d.columns=["pipeline_id","auth","oper"]
        d["pipeline_id"]=d.pipeline_id.astype(str).str.strip()
        fr.append(d[d.pipeline_id.str.endswith(".NGPL")])
    p=pd.concat(fr)
    p["auth"]=pd.to_numeric(p.auth,errors="coerce"); p["oper"]=pd.to_numeric(p.oper,errors="coerce")
    mine=set(m[m.status=="Operational"].pipeline_id)
    check("cross-check: prior transcription is a subset of ours",
          set(p.pipeline_id) <= mine, f"only in prior: {sorted(set(p.pipeline_id)-mine)}")
    check("cross-check: the only rows prior omitted are the two '*' rows",
          mine - set(p.pipeline_id) == {"19.35.NGPL","19.36.NGPL"},
          f"delta {sorted(mine-set(p.pipeline_id))}")
    j = m.merge(p, on="pipeline_id", how="inner")
    for col,pc in [("authorized_length_km","auth"),("operating_length_km","oper")]:
        bad = j[(j[col]-j[pc]).abs() > 0.001]
        check(f"cross-check: {col} agrees on all {len(j)} shared rows", len(bad)==0,
              "" if len(bad)==0 else bad[["pipeline_id",col,pc]].to_string(index=False))
else:
    skip("group 6: independent cross-check (4 checks)",
         "your earlier transcription of the PDF tables was not found",
         "put 'PDF Data.xlsx' (from the original GAIL Project folder) into "
         "data_raw/legacy_v0/ -- any of these names works: " +
         ", ".join("/".join(c) for c in CANDIDATES))

# --- 7. verify against the PDF text directly, ROW BY ROW.
#     Subtotals only prove the LENGTH columns; capacity, date and operator have
#     no subtotal anywhere in the PDF. A "value occurs somewhere in the document"
#     test is far too weak -- mutation testing showed it accepts a changed
#     capacity (86 occurs inside other numbers) and a swapped operator (GAIL
#     occurs on neighbouring rows). Each value is therefore checked inside its
#     OWN row span, and the operator inside its own table cell.
#
#     Two traps, both found by testing and both handled below:
#       (a) collapsing whitespace glues the S. No. onto a single-digit ID:
#           "1  5.01.NGPL" -> "15.01.NGPL". So spans are located by searching for
#           each KNOWN id, never by regex-discovering ids.
#       (b) "first operator code in the span" is wrong, because many pipeline
#           NAMES begin "ONGC's ...". The entity cell sits immediately before the
#           authorization date, so that is where it is checked.
pdfp = os.path.join(ROOT,"data_raw","20251231_NGPL.pdf")
try:
    import pypdf, warnings; warnings.filterwarnings("ignore")
    txt   = "".join((p.extract_text() or "") for p in pypdf.PdfReader(pdfp).pages)
    tight = re.sub(r"\s+","",txt)
    T     = lambda x: re.sub(r"\s+","",str(x))

    pos=[]                                   # (offset, id) for every known id
    for pid in m.pipeline_id:
        i = tight.find(T(pid))
        while i != -1:
            pos.append((i, pid)); i = tight.find(T(pid), i+1)
    pos.sort()
    span={}
    for k,(off,pid) in enumerate(pos):
        if pid in span: continue
        end = pos[k+1][0] if k+1 < len(pos) else len(tight)
        span[pid] = tight[off+len(T(pid)) : min(end, off+500)]

    check("every pipeline_id occurs in the PDF text",
          set(m.pipeline_id) <= set(span), str(sorted(set(m.pipeline_id)-set(span))[:6]))

    bad=[r.pipeline_id for _,r in m.iterrows()
         if r.pipeline_id in span
         and T(pd.to_datetime(r.authorization_date).strftime("%d.%m.%Y")) not in span[r.pipeline_id]]
    check("every authorization_date occurs inside its own row span", len(bad)==0, str(bad[:8]))

    bad=[]
    for _,r in m.iterrows():
        if pd.isna(r.capacity_mmscmd) or r.pipeline_id not in span: continue
        c, w = r.capacity_mmscmd, span[r.pipeline_id]
        if not any(T(f) in w for f in (f"{c:g}",f"{c:.1f}",f"{c:.2f}",f"{c:.3f}")):
            bad.append((r.pipeline_id, c))
    check("every capacity occurs inside its own row span", len(bad)==0, str(bad[:8]))

    # entity cell = the text immediately preceding the authorization date
    # The PDF has exactly two merged entity cells. Both are exempted here and
    # both must carry a note saying the value is inherited, not printed.
    EXEMPT = {"17.11.NGPL",   # entity cell merged with 17.03
              "19.38.NGPL"}   # entity cell merged with 19.37
    bad=[]
    for _,r in m.iterrows():
        if r.pipeline_id in EXEMPT or r.pipeline_id not in span: continue
        w = span[r.pipeline_id]
        d = T(pd.to_datetime(r.authorization_date).strftime("%d.%m.%Y"))
        j = w.find(d)
        if j == -1 or not w[max(0,j-12):j].lower().endswith(T(r.operator_code).lower()):
            bad.append((r.pipeline_id, r.operator_code, w[max(0,j-12):j] if j>=0 else "no date"))
    check("operator_code sits in the entity cell before its own date",
          len(bad)==0, str(bad[:8]))
    check("both merged entity cells are documented as inherited",
          EXEMPT == {"17.11.NGPL","19.38.NGPL"} and all(
              "merged" in str(m.loc[m.pipeline_id==p,"notes"].iloc[0]).lower() for p in EXEMPT))
except ImportError:
    skip("group 7: PDF row-span verification (5 checks)", "pypdf not installed",
         "pip install pypdf")
except FileNotFoundError:
    skip("group 7: PDF row-span verification (5 checks)", f"{pdfp} not present",
         "put 20251231_NGPL.pdf in data_raw/")

# ---------------------------------------------------------------------------
# Summary. A skipped group is NOT a pass. Groups 6 and 7 are the only ones that
# verify the data against a source independent of the file being checked --
# they are what catch a silently altered capacity, a swapped operator, or a
# length swap between two pipelines that preserves the subtotal. Reporting
# "ALL CHECKS PASSED" while they were skipped would be the same mistake this
# validator exists to prevent.
n_fail = ok.count(False)
print()
if skipped:
    print(f"{len(ok)-n_fail} passed, {n_fail} failed, {len(skipped)} GROUP(S) SKIPPED")
    for g,r,f in skipped:
        print(f"  skipped  {g}\n           reason: {r}\n           fix:    {f}")
    print("\nINCOMPLETE -- not a valid STEP 1 gate until the skipped groups run.")
elif n_fail:
    print(f"{n_fail} CHECK(S) FAILED")
else:
    print("ALL CHECKS PASSED -- valid STEP 1 gate (no groups skipped)")

status = 0 if (n_fail == 0 and not skipped) else 1
# Notebook-safe: sys.exit() inside a Jupyter/Colab cell raises SystemExit and
# prints a spurious traceback. Only exit when run as a real script.
if "get_ipython" in dir(__builtins__) or "IPython" in sys.modules:
    print(f"\n(exit status would be {status})")
else:
    sys.exit(status)
