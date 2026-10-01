"""Bytes a run recorded by hash that no commit reachable from main holds,
kept as a committed artefact and checked by hash (#3788, #3953).

`provenance.committed_bytes_for` recovers a file's bytes by path and hash
from the versions reachable from HEAD. A run made on a branch that was later
squash-merged can have read a version that only the branch's own commits
held: the squash keeps the branch's final state, not the intermediate one
the run read, and no remote ref reaches the branch commits. Where those
bytes are recovered, they are committed under `notes/reconstructed_bytes/`
(gzip-compressed) with a provenance sidecar, and this module reads them
from there. That needs no git and no branch, so a fresh clone, a shallow
clone and CI read the same bytes. They are accepted only where the
artefact hashes to its recorded sha256 and its decompressed bytes hash to
every hash the entry declares and every hash the caller gives.

One entry today. The 2026-08-13 generic-v4 rep1 VOICE run recorded merged-
schema sha256 fc3ca873… (`schema.full_sha256`) at repo commit 4892fcd3 with
a dirty tree. Those bytes are `data_sheets_schema_all.yaml` at 09da326f32,
the second commit of the PR #543 branch ("Write identifiers as CURIEs where
a prefix is declared", 2026-08-14T19:04:47Z, 18 minutes after the record's
`record_generated_at`), which #543 squash-merged as 0a35dfde1 with the
branch's later schema (sha256 0389e9c3…). Neither 09da326f32 nor 4892fcd3
(the branch's first commit) is reachable from a remote ref. The bytes are
the `data_sheets_schema_all.yaml` blob befe38d9 (sha256 992cbb48…, the
blob at 4892fcd3 and also at c327fd0d, which is on main) with the `ROR`,
`ORCID` and `doi` prefix declarations inserted after line 55, nothing else.
The entry records that base and edit as provenance, and `rebuild` applies
it so a test can show, in a clone with history, that the committed
artefact is exactly that edit of a commit on main. GitHub still served
09da326f32 on 2026-09-30, and its file hashed to fc3ca873….
"""
from __future__ import annotations

import gzip
import hashlib
import subprocess
from typing import Any

#: One entry per recovered version: the path, the hashes of the bytes, the
#: committed artefact holding them (repository-relative, gzip) and its own
#: sha256, its provenance sidecar, and how the bytes were made: the commit
#: on main whose blob of that path is the base, the line edits that turn
#: the base into those bytes (`at` is a 0-based line index into the base,
#: `delete` lines are removed there and `insert` put in their place;
#: applied in order to the base's lines, indices into the base), and where
#: the bytes were observed.
RECONSTRUCTIONS: tuple[dict[str, Any], ...] = (
    {
        "path": "src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
        "sha256": "fc3ca87375af6954cc47c27910574d1b67f5a2391697bf45be8097326a9e4015",
        "md5": "0c5e049f5547a0b490683efb37f906f8",
        "artefact": "notes/reconstructed_bytes/data_sheets_schema_all_fc3ca873.yaml.gz",
        "artefact_sha256": "b5cd76321a2fbbf47aace3b3450026795b00dc21b253b2e042f59bd587303a5b",
        "provenance": "notes/reconstructed_bytes/data_sheets_schema_all_fc3ca873.provenance.yaml",
        "base_commit": "c327fd0dfc5fd6e7341c96002dde83b044d6e063",
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
                        "squash-merged as 0a35dfde1; reachable from no remote ref"),
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
    git propagates, as `committed_bytes_for`'s does). Used only by
    `rebuild`, to check an entry's recipe; reading the bytes needs no git."""
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


def rebuild(entry: dict[str, Any]) -> bytes | None:
    """The entry's base blob with its edits applied, or None where the base
    commit is not in this clone (a shallow checkout). The recipe the
    committed artefact is checked against; not what callers read."""
    base = _base_blob(entry["base_commit"], entry["path"])
    return None if base is None else apply_edits(base, entry["edits"])


def _artefact_bytes(entry: dict[str, Any]) -> bytes | None:
    """The entry's committed artefact, decompressed, or None where it is not
    in this tree, does not hash to `artefact_sha256`, or is not gzip. An
    OSError reading a file that is there propagates."""
    from data_sheets_schema.provenance import _REPO_ROOT
    file = _REPO_ROOT / entry["artefact"]
    if not file.is_file():
        return None
    packed = file.read_bytes()
    if hashlib.sha256(packed).hexdigest() != entry["artefact_sha256"]:
        return None
    try:
        return gzip.decompress(packed)
    except (OSError, EOFError):
        return None


def reconstructed_bytes_for(path: str, md5: str | None = None,
                            sha256: str | None = None) -> tuple[bytes, dict[str, Any]] | None:
    """(bytes, entry) for the recorded version of `path` whose hashes match
    every one given, read from its committed artefact; None where none is
    recorded, the artefact is missing, or the artefact or its bytes do not
    hash to what the entry and the caller both name (a wrong artefact is
    refused, never trusted). The entry carries `matched_on`, the artefact,
    the base commit, the edits and where the bytes were observed. An
    OSError reading an artefact that is there propagates."""
    if not md5 and not sha256:
        return None
    for entry in RECONSTRUCTIONS:
        if entry["path"] != path:
            continue
        given = {k: v for k, v in (("md5", md5), ("sha256", sha256)) if v}
        if any(entry.get(k) != v for k, v in given.items()):
            continue
        data = _artefact_bytes(entry)
        if data is None:
            return None
        if any(getattr(hashlib, k)(data).hexdigest() != entry[k] for k in ("md5", "sha256")):
            return None
        return data, {**entry, "matched_on": sorted(given)}
    return None
