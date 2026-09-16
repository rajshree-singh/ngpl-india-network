# Superseded working files

These are the authors' own earlier versions, kept so that the correction
history can be verified independently. **Do not use them as data.**
`metadata/changelog.csv` records what was wrong with each.

They are not dead weight: two of them are load-bearing inputs to the
validators.

| file | what it is | what it is used for now |
|---|---|---|
| `pdf_tables_operational.xlsx` | an independent early transcription of the register's operational tables | group 6 of `10_validate_master.py` — the only check that compares the master table against a source independent of itself |
| `legacy_node_coordinates.csv` | 176 coordinates of unknown provenance, merged from two earlier node tables | group 5 of `11_validate_nodes.py` — used ONLY to cross-check and to break ties between gazetteer candidates, never as a published coordinate |
| `pipeline_inventory_21.csv` | a 21-row inventory built on an inclusion rule that could not be defended | `03_build_node_candidates.py` reads it to produce `unsourced_locations.csv`, the published list of 63 place names the register does not support |

## What is not here

The source register PDF is **not** stored in this repository. Its
redistribution terms are not stated, and `scripts/00a_fetch_source.py`
downloads it and verifies its SHA-256, so nothing is lost.
