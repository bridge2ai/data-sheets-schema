"""A `range:` key with no name is a degraded slot, not a missing one (#1150).

`make validate-core` lints every core file against the metamodel and
resolves every range with gen-python. Both pass `range: null` (or a bare
`range:`), which is legal LinkML and means the same as omitting the key —
but the slot then generates as a string where a class was meant:
`CoreDatasetCollection.resources` with `range: null` became
`Optional[Union[str, list[str]]]` instead of a `CoreDataset` collection,
and nothing said so. SchemaView cannot see it either: after parsing an
explicit null is indistinguishable from an omission, and 26 slots of the
core schema legitimately declare no range. Only the raw YAML can, so this
reads every file in the wrapper's directory and fails on a `range` key
whose value is null or not a string — on a slot, a class's `slot_usage`,
or an attribute. A scalar range (`range: 123`) is the linter's and
gen-python's to name; this reports it too, so one message covers the class.
A file it cannot read — not valid YAML, not UTF-8, not openable — is a
problem as well ("not readable, not checked"), named, since an all-clear
must not cover a file that was not read; the ✓ line counts the files read.

    python scripts/check_schema_ranges.py SCHEMA.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path


def problems(schema: Path, read: list[Path] | None = None) -> list[str]:
    """Every problem, one string each. A file that cannot be read — not
    valid YAML, not UTF-8, not openable — is a problem here too (#1179
    review, S2/S1): the glob reaches files the recipe's linter does not,
    and an all-clear must not cover a file that was not read. `read`, when
    given, collects the files that were."""
    import yaml

    out: list[str] = []
    for path in sorted({schema, *schema.parent.glob("*.yaml")}):
        if path.name.endswith("_all.yaml"):
            continue                       # generated from the files checked here
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, UnicodeDecodeError, OSError) as exc:
            # Named, whichever way the read failed: a byte that is not
            # UTF-8 is as concrete here as a parse error (#874, #921), and
            # a traceback names an offset, not a file (#1179 review).
            out.append(f"{path.name}: not readable, not checked ({str(exc).splitlines()[0]})")
            continue
        if read is not None:
            read.append(path)
        if not isinstance(raw, dict):
            continue
        for owner, node in _range_carriers(raw):
            if "range" not in node:
                continue
            rng = node["range"]
            if rng is None:
                out.append(f"{path.name}: {owner}: `range:` is present with no value — the slot "
                           f"generates as a string; name the class, type or enum, or drop the key")
            elif not isinstance(rng, str):
                out.append(f"{path.name}: {owner}: range is a {type(rng).__name__} ({rng!r}), not a name")
    return out


def _range_carriers(raw: dict):
    """(owner, mapping) for every mapping in the raw YAML that can carry a range."""
    for sname, slot in (raw.get("slots") or {}).items():
        if isinstance(slot, dict):
            yield f"slot {sname}", slot
    for cname, cls in (raw.get("classes") or {}).items():
        if not isinstance(cls, dict):
            continue
        for key in ("slot_usage", "attributes"):
            for sname, node in (cls.get(key) or {}).items():
                if isinstance(node, dict):
                    yield f"{cname}.{sname} ({key})", node


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    schema = Path(argv[0])
    if not schema.is_file():
        print(f"✖ {schema}: not found")
        return 1
    read: list[Path] = []
    found = problems(schema, read)
    for p in found:
        print(f"✖ {p}")
    if found:
        return 1
    print(f"✓ no `range:` without a name in the {len(read)} files read under {schema.parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
