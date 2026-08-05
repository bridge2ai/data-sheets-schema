"""Classify why a record's `related_datasets` fails, by mode (#292).

All three 2026-07-31 VOICE replicates fail validation on this slot, and each
fails differently. `linkml-validate` reports them as three unrelated errors, so
telling whether the rerun fixed anything means reading three tracebacks and
knowing which was which:

    rep1  relationship_type='has_part'        target_dataset=dict
    rep2  relationship_type='related_to'      target_dataset=str
    rep3  relationship_type='IsNewVersionOf'  target_dataset=str

Those are three different problems with three different owners:

`INLINE_TARGET` — an object where the schema declares a string. #297 established
that LinkML cannot express a string-or-inline-object range, so the schema cannot
refuse it and only validation catches it. generic-v4 adds a prompt rule against
it (#338); whether that works is what running v4 tests.

`ALIASED_TYPE` — a DataCite spelling like `IsNewVersionOf` or `References`. The
enum declares these as `aliases` (#223), so the schema says the name is valid
and `linkml-validate` rejects it anyway. `normalise_enum_aliases` rewrites them
on the write path, so this **should not survive** into a written record; if it
does, the normaliser did not run.

`UNKNOWN_TYPE` — `related_to`, which is not an alias of anything. The vocabulary
is DataCite's 36 relation types and is deliberately specific: there is no
generic "is related to", so this is a real generation failure and
`tests/test_enum_alias_normalisation.py` leaves it failing rather than
normalising it into something valid.

The point of separating them is that the rerun's answer differs per mode.
`ALIASED_TYPE` recurring means a pipeline regression; `UNKNOWN_TYPE` recurring
means the model still reached for a word the vocabulary lacks; `INLINE_TARGET`
recurring under v4 means the rule did not work, which the v4 analysis plan says
should retire it.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")

INLINE_TARGET = "inline_target"
ALIASED_TYPE = "aliased_type"
UNKNOWN_TYPE = "unknown_type"

#: Which version, if any, carries a rule aimed at each mode. `None` means no
#: prompt rule addresses it — it is either a pipeline concern or a real failure.
ADDRESSED_BY = {
    INLINE_TARGET: "generic_v4",
    ALIASED_TYPE: None,
    UNKNOWN_TYPE: None,
}


@functools.lru_cache(maxsize=1)
def _vocabulary() -> tuple[frozenset[str], dict[str, str]]:
    """Permissible values, and the alias table that maps onto them."""
    from linkml_runtime import SchemaView
    view = SchemaView(str(FULL_SCHEMA))
    for name in view.all_enums():
        if "elationship" in name:
            values = view.get_enum(name).permissible_values
            aliases = {alias: key
                       for key, value in values.items()
                       for alias in (getattr(value, "aliases", None) or [])}
            return frozenset(values), aliases
    return frozenset(), {}


@dataclass(frozen=True)
class Defect:
    index: int
    mode: str
    detail: str

    @property
    def addressed_by(self) -> str | None:
        return ADDRESSED_BY.get(self.mode)


def inspect(record: dict[str, Any]) -> list[Defect]:
    """Every `related_datasets` defect in a record, in entry order.

    Reports all of them rather than stopping at the first: rep2 carries one bad
    entry among three good ones, and a checker that stopped early would call it
    fixed as soon as the ordering changed.
    """
    values, aliases = _vocabulary()
    entries = record.get("related_datasets") or []
    if isinstance(entries, dict):
        entries = [entries]
    out: list[Defect] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        target = entry.get("target_dataset")
        if isinstance(target, (dict, list)):
            out.append(Defect(index, INLINE_TARGET,
                              "target_dataset holds an object where the schema "
                              "declares a string"))
        kind = entry.get("relationship_type")
        if isinstance(kind, str) and kind not in values:
            if kind in aliases:
                out.append(Defect(index, ALIASED_TYPE,
                                  f"{kind!r} is a declared alias of "
                                  f"{aliases[kind]!r}; the write-path "
                                  "normaliser should have rewritten it"))
            else:
                out.append(Defect(index, UNKNOWN_TYPE,
                                  f"{kind!r} is not a permissible value and not "
                                  "a declared alias"))
    return out


def summarise(defects: list[Defect]) -> str:
    """One line per mode, naming what would address it."""
    if not defects:
        return "related_datasets: no defects"
    counts: dict[str, int] = {}
    for defect in defects:
        counts[defect.mode] = counts.get(defect.mode, 0) + 1
    lines = []
    for mode in (INLINE_TARGET, ALIASED_TYPE, UNKNOWN_TYPE):
        if mode not in counts:
            continue
        owner = ADDRESSED_BY[mode] or "no prompt rule; see #292"
        lines.append(f"  {mode:14s} x{counts[mode]}  addressed by: {owner}")
    return "related_datasets defects:\n" + "\n".join(lines)
