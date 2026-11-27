#!/usr/bin/env python3
"""Scan the files a data PR adds or changes for details that must not be published.

Purpose: the content check that issue #6362 (item 1) found missing. PR #6349 was
  merged with an account name and usage estimates in its notes because nothing read
  the new files for them. This is run before a data PR is proposed for merge.
Inputs: a git checkout (--root) and a base ref (--base). The files examined are the
  ones `git diff --name-only --diff-filter=ACMRT BASE...HEAD` lists, each read as
  committed at HEAD (not from the working tree, which can differ from what would be
  merged). With --worktree the staged, unstaged and untracked files are read from disk
  as well. With --path the named files are read from disk and there is no base.
  Names to look for are given with --name; further patterns with --pattern
  'LABEL::REGEX'. At least one --name is required unless --no-names says the run is
  meant to check paths and wording only.
Outputs: one line per finding on stdout (file:line: kind), the excluded and unread
  files, a summary, and exit status 0 (nothing found and everything listed was
  examined), 1 (a finding, a file that could not be examined, or no file listed at
  all) or 2 (usage problem).
  Nothing printed contains a --name value or the user part of a home path: both are
  replaced in every line of output, file paths included.
Serves: issue #6362, the release series 2026-11-25c selection PR (#6373; hardened after
  its reviews, issues #6375 and #6383). Date: 2026-11-26.

What it looks for, every occurrence on every line:
  name            each --name, case-insensitive, its parts separated by up to four
                  characters that are not letters or digits (so '-', '_', '.', spaces,
                  tabs and the like are alike) or by nothing; also in the file path,
                  and across line breaks, reported once per file as "name across lines"
  home-path       a home-directory or per-user temporary path: /Users/<x>, /home/<x>,
                  C:\\Users\\<x>, ~/<x>, /var/folders, /private/var/folders,
                  /tmp/claude-<n>, and the dash-encoded form -Users-<x>- that session
                  directories use; with plain or JSON-escaped slashes
  email           an email address; reported, and counted as a finding only with
                  --fail-on-email (a datasheet legitimately carries its dataset's contact
                  addresses; give a private address, or its local part, as a --name)
  usage           wording about a subscription's usage, allowance, quota, plan or limits.
                  The list of phrasings is in USAGE below; it is a list, not a guarantee
  pattern:<label> each --pattern

What does not fail the run, and is still listed:
  - a finding on a line that matches an --allow-line regex ("allowed"). A new provenance
    record's `repo.resource_root` line is absolute by design (#1550) and needs one;
  - a finding on a line that the merge base's version of the same file already has
    ("on base"). Each base line gives credit once: a PR that repeats an existing line
    a second time is a finding. A renamed, copied or new file has no base.
What does fail the run besides findings: a listed file that cannot be read; a file with
NUL bytes, unless its path matches --allow-binary (it is scanned as text either way);
a name in the path of an excluded file; no file listed at all, unless --allow-empty.
A symbolic link is examined by its link text, which is what git stores.

Known limits: a name whose parts are separated by markup, by more than four characters,
or written in another order is not found; text inside compressed or encoded content is
not found; the usage list is a list.
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys
from pathlib import Path

SLASH = r"(?:\\?/)"
HOME_PATH = re.compile(
    r"(?<![\w.])" + SLASH + r"(?:Users|home)" + SLASH + r"[^/\\\s\"'<>:,;)]+"
    r"|[A-Za-z]:\\\\?Users\\\\?[^\\\s\"'<>]+"
    r"|(?<![\w/~])~" + SLASH + r"[\w.-]+"
    r"|(?<![\w.])" + SLASH + r"(?:private" + SLASH + r")?var" + SLASH + r"folders\b"
    r"|(?<![\w.])" + SLASH + r"(?:private" + SLASH + r")?tmp" + SLASH + r"claude-\d+"
    r"|(?<![A-Za-z0-9])-(?:Users|home)-[A-Za-z0-9_.]+-"
)
USER_PART = re.compile(r"((?:\\?/|-)(?:Users|home)(?:\\?/|-)|[A-Za-z]:\\\\?Users\\\\?)[^/\\\s\"'<>:,;)-]+")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
USAGE = re.compile(
    r"weekly (?:allowance|limit|usage|cap|quota)"
    r"|usage[_ -](?:estimates?|limits?|caps?)"
    r"|(?:percent|%) of (?:the |its |my |your |a )?(?:weekly|allowance|limit|cap|quota|usage)"
    r"|allowance (?:used|left|remaining)"
    r"|/usage\b"
    r"|rate[- ]limit"
    r"|(?:5|five)[- ]hour (?:limit|window|cap)"
    r"|session limit"
    r"|quota (?:exhausted|reached|left|remaining|used)"
    r"|\b(?:max|pro|team) plan\b"
    r"|\bsubscription",
    re.IGNORECASE,
)
BETWEEN = r"(?:[^A-Za-z0-9\n]|&nbsp;|\\[nt]){0,4}"


def folded(name: str, across_lines: bool = False) -> re.Pattern[str]:
    """A pattern matching the name whatever separates its parts."""
    parts = [re.escape(part) for part in re.split(r"[^A-Za-z0-9]+", name) if part]
    if not parts:
        raise ValueError("a --name must contain a letter or digit")
    return re.compile((r"[^A-Za-z0-9]{0,4}" if across_lines else BETWEEN).join(parts), re.IGNORECASE)


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True)


def listed(root: Path, *args: str) -> list[str]:
    done = run_git(root, *args)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.decode(errors='replace').strip()}")
    return [name for name in done.stdout.decode("utf-8", errors="surrogateescape").split("\0") if name]


def decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=".", help="the checkout to read (default: the working directory)")
    parser.add_argument("--base", default="origin/main", help="base ref of the PR (default: origin/main)")
    parser.add_argument("--worktree", action="store_true", help="also read staged, unstaged and untracked files from disk")
    parser.add_argument("--path", action="append", default=[], help="read these files from disk instead of the diff; repeatable")
    parser.add_argument("--name", action="append", default=[], help="a name that must not appear; repeatable; never printed")
    parser.add_argument("--no-names", action="store_true", help="run without any --name (paths and wording only)")
    parser.add_argument("--pattern", action="append", default=[], help="LABEL::REGEX, a further pattern; repeatable")
    parser.add_argument("--allow-line", action="append", default=[], help="regex; a finding on a matching line is allowed; repeatable")
    parser.add_argument("--allow-binary", action="append", default=[], help="regex on the file path; a binary file matching it does not fail the run")
    parser.add_argument("--allow-empty", action="store_true", help="do not fail when no file is listed")
    parser.add_argument("--fail-on-email", action="store_true", help="count an email address as a finding")
    parser.add_argument("--exclude", action="append", default=[], help="regex on the file path; matching files are not read; repeatable")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not args.name and not args.no_names:
        print("cannot start: give at least one --name, or --no-names to check paths and wording only", file=sys.stderr)
        return 2
    try:
        names = [(f"name[{index}]", folded(name)) for index, name in enumerate(args.name, 1)]
        squeezed_names = [(f"name[{index}]", folded(name, across_lines=True)) for index, name in enumerate(args.name, 1)]
        extra = []
        for item in args.pattern:
            label, separator, regex = item.partition("::")
            if not (separator and label and regex):
                raise ValueError("--pattern must be LABEL::REGEX")
            extra.append((f"pattern:{label}", re.compile(regex)))
        allowed = [re.compile(regex) for regex in args.allow_line]
        allow_binary = [re.compile(regex) for regex in args.allow_binary]
        excluded = [re.compile(regex) for regex in args.exclude]
        merge_base = None
        if args.path:
            sources = [(name, "disk") for name in sorted(set(args.path))]
        else:
            found = run_git(root, "merge-base", args.base, "HEAD")
            if found.returncode != 0:
                raise RuntimeError(f"no merge base of {args.base} and HEAD")
            merge_base = found.stdout.decode().strip()
            committed = listed(root, "diff", "--name-only", "-z", "--diff-filter=ACMRT", f"{merge_base}", "HEAD")
            sources = [(name, "HEAD") for name in sorted(set(committed))]
            if args.worktree:
                on_disk = set(listed(root, "diff", "--name-only", "-z", "--diff-filter=ACMRT", "HEAD"))
                on_disk |= set(listed(root, "diff", "--name-only", "-z", "--diff-filter=ACMRT", "--cached"))
                on_disk |= set(listed(root, "ls-files", "-z", "--others", "--exclude-standard"))
                sources += [(name, "disk") for name in sorted(on_disk)]
    except (ValueError, re.error, RuntimeError) as exc:
        print(f"cannot start: {exc}", file=sys.stderr)
        return 2

    def safe(text: str) -> str:
        """Text as it may be printed: no --name value and no user part of a home path."""
        for _, regex in names:
            text = regex.sub("<name>", text)
        return USER_PART.sub(lambda match: match.group(1) + "<user>", text)

    def shown(kind: str, text: str) -> str:
        return "" if kind.startswith("name") else f" {safe(text)[:80]!r}"

    checks = names + [("home-path", HOME_PATH), ("email", EMAIL), ("usage", USAGE)] + extra
    findings = allowed_findings = reported = on_base = read = 0
    not_read: list[str] = []
    skipped: list[str] = []
    binary: list[str] = []

    def record(where: str, kind: str, text: str, line: str, credit: collections.Counter[str]) -> None:
        nonlocal findings, allowed_findings, reported, on_base
        if kind == "email" and not args.fail_on_email:
            reported += 1
            print(f"{where}: {kind} (reported only){shown(kind, text)}")
        elif credit[line] > 0:
            on_base += 1
            print(f"{where}: {kind} (on base){shown(kind, text)}")
        elif any(allow.search(line) for allow in allowed):
            allowed_findings += 1
            print(f"{where}: {kind} (allowed){shown(kind, text)}")
        else:
            findings += 1
            print(f"{where}: {kind}{shown(kind, text)}")

    none: collections.Counter[str] = collections.Counter()
    for relative, source in sources:
        label = safe(relative) + ("" if source == "HEAD" or args.path else " (working tree)")
        for kind, regex in names:
            if regex.search(relative):
                findings += 1
                print(f"{label}: {kind} in the file path")
        if any(regex.search(relative) for regex in excluded):
            skipped.append(label)
            continue
        if source == "HEAD":
            blob = run_git(root, "show", f"HEAD:{relative}")
            if blob.returncode != 0:
                not_read.append(f"{label} (not readable at HEAD)")
                continue
            raw = blob.stdout
        else:
            path = root / relative
            if path.is_symlink():
                raw = os.readlink(path).encode("utf-8", errors="surrogateescape")
            elif path.is_file():
                raw = path.read_bytes()
            else:
                not_read.append(f"{label} (not a regular file on disk)")
                continue
        if b"\0" in raw[:8192] and raw[:2] not in (b"\xff\xfe", b"\xfe\xff"):
            binary.append(label)
            if not any(regex.search(relative) for regex in allow_binary):
                findings += 1
                print(f"{label}: binary content, not examined as text (see --allow-binary)")
        read += 1
        text = decode(raw)
        credit: collections.Counter[str] = collections.Counter()
        if merge_base is not None:
            base_blob = run_git(root, "show", f"{merge_base}:{relative}")
            if base_blob.returncode == 0:
                credit = collections.Counter(decode(base_blob.stdout).splitlines())
        for number, line in enumerate(text.splitlines(), 1):
            hits = []
            for kind, regex in checks:
                seen = set()
                for match in regex.finditer(line):
                    if match.group(0) not in seen:
                        seen.add(match.group(0))
                        hits.append((kind, match.group(0)))
            for kind, matched in hits:
                record(f"{label}:{number}", kind, matched, line, credit)
            if hits and credit[line] > 0:
                credit[line] -= 1          # one credit per occurrence of the line on base
        squeezed = re.sub(r"\s+", "", text)
        for kind, regex in squeezed_names:
            in_lines = sum(1 for line in text.splitlines() for _ in regex.finditer(re.sub(r"\s+", "", line)))
            if len(regex.findall(squeezed)) > in_lines:
                findings += 1
                print(f"{label}: {kind} across lines")
    del none

    for item in binary:
        print(f"binary, scanned as text: {item}")
    for item in not_read:
        print(f"not read: {item}")
    for item in skipped:
        print(f"excluded: {item}")
    print(
        f"files listed {len(sources)}, read {read}, excluded {len(skipped)}, not read {len(not_read)}; "
        f"names given {len(names)}; findings {findings}, on base {on_base}, allowed {allowed_findings}, "
        f"reported only {reported}"
    )
    if not sources and not args.allow_empty:
        print("no file is listed: nothing was examined (see --allow-empty)")
        return 1
    return 1 if findings or not_read else 0


if __name__ == "__main__":
    sys.exit(main())
