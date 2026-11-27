#!/usr/bin/env python3
"""Give the launch records of both recent series one fixed account line, take the home
directory out of the path of the `claude` binary, and state the session environment and one
placeholder of the kept review report in words that hold for any account.

Purpose: PR 6359 replaced the `account:` line of the 15 launch records of release series
  2026-11-25c by a fixed line. The 16 launch records of the series before it
  (2026-11-22 and 2026-11-22b) stated theirs differently. The owner decided on 2026-11-27
  that every series' launch records carry the same line, and that the login in the path
  of the `claude` binary is not published either (issues 6426, 6362, 6352).
What it changes, in every `*.launch.txt` directly in the launch folders below (subfolders
  are not read):
  1. a line that starts `account:` becomes ACCOUNT_LINE, the line PR 6359 wrote;
  2. on the line that starts `claude code:`, a home directory (`/Users/<x>/`, `/home/<x>/`)
     becomes `~/`;
  3. on an indented command line of the exact form `cd <dir> && <launcher> --model ...`,
     a launcher other than `claude` becomes LAUNCHER_PLACEHOLDER;
  4. only with --other-home-paths: every other home directory in these files becomes `~/`
     (the `worktree:` line and the directory of that command line);
  5. on the line that starts `environment:`, the closing words ENVIRONMENT_OLD become
     ENVIRONMENT_NEW, the words the release-series driver writes since 2026-11-27.
  And in REPORT, the kept review report of series 2026-11-25c:
  6. the placeholder PLACEHOLDER_OLD becomes PLACEHOLDER_NEW.
  No rule needs a private value: none names an account or a login.
Limits, none of which the 31 records meet: a home directory is recognised only as
  `/Users/<x>/` or `/home/<x>/` with the slash after it, so rule 4 would also rewrite a
  `/home/<x>/` inside a URL; a command line of another form (an environment prefix, a
  quoted directory, a flag before `--model`) is left as written; --forbid matches a name
  with other separators between the parts it was given in, not a name given unseparated.
  A file with a carriage return or bytes that are not UTF-8 is refused.
Inputs:  --root REPOSITORY [--other-home-paths] [--forbid NAME ...] [--check]
  --forbid gives a name that must not remain in any file of the launch folders, or in
  REPORT, after the change; it is never printed. Without it the script still checks its
  own rules.
Outputs: the files rewritten in place and a count per rule on stdout. Every file is read
  and checked before any is written; on a problem nothing is written and the exit status
  is 2. With --check nothing is written and the exit status is 1 if anything would change.
  Plain --check accepts a tree with or without rule 4 applied; --check with
  --other-home-paths is the one that says rule 4 has been applied.
Serves: the owner's decisions of 2026-11-27 on the final review of PR 6359 (issue 6426) and on
  review 1 of PR 6431 (issue 6433).
Date: 2026-11-27.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LAUNCH_DIRS = ("notes/final_agentic_2026-11-22/launch", "notes/release_series_2026-11-25/launch")
ACCOUNT_LINE = ("account: a Claude subscription account (name removed from the published copy, "
                "owner's decision of 2026-11-25)")
LAUNCHER_PLACEHOLDER = "<launcher>"
ENVIRONMENT_OLD = "and the account's configuration directory and token variable)"
ENVIRONMENT_NEW = ("and, where the launcher was given them, the configuration directory and the "
                   "token of the account)")
REPORT = "notes/release_series_2026-11-25/review_1_pr6349.md"
PLACEHOLDER_OLD = "<configuration directory>"
PLACEHOLDER_NEW = "<session storage>"
HOME = re.compile(r"/(?:Users|home)/[^/\s)\"']+/")
# The check after the rewrite is looser than the rewrite, so that it can see what the
# rewrite's own pattern would miss: a home directory at the end of a token.
HOME_LEFT = re.compile(r"/(?:Users|home)/[^/\s)\"']+")
COMMAND = re.compile(r"^(\s+cd \S+ && )(\S+)( --model .*)$")
RULES = ("account line", "binary path", "launcher", "other home paths", "environment line",
         "report placeholder")


def spelling(name: str) -> re.Pattern[str]:
    """The name with any run of up to four non-alphanumerics, or none, between its parts."""
    parts = [re.escape(part) for part in re.split(r"[^A-Za-z0-9]+", name) if part]
    return re.compile(r"[^A-Za-z0-9]{0,4}".join(parts), re.IGNORECASE)


def rewrite(text: str, other_home_paths: bool) -> tuple[str, dict[str, int]]:
    counts = dict.fromkeys(RULES, 0)
    out = []
    for line in text.split("\n"):
        new = line
        if line.startswith("account:"):
            new = ACCOUNT_LINE
            counts["account line"] += new != line
        elif line.startswith("claude code:"):
            new = HOME.sub("~/", line)
            counts["binary path"] += new != line
        elif line.startswith("environment:"):
            new = line.replace(ENVIRONMENT_OLD, ENVIRONMENT_NEW)
            counts["environment line"] += new != line
        else:
            match = COMMAND.match(line)
            if match and match.group(2) not in ("claude", LAUNCHER_PLACEHOLDER):
                new = f"{match.group(1)}{LAUNCHER_PLACEHOLDER}{match.group(3)}"
                counts["launcher"] += new != line
            if other_home_paths:
                kept = new
                new = HOME.sub("~/", new)
                counts["other home paths"] += new != kept
        out.append(new)
    return "\n".join(out), counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--other-home-paths", action="store_true")
    parser.add_argument("--forbid", action="append", default=[], metavar="NAME")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    totals = dict.fromkeys(RULES, 0)
    planned: list[tuple[Path, str]] = []
    problems: list[str] = []
    forbidden = [spelling(name) for name in args.forbid if name.strip()]
    records = 0
    for directory in LAUNCH_DIRS:
        folder = args.root / directory
        if not folder.is_dir():
            problems.append(f"{directory}: no such folder")
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue
            where = f"{directory}/{path.name}"
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                problems.append(f"{where}: not UTF-8")
                continue
            if "\r" in text:
                problems.append(f"{where}: carriage return")
                continue
            new = text
            if path.name.endswith(".launch.txt"):
                records += 1
                new, counts = rewrite(text, args.other_home_paths)
                for rule, count in counts.items():
                    totals[rule] += count
                lines = new.split("\n")
                accounts = [line for line in lines if line.startswith("account:")]
                if accounts != [ACCOUNT_LINE]:
                    problems.append(f"{where}: expected one account line, found {len(accounts)}")
                if any(HOME_LEFT.search(line) for line in lines if line.startswith("claude code:")):
                    problems.append(f"{where}: a home directory remains on the claude code line")
                if args.other_home_paths and HOME_LEFT.search(new):
                    problems.append(f"{where}: a home directory remains")
                environment = [line for line in lines if line.startswith("environment:")]
                if any(ENVIRONMENT_NEW not in line for line in environment):
                    problems.append(f"{where}: an environment line without the expected closing words")
                if new != text:
                    planned.append((path, new))
            for index, pattern in enumerate(forbidden, 1):
                hits = [number for number, line in enumerate(new.split("\n"), 1) if pattern.search(line)]
                if hits:
                    problems.append(f"{where}: forbidden name {index} remains on line(s) {hits[:5]}")
    if not records:
        problems.append("no launch record found")
    report = args.root / REPORT
    try:
        text = report.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        problems.append(f"{REPORT}: not readable ({type(error).__name__})")
    else:
        if "\r" in text:
            problems.append(f"{REPORT}: carriage return")
        else:
            lines = text.split("\n")
            totals["report placeholder"] = sum(PLACEHOLDER_OLD in line for line in lines)
            if not any(PLACEHOLDER_OLD in line or PLACEHOLDER_NEW in line for line in lines):
                problems.append(f"{REPORT}: neither spelling of the placeholder found")
            for index, pattern in enumerate(forbidden, 1):
                if any(pattern.search(line) for line in lines):
                    problems.append(f"{REPORT}: forbidden name {index} remains")
            if totals["report placeholder"]:
                planned.append((report, text.replace(PLACEHOLDER_OLD, PLACEHOLDER_NEW)))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 2
    if not args.check:
        for path, new in planned:
            path.write_bytes(new.encode("utf-8"))
    verb = "would change" if args.check else "changed"
    print(f"launch records read: {records}; files {verb}: {len(planned)}")
    for rule in RULES:
        unit = "line(s)" if rule == "report placeholder" else ""
        print(f"{verb} {rule}: {totals[rule]} {unit}".rstrip())
    return 1 if args.check and planned else 0


if __name__ == "__main__":
    sys.exit(main())
