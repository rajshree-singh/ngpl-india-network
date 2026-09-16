# Indian Natural Gas Pipeline Network — Graph and GIS Dataset

**Status: IN PROGRESS — not yet suitable for publication.**
Steps 1, 2, 6, 7 and 8 are complete and validated. The hazard-exposure layers are not. Section 9 states
exactly what exists and what does not. Do not cite the GIS or exposure layers:
the exposure layers are still derived from geometry this project has rejected
(§8.1), and the reconstructed routes now in `gis/` are straight-line
approximations, not alignments (§8.1, §8.8).

| | |
|---|---|
| Version | v0.6-dev (2026-09-15) |
| Primary source | PNGRB, *Natural Gas Pipeline Networks in India — December 2025* |
| Coverage | 99 authorized natural gas pipelines; 37 in analytical scope; 27 in the v1 graph |
| Spatial reference | EPSG:4326 published; EPSG:7755 for all metric operations |
| Licence | See §11 |

---

## 1. What this dataset is

A machine-readable reconstruction of India's authorized natural gas pipeline
network, built from the Petroleum and Natural Gas Regulatory Board's periodic
NGPL register, with a node–edge graph representation and geospatial hazard
exposure layers.

It is intended for national-scale network analysis. It is **not** an engineering
dataset: it contains no surveyed alignments, no as-built centrelines, and no
facility coordinates. §8 states the limitations precisely.

## 2. Provenance categories

Every variable in this dataset belongs to exactly one category, and the category
is recorded in `metadata/data_dictionary.csv`. This separation is the dataset's
central discipline.

| | Category | Meaning |
|---|---|---|
| **A** | Source-derived | Transcribed from the PNGRB register or another cited document. Pipeline IDs, names, operators, lengths, capacities, authorization dates, states. |
| **B** | GIS-derived | Computed from spatial data. Route lengths, buffer intersections, zonal statistics. |
| **C** | Derived analytical | Computed from A and/or B. Exposure scores, graph metrics, centrality. |

A Category-C value must never occupy a Category-A column. This rule was violated
once during development and is now enforced by an automated check (§7).

## 3. Scope — why 99, 37 and 27

Three nested populations, each with a stated inclusion rule.

**99 pipelines — the authoritative universe.** Every distinct `PL Unique ID` in
the December 2025 register, across all nine of its tables. Published in full so
that nothing is silently excluded.

**37 pipelines — the analytical scope** (`in_graph_scope = TRUE`). All
**Common Carrier** pipelines: 21 operational, 10 under construction, 6 under
construction via Section 42. Common Carrier is the only subset whose boundary is
defined by a criterion the source itself states, and it sums exactly to the
32,702 km national transmission grid the register publishes on page 1. The 18
tie-in and 44 dedicated pipelines are excluded because they are single-consumer
spurs and field connections (0.2–194 km), not network elements.

**27 pipelines — the v1 graph** (`in_graph_v1 = TRUE`). The Common Carrier
pipelines that are **linear**. The remaining 10 are **areal** — "Assam Regional
Network", "KG Basin Network", "High Pressure Gujarat Gas Grid" and others name a
*service area*, not a route. The register gives them no endpoints even in
principle, so they cannot be given nodes without inventing them. They are
retained in the master table, flagged, and deferred to a documented v2.

## 4. The node provenance rule

**The only place the register states a route point for a Common Carrier pipeline
is that pipeline's own name.** "Kochi-Koottanad-Bangalore-Mangalore" *is* the
source stating that route, in that order — and it supplies segment ordering as
well as node identity.

Nothing else in the register gives a route point. An earlier version of this
dataset carried a `Start Point` / `End Point` / `Intermediate Points` field
containing ~65 place names; a full-text search established that **39 of them
appear nowhere in the source**, and roughly 10 more appear only as the names of
CGD Geographical Areas, which are not route points. All 63 are listed in
`data_processed/unsourced_locations.csv` with the pipelines that used them. They
are excluded from the graph and published rather than deleted, so that "why is
Rajahmundry not a node?" has a documented answer.

## 5. Coordinates

Node coordinates come from the **GeoNames** gazetteer (`IN.txt`), downloaded
once and cited in `data_raw/external/SOURCES.md` with URL, size, SHA-256 prefix,
licence and access date.

