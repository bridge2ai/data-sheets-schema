"""Is the schema a run is about to be generated against the real schema?

The digest sent to the model, the schema every record is validated against, and
the identity slots the pair checker uses are all read from the **merged**
schemas — `data_sheets_schema_all.yaml` and `data_sheets_schema_core_all.yaml`.
Those are generated artifacts. The source of truth is
`data_sheets_schema.yaml` and the `D4D_*.yaml` modules it imports.

Nothing checked that the two agree before a generation run. If a module is
edited without regenerating, every record in the arm attests to a digest that
describes an older schema than the repository holds — and there is no field in
the record that could reveal it, because the record correctly hashes the merged
file it actually read.

`make check-sync` exists and is not on the generation path; #521 records a
period when it reported staleness and the remedy it named was a silent no-op.

## Rebuild and compare, not mtime

The check regenerates each merged schema into a temporary directory and
compares the bytes, for the reason `audit-bundles` does the same for bundles
(#446): a timestamp says when a file was written, not what it was written
from. A merged file can be newer than its modules and still be wrong.

This costs a `gen-linkml` invocation per schema — seconds, once per run,
against an arm that takes hours.

## Fatal, unlike the other pre-run checks

Bundle drift, pair divergence, report claims and identifier grounding are all
reported and never fatal, because each describes a record that remains usable
evidence. A stale merged schema is different in kind: it corrupts the run's
central input before a token is spent, and every record produced would have to
be discarded. There is nothing to preserve by continuing.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

#: (merged artifact, source it is generated from, digest class, leading `---`)
#:
#: The document marker is per-schema because the Makefile is: the full-schema
#: rule pipes `---` onto its output and the core rule does not. Assuming both
#: had it made this check report the core schema stale on its first run, for a
#: one-line difference the check itself had introduced.
MERGED_SCHEMAS = (
    (Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml"),
     Path("src/data_sheets_schema/schema/data_sheets_schema.yaml"),
     "Dataset", True),
    (Path("src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"),
     Path("src/data_sheets_schema/schema/data_sheets_schema_core.yaml"),
     "CoreDataset", False),
)

IN_SYNC = "in_sync"
STALE = "stale"
UNCHECKED = "unchecked"


def _regenerate(source: Path, target: Path,
                marker: bool) -> tuple[bool, str | None]:
    """Run the same generation the Makefile runs. (ok, why not)"""
    try:
        result = subprocess.run(
            ["poetry", "run", "gen-linkml", "-o", str(target), "-f", "yaml",
             str(source)],
            capture_output=True, text=True, timeout=600)
    except Exception as exc:                                   # noqa: BLE001
        return False, f"gen-linkml could not run: {exc}"
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[-300:]
        return False, f"gen-linkml failed: {tail}"
    if not target.exists():
        return False, "gen-linkml wrote nothing"
    if marker:
        target.write_text("---\n" + target.read_text(encoding="utf-8"),
                          encoding="utf-8")
    return True, None


def check_one(merged: Path, source: Path, class_name: str,
              marker: bool = False) -> dict[str, Any]:
    """Rebuild `merged` from `source` and compare."""
    from data_sheets_schema import schema_digest

    out: dict[str, Any] = {"merged": str(merged), "source": str(source),
                           "class": class_name}
    if not source.exists():
        return {**out, "status": UNCHECKED,
                "reason": f"source schema {source} is not on disk"}
    if not merged.exists():
        return {**out, "status": STALE,
                "reason": f"{merged} has never been generated"}

    with tempfile.TemporaryDirectory() as tmp:
        # Same filename, because the digest names the schema it came from and
        # a differing name would be a spurious difference.
        rebuilt = Path(tmp) / merged.name
        ok, why = _regenerate(source, rebuilt, marker)
        if not ok:
            return {**out, "status": UNCHECKED, "reason": why}
        same = rebuilt.read_bytes() == merged.read_bytes()
        try:
            live = schema_digest.fingerprint(
                schema_digest.digest_text(class_name, merged))
            # Identical bytes digest identically (the digest is a function of
            # content — `DigestIsAFunctionOfContentTest`), so the rebuilt file
            # is digested only when it differs. Digesting it every time built
            # a SchemaView of a fresh temp path per check, pinned for the
            # life of the process by linkml's method caches (#926) and kept
            # again by the digest's own path-keyed caches.
            fresh = live if same else schema_digest.fingerprint(
                schema_digest.digest_text(class_name, rebuilt))
        except Exception as exc:                               # noqa: BLE001
            return {**out, "status": UNCHECKED,
                    "reason": f"digest could not be computed: {exc}"}
        out["digest"] = live
        out["digest_rebuilt"] = fresh
        if same and live == fresh:
            return {**out, "status": IN_SYNC}
        # Keep the rebuilt file so a human can diff it, rather than reporting
        # a difference and deleting the evidence of it.
        kept = Path(tempfile.mkdtemp(prefix="d4d-schema-rebuild-")) / merged.name
        shutil.copy2(rebuilt, kept)
        return {**out, "status": STALE, "rebuilt_at": str(kept),
                "reason": ("the merged schema differs from a fresh build of "
                           "its source" if not same else
                           "the merged schema matches but its digest does not")}


def check(schemas=MERGED_SCHEMAS) -> list[dict[str, Any]]:
    return [check_one(m, s, c, k) for m, s, c, k in schemas]


def blocking(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows that must stop a generation run.

    `unchecked` blocks as well as `stale`. A gate that cannot run has not
    passed, and the whole point here is that the failure it guards against is
    invisible in the record afterwards.
    """
    return [r for r in rows if r["status"] != IN_SYNC]
