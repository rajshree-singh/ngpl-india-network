# -*- coding: utf-8 -*-
"""
00_colab_setup.py  --  run this ONCE per Colab session, before anything else.

Paste as a notebook cell, or `%run 00_colab_setup.py`.

It does three things:
  1. mounts Drive and sets NGPL_ROOT (every other script reads this one variable)
  2. creates the folder skeleton
  3. installs the packages the validator and the GIS scripts need

Point 3 matters more than it looks. Without pypdf, 10_validate_master.py cannot
open the PDF and silently drops its 5 strongest checks. Without your old
PDF Data.xlsx in place, it drops the 4 cross-check assertions. Between them
that is 9 of 43 checks -- and they are the only ones that compare the master
against a source independent of itself.
"""
import os, sys, subprocess

# ROOT: on Colab this is the Drive folder; anywhere else it is the parent of the
# folder this script sits in, which is what ngpl_paths.py uses too. Set NGPL_ROOT
# to override. This script must NOT import ngpl_paths -- it runs before the
# folder tree exists, and ngpl_paths deliberately refuses a root with no data
# folders in it.
def _default_root():
    env = os.environ.get("NGPL_ROOT")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    try:
        import google.colab            # noqa: F401
        return "/content/drive/MyDrive/ngpl-india-network"
    except ImportError:
        pass
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.path.abspath(os.getcwd())

ROOT = _default_root()

# --- 1. Drive -----------------------------------------------------------------
try:
    from google.colab import drive
    drive.mount("/content/drive")
except ImportError:
    pass                                  # running outside Colab; fine

os.environ["NGPL_ROOT"] = ROOT

# --- 2. folder skeleton -------------------------------------------------------
for d in ["data_raw/external/seismic", "data_raw/external/population",
          "data_raw/external/flood", "data_raw/external/boundaries",
          "data_raw/legacy_v0/rejected",
          "data_processed", "gis", "scripts", "metadata"]:
    os.makedirs(os.path.join(ROOT, d), exist_ok=True)

# --- 3. packages --------------------------------------------------------------
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "pypdf", "geopandas", "rasterio", "pyproj", "shapely", "openpyxl"],
               check=False)

# --- 4. tell the user what is still missing -----------------------------------
# Each entry: (list of acceptable paths, why it is needed)
NEEDED = [
    (["data_raw/20251231_NGPL.pdf"],
     "the primary source; group 7 of the validator needs it"),
    (["data_raw/legacy_v0/pdf_tables_operational.xlsx",
      "data_raw/legacy_v0/PDF Data.xlsx",
      "data_raw/PDF Data.xlsx"],
     "your own earlier transcription of the PDF tables -- in the original\n"
     "      GAIL Project folder this file is called 'PDF Data.xlsx'.\n"
     "      Group 6 of the validator needs it. Do NOT substitute a file\n"
     "      generated from 01_build_pipeline_master.py: the whole point is\n"
     "      that it is an INDEPENDENT transcription. A copy of our own output\n"
     "      would check the master against itself and prove nothing."),
]
print(f"\nNGPL_ROOT = {ROOT}\n")
missing = [(paths[0], why) for paths, why in NEEDED
           if not any(os.path.exists(os.path.join(ROOT, p)) for p in paths)]
if missing:
    print("MISSING -- the validator will skip checks until these are in place:")
    for p, why in missing:
        print(f"  {p}\n      {why}")
else:
    print("All validator inputs present. 10_validate_master.py can run complete.")

print("\nthen:  !cd \"$NGPL_ROOT/scripts\" && python 01_build_pipeline_master.py"
      "\n       !cd \"$NGPL_ROOT/scripts\" && python 10_validate_master.py")
