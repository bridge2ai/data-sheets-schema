#!/usr/bin/env python3
"""Purpose: file each finding of a pair of independent reviews (one Claude
report, one Codex CLI report) of a plan amendment as one GitHub issue, as the
amendments' own rule requires ("with each finding filed"). A Codex finding
that overlaps a Claude finding is appended to that issue; a Codex finding
with no overlap gets its own issue. This generalises the two one-off scripts
file_n1v7_review_findings_20261112.py and file_n1v8_recheck_findings_20261112.py.

Inputs (arguments):
  --claude FILE         Claude report; findings are "### <KEY>. <title>" sections
                        whose KEY matches --claude-key (a regular expression).
                        May be omitted with --no-claude.
  --codex FILE          Codex report; findings are lines "**<n>. P<g> — <title>**"
                        or "<n>. **P<g> — <title>**", each followed by its body.
  --codex-end TEXT      a line of the Codex report after which no finding follows.
  --overlap MAP         for example "1:N1,2:,3:P3-5": Codex finding number to the
                        Claude key it overlaps; empty means its own issue.
  --label TEXT          for example "N1 v9 re-check" (goes into every title).
  --subject TEXT        one sentence naming the reviewed file, commit and branch.
  --next TEXT           one sentence saying which draft responds.
  --expect-claude N, --expect-codex N   asserted counts.
  --out DIR, --map FILE, --dry-run.
Outputs: with --dry-run, titles and body sizes on stdout and the bodies under
--out. Without it, one `gh issue create` per issue and a JSON map at --map.
Refuses to run twice (the map file must not exist) and refuses any body or
title containing an at-sign.
Serves: owner direction D134; amendments N1 and NP1. Date: 2026-11-12.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def claude_findings(text: str, key_pattern: str) -> dict[str, tuple[str, str]]:
    out = {}
    parts = re.split(rf"^### ({key_pattern})\. ", text, flags=re.M)
    for i in range(1, len(parts), 2):
        key, rest = parts[i], parts[i + 1]
        rest = re.split(r"^## ", rest, flags=re.M)[0].rstrip()
        title, _, body = rest.partition("\n")
        out[key] = (title.strip(), body.strip())
    return out


def codex_findings(text: str, end_marker: str | None) -> dict[int, tuple[str, str]]:
    head = text.split(end_marker)[0] if end_marker else text
    out = {}
    pattern = re.compile(r"^(?:\*\*(\d+)\. (P[123]) — (.*?)\*\*|(\d+)\. \*\*(P[123]) — (.*?)\*\*)\s*$", flags=re.M)
    matches = list(pattern.finditer(head))
    for index, match in enumerate(matches):
        number = int(match.group(1) or match.group(4))
        grade = match.group(2) or match.group(5)
        title = (match.group(3) or match.group(6)).strip().rstrip(".")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(head)
        body = head[match.end():end]
        body = "\n".join(line[3:] if line.startswith("   ") else line[4:] if line.startswith("    ") else line
                         for line in body.splitlines()).strip()
        out[number] = (f"{grade}: {title}", body)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("--claude")
    ap.add_argument("--no-claude", action="store_true")
    ap.add_argument("--claude-key", default=r"N\d+|P[123]-\d+")
    ap.add_argument("--codex", required=True)
    ap.add_argument("--codex-end")
    ap.add_argument("--overlap", default="")
    ap.add_argument("--label", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--next", required=True, dest="next_text")
    ap.add_argument("--expect-claude", type=int, default=0)
    ap.add_argument("--expect-codex", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_dir, map_path = Path(args.out), Path(args.map)
    if map_path.exists():
        print(f"refusing: {map_path} exists, the findings were already filed", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    claude = {}
    if not args.no_claude:
        claude = claude_findings(Path(args.claude).read_text(), args.claude_key)
    codex = codex_findings(Path(args.codex).read_text(), args.codex_end)
    if len(claude) != args.expect_claude or len(codex) != args.expect_codex:
        print(f"refusing: found {len(claude)} Claude and {len(codex)} Codex findings, "
              f"expected {args.expect_claude} and {args.expect_codex}", file=sys.stderr)
        return 5
    overlap = {}
    for item in filter(None, args.overlap.split(",")):
        number, _, key = item.partition(":")
        overlap[int(number)] = key or None
    for number in codex:
        overlap.setdefault(number, None)
    for number, key in overlap.items():
        if key is not None and key not in claude:
            print(f"refusing: overlap target {key} is not a Claude finding", file=sys.stderr)
            return 6
    intro = f"Finding from an independent review. {args.subject}\n\n"
    foot = "\n\n---\nThe review files are kept outside the repository, under `d4d-executions/plans/reviews/`, and are cited by sha256:\n"
    if not args.no_claude:
        foot += f"- Claude report: `{sha(Path(args.claude))}`\n"
    foot += f"- Codex CLI report: `{sha(Path(args.codex))}`\n\n{args.next_text}"
    issues = []
    for key, (title, body) in claude.items():
        grade = "P2" if key.startswith("N") else key.split("-")[0]
        extra = ""
        for number, target in overlap.items():
            if target == key:
                ctitle, cbody = codex[number]
                extra += f"\n\n## The Codex CLI report's finding {number} on the same point ({ctitle})\n\n{cbody}"
        issues.append((f"claude-{key}", f"[{args.label} {grade} {key}] {title}", intro + f"## {key}. {title}\n\n{body}" + extra + foot))
    for number, target in overlap.items():
        if target is None:
            ctitle, cbody = codex[number]
            grade, _, rest = ctitle.partition(": ")
            issues.append((f"codex-{number}", f"[{args.label} Codex {grade}] {rest}",
                           intro + f"## Codex CLI report, finding {number} ({ctitle})\n\n{cbody}" + foot))
    result = {}
    for key, title, body in issues:
        if "@" in title or "@" in body:
            print(f"refusing: at-sign in {key}", file=sys.stderr)
            return 3
        title = title if len(title) <= 240 else title[:237] + "..."
        path = out_dir / f"{key}.md"
        path.write_text(body)
        print(f"{key}: {len(body)} chars | {title}")
        if not args.dry_run:
            done = subprocess.run(["gh", "issue", "create", "--title", title, "--body-file", str(path)],
                                  cwd=REPO, capture_output=True, text=True)
            if done.returncode != 0:
                print(done.stderr, file=sys.stderr)
                map_path.write_text(json.dumps(result, indent=2) + "\n")
                return 4
            result[key] = done.stdout.strip().splitlines()[-1]
            print("  ->", result[key])
    print(f"{len(issues)} issues")
    if not args.dry_run:
        map_path.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
