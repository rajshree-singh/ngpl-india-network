# -*- coding: utf-8 -*-
"""
01_build_pipeline_master.py
Builds data_processed/pipeline_master.csv : the authoritative pipeline universe.

SOURCE  : 20251231_NGPL.pdf  (PNGRB, "Natural Gas Pipeline Networks in India - December 2025", 19 pp.)
METHOD  : verified literal transcription of the nine PL-ID tables, embedded below.
          Every row carries pdf_table + pdf_row so any value can be traced to a page.
          Correctness is proved by reproducing the PDF's own published subtotals
          and the page-1 category totals (see 10_validate.py).
CATEGORY: every column here is Category A (source-derived). No GIS, no derived scores.
"""
import pandas as pd, numpy as np, os, sys

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
OUT  = os.path.join(ROOT, "data_processed", "pipeline_master.csv")

NA = np.nan

# --- operator glossary, PDF p.2 -------------------------------------------------
# Codes used by the PL tables that the PDF's own glossary does NOT expand are left NA.
OPERATORS = {
 "AGCL":"Assam Gas Company Limited","AGPKLPL":"AGP Karaikal LNG Private Limited",
 "APCPL":"Astha Power Corporation Private Limited",
 "DFPCL":"Deepak Fertilizer and Petrochemical Corporation Ltd.","DNPL":"DNP Limited",
 "EOGEPL":"Essar Oil and Gas Exploration and Production Limited","GGL":"Gujarat Gas Limited",
 "GIGL":"GSPL India Gasnet Limited","GITL":"GSPL India Transco Limited",
 "GSPL":"Gujarat State Petronet Limited","HPPL":"Hooghly Pipelines Private Limited",
 "IGGL":"Indradhanush Gas Grid Limited","IMC":"IMC Limited",
 "IOCL":"Indian Oil Corporation Limited","KRPEPL":"Kei RSOS Petroleum & Energy Private Limited",
 "MSIPL":"Maharaj Soaps Industry Private Limited","ONGC":"Oil and Natural Gas Corporation Limited",
 "OPaL":"ONGC Petro addition Limited","PIL":"Pipelines Infrastructure Limited",
 "RCIPL":"Recasil Ceramics Industries Private Limited","RGPL":"Reliance Gas Pipelines Limited",
 "SCPL":"Silica Ceramica Private Limited","SEIL":"Steel Exchange India Limited",
 "TPL":"Torrent Power Limited","WCPL":"Western Concessions Private Limited",
 # not expanded anywhere in the PDF -> NA, never invented:
 "GAIL":NA, "GTIL":NA, "PEPL":NA,
}

