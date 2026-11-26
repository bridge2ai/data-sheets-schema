#!/usr/bin/env python3
"""Scan the files a data PR adds or changes for details that must not be published.

Purpose: the content check that issue #6362 (item 1) found missing. PR #6349 was
  merged with an account name and usage estimates in its notes because nothing read
  the new files for them. This is run before a data PR is proposed for merge.
Inputs: a git checkout (--root) and a base ref (--base); the files examined are the
  ones `git diff --name-only --diff-filter=AMR BASE...HEAD` lists, plus, with
  --worktree, staged, unstaged and untracked files. Or explicit --path arguments.
  Names to look for are given with --name and are never written anywhere by this
  script; further patterns with --pattern 'LABEL::REGEX'.
Outputs: one line per finding on stdout (file:line: kind), a summary, and exit
  status 0 (no finding), 1 (findings) or 2 (usage or read problem).
  A --name hit never prints the matching text.
Serves: issue #6362, the release series 2026-11-25c selection PR. Date: 2026-11-26.

What it looks for in each text file:
  name            each --name, case-insensitive, with '-', '_', ' ' and '.' alike or absent
  home-path       an absolute home-directory path (/Users/<x>/, /home/<x>/, C:\\Users\\<x>\\)
  email           an email address; reported, and counted as a finding only with
                  --fail-on-email (a datasheet legitimately carries its dataset's contact
                  addresses; give a private address, or its local part, as a --name)
  usage           wording about a subscription's usage or allowance
  pattern:<label> each --pattern
A finding on a line that matches an --allow-line regex is reported as allowed and
does not fail the run. A finding on a line that the base ref's version of the same file
already has is reported as "on base" and does not fail the run either: the gate is about
what the PR adds, and the line is listed so that it is not mistaken for clean. With --path
there is no base and every line counts. Binary files are listed as not read.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HOME_PATH = re.compile(r"(/Users/[^/\s\"']+/|/home/[^/\s\"']+/|[A-Za-z]:\\\\?Users\\\\?[^\\\s\"']+)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
USAGE = re.compile(
    r"(weekly (allowance|limit|usage)|usage[_ ]estimate|percent of (the |its )?(weekly|allowance|limit)"
    r"|allowance (used|left|remaining)|/usage\b|rate[- ]limit(ed)? (until|reset))",
    re.IGNORECASE,
)


def folded(name: str) -> re.Pattern[str]:
    """A pattern matching the name whatever separates its parts."""
    parts = [re.escape(part) for part in re.split(r"[-_ .]+", name) if part]
    if not parts:
        raise ValueError("a --name must contain a letter or digit")
    return re.compile(r"[-_ .]?".join(parts), re.IGNORECASE)


def git(root: Path, *args: str) -> list[str]:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return [line for line in done.stdout.split("\0") if line]


def base_lines(root: Path, base: str, relative: str) -> set[str]:
    """The lines of the file at the merge base with `base`; empty if it is not there."""
    merge_base = subprocess.run(["git", "-C", str(root), "merge-base", base, "HEAD"], capture_output=True, text=True)
    if merge_base.returncode != 0:
        return set()
    shown = subprocess.run(["git", "-C", str(root), "show", f"{merge_base.stdout.strip()}:{relative}"], capture_output=True)
    if shown.returncode != 0:
        return set()
    return set(shown.stdout.decode("utf-8", errors="replace").splitlines())


def changed_files(root: Path, base: str, worktree: bool) -> list[str]:
    names = set(git(root, "diff", "--name-only", "-z", "--diff-filter=AMR", f"{base}...HEAD"))
    if worktree:
        names |= set(git(root, "diff", "--name-only", "-z", "--diff-filter=AMR", "HEAD"))
        names |= set(git(root, "diff", "--name-only", "-z", "--diff-filter=AMR", "--cached"))
        names |= set(git(root, "ls-files", "-z", "--others", "--exclude-standard"))
    return sorted(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=".", help="the checkout to read (default: the working directory)")
    parser.add_argument("--base", default="origin/main", help="base ref of the PR (default: origin/main)")
    parser.add_argument("--worktree", action="store_true", help="also read staged, unstaged and untracked files")
    parser.add_argument("--path", action="append", default=[], help="read these files instead of the diff; repeatable")
    parser.add_argument("--name", action="append", default=[], help="a name that must not appear; repeatable; never printed")
    parser.add_argument("--pattern", action="append", default=[], help="LABEL::REGEX, a further pattern; repeatable")
    parser.add_argument("--allow-line", action="append", default=[], help="regex; a finding on a matching line is allowed; repeatable")
    parser.add_argument("--fail-on-email", action="store_true", help="count an email address as a finding")
    parser.add_argument("--exclude", action="append", default=[], help="regex on the file path; matching files are not read; repeatable")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        names = [(f"name[{index}]", folded(name)) for index, name in enumerate(args.name, 1)]
        extra = []
        for item in args.pattern:
            label, separator, regex = item.partition("::")
            if not (separator and label and regex):
                raise ValueError("--pattern must be LABEL::REGEX")
            extra.append((f"pattern:{label}", re.compile(regex)))
        allowed = [re.compile(regex) for regex in args.allow_line]
        excluded = [re.compile(regex) for regex in args.exclude]
        files = sorted(set(args.path)) if args.path else changed_files(root, args.base, args.worktree)
    except (ValueError, re.error, RuntimeError) as exc:
        print(f"cannot start: {exc}", file=sys.stderr)
        return 2

    checks = names + [("home-path", HOME_PATH), ("email", EMAIL), ("usage", USAGE)] + extra
    findings = allowed_findings = reported = on_base = read = 0
    not_read: list[str] = []
    skipped: list[str] = []
    for relative in files:
        if any(regex.search(relative) for regex in excluded):
            skipped.append(relative)
            continue
        path = root / relative
        if not path.is_file():
            not_read.append(f"{relative} (not a file in the checkout)")
            continue
        raw = path.read_bytes()
        if b"\0" in raw[:8192]:
            not_read.append(f"{relative} (binary)")
            continue
        read += 1
        # The file name itself can carry a name too.
        for kind, regex in names:
            if regex.search(relative):
                findings += 1
                print(f"{relative}: {kind} in the file path")
        already = set() if args.path else base_lines(root, args.base, relative)
        for number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
            for kind, regex in checks:
                match = regex.search(line)
                if not match:
                    continue
                shown = "" if kind.startswith("name") else f" {match.group(0)[:80]!r}"
                if kind == "email" and not args.fail_on_email:
                    reported += 1
                    print(f"{relative}:{number}: {kind} (reported only){shown}")
                elif line in already:
                    on_base += 1
                    print(f"{relative}:{number}: {kind} (on base){shown}")
                elif any(allow.search(line) for allow in allowed):
                    allowed_findings += 1
                    print(f"{relative}:{number}: {kind} (allowed){shown}")
                else:
                    findings += 1
                    print(f"{relative}:{number}: {kind}{shown}")

    for item in not_read:
        print(f"not read: {item}")
    print(
        f"files listed {len(files)}, read {read}, excluded {len(skipped)}, not read {len(not_read)}; "
        f"names given {len(names)}; findings {findings}, on base {on_base}, allowed {allowed_findings}, "
        f"reported only {reported}"
    )
    if not names:
        print("no --name was given: the name check did not run")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