**They are populated-place centroids. They are not pipeline facility locations,**
and every row says so in `coordinate_accuracy`. Hazira the settlement is not the
Hazira LNG terminal.

### 5.1 State-constrained matching

A place name alone is not geocodable. *Dwarka* is a town in Gujarat and a
district of Delhi with 220× the population; *Maharajganj* exists in Uttar
Pradesh, Bihar and Tripura. Every lookup is therefore constrained by the
register: a node may only match a gazetteer entry inside one of the states its
own pipeline is recorded as passing through (Category A, verified in Step 1).

### 5.2 Homonym resolution

The state constraint is necessary but **not sufficient**. A homonym inside an
allowed state still has to be resolved, and it is never resolved by population
size. Measured against the independent legacy coordinate table:

| candidates in allowed states | nodes | wrong by >25 km | worst error |
|---|---|---|---|
| exactly one | 22 | 0 | 13 km |
| more than one | 19 | 4 | **945 km** |

Selecting by population placed *Hazira* in Haryana rather than Gujarat, 945 km
from the true location, because pipeline 17.03 genuinely passes through Haryana
and the state filter could not reject it. The rule now is:

1. exactly one in-state match → accept;
2. more than one, and an independent coordinate agrees within 25 km → accept the
   nearest, recorded as *two independent sources concur*, with the distance;
3. otherwise → **AMBIGUOUS**, reported, never guessed.

### 5.3 Corroboration

40 of 47 resolved nodes were cross-checked against an independent coordinate
table of unknown provenance, used only to disambiguate and to verify — never as
a published value.

| | |
|---|---|
| median offset | 0.76 km |
| 90th percentile | 5.32 km |
| maximum | 13.35 km (Koottanad) |
| disagreements > 25 km | **0** |

Seven resolved nodes have **no independent corroboration** — Dwarka,
Hazaribagh, Jammu, Jamnagar, Nellore, Ranchi, Vijayawada. Each matched a unique
in-state gazetteer entry, which is the strongest single-source evidence
available, but it remains a single source.

### 5.4 Name variants

Accepted variants are recorded in the build script with a reason, and each was
confirmed by *both* name similarity and spatial agreement:

| register | gazetteer | offset | reason |
|---|---|---|---|
| Bangalore | Bengaluru | — | official renaming, 2014 |
| Mangalore | Mangaluru | — | official renaming, 2014 |
| Tuticorin | Thoothukudi | — | official renaming, 2018 |
| Bhatinda | Bathinda | — | register spelling |
| Hissar | Hisar | — | register spelling |
| Mehsana | Mahesana | 1.99 km | official spelling |
| Taloja | Taloje | 1.74 km | Taloja MIDC, Raigad district |
| Dhamra | Dhamara | 5.59 km | Dhamra port, Bhadrak district |
| Ennore | Ennur | 3.76 km | now part of Chennai; port renamed Kamarajar |

## 6. Coordinate reference systems

| Use | CRS |
|---|---|
| Published geometry | EPSG:4326 |
| Length, area, buffering | **EPSG:7755** (WGS 84 / India NSF LCC) |
| Seismic zone source layer | custom LCC, numerically identical to EPSG:7755 (max deviation 4.7 cm nationally) |

EPSG:3395 (World Mercator) must not be used for metric work here. A 5 km buffer
built in it has a true half-width of 4.5–4.9 km varying with latitude, and
inflates route length by up to 9%.

## 7. Validation

`scripts/10_validate_master.py` — **44 checks in seven groups**, exit code 0 only
when every check passes *and* no group is skipped.

1. Shape and keys
2. Category totals reproduced against page 1 of the register
3. All seven per-table subtotals, authorized and operating
4. No fabricated values — every NA carries a specific explanation
5. Provenance completeness — every row cites a table and row number
6. **Independent cross-check** against a separate transcription of the source
7. **Row-span verification** against the PDF text — date, capacity and operator
   each checked inside that row's own span