# =============================================================================
# T1  Operational Common Carrier            PDF pp.3-4   subtotals 15,454.2 / 15,978
#     id, name, entity, auth_date, auth_km, cap, oper_km, states_verbatim
# =============================================================================
T1 = [
(1 ,"17.01.NGPL","Assam Regional Network","GAIL","04.11.2009",8,2.50,8,"Assam"),
(2 ,"17.02.NGPL","Cauvery Basin Network","GAIL","04.11.2009",240,4.33,242,"Puducherry and Tamil Nadu"),
(3 ,"17.03.NGPL","Hazira-Vijaipur-Jagdishpur -GREP (Gas Rehabilitation and Expansion Project)-Dahej-Vijaipur HVJ/VDPL","GAIL","19.04.2010",6169,111.3,6732,"Uttar Pradesh, Madhya Pradesh, Rajasthan and Gujarat, Haryana, Delhi, and Uttarakhand"),
(4 ,"17.11.NGPL","Dahej-Vijaipur (DVPL)-Vijaipur-Dadri (GREP) Upgradation DVPL 2 & VDPL","GAIL","14.02.2011",NA,NA,NA,NA),
(5 ,"17.04.NGPL","Kakinada-Hyderabad-Uran-Ahmedabad (East West Pipeline)","PIL","21.06.2019",1459,85,1485,"Andhra Pradesh, Gujarat, Maharashtra, Telangana and Karnataka"),
(6 ,"17.05.NGPL","Dahej-Uran-Panvel-Dabhol","GAIL","10.05.2010",920,22.5,943,"Gujarat, Maharashtra, UT of Dadra & Nagar Haveli and Daman & Diu"),
(7 ,"17.06.NGPL","KG Basin Network","GAIL","12.05.2010",878,16,867,"Andhra Pradesh"),
(8 ,"17.07.NGPL","Gujarat Regional Network","GAIL","03.12.2010",609,8.31,585,"Gujarat"),
(9 ,"17.08.NGPL","Agartala Regional Network","GAIL","13.12.2010",55,2,65,"Tripura"),
(10,"17.10.NGPL","Dadri-Panipat","IOCL","05.01.2011",132,20,143,"Haryana and Uttar Pradesh"),
(11,"17.13.NGPL","Mumbai Regional Network","GAIL","14.03.2011",129,7.04,125,"Maharashtra"),
(12,"17.14.NGPL","Uran-Trombay","ONGC","03.05.2011",24,6,24,"Maharashtra"),
(13,"18.01.NGPL","High Pressure Gujarat Gas Grid","GSPL","27.07.2012",2860,44.8,2738,"Gujarat"),
(14,"18.02.NGPL","Hazira-Ankleshwar (HAPi)","GGL","05.07.2012",73,5.06,73,"Gujarat"),
(15,"18.03.NGPL","Low Pressure Gujarat Gas Grid","GSPL","19.03.2013",58,12,57,"Gujarat"),
(16,"5.05.NGPL","Shahdol-Phulpur","RGPL","11.07.2013",312,3.50,304,"Madhya Pradesh and Uttar Pradesh"),
(17,"17.17.NGPL","Assam Regional Network","AGCL","20.12.2013",105,2.42,107,"Assam"),
(18,"17.18.NGPL","Dukli - Maharajganj","GAIL","09.01.2014",5.2,0.08,0,"Agartala"),
(19,"17.19.NGPL","Uran-Taloja","DFPCL","21.10.2014",42,0.70,42,"Maharashtra"),
(20,"17.09.NGPL","Chainsa-Jhajjar-Hissar","GAIL","13.12.2010",455,35,440,"Haryana, Rajasthan and Delhi"),
(21,"17.12.NGPL","Dadri-Bawana-Nangal","GAIL","15.02.2011",921,31,998,"Punjab, Haryana, Uttar Pradesh, Uttarakhand, Delhi, and Himachal Pradesh"),
]
# =============================================================================
# T2  Operational Tie-in connectivity        PDF p.5     subtotals 284.4 / 290.85
# =============================================================================
T2 = [
(1,"21.01.NGPL","Jaigarh - Dabhol","WCPL","18.05.2015",60,29.00,60.00,"Maharashtra"),
(2,"21.03.NGPL","ONGCs WHI North Penugonda to GAH, Peravali SV station","KRPEPL","16.02.2016",7.8,0.05,7.80,"Andhra Pradesh"),
(3,"21.06.NGPL","ONGC's Madnam field to GAIL's Cauvery Basin Network at SV-2 (Memathur)","GAIL","21.12.2017",29,0.85,30,"Andhra Pradesh"),
(4,"21.07.NGPL","ONGC's S1-VA fields ex-Odalarevu to GAIL's KG Basin Network at SV-1, Bodaskurru","GAIL","09.01.2018",13.6,5.20,14,"Andhra Pradesh"),
(5,"21.04.NGPL","Suvali to HVJ/DVPL Network","GAIL","24.01.2017",7,2.00,10,"Gujarat"),
(6,"21.05.NGPL","ONGC's Bantumilli gas source field to GAIL's KG Basin Network","GAIL","21.12.2017",41,0.90,38,"Andhra Pradesh"),
(7,"21.19.NGPL","Vedanta Limited's Jaya Fields at Jambusar, Gujarat to South Gujarat Main subnetwork of GAIL's Gujarat Regional Network","GAIL","07.03.2022",18,0.1,18,"Gujarat"),
(8,"21.15.NGPL","ONGC's Bokaro CBM Block to SV-01A on Bokaro-Dhamra Section of JHBDPL","GAIL","19.08.2021",23,0.99,24.3,"Jharkhand"),
(9,"21.11.NGPL","HSEPL LNG Terminal at Chhara to GSPL's dispatch terminal at Londhpur","GSPL","17.09.2019",85,18,88.75,"Gujarat"),
]
# =============================================================================
# T3  Operational Dedicated                  PDF pp.6-8  subtotals 658 / 653
# =============================================================================
T3 = [
(1 ,"19.01.NGPL","Duliajan to Numaligarh","DNPL","26.03.2009",194.00,1.20,192.00,"Assam"),
(2 ,"19.02.NGPL","Essar's LP gas gathering header to Phillips Carbon Black Ltd. Durgapur","EOGEPL","03.11.2010",8.00,0.70,8.00,"West Bengal"),
(3 ,"19.03.NGPL","Essar's LP Gas Gathering Header to Graphite India Ltd in Durgapur","EOGEPL","12.08.2015",3.00,0.06,2.36,"West Bengal"),
(4 ,"19.04.NGPL","PLL Dahej Terminal to DGEN Power Plant, Dahej SEZ","TPL","27.08.2012",13.00,8.00,13.00,"Gujarat"),
(5 ,"19.05.NGPL","EPS Akoljoni - Sapna Chemical (No Offtake)","GAIL","14.12.2012",3.40,0.01,3.40,"Gujarat"),
(6 ,"19.06.NGPL","EPS Nanda - Supreme Glass","GAIL","14.12.2012",0.37,0.01,0.37,"Gujarat"),
(7 ,"19.07.NGPL","Dahej GGS to GACL P/L","GAIL","14.12.2012",11.25,0.22,12.12,"Gujarat"),
(8 ,"19.08.NGPL","GGS Olpad to CYA. & CHEM.","GAIL","14.12.2012",1.20,0.05,1.20,"Gujarat"),
(9 ,"19.09.NGPL","Jolwa EPS to Nahar P/L","GAIL","14.12.2012",0.85,0.04,0.85,"Gujarat"),
(10,"19.10.NGPL","Jolwa EPS to GACL (MDPE)","GAIL","14.12.2012",7.80,0.13,7.80,"Gujarat"),
(11,"19.11.NGPL","Kim EPS to Spire cera P/L (MDPE)","GAIL","14.12.2012",1.20,0.01,1.20,"Gujarat"),
(12,"19.12.NGPL","EPS Wasana - Universal Metal (Manglam Alloys)","GAIL","14.12.2012",0.61,0.01,0.61,"Gujarat"),
(13,"19.13.NGPL","Motera GGS - RIL Sughad","GAIL","14.12.2012",3.72,0.07,3.72,"Gujarat"),
(14,"19.14.NGPL","Kalol collector line T/O - BVM","GAIL","14.12.2012",1.70,0.02,1.70,"Gujarat"),
(15,"19.15.NGPL","EPS Nandasan - Nirma","GAIL","14.12.2012",4.97,0.01,4.97,"Gujarat"),
(16,"19.16.NGPL","EPS Nandasan - Sterling (N)","GAIL","14.12.2012",2.84,0.01,2.84,"Gujarat"),
(17,"19.17.NGPL","EPS Nandasan - Sterling (K)","GAIL","14.12.2012",0.52,0.02,0.52,"Gujarat"),
(18,"19.18.NGPL","EPS Wadu - Pioneer","GAIL","14.12.2012",0.35,0.01,0.35,"Gujarat"),
(19,"19.19.NGPL","Sanand GGS - Jalaram","GAIL","14.12.2012",1.17,0.03,1.17,"Gujarat"),
(20,"19.20.NGPL","Limbodara EPS - Akash","GAIL","14.12.2012",0.20,0.03,0.20,"Gujarat"),
(21,"19.21.NGPL","Nandasan EPS - Akik Tiles","GAIL","14.12.2012",2.40,0.01,2.43,"Gujarat"),
(22,"19.22.NGPL","Nallur - TNEB Thirumakkottai","GAIL","14.12.2012",9.80,0.77,10.21,"Tamil Nadu"),
(23,"19.23.NGPL","Nallur - Prem Chemco","GAIL","14.12.2012",0.185,0.12,0.21,"Tamil Nadu"),
(24,"19.24.NGPL","BVG-Neycer","GAIL","14.12.2012",16.55,0.02,16.32,"Tamil Nadu"),
(25,"19.25.NGPL","AFL","GAIL","14.12.2012",1.70,0.10,1.71,"Andhra Pradesh"),
(26,"19.26.NGPL","Hitech","GAIL","14.12.2012",0.46,0.06,0.46,"Andhra Pradesh"),
(27,"19.27.NGPL","Steel Exchange","GAIL","14.12.2012",1.36,0.05,1.36,"Andhra Pradesh"),
(28,"19.28.NGPL","Dandewala - Gamnewala-RSEB Ramgarh","GAIL","14.12.2012",65.19,NA,65.32,"Rajasthan"),   # capacity verbatim "0.075 / 0.108"
(29,"19.29.NGPL","Langtala to Ramgarh","GAIL","14.12.2012",86.21,0.12,88.00,"Rajasthan"),
(30,"19.31.NGPL","ONGC Kavitam to GAIL Kavitam SV Station","SCPL","27.08.2013",3.60,0.02,3.80,"Andhra Pradesh"),
(31,"19.32.NGPL","ONGC Kammapalem isolated well to GAIL SV terminal, Dindi in East Godavari","SEIL","09.01.2014",5.40,0.05,4.75,"Andhra Pradesh"),
(32,"19.33.NGPL","ONGC's CTF Ankleshwar isolated well to GAIL's Common Carrier South Gujarat Network interconnection point","RCIPL","20.05.2015",0.53,0.015,0.53,"Gujarat"),
(33,"19.34.NGPL","Bhadol Top to Torrent Hazira Akhakol","GSPL","05.08.2015",22.00,0.48,22.00,"Gujarat"),
(34,"19.44.NGPL","LANCO Kondapalli Pipeline-I","PIL","12.08.2015",12.00,2.00,12.00,"Andhra Pradesh"),
(35,"19.36.NGPL","Sonamura GCS to GMS-Monarchak","ONGC","12.08.2015",13.00,0.50,10.50,"Tripura"),
(36,"19.35.NGPL","ADB GCS to ONGC Colony Badarghat","ONGC","12.08.2015",11.00,0.03,10.79,"Tripura"),
(37,"19.37.NGPL","ONGC Hazira-KRIBHCO HP Pipeline","ONGC","12.08.2015",5.00,2.00,4.27,"Gujarat"),
(38,"19.38.NGPL","ONGC Hazira-KRIBHCO LP Pipeline","ONGC","12.08.2015",5.00,1.00,4.86,"Gujarat"),
(39,"19.39.NGPL","Essar's Main Compressor Station in Raniganj (East) CBM Block to Matix Fertilizer and Chemicals Ltd (MFCL) in Durgapur","EOGEPL","12.08.2015",30.00,3.00,28.47,"West Bengal"),
(40,"19.43.NGPL","ONGC Poondi Fields to Maharaj Soaps Industry Private Limited","MSIPL","29.09.2020",0.20,0.002,0.26,"Tamil Nadu"),
(41,"19.41.NGPL","PLL's Dahej - Koyali Refinery Natural Gas Pipeline (DKPL)","IOCL","20.03.2020",106.00,5.23,106.0,"Gujarat"),
]
# =============================================================================
# T4  Under Construction Common Carrier      PDF p.19    subtotals 15,713 / 9,947 / 5,766
#     id, name, entity, auth_date, auth_km, cap, oper_km, uc_km, target, states
# =============================================================================
T4 = [
(1 ,"5.01.NGPL","Mehsana-Bhatinda","GIGL","07.07.2011",1943,83.11,1318,624,"June 2026","Gujarat, Rajasthan, Haryana, Punjab"),
(2 ,"5.02.NGPL","Bhatinda-Gurdaspur","GIGL","07.07.2011",261,42.42,101,160,"Dec 2024","Punjab"),
(3 ,"5.03.NGPL","Mallavaram-Bhopal-Bhilwara-Vijaipur","GITL","07.07.2011",1881,78.25,365,1517,"Mar 2020","Andhra Pradesh, Telangana, Maharashtra, MP, Rajasthan, Gujarat"),
(4 ,"17.16.NGPL","Dabhol-Bangalore","GAIL","14.11.2011",1414,16.00,1148,266,"Feb 2013","Maharashtra, Karnataka, Goa"),
(5 ,"17.15.NGPL","Kochi-Koottanad-Bangalore-Mangalore","GAIL","31.05.2012",1104,16.00,646,458,"Dec 2025","Kerala, Tamil Nadu, Karnataka, UT of Puducherry"),
(6 ,"5.08.NGPL","Ennore-Tuticorin","IOCL","10.12.2015",1431,84.67,1094,337,"Mar 2025","Tamil Nadu, Karnataka, Andhra Pradesh, UT of Puducherry"),
(7 ,"17.20.NGPL","Jagdishpur-Haldia-Bokaro Dhamra-Paradip-Barauni-Guwahati","GAIL","29.01.2018",3546,23.00,3279,267,"Dec 2025","Uttar Pradesh, Bihar, Jharkhand, West Bengal, Odisha, Assam"),
(8 ,"42.01.NGPL","North-East Natural Gas Pipeline Grid","IGGL","17.11.2020",1688,4.75,392,1296,"Mar 2026","Assam, Mizoram, Manipur, Arunachal Pradesh, Tripura, Nagaland, Meghalaya & Sikkim, West Bengal"),
(9 ,"5.13.NGPL","Mumbai-Nagpur-Jharsuguda","GAIL","15.05.2020",1755,16.50,1182,573,"Dec 2025","Maharashtra, Madhya Pradesh, Chhattisgarh and Odisha"),
(10,"5.12.NGPL","Srikakulam-Angul","GAIL","23.07.2019",690,6.65,422,268,"Dec 2025","Andhra Pradesh, Odisha"),
]
# =============================================================================
# T5  Under Construction Common Carrier, Sec.42 route   PDF p.14   subtotal 1,535
#     NOTE: this table has NO operating / under-construction length columns.
#     Those are NA -- not zero.
# =============================================================================
T5 = [
(1,"5.07.NGPL","Ennore - Nellore","GTIL","02.12.2014",220,36.00,"April 2020","Andhra Pradesh, Tamil Nadu"),
(2,"5.10.NGPL","Kakinada-Vijayawada-Nellore","IMC","19.02.2018",667,18.00,"March 2024","Andhra Pradesh"),
(3,"5.11.NGPL","Kanai - Chhata - Panitar","HPPL","08.07.2019",317,19.20,"March 2024","West Bengal"),
(4,"21.17.NGPL","Jamnagar to Dwarka (Gujarat)","GSPL","19.08.2021",100,3.00,"Oct 2026","Gujarat"),
(5,"5.14.NGPL","Hazaribagh-Ranchi","IOCL","09.02.2023",71,1.03,"February 2026","Jharkhand"),
(6,"5.15.NGPL","Gurdaspur-Jammu","GAIL","12.07.2023",160,3.10,"July 2026","UT of Jammu & Kashmir, Punjab"),
]
# =============================================================================
# T6  Under Construction Tie-in connectivity  PDF p.15   subtotal 507.91
# =============================================================================
T6 = [
(1,"21.09.NGPL","ONGC's Odelarevu terminal, Mallavaram connecting KVNPL","IMC","06.09.2019",49.10,18.00,"Sept 2022","Andhra Pradesh"),
(2,"21.10.NGPL","GSPL's proposed Terminal at Petronet LNG Limited re-gasification expansion facilities, Dahej to GSPL's existing Terminal at Bhadbhut","GSPL","17.09.2019",36,14.77,"May 2026","Gujarat"),
(3,"21.12.NGPL","Proposed LNG Terminal at Karaikal Port to Chemplast/PPCL on existing Narimanam-Kuthalam Natural Gas Pipeline Sub-Network of GAIL's Cauvery Basin Network","AGPKLPL","24.07.2020",8,2.00,"July 2023","Tamil Nadu and UT of Puducherry"),
(4,"21.14.NGPL","ONGC's Jharia CBM Block to SV-28 on Dobhi-Durgapur Section of JHBDPL","GAIL","19.08.2021",6,0.87,"Mar 2025","Jharkhand"),
(5,"21.16.NGPL","Swan LNG Private Limited's FSRU based LNG Terminal at Jafrabad to GPPC Terminal, Jafrabad falling on Darod-Jafrabad section of GSPL's HPGGG","GSPL","19.08.2021",3,18,"Aug 2024","Gujarat"),
(6,"21.22.NGPL","Swan LNG Private Limited's RLNG Terminal at Jafrabad to Hadala falling on Gana-Hadala section of GSPL's HPGGG","GSPL","31.12.2021",198,18,"Dec 2024","Gujarat"),
(7,"21.18.NGPL","Swan LNG Private Limited's RLNG Terminal at Jafrabad to GAIL's terminal at Dahej connecting to its integrated HVJ","GAIL","31.12.2021",170,7,"Dec 2024","Gujarat"),
(8,"21.20.NGPL","EPS 1 of Jharia Block I to SV-28 on Dobhi-Durgapur Section of JHBDPL","PEPL","28.10.2022",9,0.79,"Mar 2026","Jharkhand"),
(9,"21.21.NGPL","ONGC's Raniganj CBM Block to GAIL's JHBDPL Network","GAIL","30.11.2023",28.81,0.47,"Nov 2026","West Bengal"),
]
# =============================================================================
# T7  Under Construction Dedicated            PDF p.16   subtotal 121.6
# =============================================================================
T7 = [
(1,"19.30.NGPL","INOLE to Pashamylaram","APCPL","14.12.2012",14.6,1.50,"NA","Telangana"),
(2,"19.40.NGPL","PLL Re-gasification Terminal, Dahej to SUGEN Power Plant","TPL","20.03.2020",90.0,6.50,"NA","Gujarat"),
(3,"19.42.NGPL","PLL to OPaL, Dahej","OPaL","20.03.2020",17.0,3.32,"NA","Gujarat"),
]

