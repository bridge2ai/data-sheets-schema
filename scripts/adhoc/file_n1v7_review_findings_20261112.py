#!/usr/bin/env python3
"""Purpose: file each finding of the two independent re-reviews of analysis
plan amendment N1, draft v7, as one GitHub issue, as the amendment's own rule
requires ("with each finding filed"). The Claude review has 15 findings (P2-1
to P2-7, P3-1 to P3-8). The Codex CLI review has 5; four of them overlap a
Claude finding and are appended to that issue, and one (the registered policy
value) gets its own issue. 16 issues in all.

Inputs: the two review files under d4d-executions/plans/reviews/.
Outputs: with --dry-run, the titles and body sizes on stdout and the bodies
under the given --out directory. Without it, the same plus one `gh issue
create` per finding, and a JSON map finding -> issue URL written to
--map. Refuses to run twice (the map file must not exist).
Serves: owner direction D134; amendment N1 draft v8. Date: 2026-11-12.

Bodies are taken from the review text as written. A body containing an
at-sign is refused, so that nothing in it can render as a mention.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REVIEWS = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews")
CLAUDE = REVIEWS / "n1v7_2fb05037_claude_review_2026-11-12.md"
CODEX = REVIEWS / "n1v7_2fb05037_codex_review_2026-11-12.md"
REPO = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema"
# Codex finding number -> the Claude finding it overlaps (None: its own issue).
OVERLAP = {1: "P3-1", 2: None, 3: "P2-4", 4: "P2-7", 5: "P3-5"}
V7 = "2fb0503757db041e009f21dd02a1d57a45a75a88"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def claude_findings(text: str) -> dict[str, tuple[str, str]]:
    out = {}
    parts = re.split(r"^### (P[23]-\d+)\. ", text, flags=re.M)
    for i in range(1, len(parts), 2):
        key, rest = parts[i], parts[i + 1]
        rest = re.split(r"^## ", rest, flags=re.M)[0].rstrip()
        title, _, body = rest.partition("\n")
        out[key] = (title.strip(), body.strip())
    return out


def codex_findings(text: str) -> dict[int, tuple[str, str]]:
    out = {}
    head = text.split("**What I checked**")[0]
    parts = re.split(r"^(\d+)\. \*\*(P[123]) — ", head, flags=re.M)
    for i in range(1, len(parts), 3):
        number, grade, rest = int(parts[i]), parts[i + 1], parts[i + 2]
        title, _, body = rest.partition("\n")
        title = title.strip().rstrip("*").rstrip(".").strip()
        body = "\n".join(line[3:] if line.startswith("   ") else line for line in body.splitlines()).strip()
        out[number] = (f"{grade}: {title}", body)
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
    assert len(claude) == 15, len(claude)
    assert len(codex) == 5, len(codex)
    intro = (f"Finding from an independent re-review of analysis plan amendment N1, draft v7 "
             f"(`notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` at commit `{V7}` on branch "
             f"`claude/native-amendment-n1-v7-20261112`). Line numbers `L…` are lines of that file.\n\n")
    foot = ("\n\n---\nThe review files are kept outside the repository, under `d4d-executions/plans/reviews/`, "
            "and are cited by sha256:\n"
            f"- Claude review: `{sha(CLAUDE)}`\n- Codex CLI review: `{sha(CODEX)}`\n\n"
            "Draft v8 of the amendment responds to this finding; the issue stays open until a re-check of v8 confirms it.")
    issues = []
    for key, (title, body) in claude.items():
        extra = ""
        for number, target in OVERLAP.items():
            if target == key:
                ctitle, cbody = codex[number]
                extra += f"\n\n## The Codex CLI review's finding {number} on the same point ({ctitle})\n\n{cbody}"
        issues.append((f"claude-{key}", f"[N1 v7 review {key}] {title}", intro + f"## {key}. {title}\n\n{body}" + extra + foot))
    for number, target in OVERLAP.items():
        if target is None:
            ctitle, cbody = codex[number]
            grade, _, rest = ctitle.partition(": ")
            issues.append((f"codex-{number}", f"[N1 v7 review Codex {grade}] {rest}",
                           intro + f"## Codex CLI review, finding {number} ({ctitle})\n\n{cbody}" + foot))
    assert len(issues) == 16, len(issues)
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
