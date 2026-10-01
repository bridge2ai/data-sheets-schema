"""The merged schema a run recorded, read by the hash it recorded (#3931).

A check recomputed after a run asks about the rules that run was given:
which CURIE prefixes its schema declared, which slots it ranged on
`uriorcurie` or on `Person`, which enum aliases its normaliser rewrote. A
schema release moves those rules. Every run records the merged schema it
read (`schema.full_path` with `full_sha256`, else `full_md5`), so a
schema-dependent recompute keys on that hash. It does not key on today's
file, or on the record's declared version: a release's final state
(`release_history.yaml`) is not the version a run made earlier under the
same label read (#3702).

`run_schema_bytes` is the one resolution, first written inside
`removals.run_enum_aliases` (#3702, #3788, #3851, #3953):

1. the file on disk, where its bytes hash to every hash the record gives;
2. a recorded reconstruction (`reconstructed_bytes`): bytes no reachable
   commit holds, committed as a hash-checked artefact and read before git
   is asked, so a fresh or shallow clone reads them too;
3. the committed version of the path whose every recorded hash matches
   (`provenance.committed_bytes_for`);
4. else nothing, and the caller reads today's schema. The basis says so and
   why: the record names no hash, no committed version matches, git cannot
   answer (a shallow clone) or cannot be started at all (#3851), or the
   reconstruction cannot be read. Each failure is this stated fallback,
   never a traceback.

The basis is one mapping wherever it is reported: `source`, the recorded
`path` and hashes, and either a `reason` or what was read (`commit` and
`matched_on` for a git blob; `artefact`, `base_commit`, `matched_on`,
`observed_at` and `reconstruction` for a reconstruction).
"""
from __future__ import annotations

import hashlib
from typing import Any

#: The fallback's `source`: what a caller reads when the run's bytes cannot
#: be recovered.
TODAY = "today's schema"


def run_schema_bytes(record: dict[str, Any] | None) -> tuple[bytes | None, dict[str, Any]]:
    """(bytes, basis): the merged schema the run recorded, from disk, from a
    recorded reconstruction, or from the committed version that matches, in
    that order; (None, basis) where none of them can be read, the basis
    saying today's schema is read instead and why. Every hash the record
    gives must match, so an md5-only record whose file changed on disk goes
    on to git (#3803)."""
    schema = (record or {}).get("schema") if isinstance(record, dict) else None
    schema = schema if isinstance(schema, dict) else {}
    path, sha256, md5 = schema.get("full_path"), schema.get("full_sha256"), schema.get("full_md5")
    sha256 = sha256 if isinstance(sha256, str) and sha256 else None
    md5 = md5 if isinstance(md5, str) and md5 else None
    if not isinstance(path, str) or not path or not (sha256 or md5):
        return None, {"source": TODAY, "reason": "the record names no merged schema by path and hash"}
    hashes = {k: v for k, v in (("sha256", sha256), ("md5", md5)) if v}
    from data_sheets_schema.resources import resource_path
    try:
        on_disk = resource_path(path)
        data = on_disk.read_bytes() if on_disk.is_file() else None
    except OSError:
        data = None
    if data is not None and all(getattr(hashlib, k)(data).hexdigest() == v for k, v in hashes.items()):
        return data, {"source": "the run's schema, on disk", "path": path, **hashes}
    # Bytes no reachable commit holds, committed as a hash-checked artefact
    # (#3788): read before git, which a shallow clone cannot answer (#3953).
    from data_sheets_schema.reconstructed_bytes import reconstructed_bytes_for
    try:
        rebuilt = reconstructed_bytes_for(path, md5=md5, sha256=sha256)
    except OSError as exc:
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": "the run's schema is not on disk and its recorded reconstruction "
                                f"could not be read ({type(exc).__name__}: {exc})"}
    if rebuilt is not None:
        data, entry = rebuilt
        return data, {"source": "the run's schema, reconstructed", "path": path, **hashes,
                      "artefact": entry["artefact"], "base_commit": entry["base_commit"],
                      "matched_on": entry["matched_on"], "observed_at": entry["observed_at"],
                      "reconstruction": f"reconstructed_bytes.RECONSTRUCTIONS (#{entry['issue']})"}
    from data_sheets_schema.provenance import GitUnavailable, committed_bytes_for
    try:
        found = committed_bytes_for(path, md5=md5, sha256=sha256)
    except GitUnavailable as exc:
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": f"the run's schema is not on disk and git cannot answer ({exc})"}
    except OSError as exc:
        # git could not be started at all (not installed, not on PATH, not
        # executable): the same degraded fallback, not a failure (#3851).
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": f"the run's schema is not on disk and git could not be run "
                                f"({type(exc).__name__}: {exc})"}
    if found is None:
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": "no committed version of the path hashes to what the record recorded"}
    data, entry = found
    return data, {"source": "the run's schema, a git blob", "path": path, **hashes,
                  "commit": entry["commit"], "matched_on": entry["matched_on"]}