# --- assemble -------------------------------------------------------------------
rows=[]
def add(**kw): rows.append(kw)

for r in T1:
    add(pdf_row=r[0], pipeline_id=r[1], pipeline_name=r[2], operator_code=r[3],
        authorization_date=r[4], authorized_length_km=r[5], capacity_mmscmd=r[6],
        operating_length_km=r[7], under_construction_km=NA, target_completion=NA,
        states_covered_verbatim=r[8], pipeline_category="Common Carrier",
        status="Operational", authorization_regulation="Reg 5/17/18",
        pdf_table="T1_p3_4_Op_CC")
for r in T2:
    add(pdf_row=r[0], pipeline_id=r[1], pipeline_name=r[2], operator_code=r[3],
        authorization_date=r[4], authorized_length_km=r[5], capacity_mmscmd=r[6],
        operating_length_km=r[7], under_construction_km=NA, target_completion=NA,
        states_covered_verbatim=r[8], pipeline_category="Tie-in",
        status="Operational", authorization_regulation="Reg 5/17/18",
        pdf_table="T2_p5_Op_TieIn")
for r in T3:
    add(pdf_row=r[0], pipeline_id=r[1], pipeline_name=r[2], operator_code=r[3],
        authorization_date=r[4], authorized_length_km=r[5], capacity_mmscmd=r[6],
        operating_length_km=r[7], under_construction_km=NA, target_completion=NA,
        states_covered_verbatim=r[8], pipeline_category="Dedicated",
        status="Operational", authorization_regulation="Reg 5/17/18",
        pdf_table="T3_p6_8_Op_Ded")
