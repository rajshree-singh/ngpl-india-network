# -*- coding: utf-8 -*-
"""
00a_fetch_source.py  --  download the primary source and verify it is the
                         exact document this dataset was built from.

Run this FIRST, before anything else.

WHY THE PDF IS NOT IN THE REPOSITORY
  The register is published by the Petroleum and Natural Gas Regulatory Board,
  a Government of India body. It is freely downloadable, but its redistribution
  terms are not stated on the document, so this package does not redistribute
  it. Reproduction does not suffer: this script fetches it and checks its
  SHA-256 against the value recorded below.

WHY THE CHECKSUM MATTERS MORE THAN THE DOWNLOAD
  PNGRB publishes this register periodically and the data-bank page carries
  several releases. If you fetch a different release, every table in this
  package will still build, and the numbers will quietly be different ones.
  A silent version mismatch is the most likely way for someone to reproduce
  this work incorrectly. The checksum makes that impossible: a different
  document fails here, loudly, before any output exists.

IF THE DOWNLOAD FAILS
  The direct URL may change. Download the December 2025 release by hand from
  https://www.pngrb.gov.in/data-bank/ , save it as
  data_raw/20251231_NGPL.pdf , and run this script again. It will verify the
  file you placed and tell you whether it is the right one.
"""
import os, sys, hashlib

# --- package location: resolved once, in scripts/ngpl_paths.py --------------
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))
                 if "__file__" in dir() else os.getcwd())
from ngpl_paths import ROOT, ROOT_REASON, ensure_dirs

# The exact document this dataset was built from.
EXPECTED_SHA256 = "8c209fa7757b420f3485190d769a93efc8dcf7069e9c20a77aab8bf2fd5222e2"
EXPECTED_BYTES  = 902241
URL  = "https://www.pngrb.gov.in/data-bank/20251231_NGPL.pdf"
PAGE = "https://www.pngrb.gov.in/data-bank/"

ensure_dirs()
DEST = os.path.join(ROOT, "data_raw", "20251231_NGPL.pdf")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path):
    """Returns (ok, message). Never returns ok=True on a file it did not hash."""
    if not os.path.exists(path):
        return False, "file is not present"
    n = os.path.getsize(path)
    d = digest(path)
    if d == EXPECTED_SHA256:
        return True, f"{n:,} bytes, SHA-256 matches"
    if n != EXPECTED_BYTES:
        return False, (f"WRONG DOCUMENT: {n:,} bytes, expected {EXPECTED_BYTES:,}. "
                       f"This is almost certainly a different release of the "
                       f"register. Do not build from it.")
    return False, (f"WRONG DOCUMENT: size matches but SHA-256 is {d[:16]}..., "
                   f"expected {EXPECTED_SHA256[:16]}...")


print(f"package root  {ROOT}\n  (via {ROOT_REASON})")

ok, msg = verify(DEST)
if ok:
    print(f"\nalready present and verified: {msg}")
    print("Nothing to do. Next: python 00b_fetch_gazetteer.py")
    sys.exit(0)

if os.path.exists(DEST):
    print(f"\nA file is already at {DEST} but it is not the right document.")
    print(f"  {msg}")
    print("  Move it aside and re-run, or replace it with the December 2025 release.")
    sys.exit(1)

print(f"\ndownloading {URL}")
try:
    import urllib.request
    req = urllib.request.Request(URL, headers={"User-Agent": "ngpl-india-network/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(DEST, "wb") as f:
        f.write(r.read())
except Exception as e:
    if os.path.exists(DEST):
        os.remove(DEST)          # never leave a partial file that looks like a source
    print(f"  download failed: {e}\n")
    print("  Fetch it by hand instead:")
    print(f"    1. open {PAGE}")
    print("    2. download the 31 December 2025 release")
    print(f"    3. save it as {DEST}")
    print("    4. run this script again to verify it")
    sys.exit(1)

ok, msg = verify(DEST)
print(f"  {msg}")
if not ok:
    os.remove(DEST)
    print("\n  The downloaded file is not the December 2025 release this dataset")
    print("  was built from. It has been deleted rather than left in place.")
    print(f"  Download the correct release by hand from {PAGE}")
    sys.exit(1)

print("\nverified. Next: python 00b_fetch_gazetteer.py")
