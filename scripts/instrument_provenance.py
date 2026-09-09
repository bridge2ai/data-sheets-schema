#!/usr/bin/env python3
"""Resolve which instrument version scored each semantic rubric evaluation (#1077).

An evaluation records `metadata.rubric_hash`, and the agents' output contract
asks for "the sha256 of rubric10.txt". That file is the rubric *text*; the
rules that decide a score live in the agent definition, which is what #1059,
#1060 and #1082 kept revising. `rubric10.txt` did not change across any of
them, so a hash of it cannot tell two instruments apart — and 29 of the 53
live rubric10 evaluations followed the contract exactly and are therefore
unidentifiable from their own artifact.

None of that is lost, because both files are in git. This resolves every
evaluation to the agent version that scored it, by one of two bases:

- `recorded` — the hash is some version of the agent definition, so the
  artifact names its own instrument;
- `recovered_from_commit` — the hash is a version of the rubric text, so the
  agent file **as it stood in the commit that last wrote this evaluation's
  bytes** is named instead. Weaker than a recorded claim and labelled as
  such, the way #399's prompt hashes recovered from git are.

Resolution is deliberately **not** by timestamp (#1100). The workflow here is
revise the agent, re-adjudicate, commit both together, so an evaluation's
`evaluation_timestamp` precedes the commit date of the very version that
produced it, and a time-based lookup returns the version being replaced —
off by one, always towards the instrument the revision corrected. It was
wrong on 19 of 43 recovered attributions. `evaluation_timestamp` is also
model-written and demonstrably stale in places: three CM4AI 09-01 files
record a time four hours before the commit of the agent text they hash. The
commit that carries the bytes is the fact; the timestamp is a claim.

    python scripts/instrument_provenance.py            # report
    python scripts/instrument_provenance.py --write    # rewrite the manifest
"""
import argparse
import glob
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "data" / "evaluation_instruments.json"
RUBRICS = {
    "rubric10_semantic": (".claude/agents/d4d-rubric10-semantic.md",
                          "data/rubric/rubric10.txt"),
    "rubric20_semantic": (".claude/agents/d4d-rubric20-semantic.md",
                          "data/rubric/rubric20.txt"),
}


def versions(path):
    """Every distinct version of a tracked file, oldest first."""
    out, seen = [], set()
    log = subprocess.run(["git", "log", "--all", "--reverse", "--format=%H %cI",
                          "--", path], capture_output=True, text=True,
                         cwd=ROOT).stdout.strip().splitlines()
    for line in log:
        commit, when = line.split()
        blob = subprocess.run(["git", "show", f"{commit}:{path}"],
                              capture_output=True, cwd=ROOT)
        if blob.returncode:
            continue
        digest = hashlib.sha256(blob.stdout).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        out.append({"sha256": digest, "first_seen": when, "commit": commit[:8]})
    return out


def is_shallow():
    """A shallow clone cannot answer any of this (#1100).

    CI checks out at depth 1, so `git log --all` sees one commit and every
    evaluation resolves to nothing. Callers skip rather than write a manifest
    that declares the corpus unidentifiable.
    """
    out = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                         capture_output=True, text=True, cwd=ROOT).stdout
    return out.strip() == "true"


def _writing_commit(path):
    """The commit that last wrote this file's bytes."""
    out = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(path)],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip()
    return out or None


def _agent_at(commit, agent_path):
    """The sha256 of the agent definition as of `commit`."""
    blob = subprocess.run(["git", "show", f"{commit}:{agent_path}"],
                          capture_output=True, cwd=ROOT)
    if blob.returncode:
        return None
    return hashlib.sha256(blob.stdout).hexdigest()


def resolve(rubric):
    agent_path, rubric_path = RUBRICS[rubric]
    agents, texts = versions(agent_path), versions(rubric_path)
    by_agent = {v["sha256"]: v for v in agents}
    by_text = {v["sha256"]: v for v in texts}
    out = {}
    base = ROOT / "data" / "evaluation_llm" / rubric / "label_aware"
    for path in sorted(glob.glob(str(base / "*_evaluation.json"))):
        doc = json.loads(Path(path).read_text())
        digest = (doc.get("metadata") or {}).get("rubric_hash")
        name = Path(path).name
        if digest in by_agent:
            v = by_agent[digest]
            out[name] = {"basis": "recorded", "instrument_sha256": digest,
                         "instrument_commit": v["commit"]}
        elif digest in by_text:
            commit = _writing_commit(path)
            at = _agent_at(commit, agent_path) if commit else None
            out[name] = {
                "basis": "recovered_from_commit" if at else "unresolved",
                "recorded_hash_is": "the rubric text, which does not identify "
                                    "the scoring rules",
                "recovered_from": commit[:8] if commit else None,
                "instrument_sha256": at,
                "instrument_commit": (by_agent[at]["commit"]
                                      if at in by_agent else None),
            }
        else:
            out[name] = {"basis": "unresolved", "recorded": digest}
    return {"agent_versions": agents, "evaluations": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    doc = {"_note": __doc__.strip().splitlines()[0],
           "rubrics": {r: resolve(r) for r in RUBRICS}}
    if args.write:
        MANIFEST.write_text(json.dumps(doc, indent=1) + "\n")
        print(f"wrote {MANIFEST.relative_to(ROOT)}")
    for rubric, block in doc["rubrics"].items():
        counts = {}
        for entry in block["evaluations"].values():
            counts[entry["basis"]] = counts.get(entry["basis"], 0) + 1
        print(f"{rubric}: {len(block['evaluations'])} evaluations, "
              f"{len(block['agent_versions'])} instrument versions — "
              + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
