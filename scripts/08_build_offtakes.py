# -*- coding: utf-8 -*-
"""
08_build_offtakes.py  --  STEP 7b.

Writes:
  data_processed/pipeline_offtakes.csv   one row per CGD tap-off from a trunk pipeline

WHAT THIS TABLE IS
  The register's STPL tables (pages 9-13 operational, 17-18 under construction)
  record, for each City Gas Distribution area, how many km of spur pipeline
  connect it and WHICH trunk pipeline it taps off. That is the only place in the
  document where the transmission network is linked to the distribution network.
  It is the demand side of the graph.

WHY IT IS A SEPARATE TABLE AND NOT EDGES
  These rows are keyed by GA ID (a Geographical Area), not by PL Unique ID. A GA
  is a licensed distribution territory, not a pipeline. Merging them into the
  edge table would put two different kinds of object in one table and would imply
  a spatial connection we cannot draw -- the register gives the spur's LENGTH but
  never its route or its tap-off point.

TRANSCRIPTION, NOT EXTRACTION
  As with the master table, the rows are literal Python data below. The source
  PDF has merged cells, multi-line area names and sub-rows where one GA taps the
  network several times; automated table extraction on it fails silently.
  Correctness is demonstrated the same way as STEP 1 -- by reproducing the
  register's own printed total of 558 km for each table. A reader can check that
  against the public PDF without running anything.

THREE THINGS THE REGISTER DOES HERE THAT A NAIVE READER WOULD GET WRONG
  1. GA IDs are NOT unique. 9.72 appears at S.No 47 and again at 59; 9.29 at 51
     and 65. Keying this table on GA ID would silently lose rows.
  2. Several tap-offs are not from a transmission pipeline at all. 98.02 draws
     from "Mora-Sachin STPL" (another spur), from a "Sunpertro Source" and from a
     "GAIL APM Source". These are recorded verbatim and flagged, not forced into
     a pipeline column.
  3. S.No 70 prints "GAIL" in the pipeline column -- an operator name where a
     pipeline name belongs. Recorded verbatim, mapped to UNKNOWN.
"""
import os
import pandas as pd

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON, require

DP = os.path.join(ROOT, "data_processed")
_m = pd.read_csv(require("data_processed/pipeline_master.csv"),
                 keep_default_na=False, na_values=[], dtype=str)
MASTER_NAME = dict(zip(_m.pipeline_id, _m.pipeline_name))
MASTER_OPER = dict(zip(_m.pipeline_id, _m.operator_code))

