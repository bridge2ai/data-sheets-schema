"""Refuse to generate a run that exists on another git ref but not on disk (#795).

Run data lives untracked in the working tree until its data PR merges. On
2026-08-30 the v7 canary directories were committed on a data branch and
`git checkout main` removed them from the working tree while a sweep held a
lock; the sweep saw no AI_READI rep1 and generated a second run under the
same label. The originals were safe on the branch; the duplicate cost ~$15
and could never be told apart by label. This guard is the check the sweep
lacked: before it spends, every label it would write is looked up in every
local and remote-tracking ref, and a label that is tracked somewhere but is
not on disk is a refusal with the ref named — merge or check it out first.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _refs() -> list[str]:
    out = subprocess.run(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"],
                         capture_output=True, text=True)
    return [r for r in out.stdout.split() if r and not r.endswith("/HEAD")]


def _tracked_on(ref: str, path: str) -> bool:
    out = subprocess.run(["git", "ls-tree", "-d", "--name-only", ref, "--", path],
                         capture_output=True, text=True)
    return out.returncode == 0 and out.stdout.strip() != ""


def runs_on_other_refs(labels: list[str], concat_dir: Path = Path("data/d4d_concatenated"),
                       method: str = "claudecode_agent") -> list[tuple[str, str]]:
    """(label, ref) for each label whose core directory is tracked on some
    ref but absent from the working tree. Empty when git is unavailable —
    the guard is a check on a repository, not a requirement for one."""
    try:
        refs = _refs()
    except (OSError, subprocess.SubprocessError):
        return []
    found: list[tuple[str, str]] = []
    for label in labels:
        rel = (concat_dir / f"{method}_core" / label).as_posix()
        if Path(rel).exists():
            continue
        for ref in refs:
            if _tracked_on(ref, rel):
                found.append((label, ref))
                break
    return found


def message(found: list[tuple[str, str]]) -> str:
    lines = ["these runs exist on a git ref but not in the working tree (#795):"]
    lines += [f"   {label}  —  tracked on {ref}" for label, ref in found]
    lines.append("   Generating them again would write a second run under the same label. "
                 "Merge that ref or check the directories out first; never switch branches "
                 "while a sweep is live.")
    return "\n".join(lines)
