#!/usr/bin/env python3
"""Purpose: file each new finding of the two re-checks of analysis plan
amendment N1, draft v8, as one GitHub issue ("with each finding filed"). The
Claude re-check has 12 new findings (N1 to N5 graded P2, P3-1 to P3-7). The
Codex CLI re-check has 4; three overlap a Claude finding and are appended to
that issue, and one (a "no" to item (z)) gets its own. 13 issues in all.

Same method as file_n1v7_review_findings_20261112.py; the two reports use
different heading forms, so this is a separate script.

Inputs: the two re-check files under d4d-executions/plans/reviews/.
Outputs: with --dry-run, titles and body sizes on stdout and the bodies under
--out. Without it, one `gh issue create` per finding and a JSON map finding ->
issue URL at --map. Refuses to run twice (the map file must not exist).
Serves: owner direction D134; amendment N1 draft v9. Date: 2026-11-12.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REVIEWS = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews")
CLAUDE = REVIEWS / "n1v8_98adf23e_claude_recheck_2026-11-12.md"
CODEX = REVIEWS / "n1v8_98adf23e_codex_recheck_2026-11-12.md"
REPO = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema"
OVERLAP = {1: "N2", 2: None, 3: "P3-1", 4: "N1"}
V8 = "98adf23eb96661af33690d6b5593809d8b02a623"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def claude_findings(text: str) -> dict[str, tuple[str, str]]:
    out = {}
    parts = re.split(r"^### (N\d+|P3-\d+)\. ", text, flags=re.M)
    for i in range(1, len(parts), 2):
        key, rest = parts[i], parts[i + 1]
        rest = re.split(r"^## ", rest, flags=re.M)[0].rstrip()
        title, _, body = rest.partition("\n")
        out[key] = (title.strip(), body.strip())
    return out


def codex_findings(text: str) -> dict[int, tuple[str, str]]:
    out = {}
    head = text.split("**Owner decisions, ballot coverage and change account**")[0]
    parts = re.split(r"^\*\*(\d+)\. (P[123]) — (.*?)\*\*\s*$", head, flags=re.M)
    for i in range(1, len(parts), 4):
        number, grade, title, body = int(parts[i]), parts[i + 1], parts[i + 2], parts[i + 3]
        out[number] = (f"{grade}: {title.strip().rstrip('.')}", body.strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_dir, map_path = Path(args.out), Path(args.map)
    if map_path.exists():
        print(f"refusing: {map_path} exists, the findings were already filed", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    claude = claude_findings(CLAUDE.read_text())
    codex = codex_findings(CODEX.read_text())
    assert len(claude) == 12, sorted(claude)
    assert len(codex) == 4, sorted(codex)
    intro = (f"Finding from a re-check of analysis plan amendment N1, draft v8 "
             f"(`notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` at commit `{V8}` on branch "
             f"`claude/native-amendment-n1-v7-20261112`). Line numbers `L…` are lines of that file.\n\n")
    foot = ("\n\n---\nThe re-check files are kept outside the repository, under `d4d-executions/plans/reviews/`, "
            "and are cited by sha256:\n"
            f"- Claude re-check: `{sha(CLAUDE)}`\n- Codex CLI re-check: `{sha(CODEX)}`\n\n"
            "Draft v9 of the amendment responds to this finding; the issue stays open until a re-check of v9 confirms it.")
    issues = []
    for key, (title, body) in claude.items():
        grade = "P2" if key.startswith("N") else "P3"
        extra = ""
        for number, target in OVERLAP.items():
            if target == key:
                ctitle, cbody = codex[number]
                extra += f"\n\n## The Codex CLI re-check's finding {number} on the same point ({ctitle})\n\n{cbody}"
        issues.append((f"claude-{key}", f"[N1 v8 re-check {grade} {key}] {title}", intro + f"## {key}. {title}\n\n{body}" + extra + foot))
    for number, target in OVERLAP.items():
        if target is None:
            ctitle, cbody = codex[number]
            grade, _, rest = ctitle.partition(": ")
            issues.append((f"codex-{number}", f"[N1 v8 re-check Codex {grade}] {rest}",
                           intro + f"## Codex CLI re-check, finding {number} ({ctitle})\n\n{cbody}" + foot))
    assert len(issues) == 13, len(issues)
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
    if not args.dry_run:
        map_path.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