Groups 6 and 7 are the only ones that compare the data against a source
independent of the file being checked. If either is skipped the summary reports
`INCOMPLETE`, never success. Internal consistency alone would pass on a silently
altered capacity, a swapped operator, or a length exchanged between two
pipelines in a way that preserves the subtotal.

`scripts/11_validate_nodes.py` — **23 checks in five groups**. Group 5 does not
trust the stored `legacy_delta_km`: it recomputes every offset from the
independent coordinate table, because a coordinate can be moved without its
metadata being updated, and a stale stored number would conceal exactly that.

`scripts/12_validate_routes.py` — **47 checks in six groups**. The load-bearing
one is group 2: the set of vertices in `pipeline_routes.geojson` must be a
**subset** of the set of resolved node coordinates. If it holds, no coordinate in
the route file was invented, moved or interpolated. Group 4 recomputes every
geodesic length from the geometry rather than reading the stored value.

Every validator was mutation-tested — the output is deliberately corrupted N ways
and each corruption must be rejected. A validator that has never failed has not
been shown to work.

| validator | mutations | caught |
|---|---|---|
| `10_validate_master.py` | 13 | 13 |
| `12_validate_routes.py` | 14 | 14 |

`scripts/13_validate_tables.py` — **52 checks in five groups**, covering the
states, coverage, offtake and edge tables. Two carry the step. **S-12** recomputes
every coverage verdict from the master, the node candidates and the node table and
rejects the stored value if it disagrees, because a finding that says "the source
contradicts itself" must be reproducible from the inputs rather than asserted by
the file making the claim. **O-02** is the offtake closure proof (below).

`scripts/15_validate_vulnerability.py` — **49 checks in five groups**. Its group 2
recomputes every graph metric with **networkx** and requires exact agreement on
the discrete measures and agreement to 1e-9 on betweenness. That cross-check
exists because `14_build_vulnerability.py` implements components, articulation
points, bridges and betweenness by hand so a reviewer can read them; a
hand-rolled graph algorithm that nothing has checked is not evidence. If networkx
is absent the group is SKIPPED and the script exits non-zero — never reported as
a pass.

**It immediately earned its place.** The hand-written betweenness was exactly
twice the correct value: on an undirected graph Brandes visits every pair from
both ends, so the accumulated score must be halved before normalising. The error
changed no ranks, so nothing in the printed output looked wrong. Only the
independent implementation caught it.

`12_validate_routes.py --mutate`, `13_validate_tables.py --mutate` and
`15_validate_vulnerability.py --mutate` run their own self-tests.

| validator | mutations | caught |
|---|---|---|
| `10_validate_master.py` | 13 | 13 |
| `12_validate_routes.py` | 14 | 14 |
| `13_validate_tables.py` | 15 | 15 |
| `15_validate_vulnerability.py` | 15 | 15 |

Two of these checks were written after a mutation escaped. `O-13` exists because
re-pointing a CGD tap-off from one GAIL pipeline to another GAIL pipeline passed
every check: the operator still matched. The table now stores the register's own
pipeline name alongside the ID, copied from the master, so an altered ID leaves a
name that no longer belongs to it.

### 7.1 A trap that affects every CSV here

Pandas' default `na_values` list contains the literal string `NA`. A column
written with an explicit `NA` sentinel is read back as `NaN`, and `.astype(str)`
then yields `"nan"`. Four of the NA-discipline checks — the ones whose whole
purpose is to stop a missing value being written as `0` — silently tested nothing
until this was found. Validators in this package therefore read with
`keep_default_na=False, na_values=[], dtype=str` and coerce numeric columns by
name. **Validate the bytes on disk, not a library's interpretation of them.**

### 7.2 Closure proofs

Three totals printed in the register are reproduced by transcriptions built
independently of them. A reader can check each against the public PDF without
running any code — which is worth more than any number of internal assertions.

| what | register prints | this dataset | source |
|---|---|---|---|
| Common Carrier length | 32,702 km | 32,702.2 km | p.1 |
| Tie-in length | 792 km | 792.31 km | p.1 |
| Dedicated length | 779 km | 779.335 km | p.1 |
| Operational CGD tap-offs | 558 km | 558.032 km | p.13 |
| Under-construction CGD tap-offs | 558 km | 557.802 km | p.18 |

## 8. Known limitations

