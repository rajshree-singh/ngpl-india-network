# -*- coding: utf-8 -*-
"""
ngpl_paths.py  --  one place that decides where the package lives.

Every other script does:

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ngpl_paths import ROOT, RAW, DP, GIS, META

WHY THIS EXISTS
  Until now each script carried its own line

      ROOT = os.environ.get("NGPL_ROOT", "/content/drive/MyDrive/ngpl-india-network")

  twelve times over. That hard-codes a Colab-and-Drive assumption into a package
  that is also run from a Windows desktop, and it means changing the location of
  the dataset requires editing twelve files -- exactly the kind of duplication
  that produced three separate, separately-buggy copies of the state-name
  normaliser earlier in this project.

HOW ROOT IS DECIDED, in order:
  1. the NGPL_ROOT environment variable, if set. Always wins, so a reviewer can
     point the scripts at a copy without editing anything.
  2. the parent of the directory this file sits in. The package layout is
     <root>/scripts/ngpl_paths.py, so the parent of scripts/ IS the root. This
     is the rule that makes the package portable: it works on Windows, on Linux,
     on a Mac and in Colab, from a Drive folder or a Desktop folder or a git
     clone, with no configuration at all.
  3. a short list of known locations, for the case where this file was pasted
     into a Colab cell and so has no __file__ to work from.

  Whichever candidate is chosen, it is CHECKED: it must contain data_raw/ or
  data_processed/. A path that does not is not silently accepted -- being wrong
  about where the data is would make every "file not found" message in this
  package point at the wrong problem.
"""
import os, sys

_MARKERS = ("data_raw", "data_processed")

def _looks_like_root(p):
    return bool(p) and os.path.isdir(p) and any(
        os.path.isdir(os.path.join(p, m)) for m in _MARKERS)

def _candidates():
    env = os.environ.get("NGPL_ROOT")
    if env:
        yield os.path.abspath(os.path.expanduser(env)), "NGPL_ROOT environment variable"
    try:                                    # normal case: run as a .py file
        here = os.path.dirname(os.path.abspath(__file__))
        yield os.path.dirname(here), "parent of the scripts/ folder containing ngpl_paths.py"
    except NameError:                       # pasted into a notebook cell
        pass
    cwd = os.path.abspath(os.getcwd())      # run from inside the package
    yield cwd, "current working directory"
    yield os.path.dirname(cwd), "parent of the current working directory"
    for p, why in [
        ("/content/drive/MyDrive/ngpl-india-network", "Google Drive (Colab)"),
        (os.path.expanduser("~/Desktop/GAIL Project/ngpl-india-network"), "Desktop/GAIL Project"),
        (os.path.expanduser("~/ngpl-india-network"), "home directory"),
    ]:
        yield p, why

ROOT = None
ROOT_REASON = None
_tried = []
for _p, _why in _candidates():
    _tried.append(_p)
    if _looks_like_root(_p):
        ROOT, ROOT_REASON = _p, _why
        break

if ROOT is None:
    raise SystemExit(
        "Cannot locate the ngpl-india-network package root.\n"
        "  Looked in:\n    " + "\n    ".join(dict.fromkeys(_tried)) +
        "\n  A root is a folder containing data_raw/ and/or data_processed/.\n"
        "  Fix: run the script from inside <root>/scripts/, or set NGPL_ROOT:\n"
        "    Windows  : set NGPL_ROOT=C:\\path\\to\\ngpl-india-network\n"
        "    Linux/Mac: export NGPL_ROOT=/path/to/ngpl-india-network\n"
        "    Colab    : os.environ['NGPL_ROOT'] = '/content/drive/MyDrive/ngpl-india-network'")

RAW  = os.path.join(ROOT, "data_raw")
DP   = os.path.join(ROOT, "data_processed")
GIS  = os.path.join(ROOT, "gis")
META = os.path.join(ROOT, "metadata")
EXT  = os.path.join(RAW, "external")
LEG  = os.path.join(RAW, "legacy_v0")

