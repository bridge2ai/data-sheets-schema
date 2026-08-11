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
- ``unpinned``    — no pin exists for that path. Reported, never failed; the
  registry is not required to be exhaustive and a missing pin is an absence of
  evidence.

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

import yaml

REGISTRY = Path("src/download/prompts/canonical_hashes.yaml")

CANONICAL = "canonical"
SUPERSEDED = "superseded"
UNCANONICAL = "uncanonical"
UNPINNED = "unpinned"


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


def load(registry: Path = REGISTRY) -> dict[str, Any]:
    if not Path(registry).exists():
        return {"hash_algorithm": "sha256", "files": {}}
    return yaml.safe_load(Path(registry).read_text(encoding="utf-8")) or {
        "hash_algorithm": "sha256", "files": {}}


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
        return UNPINNED, "no hash recorded to compare"
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
        return UNPINNED, f"{normalise(path)} is not on disk"
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


def _head_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


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