Stated as limitations, not defects — a limitation is documented, a defect is not.

**8.1 There are no route alignments.** No surveyed or as-built centreline exists
in this dataset or in any source available to it.

The parametric-arc geometry of earlier versions is **rejected and removed**: it
left Indian territory, passing through Nepal and several hundred kilometres into
the Bay of Bengal and Arabian Sea.

`gis/pipeline_routes.geojson` replaces it with straight **geodesic segments
between the gazetteer points the register names in each pipeline's own title**.
Every feature carries `geometry_type = "reconstructed_straight_segment"` and
`NOT_AN_ALIGNMENT = true`. It is a reading aid and a basis for coarse national
analysis. It is not a right of way and must not be used for routing, land
matters, encroachment, or any distance-to-pipeline figure presented as fact.

Whether OpenStreetMap could supply real alignments was tested directly
(`06_survey_osm_pipelines.py`) and the answer is no: of 30 in-scope pipeline
names probed against OSM `man_made=pipeline` features, **2 matched**. One
pipeline is well covered — Kochi–Koottanad–Bangalore–Mangalore, whose OSM
fragments total roughly 913 km against 1,104 km authorized. That survey has two
defects of its own, recorded here rather than quietly dropped: its south-eastern
quadrant failed with HTTP 429 and was never retried, so its totals are floors
rather than totals; and its bounding boxes extend past the national border, so
its results include two pipelines in Qinghai, China. Neither defect changes the
finding, which rests on the name-match test, not the totals.

The 5 km buffer and the seismic, population and flood exposure tables remain
invalid pending regeneration at Steps 7–9.

**8.2 Coordinates are settlement centroids, not facilities.** See §5.

**8.3 The graph covers 27 of 37 in-scope pipelines.** See §3.

**8.4 Five of the 56 nodes have no coordinate** — *Vijaipur*, *Chainsa*,
*Maharajganj*, *Kanai Chhata*, *Panitar*.

*Vijaipur* is a GAIL facility rather than a settlement and is genuinely absent
from a populated-place gazetteer: the three exact name matches lie 158, 500 and
633 km away and are different places. It requires a separately cited source, and
it is the consequential one — an interconnection on three pipelines (17.03,
17.11, 5.03), and the sole cause of five of the eight gapped segments.
*Chainsa*, *Maharajganj* (Tripura), *Kanai Chhata* and *Panitar* have no
defensible candidate.

All five are **published as rows** with `coordinate_status` set, not dropped, so
that the route and edge tables can express the gap rather than conceal it.

**8.5 Exposure scores are not risk scores.** What is measured is co-location of
an asset with a hazard and with population. There is no vulnerability term, no
failure probability and no consequence model. Fields are named
`*_exposure_score` accordingly.

**8.6 Length semantics.** The register publishes authorized, operating and
under-construction length separately; all three are carried as distinct fields
and none is overwritten by a computed value.

**8.7 Single-snapshot model.** The dataset represents the December 2025 register.
Authorizations are amended over time — pipeline 5.11's terminus changed from
Shrirampur to Panitar in 2022 — and this model cannot express that history.
Earlier releases of the same register (§10) are used to verify and to date
changes, never to contribute rows.

**8.8 For eight pipelines the register contradicts itself, and the route points
it names are demonstrably incomplete.**

The register states a Common Carrier pipeline's route points only in its name,
and the states it crosses in a separate column. Those two facts must agree.
`pipeline_state_coverage.csv` compares them for all 27 linear pipelines.

For **eight**, every named point is located and yet the register records states
that none of them enters. The clearest case is `5.08`, named *Ennore-Tuticorin* —
both in Tamil Nadu — while the register also records Karnataka, Andhra Pradesh
and Puducherry. A route between two Tamil Nadu towns cannot enter those states.