def ensure_dirs():
    for d in (RAW, DP, GIS, META, EXT, LEG,
              os.path.join(EXT, "gazetteer"), os.path.join(EXT, "seismic"),
              os.path.join(EXT, "population"), os.path.join(EXT, "flood"),
              os.path.join(EXT, "boundaries"), os.path.join(LEG, "rejected")):
        os.makedirs(d, exist_ok=True)

def require(*relpaths):
    """Return absolute paths, raising a useful error for the first one missing.
    Never returns a path to a file that does not exist, so no caller can
    proceed on the assumption that an intermediate file is there."""
    out = []
    for rel in relpaths:
        p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
        if not os.path.exists(p):
            raise SystemExit(f"MISSING INPUT: {p}\n"
                             f"  ROOT was resolved to: {ROOT}\n"
                             f"  (via {ROOT_REASON})\n"
                             f"  If that is the wrong folder, set NGPL_ROOT.")
        out.append(p)
    return out[0] if len(out) == 1 else out

# ---------------------------------------------------------------------------
# State-name normalisation, ONE copy.
#
# This has bitten the project three times, in three separate hand-written
# copies: "Meghalaya & Sikkim" is two states, "UT of Jammu & Kashmir" is one,
# "UT of Dadra & Nagar Haveli and Daman & Diu" is one containing two ampersands
# and the word "and", and 17.18 prints the CITY "Agartala" in the states column.
# Any splitter that reaches for "&" or " and " before consuming these compounds
# gets the wrong count. Compounds are therefore consumed FIRST, by exact match,
# longest first, and only the remainder is split.
# ---------------------------------------------------------------------------
_COMPOUND = [   # (verbatim register wording, one-or-more canonical names)
    ("UT of Dadra & Nagar Haveli and Daman & Diu", ["Dadra and Nagar Haveli and Daman and Diu"]),
    ("Dadra & Nagar Haveli and Daman & Diu",       ["Dadra and Nagar Haveli and Daman and Diu"]),
    ("UT of Jammu & Kashmir",                      ["Jammu and Kashmir"]),
    ("Jammu & Kashmir",                            ["Jammu and Kashmir"]),
    ("Meghalaya & Sikkim",                         ["Meghalaya", "Sikkim"]),   # genuinely two
    ("UT of Puducherry",                           ["Puducherry"]),
]
_FIX = {
    "MP": "Madhya Pradesh", "UP": "Uttar Pradesh",
    "Orissa": "Odisha", "Uttaranchal": "Uttarakhand",
    "NCT of Delhi": "Delhi", "Pondicherry": "Puducherry",
    "Agartala": "Tripura",          # the register prints a city here for 17.18
    "Chhatisgarh": "Chhattisgarh", "Chhattisgarh": "Chhattisgarh",
}

def normalise_states(s):
    """'Gujarat, MP & Meghalaya & Sikkim' -> {'Gujarat','Madhya Pradesh','Meghalaya','Sikkim'}

    Returns a set of canonical names. Never guesses: an unrecognised fragment is
    returned as-is (title-cased input preserved) so it shows up in a validator
    rather than vanishing."""
    if s is None:
        return set()
    txt = str(s).strip()
    if not txt or txt.lower() in ("nan", "na", "none", "-"):
        return set()
    out = set()
    for pat, repl in sorted(_COMPOUND, key=lambda x: -len(x[0])):
        while pat in txt:
            out.update(repl)
            txt = txt.replace(pat, " ", 1)
    txt = txt.replace(" and ", ",").replace("&", ",")
    for part in txt.split(","):
        part = part.strip(" ,&.\t")
        if not part:
            continue
        if part.startswith("UT of "):
            part = part[6:].strip()
        out.add(_FIX.get(part, part))
    return {x for x in out if x}

def count_states(s):
    """The Category-C state count. Deliberately NOT a column in any Category-A
    table -- it is computed on demand, here, from the verbatim register text."""
    return len(normalise_states(s))
