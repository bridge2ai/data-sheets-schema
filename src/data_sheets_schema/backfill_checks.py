"""Recompute the three post-generation checks for records that predate them.

#544, #546 and #547 landed within a day of each other, each adding a block that
`d4d api run` writes from then on. Nothing gave those blocks to the 122 records
already on disk, so `d4d runs check` reported the whole corpus as unknown —
including the 15 agentic records whose playbook *does* run the pair checker and
whose result is the arm comparison that motivated #544 in the first place.

## A backfilled verdict is a different claim

The runner's block is attested by the run: it was computed from the bytes the
run produced, at the moment it produced them. A backfilled block is computed
today from the bytes on disk now. Where those are the same bytes the two claims
coincide, and where they are not they must not be confused — so every block
this writes carries `recorded_by: backfill_checks`, the same distinction
`backfill-effort` draws between observed and asserted (#448, #470).

## Grounding is not backfillable for a drifted record

59 records name an input bundle whose bytes have since changed (#452). Checking
their identifiers against today's bundle would answer a question about a file
the run never read, and would report as ungrounded values that were in the
bundle when it was consumed — or worse, as grounded values that were not.

Those records get `checked: false` with the drift named. This is the one place
where "we cannot say" is the only honest answer, and it is why this is not a
single pass over everything.

The pair and report checks are unaffected: both read the run's own outputs,
whose staleness is already detectable by their pinned hashes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

#: Written into every block this produces. The runner writes its own blocks
#: without it, so absence means "attested by the run".
RECORDED_BY = "backfill_checks"

BLOCKS = ("pair_consistency", "report_claims", "grounding")


def _split_header(text: str) -> tuple[str, str]:
    """(leading comment lines, the rest).

    The writer emits two comment lines that `yaml.safe_dump` would drop. They
    are re-emitted verbatim rather than reconstructed, so a record carrying
    more than the standard two keeps them.
    """
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and (lines[i].startswith("#") or not lines[i].strip()):
        i += 1
    return "".join(lines[:i]), "".join(lines[i:])


def record_paths(provenance: Path) -> dict[str, Path]:
    """The artifacts a provenance record describes, from its own location.

    The core record and the report sit beside it under `{method}_core/{label}/`;
    the full record is under `{method}/{label}/`. Derived rather than read from
    the record because older records do not all name their outputs.
    """
    label_dir = provenance.parent
    project = provenance.name[: -len("_provenance.yaml")]
    core_method = label_dir.parent.name
    method = core_method[: -len("_core")] if core_method.endswith("_core") \
        else core_method
    full_dir = label_dir.parent.parent / method / label_dir.name
    return {"project": project,
            "core": label_dir / f"{project}_d4d_core.yaml",
            "report": label_dir / f"{project}_reconciliation.md",
            "full": full_dir / f"{project}_d4d.yaml"}


def declared_bundle(record: dict[str, Any]) -> Path | None:
    """The bundle the record says it read, if it says."""
    inputs = record.get("inputs") or {}
    path = inputs.get("bundle_path") or inputs.get("bundle")
    return Path(path) if path else None


def compute(provenance: Path, declared: dict[str, set[str]] | None = None
            ) -> dict[str, Any]:
    """The three blocks for one record, or reasons they cannot be computed."""
    from data_sheets_schema.grounding import check_run
    from data_sheets_schema.identifiers import uriorcurie_slots
    from data_sheets_schema.provenance import (CORE_SCHEMA, FULL_SCHEMA,
                                                _md5, _sha256)
    from data_sheets_schema.report_claims import check_report, declared_slots

    text = provenance.read_text(encoding="utf-8")
    record = yaml.safe_load(_split_header(text)[1]) or {}
    paths = record_paths(provenance)
    full, core, report = paths["full"], paths["core"], paths["report"]
    out: dict[str, Any] = {}

    # --- pair consistency -------------------------------------------------
    if not (full.exists() and core.exists()):
        missing = [str(p) for p in (full, core) if not p.exists()]
        out["pair_consistency"] = {"checked": False, "ran": False,
                                   "reason": f"missing: {', '.join(missing)}",
                                   "recorded_by": RECORDED_BY}
    else:
        from data_sheets_schema.d4d_pair_consistency import (
            load_pair_schema, validate_pair_data,
        )
        pair = load_pair_schema(FULL_SCHEMA, CORE_SCHEMA)
        rep = validate_pair_data(
            yaml.safe_load(full.read_text(encoding="utf-8")) or {},
            yaml.safe_load(core.read_text(encoding="utf-8")) or {}, pair)
        out["pair_consistency"] = {
            "ran": True, "consistent": rep.passed, "errors": len(rep.errors),
            "warnings": len(rep.warnings),
            "identity_slots": len(rep.identity_slots),
            "findings": [{"code": i.code, "path": i.path,
                          "message": i.message[:200]} for i in rep.errors[:20]],
            "findings_truncated": max(0, len(rep.errors) - 20) or None,
            "artifacts": {"full": {"path": str(full), "md5": _md5(full)},
                          "core": {"path": str(core), "md5": _md5(core)}},
            # The schema, not only the records. "The pair is consistent" is a
            # claim about two files *against a set of identity slots*, and
            # those come from the schema — #426 is the same lesson for
            # validation verdicts. Without this, a backfilled verdict cannot
            # be told apart from one reached against a schema that has since
            # moved, which is precisely the question a reader asks of a
            # recomputed result.
            "schema": {"full_sha256": _sha256(FULL_SCHEMA),
                       "core_sha256": _sha256(CORE_SCHEMA)},
            "recorded_by": RECORDED_BY}

    # --- report claims ----------------------------------------------------
    if not report.exists():
        out["report_claims"] = {"checked": False,
                                "reason": "no reconciliation report",
                                "recorded_by": RECORDED_BY}
    else:
        block = check_report(
            report,
            yaml.safe_load(full.read_text(encoding="utf-8")) if full.exists() else {},
            yaml.safe_load(core.read_text(encoding="utf-8")) if core.exists() else {},
            declared if declared is not None else declared_slots())
        block["artifacts"] = {"report": {"path": str(report),
                                         "md5": _md5(report)}}
        block["recorded_by"] = RECORDED_BY
        out["report_claims"] = block

    # --- grounding --------------------------------------------------------
    bundle = declared_bundle(record)
    if bundle is None:
        out["grounding"] = {"checked": False,
                            "reason": "the record names no input bundle",
                            "recorded_by": RECORDED_BY}
    elif not bundle.exists():
        out["grounding"] = {"checked": False,
                            "reason": f"declared bundle absent: {bundle}",
                            "recorded_by": RECORDED_BY}
    else:
        recorded = ((record.get("inputs") or {}).get("bundle_md5")
                    or (record.get("inputs") or {}).get("bundle_hash"))
        if recorded and _md5(bundle) != recorded:
            # The whole reason this is not one uniform pass. See module docstring.
            out["grounding"] = {
                "checked": False,
                "reason": ("bundle drifted since the run; grounding against "
                           "today's bytes would test a file the run never read"),
                "recorded_by": RECORDED_BY}
        else:
            block = check_run(full, core, bundle, uriorcurie_slots())
            if block.get("checked"):
                block["artifacts"] = {"bundle": {"path": str(bundle),
                                                 "md5": _md5(bundle)}}
                if not recorded:
                    # Not the same claim as a verified match. The bundle is
                    # current *as far as anyone can tell*, which for a record
                    # that pinned no hash is not very far.
                    block["bundle_hash_basis"] = "the record pinned no hash"
            block["recorded_by"] = RECORDED_BY
            out["grounding"] = block
    return out


def apply(provenance: Path, blocks: dict[str, Any],
          overwrite: bool = False) -> bool:
    """Write the blocks into the record. Returns whether anything changed.

    Rewrites through `safe_dump` after splitting the leading comments off and
    re-emitting them verbatim, so the header the reader relies on survives.
    """
    text = provenance.read_text(encoding="utf-8")
    header, body = _split_header(text)
    record = yaml.safe_load(body)
    # Refuse rather than write. `safe_load` returning None or a non-mapping for
    # a file with content means the record did not parse as expected, and
    # writing then would replace a provenance record with nothing but the three
    # blocks — losing the run it describes to make room for a note about it.
    if not isinstance(record, dict) or (body.strip() and not record):
        raise ValueError(f"{provenance} did not parse as a mapping; not written")
    changed = False
    for name in BLOCKS:
        if name in record and not overwrite:
            continue
        if name in blocks:
            record[name] = blocks[name]
            changed = True
    if not changed:
        return False
    provenance.write_text(
        header + yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    return True


def summarise(blocks: dict[str, Any]) -> str:
    """A one-line account of what was computed, for the report line."""
    bits = []
    pair = blocks.get("pair_consistency") or {}
    if pair.get("ran"):
        bits.append("pair ok" if pair.get("consistent")
                    else f"pair {pair.get('errors')} err")
    else:
        bits.append("pair —")
    rep = blocks.get("report_claims") or {}
    bits.append(f"report {len(rep.get('findings') or [])}" if rep.get("checked")
                else "report —")
    gr = blocks.get("grounding") or {}
    if gr.get("checked"):
        absent = (gr.get("distinct") or gr.get("counts") or {}).get("absent", 0)
        bits.append(f"ungrounded {absent}")
    else:
        bits.append("grounding —")
    return " · ".join(bits)