| pipeline | name | states recorded that no named point enters |
|---|---|---|
| 17.12 | Dadri-Bawana-Nangal | Haryana, Himachal Pradesh, Uttarakhand |
| 5.08 | Ennore-Tuticorin | Andhra Pradesh, Karnataka, Puducherry |
| 17.15 | Kochi-Koottanad-Bangalore-Mangalore | Puducherry, Tamil Nadu |
| 5.01 | Mehsana-Bhatinda | Haryana, Rajasthan |
| 5.13 | Mumbai-Nagpur-Jharsuguda | Chhattisgarh, Madhya Pradesh |
| 17.05 | Dahej-Uran-Panvel-Dabhol | Dadra & Nagar Haveli and Daman & Diu |
| 17.04 | Kakinada-Hyderabad-Uran-Ahmedabad | Karnataka |
| 17.16 | Dabhol-Bangalore | Goa |

This is a **source-internal** result: it uses nothing but two columns of the
public PDF, and needs no gazetteer, no third party and no code to verify.

**The register itself supplies the confirmation.** In the under-construction CGD
table (p.17) the same pipeline 5.08 is written not as "Ennore-Tuticorin" but as
the acronym **`ETBPNMTPL`** — seven initials where the name in Table 1 gives two —
and the row recording it is *Puducherry District* tapping off it directly. The
document therefore contains, in two different tables, both the short name and
evidence that the short name is not the whole route.

**A second, independent signal agrees.** Comparing each pipeline's authorised
length against the geodesic through its named points flags ten pipelines above a
ratio of 1.6 — 17.12 at 2.62, 5.08 at 2.60, 5.01 at 2.51. **Six pipelines are
flagged by both tests**, which are computed from entirely different columns.

**Four pipelines cannot be judged and are NOT counted** — 17.03, 17.09, 5.03 and
5.11. Each has a node with no coordinate, and an unlocated node is
indistinguishable from an unnamed route point. 17.03 appears to miss Madhya
Pradesh only because Vijaipur is unresolved, and Vijaipur is *in* Madhya Pradesh.
Counting those would be reporting our own missing data as a discovery about the
source. Check `S-14` fails the build if any such row is ever promoted to a
finding.

**What this does and does not establish.** It establishes that these pipelines
have route points the register does not name. It does **not** establish where
those points are. `straight_line_total_km` must therefore not be used as a length
estimate for any of the eight.

**8.9 One unlocated node carries most of the topological cost.** *Vijaipur* has
degree 5 — the second-busiest point in the network after Uran — and no
coordinate. Over the edges the register states, the graph has 10 components; over
the edges that can be drawn, 17. Locating Vijaipur alone would merge 4 of those
7 lost components. The drawable-component count is an artefact of missing
coordinates and must never be reported as network fragmentation; both counts are
published side by side for that reason.

**8.10 The network graph assumes that pipelines sharing a place name are
connected there, and the register never says so.** Uran is named by 17.04, 17.05,
17.14 and 17.19, so this graph has those four pipelines meeting at Uran. The
register gives each pipeline's route points and nothing about physical
interconnection. The inference is reasonable — these are major terminals and a
grid is only useful if it interconnects — but it is an inference. If two
pipelines pass through the same town without a tie-in, the graph contains a
connection that does not exist and every figure in §8.11 shifts. Every row of
`node_vulnerability.csv` and `edge_criticality.csv` carries this in
`interconnection_basis`. **This is the largest single threat to the validity of
the vulnerability analysis.**

**8.11 The network has almost no redundancy, and its third most central point is
one we cannot locate.** All figures are Category C and are published twice —
over the topology the register states, and over the topology this dataset can
draw. Quoting one without the other misleads in opposite directions.

| | register's topology | drawable |
|---|---|---|
| edges | 47 | 39 |
| components | 10 | 17 |
| largest component | 34 nodes | 24 nodes |
| articulation points | 27 | 23 |
| bridges | 44 of 47 | 39 of 39 |

**44 of 47 segments are bridges** — cutting any one of them disconnects part of
the network. The reconstructed graph is very nearly a tree. Whether the physical
system is equally fragile cannot be answered from the register, because the
register does not describe interconnection (§8.10).

Ranked by betweenness on the register's own topology, the three most central
points are **Uran** (degree 6, 345 node pairs lost on removal), **Dahej** (272)
and **Vijaipur** (242). Vijaipur is third of 56 — and it is one of the five nodes
with no coordinate. On the drawable graph it falls to rank 24, a shift of 21
places, purely because the data cannot place it.