# (s_no, ga_id, ga_name, cgd_entity, length_km, tap_from_verbatim, tx_entity, pdf_page)
OPERATIONAL = [
 (1,"2.01","Chandigarh","IOAGPL",22.000,"DBNPL","GAIL",9),
 (2,"2.02","Allahabad","IOAGPL",17.200,"HVJ","GAIL",9),
 (3,"2.03","Jhansi","CUGL",8.45,"VAPL","GAIL",9),
 (4,"4.06","UT of Daman","IOAGPL",15.600,"DUPL-DPPL","GAIL",9),
 (5,"4.07","Amritsar District","GGL",4.8,"BGPL","GIGL",9),
 (6,"4.08","Pune District (EAAA)","TGPL",0.198,"DUPL-DPPL","GAIL",9),
 (6,"4.08","Pune District (EAAA)","TGPL",1.710,"EWPL","PIL",9),
 (6,"4.08","Pune District (EAAA)","TGPL",0.927,"EWPL","PIL",9),
 (6,"4.08","Pune District (EAAA)","TGPL",0.565,"EWPL","PIL",9),
 (7,"5.03","East Godavari District (EAAA)","GGPL",6.845,"KG basin Network","GAIL",9),
 (8,"5.04","West Godavari District","GGPL",0.02,"KG Basin Network","GAIL",9),
 (8,"5.04","West Godavari District","GGPL",3.312,"KG Basin Network","GAIL",9),
 (8,"5.04","West Godavari District","GGPL",5.772,"KG Basin Network","GAIL",9),
 (8,"5.04","West Godavari District","GGPL",4.094,"KG Basin Network","GAIL",9),
 (8,"5.04","West Godavari District","GGPL",12.3,"KG Basin Network","GAIL",9),
 (9,"5.05","Tumkur District","MCGDPL",2.4,"DBPL","GAIL",9),
 (9,"5.05","Tumkur District","MCGDPL",0.16,"DBPL","GAIL",9),
 (10,"5.06","Krishna District (EAAA)","MCGDPL",0.48,"KG Basin Network","GAIL",9),
 (11,"5.08","Belgaum District","MCGDPL",0.25,"DBPL","GAIL",9),
 (12,"6.13","Yamunanagar District","BPCL",2.30,"DBNPL","GAIL",9),
 (13,"6.14","Ratnagiri District","UEPL",0.254,"DBPL","GAIL",9),
 (14,"9.07","Diu & Gir Somnath Districts","IRMEPL",6.48,"HPGGG","GSPL",10),
 (15,"9.10","Navsari District (EAAA), Surat District (EAAA), Tapi District (EAAA) & the Dangs District","ATGL",17.8,"HPGGG","GSPL",10),
 (16,"9.12","Kheda District (EAAA) & Mahisagar District","ATGL",0.74,"HPGGG","GSPL",10),
 (17,"9.24","Chitradurga & Davanagere Districts","UEPL",0.14,"DBPL","GAIL",10),
 (18,"9.58","Bhilwara & Bundi Districts","ATGL",0.88,"HVJ","GAIL",10),
 (19,"9.59","Chittorgarh (Other than Rawatbhata Taluka) & Udaipur Districts","ATGL",0.45,"HVJ","GAIL",10),
 (20,"9.70","Jangaon, Jayashankar Bhupalpally, Mahabubabad, Warangal Urban & Warangal Rural Districts","MCGDPL",1.319,"MBBVPL","GITL",10),
 (21,"9.71","Medak, Siddipet & Sangareddy Districts","TGPL",17.4,"EWPL","PIL",10),
 (22,"9.73","Nalgonda Suryapet & Yadadri Bhuvanagiri Districts","MCGDPL",2.8,"EWPL","PIL",10),
 (23,"9.78","Amethi, Pratapgarh & Raebareli Districts","BPCL",0.75,"HVJ","GAIL",10),
 (24,"9.79","Auraiya, Kanpur Dehat & Etawah Districts","TGPL",2.5,"HVJ","GAIL",10),
 (25,"9.40","Latur & Osmanabad Districts","UEPL",11.865,"EWPL","PIL",10),
 (26,"10.33","Hoshiarpur and Gurdaspur Districts","GGL",0.123,"BGPL","GIGL",10),
 (27,"98.02","Surat, Bharuch, Ankleshwar","GGL",25.87,"HAPi","GGL",10),
 (27,"98.02","Surat, Bharuch, Ankleshwar","GGL",10.43,"Mora-Sachin STPL","GGL CGD",10),
 (27,"98.02","Surat, Bharuch, Ankleshwar","GGL",21.6,"HAPi","GGL",10),
 (27,"98.02","Surat, Bharuch, Ankleshwar","GGL",11.52,"Connected with Sunpertro Source","GGL",11),
 (27,"98.02","Surat, Bharuch, Ankleshwar","GGL",11,"Connected with GAIL APM Source","GGL",11),
 (28,"98.08","Ahmedabad City and Daskroi Area","ATGL",0.38,"HPGGG","GSPL",11),
 (29,"98.11","Anand area including Kanjari & Vadtal Villages (in Kheda District)","CGSML",6.2,"HPGGG","GSPL",11),
 (30,"98.12","Bhiwadi District","Haryana City Gas (Bhiwadi) Private Limited",2.23,"CJHPL","GAIL",11),
 (31,"99.18","Vadodara","VGL",0.423,"HVJ","GAIL",11),
 (31,"99.18","Vadodara","VGL",14.59,"HVJ","GAIL",11),
 (31,"99.18","Vadodara","VGL",3.62,"HVJ","GAIL",11),
 (31,"99.18","Vadodara","VGL",13.26,"HVJ","GAIL",11),
 (31,"99.18","Vadodara","VGL",33.58,"HVJ","GAIL",11),
 (32,"99.04","Kanpur","CUGL",8.89,"HVJ","GAIL",11),
 (33,"99.09","Hyderabad","BGL",3.230,"EWPL","PIL",11),
 (34,"96.04","Faridabad (Based on court order)","ATGL",0.55,"HVJ","GAIL",11),
 (35,"96.07","Vadodara (Sub judice)","ATGL",0.36,"HPGGG","GSPL",11),
 (36,"9.41","Sangli & Satara Districts","BPCL",0.09,"DBPL","GAIL",11),
 (37,"10.40","Gonda and Barabanki Districts","TGPL",19.04,"HVJ","GAIL",11),
 (38,"9.11","Junagadh District","TGPL",56,"HPGGG","GSPL",12),
 (39,"9.56","Alwar (other than Bhiwadi) & Jaipur District","TGPL",2.43,"MBPL","GIGL",12),
 (40,"9.62","Chennai and Thiruvallur Districts","TGPL",1.31,"EMPL","IOCL",12),
 (41,"9.20","Nuh & Palwal Districts","ATGL",0.25,"CJHPL","GAIL",12),
 (42,"9.08","Surendranagar District (EAAA) & Morbi District (EAAA)","ATGL",13.9,"HPGGG","GSPL",12),
 (43,"9.16","Bhiwani, Charkhi Dadri & Mahendragarh Districts","ATGL",1.3,"CJHPL","GAIL",12),
 (44,"10.31","Jhansi (EAAA) District, Bhind, Jalaun, Lalitpur and Datia Districts","ATGL",3.8,"HVJ","GAIL",12),
 (45,"10.12","Sirsa-Fatehabad-Mansa Districts","GGL",0.848,"MBPL","GIGL",12),
 (46,"9.68","Bhadradri Kothagudem & Khamman Districts","MCGDPL",0.44,"EWPL","PIL",12),
 (47,"9.72","Medchal-Malkajgiri, Ranga Reddy & Vikarabad Districts","MCGDPL",8.5,"EWPL","PIL",12),
 (47,"9.72","Medchal-Malkajgiri, Ranga Reddy & Vikarabad Districts","MCGDPL",6.9,"EWPL","PIL",12),
 (48,"10.29","Anuppur, Bilaspur and Korba Districts","ATGL",18.3,"SPPL","RGPL",12),
 (49,"10.35","Jalore and Sirohi Districts","GGL",3.82,"MBPL","GIGL",12),
 (50,"6.10","Anand District (EAAA)","GGL",2.68,"HP-GGG","GSPL",12),
 (51,"9.29","Ramanagara District","MNGL",4.7,"DBPL","GAIL",12),
 (52,"9.42","Sindhudurg District","MNGL",11.5,"DBPL","GAIL",12),
 (53,"9.09","Barwala & Ranpur Talukas (C)","ATGL",0.65,"HPGGG","GSPL",12),
 (54,"11.40","Tarn Taran District","MCGDPL",22.0,"BGPL","GIGL",12),
 (55,"11.46","Tiruvannamalai district","MCGDPL",0.132,"ETPL","IOCL",12),
 (56,"11.10","Mungeli, Bemetara, Durg, Balod And Dhamtari Districts","ATGL",0.1,"MNJPL","GAIL",12),
 (57,"11.11","Jashpur, Raigarh, JanjgirChampa And Mahasamund Districts","ATGL",0.25,"MNJPL","GAIL",12),
 (58,"11.34","Bhandara, Gondiya And Garchiroli Districts","ATGL",0.35,"MNJPL","GAIL",12),
 (59,"9.72","Medchal-Malkajgiri, Ranga Reddy & Vikarabad Districts","MCGDPL",9.0,"EWPL","PIL",13),
 (59,"9.72","Medchal-Malkajgiri, Ranga Reddy & Vikarabad Districts","MCGDPL",7.0,"EWPL","PIL",13),
 (60,"11.20","Chikkaballapur district","MCGDPL",0.585,"ETPL","IOCL",13),
 (61,"11.47","Ariyalur and Perambalur districts","MCGDPL",0.1,"ETPL","IOCL",13),
 (62,"11.49","Pudukottai, Sivaganga and Thanjavur districts","MCGDPL",0.085,"ETPL","IOCL",13),
 (62,"11.49","Pudukottai, Sivaganga and Thanjavur districts","MCGDPL",0.085,"ETPL","IOCL",13),
 (63,"11.52","Dindigul and Karur districts","MCGDPL",0.11,"ETPL","IOCL",13),
 (64,"11.58","Amroha (except area already authorized) & Sambhal (except area already authorized) districts","MCGDPL",1.51,"HVJ","GAIL",13),
 (65,"9.29","Ramanagara","MNGL",4.7,"DBPL","GAIL",13),
 (66,"9.39","Valsad (Except the area already authorized), Dhule & Nashik Districts","MNGL",2.7,"MNJPL","GAIL",13),
 (67,"9.21","Bilaspur, Hamirpur & Una Districts","BPCL",4.7,"DBNPL","GAIL",13),
 (68,"9.26","Ballari & Gadag Districts","BPCL",0.1,"DBPL","GAIL",13),
 (69,"9.48","Jagatsinghpur & Kendrapara Districts","BPCL",2.1,"JHBDPL","GAIL",13),
 (70,"10.13","Chatra & Palamu Districts","BPCL",0.85,"GAIL","GAIL",13),
 (71,"9.43","Angul & Dhekanal District","BPCL",4.2,"JHBDPL","GAIL",13),
 (72,"9.64","Cuddalore, Nagapattinam & Tiruvarur Districts","ATGL",0.2,"CBNPL","GAIL",13),
 (73,"9.45","Balasore, Bhadrak & Mayurbhanj Districts","ATGL",0.1,"JHBDPL","GAIL",13),
]

