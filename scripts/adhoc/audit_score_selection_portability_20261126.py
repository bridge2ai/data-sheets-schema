#!/usr/bin/env python3
"""Audit new selection-branch files for local-path disclosures, issue 6385.

2026-11-26. Inputs: repository root, base and historical commits, account name.
Output: a fresh JSON receipt with relative file paths, hashes and match kinds.
Reads added tracked files plus all untracked files, including ignored/hidden
files, directly from Git inventories; no ignore filter is applied to reads.
The historical revision is inspected without rewriting history.
"""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


POLICY_PATH = "notes/score_selection_policy_2026-11-26.md"
POLICY_COMMIT = "c08bd9edde73ec06473393d479d5cc597641de6c"
DISCLOSURE_CORRECTION = (
    "Correction, 2026-11-26 (issue 6387): when this note was committed at 06:21:57Z, "
    "the three replacements had been authorized and started; one had been published "
    "(06:18:23Z) and two were still running (they were published at 06:23:13Z and "
    "06:24:37Z). The variation report was saved at 06:24:58Z, after this commit. "
    "This note is the first committed form of the rule; it was not committed before "
    "the second and third scorings existed."
)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1"),
                          timeout=60).stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def paths(raw):
    return {name.decode() for name in raw.split(b"\0") if name}


def patterns(account):
    # Build delimiter patterns without introducing example user-directory paths
    # into the files being audited, including this detector itself.
    return {
        "mac_home_prefix": re.compile(re.escape("/" + "Users" + "/")),
        "unix_home_prefix": re.compile(re.escape("/" + "home" + "/")),
        "tilde_home_prefix": re.compile("~" + "/"),
        "workspace_directory": re.compile(re.escape("agent" + "-work")),
        "local_account": re.compile(re.escape(account), re.IGNORECASE),
    }


def inspect(name, raw, matchers):
    findings = []
    for number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
        kinds = sorted(kind for kind, matcher in matchers.items() if matcher.search(line))
        if kinds:
            findings.append({"path": name, "line": number, "kinds": kinds,
                             "line_sha256": sha(line.encode())})
    return {"path": name, "bytes": len(raw), "sha256": sha(raw)}, findings


def policy_disclosure(registered, current):
    """Accept only the exact issue-6387 insertion; all registered bytes survive."""
    anchor = b"\n## Owner decisions\n"
    if registered.count(anchor) != 1:
        raise ValueError("registered disclosure insertion point is not unique")
    insertion = b"\n" + DISCLOSURE_CORRECTION.encode() + b"\n"
    expected = registered.replace(anchor, insertion + anchor, 1)
    permitted = lambda candidate: candidate == expected
    controls = {
        "current_exact_insertion_accepted": permitted(current),
        "missing_correction_refused": not permitted(registered),
        "altered_paragraph_refused": not permitted(expected.replace(b"06:21:57Z", b"06:21:58Z", 1)),
        "extra_rule_edit_refused": not permitted(expected.replace(b"1. **Candidates.**", b"1. **Changed candidates.**", 1)),
        "duplicate_correction_refused": not permitted(expected.replace(anchor, insertion + anchor, 1)),
    }
    unchanged_rest = current.count(insertion) == 1 and current.replace(insertion, b"", 1) == registered
    return {"registered_policy_unchanged": current == registered,
            "policy_only_authorized_disclosure_added": permitted(current),
            "registered_policy_without_disclosure_unchanged": unchanged_rest,
            "registered_policy_sha256": sha(registered), "current_policy_sha256": sha(current),
            "expected_policy_sha256": sha(expected), "disclosure_paragraph_sha256": sha(DISCLOSURE_CORRECTION.encode()),
            "policy_changed_lines": [line for line in difflib.ndiff(registered.decode().splitlines(),
                                                                    current.decode().splitlines())
                                     if line.startswith(("+ ", "- "))],
            "policy_guard_controls": controls,
            "policy_guard_passed": permitted(current) and unchanged_rest and all(controls.values())}


def audit(args):
    root = args.root.resolve()
    base = git(root, "rev-parse", args.base).decode().strip()
    historical = git(root, "rev-parse", args.historical).decode().strip()
    head = git(root, "rev-parse", "HEAD").decode().strip()
    tracked = paths(git(root, "diff", "--name-only", "--diff-filter=A", "--no-renames", "-z", base))
    # No exclude-standard flag: ignored and hidden untracked paths are included.
    untracked = paths(git(root, "ls-files", "--others", "-z"))
    current_names = sorted(tracked | untracked)
    matchers = patterns(args.account_name)
    current_inventory, current_matches = [], []
    for name in current_names:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("audit needs a regular new file: " + name)
        inventory, matches = inspect(name, path.read_bytes(), matchers)
        current_inventory.append(inventory)
        current_matches.extend(matches)
    old_names = sorted(paths(git(root, "diff", "--name-only", "--diff-filter=A", "--no-renames",
                                "-z", base, historical)))
    old_inventory, old_matches = [], []
    for name in old_names:
        inventory, matches = inspect(name, git(root, "show", historical + ":" + name), matchers)
        old_inventory.append(inventory)
        old_matches.extend(matches)
    registered_policy = git(root, "show", POLICY_COMMIT + ":" + POLICY_PATH)
    disclosure = policy_disclosure(registered_policy, (root / POLICY_PATH).read_bytes())
    return {"status": "PASSED" if not current_matches and disclosure["policy_guard_passed"] else "BLOCKED",
            "base": base, "head": head, "historical_commit": historical,
            "scope": "added tracked files plus all untracked files, including ignored and hidden",
            "ignore_independent": True, "account_name_sha256": sha(args.account_name.encode()),
            "current_inventory": current_inventory, "current_matches": current_matches,
            "historical_inventory": old_inventory, "historical_matches": old_matches,
            **disclosure,
            "history_rewritten": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--base", default="483bed03b")
    parser.add_argument("--historical", default="01de8a490")
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.account_name.strip():
        parser.error("account name must be nonempty")
    result = audit(args)
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    with args.output.open("xb") as handle:
        handle.write(raw)
    if args.output.read_bytes() != raw:
        raise ValueError("saved audit receipt differs")
    print(json.dumps({"status": result["status"], "files": len(result["current_inventory"]),
                      "current_match_lines": len(result["current_matches"]),
                      "historical_match_lines": len(result["historical_matches"]),
                      "receipt_sha256": sha(raw)}, sort_keys=True))
    return 0 if result["status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