That is the finding: **the point this network most depends on is the one a
populated-place gazetteer does not contain**, because it is an industrial
facility rather than a settlement. The other four unlocated nodes are degree-1
leaves and cost the analysis almost nothing. The failure is concentrated, not
diffuse.

29 of 56 nodes have metrics that differ between the two graphs and are labelled
`uncertain` in `metric_certainty`. For those, no single figure should be quoted
without its range.

## 9. Contents

Status is stated per file. Nothing marked *pending* should be used.

```
data_raw/                                    immutable after ingest
  20251231_NGPL.pdf                          primary source                 COMPLETE
  external/gazetteer/                        GeoNames IN.txt, admin1 codes  COMPLETE
  external/SOURCES.md                        publisher, licence, checksums  COMPLETE
  legacy_v0/                                 superseded versions, preserved COMPLETE

data_processed/
  pipeline_master.csv          99 rows, 20 cols, 44/44 checks passing       COMPLETE
  pipeline_topology.csv        37 rows; 27 linear / 10 areal                COMPLETE
  node_candidates.csv          74 waypoint rows, 56 distinct names          COMPLETE
  unsourced_locations.csv      63 excluded locations, with reasons          COMPLETE
  node_geocode_review.csv      every candidate + evidence, for audit        COMPLETE
  pipeline_nodes.csv           56 nodes, 51 resolved, 23/23 checks passing   COMPLETE
  route_segments.csv           47 waypoint pairs; 39 drawable, 8 gapped      COMPLETE
  route_status.csv             37 rows; geometry status per pipeline         COMPLETE
  pipeline_states.csv          157 rows, one per pipeline x state, Cat. A     COMPLETE
  pipeline_state_coverage.csv  37 rows; the s8.8 finding, Category C          COMPLETE
  pipeline_offtakes.csv        115 CGD tap-offs; closes on 558 km twice       COMPLETE
  pipeline_edges.csv           47 edges; 8 published without geometry         COMPLETE
  node_vulnerability.csv       56 nodes; every metric on both graphs, Cat. C   COMPLETE
  edge_criticality.csv         47 edges; bridge status on both graphs          COMPLETE
  network_summary.csv          2 rows, one per graph                           COMPLETE
  pipeline_inventory_{seismic,population,flood}.csv                         pending
  pipeline_inventory_gis.csv   integrated analytical table                  pending

gis/
  pipeline_routes.geojson      24 features, 39 segments, 47/47 checks        COMPLETE
  osm_pipelines_raw.geojson    OSM survey output — EVIDENCE ONLY, see §8.1   reference
  pipeline_buffer_5km.geojson  5 km corridor, EPSG:7755                      pending

metadata/
  changelog.csv                substantive corrections, with sources        COMPLETE
  data_dictionary.csv          every column, with provenance category       COMPLETE

scripts/                       numbered, deterministic, run in order        COMPLETE
  ngpl_paths.py                package root + the shared state normaliser
```

## 10. Reproduction

```bash
python scripts/00b_fetch_gazetteer.py        # downloads GeoNames, writes SOURCES.md
python scripts/01_build_pipeline_master.py   # the 99-row authoritative universe
python scripts/10_validate_master.py         # gate — must print ALL CHECKS PASSED
python scripts/03_build_node_candidates.py   # topology + node names from the source
python scripts/04_geocode_nodes.py           # state-constrained geocoding
python scripts/04b_resolve_unresolved.py     # evidence for anything unresolved
python scripts/11_validate_nodes.py          # gate — must print ALL CHECKS PASSED
python scripts/05_resolve_facility_nodes.py  # facility audit (OSM, evidence only)
python scripts/06_survey_osm_pipelines.py    # alignment survey (evidence only)
python scripts/07_build_routes.py            # reconstructed route geometry
python scripts/12_validate_routes.py         # gate — must print VALIDATION PASSED
python scripts/02_build_pipeline_states.py   # states, long format + the §8.8 finding
python scripts/08_build_offtakes.py          # CGD tap-offs, closes on 558 km
python scripts/09_build_edges.py             # the graph edge list
python scripts/13_validate_tables.py         # gate — must print VALIDATION PASSED
python scripts/14_build_vulnerability.py     # centrality, cut points, bridges
python scripts/15_validate_vulnerability.py  # gate — needs networkx installed

# validator self-tests — each must catch every mutation
python scripts/12_validate_routes.py --mutate   # 14/14
python scripts/13_validate_tables.py --mutate   # 15/15
python scripts/15_validate_vulnerability.py --mutate  # 15/15
```

