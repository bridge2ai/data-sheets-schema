#!/usr/bin/env python3
"""Purpose: file each finding of one Codex CLI code review as one GitHub issue,
as the repository's review rule requires. Findings are Markdown sections whose
heading is "### P<g> — <title>" (an em dash); a section ends at the next
heading of level two or three.

Inputs: --report FILE (the review), --label TEXT (goes into every title),
--subject TEXT (one sentence naming what was reviewed), --expect N (asserted
finding count), --out DIR (issue bodies), --map FILE (written after filing;
must not exist), --dry-run.
Outputs: one `gh issue create` per finding and a JSON map of finding index to
issue URL. Refuses any title or body containing an at-sign.
Serves: the native arm's integration reviews (owner direction D134).
Date: 2026-11-13.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema"
HEAD = re.compile(r"^### (P[123]) — (.+)$", re.M)


def main():
    ap = argparse.ArgumentParser()
    for name in ("--report", "--label", "--subject", "--out", "--map"):
        ap.add_argument(name, required=True)
    ap.add_argument("--expect", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if Path(a.map).exists():
        sys.exit("map exists: refusing to file twice")
    raw = Path(a.report).read_bytes()
    text = raw.decode()
    digest = hashlib.sha256(raw).hexdigest()
    heads = list(HEAD.finditer(text))
    if len(heads) != a.expect:
        sys.exit(f"expected {a.expect} findings, found {len(heads)}")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    filed = {}
    for n, m in enumerate(heads, 1):
        start = m.end()
        nxt = re.search(r"^#{2,3} ", text[start:], re.M)
        section = text[start:start + nxt.start()] if nxt else text[start:]
        grade, title_text = m.group(1), m.group(2).strip()
        title = f"[{a.label} {grade}-{n}] {title_text}"
        body = "\n".join([
            f"**Finding {grade}-{n} of an independent Codex CLI code review.** {a.subject}",
            "",
            section.strip(),
            "",
            f"Source: `{Path(a.report).name}` (sha256 `{digest}`), kept in the lead's "
            "review folder. Filed by the Claude lead, as the review rule requires; the "
            "lead's disposition follows in a comment or in the fixing commit.",
        ])
        if "@" in title or "@" in body:
            sys.exit(f"at-sign in finding {n}: refusing")
        path = out / f"finding-{n}.md"
        path.write_text(body)
        if a.dry_run:
            print(f"{n}: {title} ({len(body)} chars)")
            continue
        r = subprocess.run(["gh", "issue", "create", "--title", title, "--body-file",
                            str(path)], cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            Path(a.map).write_text(json.dumps(filed, indent=2))
            sys.exit(f"gh failed on finding {n}: {r.stderr.strip()}")
        filed[str(n)] = r.stdout.strip()
        print(n, filed[str(n)], flush=True)
        time.sleep(1.5)
    if not a.dry_run:
        Path(a.map).write_text(json.dumps(filed, indent=2))
        print(f"filed {len(filed)}; map {a.map}")


if __name__ == "__main__":
    main()