for r in T4:
    add(pdf_row=r[0], pipeline_id=r[1], pipeline_name=r[2], operator_code=r[3],
        authorization_date=r[4], authorized_length_km=r[5], capacity_mmscmd=r[6],
        operating_length_km=r[7], under_construction_km=r[8], target_completion=r[9],
        states_covered_verbatim=r[10], pipeline_category="Common Carrier",
        status="Under Construction", authorization_regulation="Reg 5/17/18",
        pdf_table="T4_p19_UC_CC")
for r in T5:
    add(pdf_row=r[0], pipeline_id=r[1], pipeline_name=r[2], operator_code=r[3],
        authorization_date=r[4], authorized_length_km=r[5], capacity_mmscmd=r[6],
        operating_length_km=NA, under_construction_km=NA, target_completion=r[7],
        states_covered_verbatim=r[8], pipeline_category="Common Carrier",
        status="Under Construction", authorization_regulation="Section 42",
        pdf_table="T5_p14_UC_CC_S42")
for r in T6:
    add(pdf_row=r[0], pipeline_id=r[1], pipeline_name=r[2], operator_code=r[3],
        authorization_date=r[4], authorized_length_km=r[5], capacity_mmscmd=r[6],
        operating_length_km=NA, under_construction_km=NA, target_completion=r[7],
        states_covered_verbatim=r[8], pipeline_category="Tie-in",
        status="Under Construction", authorization_regulation="Reg 5/17/18",
        pdf_table="T6_p15_UC_TieIn")