UNDER_CONSTRUCTION = [
 (1,"3.01","Jalandhar","JMEPL",4.00,"DBNPL","GIGL",17),
 (2,"5.03","East Godavari District (EAAA)","GGPL",51.3,"KG basin Network","GAIL",17),
 (3,"5.04","West Godavari District","GGPL",53.4,"KG basin Network","GAIL",17),
 (4,"9.25","Udupi District","ATGL",3.1,"KKMBPL","GAIL",17),
 (5,"11.30","Akola, Hingoli And Washim Districts","ATGL",0.05,"MNJPL","GAIL",17),
 (6,"9.51","Puducherry District","ECNGDPL",8.00,"ETBPNMTPL","IOCL",17),
 (7,"11.31","Amravati and Yavatmal District","ATGL",0.2,"MNJPL","GAIL",17),
 (8,"9.71","Medak, Siddipet & Sangareddy Districts","TGPL",2,"EWPL","PIL",17),
 (9,"11.19","Gumla, Latehar, Lohardaga, Simdega, Garhwa And Khunti Districts","ATGL",0.18,"JHBDPL","GAIL",17),
 (10,"11.04","Kokrajhar, Dhubri, South Salmaramankachar & Goalpara Districts","ATGL",0.4,"JHBDPL","GAIL",17),
 (11,"11.05","Baksa, Barpeta, Bongaigaon, Chirang, Nalbari & Bajali Districts","ATGL",0.15,"JHBDPL","GAIL",17),
 (12,"11.24","Tikamgarh, Niwari, Chattarpur and Panna Districts","ATGL",0.6,"HVJ","GAIL",17),
 (13,"11.06","Darbhanga, Madhubani, Supaul, Sitamarhi and Sheohar Districts","BPCL",74.3,"JHBDPL","GAIL",17),
 (14,"11.07","Gopalganj, Siwan, West Champaran, East Champaran and Deoria (UP) Districts","BPCL",38,"JHBDPL","GAIL",17),
 (15,"11.41","Fazilka (except area already authorized) (PB), Ganganagar (RJ) and Hanumangarh (RJ)","BPCL",65,"DBNPL","GAIL",17),
 (16,"11.60","Purulia and Bankura Districts","BPCL",1,"JHBDPL","GAIL",17),
 (17,"11.62","Alipurduar and Koch Bihar Districts","BPCL",1.5,"JHBDPL","GAIL",18),
 (18,"11A.01","Lakhimpur Kheri, Sitapur, Bahraich, Shravasti, Balrampur, Siddharth Nagar & Maharajganj Districts","BPCL",58.1,"HVJPL & JHDPL","GAIL",18),
 (19,"11A.04","Koria, Surajpur, Balrampur & Surguja Districts","BPCL",96,"Shadol-Phulpur","RGPL",18),
 (20,"11.54","Nizamabad, Kamareddy, Nirmal, Adilabad, Mancherial and Asifabad GA","MNGL",95,"EWPL","PIL",18),
 (21,"11.22","Agar Malwa, Neemuch, Mandsaur and Jhalawar districts","MCGDPL",0.172,"DVPL","GAIL",18),
 (22,"11.32","Chandrapur and Wardha districts","MCGDPL",5,"SAPL","GAIL",18),
 (23,"11.38","Rayagada, Kalahandi, Bolangir and Nuapada districts","MCGDPL",0.35,"MNJPL","GAIL",18),
]

