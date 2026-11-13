#!/usr/bin/env python3
"""Purpose: file each finding that helper 3 recorded in its environment-manifest
and pin-gate handoff as one GitHub issue, as the repository's rule requires
(every review finding becomes an issue, including fixed ones). Helper 3 has no
GitHub write; the lead files.

Inputs: --handoff JSON (helper 3's handoff JSON), --md (its Markdown twin, for
the sha256 only), --out DIR (bodies on --dry-run), --map FILE (written after
filing; must not exist), --dry-run.
Reads findings at /environment_manifest_and_gate_followup_20261113/
environment_manifest/findings[*] (H3-EMn), .../gate_findings[*] (H3-Gn) and
.../cache_fixture_finding (H3-G-FIXTURE-CACHE). Asserts 10, 17 and 1.
Outputs: one `gh issue create` per finding and a JSON map id -> issue URL.
Refuses any title or body that contains an at-sign, and refuses to run twice.
Serves: owner direction D134 (native arm first); NP1 gate and environment
manifest work. Date: 2026-11-13.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema"
ROOT = "/environment_manifest_and_gate_followup_20261113"
BRANCHES = {
    "EM": ("codex/native-environment-manifest-20261113",
           "ecb628c68328397ae1b4f31b76a57df63e87a89c (tests and export), "
           "1a466d6f6a42989371d0d126c622e0f661b92080 (provenance)"),
    "G": ("codex/native-pin-comparison-20261113",
          "d2a2957c06f03b509a2df41bde7b47efb394a08e"),
}
STATUS_WORDS = {
    "fixed": "fixed on helper 3's branch",
    "production_environment_hold": "open: production registration held",
    "open_deferred_python39_portability_not_fixed": "open, deferred",
    "design_approved_implementation_elsewhere": "design ruled; implemented in the gate",
}
NOTES = {
    "H3-EM4": ("The reply quoted in the handoff (\"Approve reference-only validation "
               "context\") was not sent by the lead's relay; the lead has asked helper 3 "
               "where its session recorded it. The substance matches the lead's ruling of "
               "2026-11-13T04:21Z: production validators may run read-only and isolated "
               "from the reference run's own source export only."),
    "H3-EM5": ("Lead's ruling (2026-11-13T06:55Z, assignment "
               "claude-lead-helper3-gate-addendum-20261113.md): the manifest records every "
               "file under the interpreter's import roots that no distribution owns, with "
               "path, size and sha256, in a closed sorted unowned_files list; ambiguous "
               "ownership still holds; the primary environment is not modified to pass."),
    "H3-G16": ("Python 3.9 is outside the supported range of this native path; the lead "
               "leaves it deferred. Native runs use the registered interpreter (CPython "
               "3.13 on the production host)."),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def short(value, limit=1500):
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + " [...]"


def body_for(kind, idx, rec, pointer, handoff, md):
    branch, head = BRANCHES[kind]
    lines = [
        f"**Finding ({rec['id']}):** {rec.get('finding', '(see the handoff record)')}",
        "",
        f"**Status recorded by helper 3:** {STATUS_WORDS.get(rec.get('status'), rec.get('status', 'not stated'))} "
        f"(`{rec.get('status', '')}`).",
    ]
    for key, label in (("repair", "Repair"), ("fix_commit", "Fix commit"),
                       ("original_failure_cohort", "Original failing cohort")):
        if rec.get(key):
            lines.append(f"**{label}:** {short(rec[key], 600)}")
    if rec.get("required_controls"):
        lines.append("**Controls:** " + ", ".join(f"`{c}`" for c in rec["required_controls"]))
    if rec["id"] in NOTES:
        lines += ["", "**Lead's note:** " + NOTES[rec["id"]]]
    lines += [
        "",
        f"**Where:** branch `{branch}`, head {head}. Not yet integrated into the native "
        "candidate (draft PR 5968); it reaches main only through that PR's review and the "
        "owner's merge approval.",
        "",
        f"**Evidence:** helper 3's handoff `notes/development_efficiency_20261111/handoffs/"
        f"codex-h3-recorder-env-and-pin-comparison-20261113.json` (sha256 `{sha(handoff)}`), "
        f"record `{pointer}`; Markdown twin sha256 `{sha(md)}`. Both are kept in the lead's "
        "report worktree under `notes/development_efficiency_20261111/handoffs/`.",
        "",
        "Filed by the Claude lead from helper 3's handoff, as the review rule requires; "
        "a fixed finding is filed for the record.",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", required=True)
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if Path(a.map).exists():
        sys.exit("map exists: refusing to file twice")
    data = json.loads(Path(a.handoff).read_text())
    base = data["environment_manifest_and_gate_followup_20261113"]
    em = base["environment_manifest"]["findings"]
    gate = base["gate_findings"]
    fixture = base["cache_fixture_finding"]
    assert len(em) == 10, len(em)
    assert len(gate) == 17, len(gate)
    items = []
    for i, rec in enumerate(em):
        assert rec["id"] == f"H3-EM{i + 1}", rec["id"]
        items.append(("EM", rec, f"{ROOT}/environment_manifest/findings[{i}]"))
    for i, rec in enumerate(gate):
        assert rec["id"] == f"H3-G{i + 1}", rec["id"]
        items.append(("G", rec, f"{ROOT}/gate_findings[{i}]"))
    assert fixture["id"] == "H3-G-FIXTURE-CACHE"
    fixture = dict(fixture)
    fixture.setdefault("finding", "The stale-bytecode fixture failed independently of the "
                                  "real two-project rehearsal case.")
    items.append(("G", fixture, f"{ROOT}/cache_fixture_finding"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    filed = {}
    for kind, rec, pointer in items:
        area = "native environment manifest" if kind == "EM" else "native pin gate"
        text = rec.get("finding", "")
        title = f"[{area} {rec['id']}] {text[:110].rstrip('.')}"
        body = body_for(kind, 0, rec, pointer, a.handoff, a.md)
        if "@" in title or "@" in body:
            sys.exit(f"at-sign in {rec['id']}: refusing")
        (out / f"{rec['id']}.md").write_text(body)
        if a.dry_run:
            print(f"{rec['id']}: {len(title)} chars title, {len(body)} chars body :: {title}")
            continue
        r = subprocess.run(["gh", "issue", "create", "--title", title, "--body-file",
                            str(out / f"{rec['id']}.md")], cwd=REPO, capture_output=True,
                           text=True)
        if r.returncode != 0:
            Path(a.map).write_text(json.dumps(filed, indent=2))
            sys.exit(f"gh failed on {rec['id']}: {r.stderr.strip()}")
        filed[rec["id"]] = r.stdout.strip()
        print(rec["id"], filed[rec["id"]], flush=True)
        time.sleep(1.5)
    if not a.dry_run:
        Path(a.map).write_text(json.dumps(filed, indent=2))
        print(f"filed {len(filed)}; map {a.map}")


if __name__ == "__main__":
    main()
