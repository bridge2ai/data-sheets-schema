#!/usr/bin/env python3
"""Remove the account name and the account usage estimates from the published notes of
release series 2026-11-25c.

Purpose: the launch records, stream logs, README and review report of the series were
  first committed as written by the run. They named the subscription account the series ran
  on, each budget line of the stream logs held estimates of that account's weekly allowance,
  and the review report quoted figures those estimates can be rebuilt from. The owner
  decided on 2026-11-25 that none of this is published (issue 6352). This script makes the
  published copies from the originals, so that anyone holding the originals can reproduce
  them and see that nothing else changed.
What it changes, under notes/release_series_2026-11-25/ of --root:
  launch/*.launch.txt   the one line starting "account: " is replaced by a fixed line.
  streams/stream_rep*.txt   each "budget:" line keeps decision, next, rep, finished_runs and
                        in_flight_elsewhere; every other field (the usage estimates, the
                        limit, the amount spent, a stop reason) is dropped and
                        "usage_estimates": "removed" is added.
  README.md             the Account row of the first table.
  review_1_pr6349.md    each --scrub text is replaced by its substitute, in the order
                        given; any account name left after that becomes <account>.
  Nothing under data/ is read or written. The account name and the texts to scrub are
  arguments and are not in this file.
Inputs:  --root REPOSITORY --account-name NAME [--scrub 'OLD::NEW' ...] [--check]
  --scrub replaces the literal text OLD by NEW in the review report; OLD must then be absent
  from every file of the notes directory. The series' texts (the mentions of the account and two phrases giving figures) are not
  kept in the repository.
Outputs: the files rewritten in place (running it again changes nothing); one count line
  per kind on stdout. Every file is read and checked before any is written: on a problem
  nothing is written and the exit status is 1. A problem is a launch record without exactly
  one account line, a line holding "budget:" that is not "<time> stream rep<N> budget:
  <JSON object>", or, after the pass, any notes file that would still hold the account name
  (compared without case, "-" and "_" alike), a scrubbed text, or, in a stream log, the
  word "percent". With --check nothing is written
  and exit 1 also means the tree is not yet clean.
Serves:  draft PR 6359, issue 6352. Date: 2026-11-25.
"""
import argparse
import glob
import json
import os
import re
import sys

NOTES = "notes/release_series_2026-11-25"
ACCOUNT_LINE = ("account: a Claude subscription account (name removed from the published copy, "
                "owner's decision of 2026-11-25)")
README_ROW = "| Account | a Claude subscription account, through headless Claude Code |"
BUDGET = re.compile(r"^(\S+ stream rep\d+ budget: )(\{.*\})(\r?)$")
KEEP = ("decision", "next", "rep", "finished_runs", "in_flight_elsewhere")


def fold(text):
    return text.lower().replace("_", "-")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--scrub", action="append", default=[], metavar="OLD::NEW")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    name = args.account_name
    if len(name) < 4:
        parser.error("the account name is too short to search for safely")
    scrubs = []
    for item in args.scrub:
        old, separator, new = item.partition("::")
        if not separator or len(old) < 8:
            parser.error("--scrub takes 'OLD::NEW' with OLD of at least 8 characters")
        scrubs.append((old, new))
    notes = os.path.join(args.root, NOTES)
    problems = []
    changed = {"launch": 0, "stream lines": 0, "readme": 0, "review": 0}
    result = {}       # path -> (relative path, text before, text after), every notes file

    for path in sorted(glob.glob(os.path.join(notes, "**", "*"), recursive=True)):
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="surrogateescape", newline="") as handle:
            text = handle.read()
        relative = os.path.relpath(path, notes).replace(os.sep, "/")
        new = text
        if relative.startswith("launch/") and relative.endswith(".launch.txt"):
            lines = text.split("\n")
            hits = [i for i, line in enumerate(lines) if line.startswith("account: ")]
            if len(hits) != 1:
                problems.append("%s: %d account lines" % (relative, len(hits)))
            else:
                lines[hits[0]] = ACCOUNT_LINE + ("\r" if lines[hits[0]].endswith("\r") else "")
                new = "\n".join(lines)
            changed["launch"] += new != text
        elif relative.startswith("streams/"):
            out = []
            for number, line in enumerate(text.split("\n"), 1):
                match = BUDGET.match(line)
                if match:
                    try:
                        record = json.loads(match.group(2))
                        if not isinstance(record, dict):
                            raise ValueError("not an object")
                    except ValueError as exc:
                        problems.append("%s line %d: budget line is not a JSON object (%s)"
                                        % (relative, number, exc))
                        out.append(line)
                        continue
                    kept = {key: record[key] for key in KEEP if key in record}
                    kept["usage_estimates"] = "removed"
                    redone = match.group(1) + json.dumps(kept, sort_keys=True) + match.group(3)
                    changed["stream lines"] += redone != line
                    line = redone
                elif "budget:" in line:
                    problems.append("%s line %d: a budget line of another shape" % (relative, number))
                out.append(line)
            new = "\n".join(out)
        elif relative == "README.md":
            new = "\n".join(README_ROW if line.startswith("| Account |") else line
                            for line in text.split("\n"))
            changed["readme"] += new != text
        elif relative == "review_1_pr6349.md":
            for old, substitute in scrubs:
                new = new.replace(old, substitute)
            new = new.replace(name, "<account>")
            changed["review"] += new != text
        result[path] = (relative, text, new)

    for path, (relative, text, new) in sorted(result.items()):
        if fold(name) in fold(new):
            problems.append("%s: would still hold the account name" % relative)
        for old, substitute in scrubs:
            if old in new:
                problems.append("%s: would still hold a scrubbed text" % relative)
        if relative.startswith("streams/") and re.search("percent", new, re.IGNORECASE):
            problems.append("%s: would still hold a usage estimate" % relative)

    for problem in problems:
        print("PROBLEM " + problem)
    if problems:
        print("nothing written")
        return 1
    if not args.check:
        for path, (relative, text, new) in sorted(result.items()):
            if new != text:
                with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as handle:
                    handle.write(new)
    for kind, count in changed.items():
        print("%s %s: %d" % ("would change" if args.check else "changed", kind, count))
    return 1 if args.check and any(changed.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
