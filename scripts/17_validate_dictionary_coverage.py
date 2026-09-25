# -*- coding: utf-8 -*-
"""
17_validate_dictionary_coverage.py

THE CHECK THAT WAS MISSING.

The README and the accompanying article both state that every published column is
described in metadata/data_dictionary.csv. Nothing tested that, and it was false:
node_geocode_review.csv was published with none of its 26 columns documented, and
survived 215 passing data checks and five closure proofs because every one of
those checks looks at values, not at the metadata describing them.

This validator makes the claim testable. It compares the dictionary with the real
headers of data_processed/*.csv in BOTH directions:

  1. every published .csv appears in the dictionary          (no undocumented file)
  2. every dictionary file exists in data_processed/         (no phantom file)
  3. per file, documented column set == real header set      (no drift either way)
  4. per file, documented column ORDER == header order       (it is a reading aid)
  5. every row's provenance_category is in {A, B, C}         (the discipline holds)
  6. no (file, column) pair entered twice                    (no silent duplicate)

It reads headers only, so it is cheap and cannot alter anything.

Exit status 0 = all six pass. Non-zero = a claim made to the reader is false.

Usage:
    python 17_validate_dictionary_coverage.py [package_root]
    python 17_validate_dictionary_coverage.py --mutate [package_root]

--mutate is the validator's self-test, in the same style as scripts 12, 13 and 15.
It corrupts COPIES of the dictionary in eight ways, one per rule plus two extra,
and requires this validator to reject every one. A validator that passes a
corrupted input is worse than no validator, because it converts an unchecked
claim into a checked one that happens to be wrong.
"""
import csv, glob, os, shutil, sys, tempfile

ARGS = [a for a in sys.argv[1:] if a != "--mutate"]
MUTATE = "--mutate" in sys.argv[1:]
ROOT0 = os.path.abspath(ARGS[0]) if ARGS else \
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

COLS = ["file", "column", "provenance_category", "unit", "description"]