for r in T7:
    add(pdf_row=r[0], pipeline_id=r[1], pipeline_name=r[2], operator_code=r[3],
        authorization_date=r[4], authorized_length_km=r[5], capacity_mmscmd=r[6],
        operating_length_km=NA, under_construction_km=NA, target_completion=r[7],
        states_covered_verbatim=r[8], pipeline_category="Dedicated",
        status="Under Construction", authorization_regulation="Reg 5/17/18",
        pdf_table="T7_p16_UC_Ded")

m = pd.DataFrame(rows)
m["operator_name"] = m.operator_code.map(OPERATORS)
m["authorization_date"] = pd.to_datetime(m.authorization_date, format="%d.%m.%Y",
                                         errors="coerce").dt.strftime("%Y-%m-%d")
m["in_graph_scope"] = m.pipeline_category.eq("Common Carrier")
# NOTE: a state COUNT is deliberately NOT computed here.
#   "Meghalaya & Sikkim"                        -> 2 states
#   "UT of Jammu & Kashmir"                     -> 1
#   "UT of Dadra & Nagar Haveli and Daman & Diu"-> 1
# No string rule separates these; only a lookup against an authoritative state
# list does. Counting therefore belongs in 02_build_pipeline_states.py, against
# the LGD state directory, where it is a checkable derived value rather than a
# Category-C guess sitting inside a Category-A table.