# The register's own printed totals, used as the correctness gate.
PRINTED_TOTAL = {"Operational": 558.0, "Under Construction": 558.0}

# ---------------------------------------------------------------------------
# Acronym -> PL Unique ID. This is the ONLY derived (Category C) column in the
# table, and it is deliberately conservative: an acronym is mapped only where it
# expands unambiguously to a pipeline name in pipeline_master.csv AND the
# register's own "Transmission PL Entity" column names that pipeline's operator.
# Anything else is UNKNOWN. A wrong link here would silently connect a CGD area
# to the wrong trunk line, which is worse than no link at all.
TAP_TO_PIPELINE = {
 "HVJ":        ("17.03.NGPL", "Hazira-Vijaipur-Jagdishpur", "GAIL"),
 "HVJPL":      ("17.03.NGPL", "Hazira-Vijaipur-Jagdishpur", "GAIL"),
 "DVPL":       ("17.11.NGPL", "Dahej-Vijaipur / Vijaipur-Dadri", "GAIL"),
 "DBNPL":      ("17.12.NGPL", "Dadri-Bawana-Nangal", "GAIL"),
 "DBPL":       ("17.16.NGPL", "Dabhol-Bangalore", "GAIL"),
 "DUPL-DPPL":  ("17.05.NGPL", "Dahej-Uran-Panvel-Dabhol", "GAIL"),
 "EWPL":       ("17.04.NGPL", "Kakinada-Hyderabad-Uran-Ahmedabad (East West)", "PIL"),
 "CJHPL":      ("17.09.NGPL", "Chainsa-Jhajjar-Hissar", "GAIL"),
 "JHBDPL":     ("17.20.NGPL", "Jagdishpur-Haldia-Bokaro Dhamra-Paradip-Barauni-Guwahati", "GAIL"),
 "KKMBPL":     ("17.15.NGPL", "Kochi-Koottanad-Bangalore-Mangalore", "GAIL"),
 "CBNPL":      ("17.02.NGPL", "Cauvery Basin Network", "GAIL"),
 "KG basin Network": ("17.06.NGPL", "KG Basin Network", "GAIL"),
 "KG Basin Network": ("17.06.NGPL", "KG Basin Network", "GAIL"),
 "HPGGG":      ("18.01.NGPL", "High Pressure Gujarat Gas Grid", "GSPL"),
 "HP-GGG":     ("18.01.NGPL", "High Pressure Gujarat Gas Grid", "GSPL"),
 "HAPi":       ("18.02.NGPL", "Hazira-Ankleshwar (HAPi)", "GGL"),
 "MBPL":       ("5.01.NGPL",  "Mehsana-Bhatinda", "GIGL"),
 "BGPL":       ("5.02.NGPL",  "Bhatinda-Gurdaspur", "GIGL"),
 "MBBVPL":     ("5.03.NGPL",  "Mallavaram-Bhopal-Bhilwara-Vijaipur", "GITL"),
 "SPPL":       ("5.05.NGPL",  "Shahdol-Phulpur", "RGPL"),
 "Shadol-Phulpur": ("5.05.NGPL", "Shahdol-Phulpur", "RGPL"),
 "ETPL":       ("5.08.NGPL",  "Ennore-Tuticorin", "IOCL"),
 "ETBPNMTPL":  ("5.08.NGPL",  "Ennore-Tuticorin", "IOCL"),
 "MNJPL":      ("5.13.NGPL",  "Mumbai-Nagpur-Jharsuguda", "GAIL"),
}
# Recorded verbatim, deliberately NOT mapped, each with the reason.
NOT_A_PIPELINE = {
 "Mora-Sachin STPL": "another CGD spur line, not a transmission pipeline",
 "Connected with Sunpertro Source": "a gas source, not a transmission pipeline",
 "Connected with GAIL APM Source": "a gas source (APM allocation), not a pipeline",
 "GAIL": "the register prints an OPERATOR name where a pipeline name belongs "
         "(S.No 70, operational table) -- transcribed verbatim, not guessed",
}
UNMAPPED_NOTE = {
 "VAPL":  "Vijaipur-Auraiya; a segment of the HVJ system, not a separate PL ID "
          "in the December 2025 register",
 "EMPL":  "not expandable to any pipeline name in the register",
 "SAPL":  "not expandable to any pipeline name in the register",
 "JHDPL": "appears only inside the compound 'HVJPL & JHDPL'",
 "ECNGDPL": "CGD entity acronym, appears in the entity column",
}