def header(p):
    # text only; csv never invents NA, unlike a pandas default read
    with open(p, encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


def read_dict(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_dict(p, rows):
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)


def audit(root):
    """Return a list of problem strings. Empty list = the record is consistent."""
    dp = os.path.join(root, "data_processed")
    dct = os.path.join(root, "metadata", "data_dictionary.csv")
    for p in (dp, dct):
        if not os.path.exists(p):
            return [f"missing {p}"]

    drows = read_dict(dct)
    if list(drows[0]) != COLS:
        return [f"dictionary header is {list(drows[0])}, expected {COLS}"]
    fail = []

    seen = set()
    for r in drows:                                             # rule 6
        k = (r["file"], r["column"])
        if k in seen:
            fail.append(f"duplicate dictionary entry: {k[0]} / {k[1]}")
        seen.add(k)

    for r in drows:                                             # rule 5
        if r["provenance_category"] not in ("A", "B", "C"):
            fail.append(f"bad provenance_category {r['provenance_category']!r} "
                        f"on {r['file']} / {r['column']}")

    documented = {}
    for r in drows:
        documented.setdefault(r["file"], []).append(r["column"])
    published = {os.path.basename(p): header(p)
                 for p in sorted(glob.glob(os.path.join(dp, "*.csv")))}

    for f_ in sorted(set(published) - set(documented)):          # rule 1
        fail.append(f"PUBLISHED BUT UNDOCUMENTED: {f_} ({len(published[f_])} columns)")
    for f_ in sorted(set(documented) - set(published)):          # rule 2
        fail.append(f"DOCUMENTED BUT NOT PUBLISHED: {f_}")

    for f_ in sorted(set(published) & set(documented)):
        real, doc = published[f_], documented[f_]
        for c in sorted(set(real) - set(doc)):                   # rule 3
            fail.append(f"{f_}: column {c!r} in the file but not the dictionary")
        for c in sorted(set(doc) - set(real)):                   # rule 3
            fail.append(f"{f_}: column {c!r} in the dictionary but not the file")
        if set(real) == set(doc) and real != doc:                # rule 4
            fail.append(f"{f_}: dictionary lists the right columns in a different order "
                        f"(file starts {real[:3]}, dictionary starts {doc[:3]})")
    return fail


# --------------------------------------------------------------------------- #
#  --mutate : eight corruptions, every one of which must be caught
# --------------------------------------------------------------------------- #
def mutations(rows):
    """Yield (name, mutated_rows, extra_file_to_create_or_None)."""
    R = lambda: [dict(r) for r in rows]

    m = R(); dropped = m.pop(0)
    yield (f"drop the dictionary row for {dropped['file']} / {dropped['column']}", m, None)

    m = R(); m.append({"file": "pipeline_master.csv", "column": "invented_column",
                       "provenance_category": "A", "unit": "text", "description": "x"})
    yield ("document a column that does not exist", m, None)

    m = R(); m.append({"file": "not_a_real_file.csv", "column": "x",
                       "provenance_category": "A", "unit": "text", "description": "x"})
    yield ("document a file that does not exist", m, None)

    m = R(); m[0]["column"] = m[0]["column"] + "_typo"
    yield ("a single typo in one column name", m, None)

    m = R()
    idx = [i for i, r in enumerate(m) if r["file"] == m[0]["file"]]
    if len(idx) >= 2:
        m[idx[0]], m[idx[1]] = m[idx[1]], m[idx[0]]
    yield ("swap two rows inside one file block (order only)", m, None)

    m = R(); m[0]["provenance_category"] = "D"
    yield ("provenance_category outside {A, B, C}", m, None)

    m = R(); m.append(dict(m[0]))
    yield ("the same (file, column) pair entered twice", m, None)

    tgt = rows[-1]["file"]
    m = [r for r in R() if r["file"] != tgt]
    yield (f"remove every row for {tgt} (a whole undocumented file)", m, None)


def self_test():
    base = read_dict(os.path.join(ROOT0, "metadata", "data_dictionary.csv"))
    clean = audit(ROOT0)
    if clean:
        print("REFUSING to self-test: the real package does not pass.")
        for x in clean:
            print("  - " + x)
        return 1

    caught = total = 0
    for name, mrows, _ in mutations(base):
        total += 1
        with tempfile.TemporaryDirectory() as td:
            work = os.path.join(td, "pkg")
            os.makedirs(os.path.join(work, "metadata"))
            os.symlink(os.path.join(ROOT0, "data_processed"),
                       os.path.join(work, "data_processed"))
            write_dict(os.path.join(work, "metadata", "data_dictionary.csv"), mrows)
            problems = audit(work)
        ok = bool(problems)
        caught += ok
        print(f"  {'CAUGHT ' if ok else 'MISSED '} {name}")
        if not ok:
            print("           this corruption passed every rule -- the validator is incomplete")
    print(f"\n{caught}/{total} mutations caught")
    if caught == total:
        print("Mutation self-test passed.")
        return 0
    print("MUTATION SELF-TEST FAILED.")
    return 1


if __name__ == "__main__":
    if MUTATE:
        sys.exit(self_test())

    problems = audit(ROOT0)
    dp = os.path.join(ROOT0, "data_processed")
    pub = {os.path.basename(p): header(p) for p in sorted(glob.glob(os.path.join(dp, "*.csv")))}
    drows = read_dict(os.path.join(ROOT0, "metadata", "data_dictionary.csv"))
    print(f"package: {ROOT0}")
    print(f"published data files: {len(pub)}   dictionary rows: {len(drows)}")
    print(f"published columns: {sum(len(v) for v in pub.values())}")
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for x in problems:
            print("  - " + x)
        sys.exit(1)
    print("\nPASS: every published column is documented, every documented column is published, "
          "orders agree, all categories are A/B/C, no duplicates.")
