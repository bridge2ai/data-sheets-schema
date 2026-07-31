#!/usr/bin/env python3
"""Report RO-Crate mapping coverage against the current schema, and flag decay.

The agent doc asserted "95.2% coverage (83 fields)". That was true in March
against a `Dataset` of 87 induced slots; the class has since grown to 94, so the
real figure is 88.3% and nothing recomputed it. A coverage number that is written
down rather than measured decays silently every time the schema grows — and the
number exists precisely to answer "is this mapping adequate?".

It also validates the mapping's D4D column against the schema. A row naming a
slot that no longer exists is invisible at run time: the transformation produces
an absent field, which is indistinguishable from a crate that simply lacked the
property, and reports success either way. That is how a row mapping to
`vulnerable_populations` survived its rename to `at_risk_populations` for five
months.
"""

import argparse
import csv
import sys
from pathlib import Path

DEFAULT_MAPPING = Path("data/ro-crate_mapping/"
                       "D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv")
DEFAULT_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")


def d4d_slots(schema: Path, class_name: str = "Dataset") -> set[str]:
    from linkml_runtime import SchemaView
    return {s.name for s in SchemaView(str(schema)).class_induced_slots(class_name)}


def all_schema_slots(schema: Path) -> set[str]:
    """Every slot in the schema, not only those induced on one class.

    A mapping legitimately targets nested classes: `md5`, `bytes` and `media_type`
    belong to `File`, which `Dataset` reaches through `file_collections`. Grading
    the mapping against `Dataset`'s induced slots alone reported eight valid
    mappings as broken — a checker whose false positives outnumber its true ones
    is worse than none, because the real two get lost among them.
    """
    from linkml_runtime import SchemaView
    return set(SchemaView(str(schema)).all_slots())


def mapped_slots(mapping: Path) -> set[str]:
    """Slot names in the mapping's D4D column, whichever column that is."""
    with mapping.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if not rows:
        return set()
    # The column carrying D4D field names is found by content rather than by a
    # fixed header, so a re-exported spreadsheet with renamed columns still works.
    best, best_hits = None, 0
    known = d4d_slots(DEFAULT_SCHEMA)
    for col in rows[0]:
        hits = sum(1 for r in rows if (r.get(col) or "").strip() in known)
        if hits > best_hits:
            best, best_hits = col, hits
    if best is None:
        return set()
    return {(r.get(best) or "").strip() for r in rows if (r.get(best) or "").strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-m", "--mapping", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("-s", "--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("-c", "--class-name", default="Dataset")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if the mapping names unknown slots")
    a = ap.parse_args()

    slots = d4d_slots(a.schema, a.class_name)
    every = all_schema_slots(a.schema)
    mapped = mapped_slots(a.mapping)

    direct = mapped & slots            # maps a slot of the target class
    nested = (mapped & every) - slots  # maps a slot of a class it reaches
    unknown = sorted(mapped - every)   # maps nothing at all

    print(f"schema {a.class_name}: {len(slots)} induced slots")
    print(f"mapped, direct: {len(direct)}  ({len(direct) / len(slots):.1%} of "
          f"{a.class_name})")
    print(f"mapped, nested classes: {len(nested)}")
    if unknown:
        print(f"\n{len(unknown)} mapped name(s) in no class — these resolve to "
              "nothing and are silently dropped:")
        for u in unknown:
            import difflib
            near = difflib.get_close_matches(u, every, 1, 0.7)
            print(f"  {u}" + (f"   (did you mean {near[0]}?)" if near else ""))
    else:
        print("every mapped name exists somewhere in the schema")
    return 1 if (unknown and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
