# ============================================================
# Writes data_raw/legacy_v0/legacy_node_coordinates.csv directly.
# These are the coordinates from your ORIGINAL 42-node and 148-node
# tables, restricted to the 46 node names the graph actually needs.
#
# Their provenance is unknown, so they are NEVER published as a
# coordinate. 04_geocode_nodes.py uses them for two things only:
#   1. choosing between same-named gazetteer entries (Hazira: Gujarat
#      vs Haryana), and
#   2. cross-checking the GeoNames value it does publish.
# ============================================================
import os, csv

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON
OUT  = os.path.join(ROOT, "data_raw", "legacy_v0", "legacy_node_coordinates.csv")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

LEGACY = [
    ("Ahmedabad", 23.0225, 72.5714),
    ("Angul", 20.8444, 85.1511),
    ("Ankleshwar", 21.626, 73.015),
    ("Bangalore", 12.9716, 77.5946),
    ("Barauni", 25.477, 85.968),
    ("Bawana", 28.8004, 77.0343),
    ("Bhatinda", 30.211, 74.9455),
    ("Bhilwara", 25.347, 74.6408),
    ("Bhopal", 23.2599, 77.4126),
    ("Bokaro", 23.6693, 86.1511),
    ("Chainsa", 28.295, 77.34),
    ("Dabhol", 17.589, 73.18),
    ("Dadri", 28.547, 77.554),
    ("Dahej", 21.7129, 72.582),
    ("Dhamra", 20.79, 86.95),
    ("Dukli", 23.86, 91.31),
    ("Ennore", 13.2146, 80.3203),
    ("Gurdaspur", 32.041, 75.403),
    ("Guwahati", 26.1445, 91.7362),
    ("Haldia", 22.0667, 88.0698),
    ("Hazira", 21.1162, 72.6518),
    ("Hissar", 29.1492, 75.7217),
    ("Hyderabad", 17.385, 78.4867),
    ("Jagdishpur", 26.555, 80.915),
    ("Jhajjar", 28.6063, 76.6565),
    ("Jharsuguda", 21.8554, 84.0062),
    ("Kakinada", 16.9891, 82.2475),
    ("Kochi", 9.9312, 76.2673),
    ("Koottanad", 10.683, 76.021),
    ("Mallavaram", 16.56, 81.73),
    ("Mangalore", 12.9141, 74.856),
    ("Mehsana", 23.588, 72.369),
    ("Mumbai", 19.076, 72.8777),
    ("Nagpur", 21.1458, 79.0882),
    ("Nangal", 31.389, 76.375),
    ("Panipat", 29.3909, 76.9635),
    ("Panvel", 18.9894, 73.1175),
    ("Paradip", 20.3167, 86.6167),
    ("Phulpur", 25.548, 82.09),
    ("Shahdol", 23.298, 81.356),
    ("Srikakulam", 18.2969, 83.8978),
    ("Taloja", 19.07, 73.1),
    ("Trombay", 19.0, 72.92),
    ("Tuticorin", 8.7642, 78.1348),
    ("Uran", 18.878, 72.939),
    ("Vijaipur", 24.043, 77.16),
]

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["node_name", "latitude", "longitude", "legacy_source"])
    for name, lat, lon in LEGACY:
        w.writerow([name, lat, lon, "pipeline_nodes.csv / Dataset/pipeline_nodes.csv (v0 tables, provenance unknown)"])

print(f"wrote {OUT}  ({len(LEGACY)} nodes)")
print("now re-run:  04_geocode_nodes.py")