**Paths need no configuration.** `scripts/ngpl_paths.py` resolves the package
root as the parent of the folder it sits in, so the package runs unchanged from a
Windows desktop, a Linux path, a Google Drive mount or a git clone. Setting
`NGPL_ROOT` overrides it, which lets a reviewer point the scripts at a copy
without editing anything. The resolved root and the reason for it appear in every
"missing input" message, so a path problem never presents as a data problem.

`ngpl_paths.py` also holds the single copy of the state-name normaliser. Three
separate hand-written copies existed at one point and each was separately wrong:
`Meghalaya & Sikkim` is two states, `UT of Jammu & Kashmir` is one, `UT of Dadra
& Nagar Haveli and Daman & Diu` is one containing two ampersands and the word
"and", and pipeline 17.18 prints the city `Agartala` in the states column. Any
splitter that reaches for `&` before consuming those compounds returns the wrong
count.

The register tables are transcribed as literal data inside
`01_build_pipeline_master.py` rather than extracted programmatically. The source
PDF is word-processor generated, with merged cells, split headers and intra-word
line breaks; automated table extraction on it fails silently. The script is
therefore itself the transcription record, and its correctness is demonstrated by
reproducing the register's own published subtotals — a check any reader can
verify against the public PDF without running the code.

## 11. Sources, licence and citation

**Primary.** Petroleum and Natural Gas Regulatory Board (PNGRB), *Natural Gas
Pipeline Networks in India — December 2025*. Earlier releases used for
verification: 2 December 2022, 23 May 2022, 25 June 2021, 27 August 2020, from
`https://www.pngrb.gov.in/data-bank/`.

**Gazetteer.** GeoNames, `IN.txt` and `admin1CodesASCII.txt`, CC-BY 4.0,
`https://www.geonames.org/`. Access date and checksums in
`data_raw/external/SOURCES.md`.

**Third-party corroboration.** Global Energy Monitor, `https://www.gem.wiki/`,
used only where no PNGRB release settles a question, and cited as third-party.

Licence for this dataset, and the citation to use, are to be set before release.
Redistribution terms for the seismic zone layer must be confirmed first.

## 12. Change log

Substantive corrections to earlier versions are recorded in
`metadata/changelog.csv` with file, issue, original value, correction, reason and
source. The largest to date:

- Pipeline universe fixed at 99 with a stated inclusion rule, replacing four
  mutually inconsistent tables of 21, 25, 71 and 98 IDs. The 25-row version was
  bounded by a page break in the source, not by any criterion.
- Route point fields removed as unsourced; 63 locations excluded and published.
- Node coordinates rebuilt from a cited gazetteer under a state constraint.
  Four coordinates corrected, the largest by 945 km.
- Reconstructed curved routes rejected; all derived GIS layers invalidated.
- `n_states_verbatim` removed: a derived count inside a source-derived table,
  and wrong wherever "&" formed part of a single state name.
- Curved-arc geometry deleted and replaced by labelled straight-segment
  reconstruction with explicit gaps (v0.4).
- Path resolution and state-name normalisation consolidated into
  `scripts/ngpl_paths.py`, replacing twelve hard-coded roots and three divergent
  normalisers (v0.4).
- CGD tap-off tables transcribed from register pages 9–13 and 17–18; both
  reproduce the register's printed 558 km total (v0.5).
- Edge table published with its eight geometry-less edges retained, so that the
  network cannot appear better connected than the source states (v0.5).
- State-coverage cross-check added; eight pipelines shown to have route points
  the register does not name, four explicitly excluded as inconclusive (v0.5).
- Vulnerability analysis added, every metric computed over both the stated and
  the drawable topology so the cost of the unlocated nodes is visible (v0.6).
- Hand-written betweenness corrected: it was exactly 2x too large, caught only by
  the networkx cross-check, ranks unaffected (v0.6).
