"""Refuse to generate a run that exists on another git ref but not on disk (#795).

Run data lives untracked in the working tree until its data PR merges. On
2026-08-30 (UTC) the v7 canary directories were committed on a data branch
and `git checkout main` removed them from the working tree while a sweep
held a lock; the sweep saw no AI_READI rep1 and generated a second run under
the same label. The originals were safe on the branch; the duplicate cost
~$15 and could never be told apart by label. This guard is the check the
sweep lacked: a label whose core directory (`{method}_core/{label}`) is
tracked on any local or remote-tracking ref but is neither in the working
tree nor archived under data/ATTIC/ is refused with the ref named. It runs
once before a batch spends and again before each run (#799), since the
checkout can happen while a batch is live. A deliberate removal (#511)
looks the same from here; `--no-branch-guard` is the override, and says so.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

CONCAT = Path("data/d4d_concatenated")
ATTIC = Path("data/ATTIC")


def _refs() -> list[str]:
    out = subprocess.run(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return []
    return [r for r in out.stdout.split() if r and not r.endswith("/HEAD")]


def tracked_core_dirs() -> dict[str, set[str]]:
    """ref -> {"{method}_core/{label}", …}: one `ls-tree` per ref over the
    whole concatenated tree, not one per (label, ref) (#800)."""
    found: dict[str, set[str]] = {}
    try:
        refs = _refs()
    except (OSError, subprocess.SubprocessError):
        return {}
    prefix = CONCAT.as_posix() + "/"
    for ref in refs:
        out = subprocess.run(["git", "ls-tree", "-d", "--name-only", f"{ref}:{CONCAT.as_posix()}"],
                             capture_output=True, text=True)
        if out.returncode != 0:
            continue
        methods = [m for m in out.stdout.split() if m.endswith("_core")]
        dirs: set[str] = set()
        for m in methods:
            sub = subprocess.run(["git", "ls-tree", "-d", "--name-only", f"{ref}:{CONCAT.as_posix()}/{m}"],
                                 capture_output=True, text=True)
            dirs.update(f"{m}/{lab}" for lab in sub.stdout.split())
        if dirs:
            found[ref] = dirs
    return found


def _archived(label: str) -> bool:
    return ATTIC.exists() and any(p.name == label for p in ATTIC.rglob(label) if p.is_dir())


def runs_on_other_refs(runs: list[tuple[str, str]], tracked: dict[str, set[str]] | None = None) -> list[tuple[str, str, str]]:
    """(label, method, ref) for each (label, method) whose core directory is
    tracked on some ref but neither on disk nor archived. `tracked` may be
    passed from `tracked_core_dirs()` so a batch queries git once."""
    tracked = tracked_core_dirs() if tracked is None else tracked
    out: list[tuple[str, str, str]] = []
    for label, method in dict.fromkeys(runs):
        key = f"{method}_core/{label}"
        if (CONCAT / key).exists() or _archived(label):
            continue
        for ref, dirs in tracked.items():
            if key in dirs:
                out.append((label, method, ref))
                break
    return out


def message(found: list[tuple[str, str, str]]) -> str:
    lines = ["these runs exist on a git ref but not in the working tree (#795):"]
    lines += [f"   {method}_core/{label}  —  tracked on {ref}" for label, method, ref in found]
    lines.append("   Generating them again would write a second run under the same label. "
                 "Merge that ref or check the directories out first; never switch branches "
                 "while a sweep is live. A run removed on purpose (#511) looks the same from "
                 "here: pass --no-branch-guard to say so.")
    return "\n".join(lines)