def build(rows, status):
    out = []
    for sno, ga, name, ent, km, tap, txent, page in rows:
        pid, pname, note, cat = "UNKNOWN", "UNKNOWN", "", "C"
        if tap in NOT_A_PIPELINE:
            note = "NOT A TRANSMISSION PIPELINE: " + NOT_A_PIPELINE[tap]
        elif tap in TAP_TO_PIPELINE:
            pid, expansion, want = TAP_TO_PIPELINE[tap]
            # pipeline_name_matched carries the REGISTER's own name for that ID,
            # copied from the master -- not a paraphrase. That makes the link
            # checkable by exact equality, so a wrong pipeline_id cannot hide
            # behind a plausible-looking name.
            pname = MASTER_NAME.get(pid, "UNKNOWN")
            if want != txent:
                # entity disagreement is a red flag, not something to paper over
                note = (f"MAPPING WITHHELD: acronym expands to {expansion}, whose "
                        f"operator is {want}, but the register records the "
                        f"transmission entity as {txent}")
                pid, pname = "UNKNOWN", "UNKNOWN"
            else:
                note = (f"acronym '{tap}' expands to '{expansion}', the register's "
                        f"own name for {pid}; transmission entity {txent} matches "
                        f"that pipeline's operator")
        elif "&" in tap:
            note = ("compound: the register names more than one pipeline for a "
                    "single tap-off; not resolvable to one PL ID")
        else:
            note = "UNMAPPED: " + UNMAPPED_NOTE.get(tap, "acronym not expandable "
                                                    "to a pipeline in the register")
        out.append(dict(
            offtake_id=f"OT-{status[:2].upper()}-{len(out)+1:03d}",
            pdf_s_no=sno, ga_id=ga, ga_name=name, cgd_entity=ent,
            stpl_length_km=km, status=status,
            tap_from_verbatim=tap, transmission_entity=txent,
            tap_acronym_expansion=(TAP_TO_PIPELINE[tap][1]
                                   if tap in TAP_TO_PIPELINE else "NA"),
            pipeline_id=pid, pipeline_name_matched=pname,
            link_basis=note, link_provenance_category=cat,
            pdf_page=page, source_document="20251231_NGPL.pdf",
            provenance_category="A (all columns except pipeline_id / "
                                "pipeline_name_matched / link_basis, which are C)"))
    return out

