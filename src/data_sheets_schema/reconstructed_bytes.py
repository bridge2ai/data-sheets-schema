"""Bytes a run recorded by hash that no reachable commit holds, rebuilt from
one that does (#3788).

`provenance.committed_bytes_for` recovers a file's bytes by path and hash
from the versions reachable from HEAD. A run made on a branch that was later
squash-merged can have read a version that only the branch's own commits
held: the squash keeps the branch's final state, not the intermediate one
the run read, and no local ref reaches the branch commits. Those bytes are
not lost where they are a known, small edit of a version that *is*
reachable; this module records such edits and rebuilds the bytes from the
reachable blob, accepting the result only where it hashes to every hash
given and every hash the entry declares.

One entry today. The 2026-08-13 generic-v4 rep1 VOICE run recorded merged-
schema sha256 fc3ca873… (`schema.full_sha256`) at repo commit 4892fcd3 with
a dirty tree. Those bytes are `data_sheets_schema_all.yaml` at 09da326f32,
the second commit of the PR #543 branch ("Write identifiers as CURIEs where
a prefix is declared", 2026-08-14T19:04:47Z, 18 minutes after the record's
`record_generated_at`), which #543 squash-merged as 0a35dfde1 with the
branch's later schema (sha256 0389e9c3…) — so no local ref reaches them.
They were fetched from GitHub (the pull request's commit, still served there)
on 2026-09-30 and compared: they are the 4892fcd3 blob with the `ROR`,
`ORCID` and `doi` prefix declarations inserted after line 55, nothing else.
The edit is recorded here rather than the 1.4 MB file, so the rebuild is
offline and checkable, and a wrong entry is refused by its hash rather than
trusted.
"""
from __future__ import annotations

import hashlib
import subprocess
from typing import Any

#: One entry per rebuilt version: the path, the hashes of the bytes rebuilt,
#: the reachable commit whose blob of that path is the base, the line edits
#: that turn the base into those bytes (`at` is a 0-based line index into
#: the base, `delete` lines are removed there and `insert` put in their
#: place; applied in order to the base's lines, indices into the base), and
#: where the rebuilt bytes were observed.
RECONSTRUCTIONS: tuple[dict[str, Any], ...] = (
    {
        "path": "src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
        "sha256": "fc3ca87375af6954cc47c27910574d1b67f5a2391697bf45be8097326a9e4015",
        "md5": "0c5e049f5547a0b490683efb37f906f8",
        "base_commit": "4892fcd3a5e7d805653bf6426c0ac8b8ad173822",
        "edits": (
            {"at": 55, "delete": 0,
             "insert": ("  ROR:\n"
                        "    prefix_prefix: ROR\n"
                        "    prefix_reference: https://ror.org/\n"
                        "  ORCID:\n"
                        "    prefix_prefix: ORCID\n"
                        "    prefix_reference: https://orcid.org/\n"
                        "  doi:\n"
                        "    prefix_prefix: doi\n"
                        "    prefix_reference: https://doi.org/\n")},
        ),
        "observed_at": ("09da326f32aed4bc501355efc7a4a1aee1819257, a commit of the PR #543 branch "
                        "squash-merged as 0a35dfde1; reachable from no local ref"),
        "issue": 3788,
    },
)


def apply_edits(base: bytes, edits: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> bytes:
    """The base's lines with each edit applied; indices name the base's lines."""
    lines = base.decode("utf-8").splitlines(keepends=True)
    out: list[str] = []
    cursor = 0
    for edit in sorted(edits, key=lambda e: e["at"]):
        at, delete = int(edit["at"]), int(edit.get("delete") or 0)
        if at < cursor or at + delete > len(lines):
            raise ValueError(f"edit at line {at} (delete {delete}) does not fit a base of {len(lines)} lines")
        out += lines[cursor:at]
        out.append(edit.get("insert") or "")
        cursor = at + delete
    out += lines[cursor:]
    return "".join(out).encode("utf-8")


def _base_blob(commit: str, path: str) -> bytes | None:
    """`git show commit:path`, or None where git answers that it has no such
    object; `GitUnavailable` where git fails otherwise (an OSError starting
    git propagates, as `committed_bytes_for`'s does)."""
    from data_sheets_schema.provenance import _REPO_ROOT, GitUnavailable
    blob = subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True, check=False,
                          cwd=_REPO_ROOT)
    if blob.returncode == 0:
        return blob.stdout
    err = blob.stderr.decode("utf-8", "replace")
    if ("does not exist in" in err or "exists on disk, but not in" in err or "invalid object name" in err
            or "bad revision" in err or "unknown revision" in err):
        return None
    raise GitUnavailable(f"git show {commit[:12]}:{path}: {err.strip() or 'failed'}")


def reconstructed_bytes_for(path: str, md5: str | None = None,
                            sha256: str | None = None) -> tuple[bytes, dict[str, Any]] | None:
    """(bytes, entry) for the recorded rebuild of `path` whose hashes match
    every one given, or None where none is recorded, its base commit is not
    in this clone, or the rebuild does not hash to what the entry and the
    caller both name (a wrong entry is refused, never trusted). The entry
    carries `matched_on`, the base commit, the edits and where the bytes
    were observed. Raises `GitUnavailable` where git fails other than by
    lacking the base."""
    if not md5 and not sha256:
        return None
    for entry in RECONSTRUCTIONS:
        if entry["path"] != path:
            continue
        given = {k: v for k, v in (("md5", md5), ("sha256", sha256)) if v}
        if any(entry.get(k) != v for k, v in given.items()):
            continue
        base = _base_blob(entry["base_commit"], path)
        if base is None:
            return None
        data = apply_edits(base, entry["edits"])
        if any(getattr(hashlib, k)(data).hexdigest() != entry[k] for k in ("md5", "sha256")):
            return None
        return data, {**entry, "matched_on": sorted(given)}
    return None