# --- explicit notes: every NA and every anomaly is explained, never left silent ---
NOTES = {
 "17.11.NGPL":"Length and capacity reported jointly with 17.03.NGPL in the PDF; NA here rather than duplicated or invented. States column also merged with 17.03.",
 "17.18.NGPL":"operating_length_km = 0 is a TRUE measured zero: the PDF reports 5.2 km authorized and 0 km operating (authorized but not in operation). It is not a missing value. Separately, the PDF 'States' cell reads 'Agartala' (a city, not a State); normalised to Tripura in 02_build_pipeline_states.py with a changelog entry.",
 "19.28.NGPL":"PDF capacity cell reads '0.075 / 0.108' (two values). capacity_mmscmd is NA; see capacity_verbatim.",
 "19.38.NGPL":"Entity cell is merged with 19.37.NGPL in the PDF ('ONGC' printed once across both rows); operator_code is inherited from that merged cell, not printed on this row.",
 "5.11.NGPL":"Dec-2025 name prints as 'Kanai - Chhata - Panitar'; 'Kanai Chhata' is a single place name, per the PNGRB NGPL register, 2 December 2022 release (https://www.pngrb.gov.in/data-bank/NGPL-02122022.pdf) which prints 'Kanai Chhata - Shrirampur'. Terminus amended Shrirampur -> Panitar by PNGRB in 2022.",
 "19.35.NGPL":"Marked '*' in the PDF: latest data not submitted/available.",
 "19.36.NGPL":"Marked '*' in the PDF: latest data not submitted/available.",
 "21.17.NGPL":"ID carries the 21.xx (tie-in) prefix but appears in the p.14 Common Carrier table. VERIFIED: the PNGRB NGPL register, 2 December 2022 release (https://www.pngrb.gov.in/data-bank/NGPL-02122022.pdf) lists this pipeline under the explicit heading 'Under Construction Common Carrier Natural Gas Pipelines'. Classification is therefore stated by the source, not inferred from the p.1 total.",
 "17.16.NGPL":"Target completion 'Feb 2013' precedes the report date; transcribed verbatim from the PDF.",
 "5.03.NGPL":"Target completion 'Mar 2020' precedes the report date; transcribed verbatim from the PDF.",
}
m["notes"] = m.pipeline_id.map(NOTES).fillna("")
m.loc[m.pdf_table=="T5_p14_UC_CC_S42","notes"] += " PDF p.14 reports no operating/under-construction split; those fields are NA, not zero."
m.loc[m.pdf_table.isin(["T6_p15_UC_TieIn","T7_p16_UC_Ded"]),"notes"] += " PDF reports no operating/under-construction split; those fields are NA, not zero."
m.loc[m.operator_name.isna(),"notes"] += " Operator code not expanded in the PDF p.2 glossary; operator_name left NA rather than inferred."
m["capacity_verbatim"] = ""
m.loc[m.pipeline_id=="19.28.NGPL","capacity_verbatim"] = "0.075 / 0.108"
m["notes"] = m.notes.str.strip()

m["source_document"] = "20251231_NGPL.pdf (PNGRB, Natural Gas Pipeline Networks in India, December 2025)"

COLS = ["pipeline_id","pipeline_name","pipeline_category","status","authorization_regulation",
        "operator_code","operator_name","authorization_date",
        "authorized_length_km","operating_length_km","under_construction_km",
        "capacity_mmscmd","capacity_verbatim","target_completion",
        "states_covered_verbatim",
        "pdf_table","pdf_row","source_document","in_graph_scope","notes"]
m = m[COLS]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
m.to_csv(OUT, index=False, encoding="utf-8")
print(f"wrote {OUT}  rows={len(m)}  in_graph_scope={int(m.in_graph_scope.sum())}")