rows = build(OPERATIONAL, "Operational") + build(UNDER_CONSTRUCTION, "Under Construction")
df = pd.DataFrame(rows)
os.makedirs(DP, exist_ok=True)
df.to_csv(os.path.join(DP, "pipeline_offtakes.csv"), index=False)

# ----------------------------------------------------- report + closure proof
print(f"pipeline_offtakes.csv       {len(df)} tap-off rows "
      f"({df.ga_id.nunique()} distinct GA IDs)")
print(f"                            operational {len(df[df.status=='Operational'])}, "
      f"under construction {len(df[df.status=='Under Construction'])}")

print("\nCLOSURE PROOF -- our sum vs the register's own printed total")
allok = True
for st, printed in PRINTED_TOTAL.items():
    got = df[df.status == st].stpl_length_km.sum()
    d = abs(got - printed)
    flag = "OK" if d <= 0.5 else "MISMATCH"
    if d > 0.5: allok = False
    print(f"  {st:20s} transcribed {got:8.3f} km   register prints {printed:6.1f} km   "
          f"diff {d:5.3f}  {flag}")
if not allok:
    print("  A MISMATCH means the transcription is wrong. Do not use this file.")

print(f"\nLINK TO TRUNK PIPELINE  (Category C -- conservative by design)")
print(f"  mapped to a PL Unique ID   {int((df.pipeline_id!='UNKNOWN').sum())}")
print(f"  UNKNOWN                    {int((df.pipeline_id=='UNKNOWN').sum())}")
for reason, n in df[df.pipeline_id == "UNKNOWN"].link_basis.str.split(":").str[0].value_counts().items():
    print(f"     {reason:44s} {n}")

print("\nGA IDs APPEARING MORE THAN ONCE (why this table is not keyed on GA ID)")
dup = df.groupby(["status", "ga_id"]).size()
dup = dup[dup > 1].sort_values(ascending=False)
for (st, ga), n in dup.items():
    nm = df[(df.status == st) & (df.ga_id == ga)].ga_name.iloc[0]
    print(f"  {ga:8s} x{n}  {st:18s} {nm[:44]}")

print("\nTOP TRUNK PIPELINES BY NUMBER OF CGD TAP-OFFS")
t = df[df.pipeline_id != "UNKNOWN"].groupby(["pipeline_id", "pipeline_name_matched"]).agg(
        n=("offtake_id", "size"), km=("stpl_length_km", "sum")).sort_values("n", ascending=False)
for (pid, pname), r in t.head(8).iterrows():
    print(f"  {pid:12s} {int(r.n):2d} tap-offs, {r.km:7.2f} km of spur   {pname[:40]}")
print("\nNEXT: python 09_build_edges.py")
