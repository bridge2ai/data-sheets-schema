"""Canonical hashes for the prompt files each condition is defined by (#432).

The render gate (#425, #430) proves a run's recorded instruction is what its
spec renders *from the files as they stand now*. That catches an instruction
edited after rendering. It cannot catch one edited **before**: add a paragraph
to `d4d_generic_arm_prompt_v3.md`, render, run, record — and re-rendering reads
the same edited file and reports `match`. The record is self-consistent and the
condition label is a lie.

What is missing is a value the prompt file can be checked *against*, rather than
only against itself. That is all this module is: a versioned pin per file, and
the vocabulary to say which of four things a hash is.

- ``canonical``   — the pinned hash for that file.
- ``superseded``  — a hash this file used to be pinned at. A run made under the
  prompt of the day is not a defect; conditions are allowed to evolve, and the
  study's whole point is that they do so visibly and in order.
- ``uncanonical`` — a hash that was never pinned. The finding: whatever
  produced it was not a published version of its condition.
- ``missing``     — pinned, but there are no bytes to check: the file has been
  deleted, or a record named it and hashed nothing. Evidence of an absence, as
  against the next one (#437).
- ``unpinned``    — no pin exists for that path. Reported, never failed on the
  record side; the registry is not required to be exhaustive and a missing pin
  is an absence of evidence. On the working-tree side it *is* failed, because a
  condition prompt nobody pinned is text that was never declared.

**What this does not do.** The pin lives in the repo, so anyone who can edit a
prompt file can also rotate its pin. This is not tamper-proofing and nothing
here should be read as claiming it is. What it buys is that the two are now
*separate, deliberate acts*, and rotating a pin leaves a dated line in a small
file that a reviewer reads, rather than a paragraph inside a 200-line prompt
that they do not. `pinned_at_commit` makes each pin re-derivable with
`git show <commit>:<path>`, so the registry can be audited against history
instead of trusted.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import subprocess
from pathlib import Path
from typing import Any

import copy

import yaml

REGISTRY = Path("src/download/prompts/canonical_hashes.yaml")

CANONICAL = "canonical"
SUPERSEDED = "superseded"
UNCANONICAL = "uncanonical"
UNPINNED = "unpinned"
# Pinned, but there are no bytes to check: the file has been deleted, or the
# record named it and hashed nothing. Distinct from `unpinned`, which is an
# absence of evidence — this is evidence of an absence (#437).
MISSING = "missing"


def sha256_of(path: Path) -> str | None:
    if not path or not Path(path).exists():
        return None
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalise(path: str | Path) -> str:
    """Registry key for a path: repo-relative, posix.

    Records store the path the launcher passed, which is repo-relative in every
    real run and absolute in tests. Keying on the basename instead would be
    simpler and wrong — two files can share a name, and the pin would then
    vouch for the wrong one.
    """
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            return p.as_posix()
    return p.as_posix()


#: Parsed registries, keyed on (path, mtime_ns, size) — see `load` (#439).
_REGISTRY_CACHE: dict[tuple[str, int, int], dict[str, Any]] = {}


def _empty() -> dict[str, Any]:
    return {"hash_algorithm": "sha256", "files": {}}


def load(registry: Path = REGISTRY) -> dict[str, Any]:
    """The pin registry, parsed once per (path, mtime, size) (#439).

    `entry_for` and `status_of_hash` each call this, and a corpus check calls
    them once per record: 163 lookups re-parsed the file 239 times.

    Cached, unlike the deliberately un-memoised `bundle_drift` (#469), and the
    difference is what the reader is *for*. `bundle_drift` exists to notice
    that a file's bytes changed, so a cache would defeat it. Nothing here is
    watching the registry for change — it is a checked-in declaration, read to
    compare *other* files against. Keyed on mtime and size so a rotation is
    picked up anyway, and `pin` clears the cache outright so a write is visible
    within the same tick, which mtime granularity alone would not guarantee.

    A copy is returned. Callers that mutated the result would otherwise be
    editing every later caller's view of the file.
    """
    path = Path(registry)
    try:
        stat = path.stat()
    except OSError:
        return _empty()
    key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    hit = _REGISTRY_CACHE.get(key)
    if hit is None:
        hit = yaml.safe_load(path.read_text(encoding="utf-8")) or _empty()
        _REGISTRY_CACHE[key] = hit
    return copy.deepcopy(hit)


def pins(registry: Path = REGISTRY) -> dict[str, dict]:
    return (load(registry).get("files") or {})


def entry_for(path: str | Path, registry: Path = REGISTRY) -> dict | None:
    return pins(registry).get(normalise(path))


def status_of_hash(path: str | Path, sha: str | None,
                   registry: Path = REGISTRY) -> tuple[str, str | None]:
    """What a *recorded* hash is, relative to the pin for its file.

    Takes the hash rather than reading the file, because the question a record
    asks is about bytes that no longer have to exist on disk.
    """
    entry = entry_for(path, registry)
    if entry is None:
        return UNPINNED, f"no canonical hash pinned for {normalise(path)}"
    if not sha:
        return MISSING, (f"{normalise(path)} is pinned, but no hash was "
                         "recorded for it — the run named a prompt file it did "
                         "not read")
    if sha == entry.get("sha256"):
        return CANONICAL, None
    for old in entry.get("superseded") or []:
        if old.get("sha256") == sha:
            return SUPERSEDED, (
                f"{normalise(path)} was pinned at {sha[:12]}… until "
                f"{old.get('retired_on', 'an unrecorded date')}; it is now "
                f"{str(entry.get('sha256'))[:12]}…")
    return UNCANONICAL, (
        f"{normalise(path)} hashed {sha[:12]}…, which is neither the pinned "
        f"{str(entry.get('sha256'))[:12]}… nor any hash it was pinned at "
        "before; that file was not a published version of its condition")


def disk_status(path: str | Path,
                registry: Path = REGISTRY) -> tuple[str, str | None]:
    """What the file *on disk* is, relative to its pin.

    `uncanonical` here means the working tree carries a prompt that no pin
    vouches for — an edit that has not been declared. This is the repo-state
    check; `status_of_hash` is the record check, and they answer different
    questions.
    """
    sha = sha256_of(Path(path))
    if sha is None:
        # A pinned file that has been deleted is not an absence of evidence:
        # the condition's declared text is gone, which is a stronger finding
        # than never having pinned it (#437).
        if entry_for(path, registry) is not None:
            return MISSING, (f"{normalise(path)} is pinned but not on disk; "
                             "the declared text of its condition is gone")
        return UNPINNED, f"{normalise(path)} is neither pinned nor on disk"
    return status_of_hash(path, sha, registry)


def registered_paths(registry: Path = REGISTRY) -> list[str]:
    return sorted(pins(registry))


def prompt_files() -> list[Path]:
    """Every prompt file a condition can consume, from the condition registry.

    Derived rather than listed, for the reason `condition_of` records: a
    written-out list knew only v1, v2 and tuned, and every v3 and v4 run fell
    through it silently (#340). A new condition therefore arrives here already
    pinnable, and `test_every_condition_prompt_is_pinned` fails until it is
    actually pinned.
    """
    from data_sheets_schema.api_runner import (COMPONENTS, CONDITION_PROMPTS,
                                               TUNED_PROMPT)

    files = set(CONDITION_PROMPTS.values()) | {TUNED_PROMPT}
    if COMPONENTS.is_dir():
        files |= {p for p in COMPONENTS.glob("*.md") if p.name != "README.md"}
    return sorted(files, key=lambda p: p.as_posix())


def check_disk(paths: list[Path] | None = None,
               registry: Path = REGISTRY) -> list[dict]:
    """Every condition prompt on disk against its pin. One row each."""
    rows = []
    for path in paths if paths is not None else prompt_files():
        status, why = disk_status(path, registry)
        rows.append({"path": normalise(path), "status": status, "reason": why,
                     "sha256": sha256_of(Path(path))})
    return rows


def _git(*args: str) -> str | None:
    """Run a git command, or None if git cannot answer (not a repo, no git)."""
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True,
                             timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _head_commit() -> str | None:
    out = _git("rev-parse", "HEAD")
    return (out or "").strip() or None


def _is_dirty(path: Path) -> bool:
    """Does the working tree differ from HEAD for this file?

    `pinned_at_commit` is offered as the audit route — `git show <commit>:<path>`
    should reproduce the pinned bytes. Pinning an uncommitted edit would name a
    commit that hashes to something else, and produce the wrong answer for
    exactly the case the registry exists to catch (#438).
    """
    out = _git("status", "--porcelain", "--", str(path))
    return bool((out or "").strip())


def pin(path: str | Path, reason: str, registry: Path = REGISTRY,
        today: str | None = None) -> dict:
    """Declare the file's current bytes canonical, retiring the previous pin.

    Rotation rather than overwrite. Dropping the old hash would make every
    record written under it read `uncanonical` the moment a prompt is edited —
    the same retroactive-failure error the live-provenance cutoff exists to
    avoid, and it would push anyone hitting it toward silencing the check.

    `reason` is required and not defaulted. A pin whose diff says only that a
    hash changed records nothing a reviewer could not compute; the sentence
    saying *why* the condition moved is the part worth versioning.
    """
    if not reason or not reason.strip():
        raise ValueError("a pin needs a reason — see the docstring")
    p = Path(path)
    sha = sha256_of(p)
    if sha is None:
        raise FileNotFoundError(f"{p} is not on disk; nothing to pin")
    if _is_dirty(p):
        raise ValueError(
            f"{p} has uncommitted changes. Commit the prompt first, then pin "
            "it: the pin records the commit it was taken at and offers "
            "`git show <commit>:<path>` as the way to audit it, which is false "
            "for bytes that are not in history (#438). A canonical text that "
            "cannot be found in the repository's history is not canonical.")
    today = today or _dt.date.today().isoformat()

    data = load(registry)
    data.setdefault("hash_algorithm", "sha256")
    files = data.setdefault("files", {})
    key = normalise(p)
    prev = files.get(key)
    if prev and prev.get("sha256") == sha:
        return {"path": key, "status": "unchanged", "sha256": sha}

    superseded = list((prev or {}).get("superseded") or [])
    if prev and prev.get("sha256"):
        superseded.append({"sha256": prev["sha256"],
                           "pinned_on": prev.get("pinned_on"),
                           "retired_on": today,
                           "reason": prev.get("reason")})
    files[key] = {"sha256": sha, "bytes": p.stat().st_size,
                  "pinned_on": today, "pinned_at_commit": _head_commit(),
                  "reason": reason.strip()}
    if superseded:
        files[key]["superseded"] = superseded

    Path(registry).parent.mkdir(parents=True, exist_ok=True)
    Path(registry).write_text(
        _HEADER + yaml.safe_dump(data, sort_keys=True, width=88),
        encoding="utf-8")
    # Cleared outright rather than relying on the mtime key: a rotation
    # followed by a read within the same filesystem tick would otherwise serve
    # the pre-rotation pins, and a pin nobody can see is worse than no cache.
    _REGISTRY_CACHE.clear()
    return {"path": key, "status": "pinned" if prev else "added",
            "sha256": sha, "previous": (prev or {}).get("sha256")}


_HEADER = """\
# Canonical hashes for the prompt files the study's conditions are defined by.
#
# Written by `d4d api prompts pin`, read by `d4d api prompts check` (the repo
# gate) and by `d4d runs check` (the record gate). See
# src/data_sheets_schema/prompt_registry.py for what each status means and,
# just as importantly, what this file does not prove.
#
# Editing a prompt file without rotating its pin fails
# tests/test_prompt_registry.py. That is the point: the edit and the
# declaration that it is the new canonical text are two acts, and the second
# one is small enough to read.
"""
