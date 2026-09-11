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
    """Every distinct version in this checkout's history, oldest first.

    Unmerged branches do not define this checkout's instruments (#1240).
    """
    out, seen = [], set()
    log = subprocess.run(["git", "log", "HEAD", "--reverse", "--format=%H %cI",
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
    """The last content-writing commit, following byte-identical renames.

    An archive move must not attribute an old score to the agent in force
    when it was archived (#1223). Only exact renames are followed: a move
    that also changes the evaluation is an addition at the new path and
    must use that commit's instrument. `_dirty` is checked before trusting
    this history for bytes on disk (#1100).
    """
    out = subprocess.run(["git", "log", "--follow", "--find-renames=100%",
                          "--diff-filter=AM", "-1", "--format=%H", "--", str(path)],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip()
    return out or None


def _what(digest, by_text):
    """What the evaluation's own hash field turned out to name."""
    if digest is None:
        return "nothing — this evaluation predates the field"
    if digest in by_text:
        return "the rubric text, which does not identify the scoring rules"
    return f"an unrecognised value ({digest[:12]}…)"


def _dirty(path):
    """Whether the file differs from HEAD, or is untracked."""
    rel = Path(path).resolve().relative_to(ROOT)
    out = subprocess.run(["git", "status", "--porcelain", "-z", "--", str(rel)],
                         capture_output=True, text=True, cwd=ROOT).stdout
    return bool(out.strip("\x00").strip())


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
    # Every semantic evaluation under the rubric, not only the live
    # label-aware ones (#1100). The `superseded_*` archives are the direct
    # evidence of the instrument changes this exists to make legible — the
    # scorings #1059, #1060 and #1082 displaced — and were the first thing
    # out of scope. `concatenated/` predates label-aware runs and is included
    # for the same reason: an archived score whose rules cannot be named is
    # exactly the gap.
    base = ROOT / "data" / "evaluation_llm" / rubric
    for path in sorted(glob.glob(str(base / "**" / "*_evaluation.json"),
                                 recursive=True)):
        doc = json.loads(Path(path).read_text())
        meta = doc.get("metadata") or {}
        # The new contract's key first (#1100). Reading only `rubric_hash`
        # meant an evaluation that *obeyed* the revised contract — recording
        # its instrument outright — was still resolved from its writing
        # commit, so following the fix downgraded the evidence it produced.
        digest = meta.get("instrument_sha256") or meta.get("rubric_hash")
        name = str(Path(path).resolve().relative_to(base))
        if meta.get("instrument_kind") == "api_system_prompt":
            api_digest = meta.get("instrument_sha256")
            valid_digest = (isinstance(api_digest, str) and len(api_digest) == 64
                            and all(c in "0123456789abcdef" for c in api_digest))
            out[name] = {
                "basis": "recorded_api_system_prompt" if valid_digest else "unresolved",
                "instrument_kind": "api_system_prompt",
                "instrument_sha256": api_digest if valid_digest else None,
                "instrument_commit": None,
                **({"reason": "API system prompt digest is missing or malformed"} if not valid_digest else {}),
            }
        elif meta.get("instrument_kind") not in (None, "agent_definition"):
            out[name] = {
                "basis": "unresolved", "instrument_kind": meta["instrument_kind"],
                "instrument_sha256": None, "instrument_commit": None,
                "reason": "unknown instrument kind; not assumed to be an agent definition",
            }
        elif digest in by_agent:
            v = by_agent[digest]
            out[name] = {"basis": "recorded", "instrument_sha256": digest,
                         "instrument_commit": v["commit"]}
        elif _dirty(path):
            # Written but not yet committed (#1100). `d4d evaluate llm` leaves
            # exactly this state, and resolving it from the previous commit
            # would name an instrument that did not produce it. The agent on
            # disk is what scored it, and saying so beats calling the corpus
            # unidentifiable the moment an evaluation is produced.
            live = hashlib.sha256((ROOT / agent_path).read_bytes()).hexdigest()
            out[name] = {
                "basis": "working_tree",
                "recorded_hash_is": _what(digest, by_text),
                "recovered_from": "the agent file on disk; this evaluation is "
                                  "not committed",
                "instrument_sha256": live,
                "instrument_commit": (by_agent[live]["commit"]
                                      if live in by_agent else None),
            }
        else:
            # A rubric-text hash, or none at all: the pre-contract evaluations
            # under `concatenated/` record no `rubric_hash`. Either way the
            # commit that carries the bytes is the evidence (#1100).
            commit = _writing_commit(path)
            at = _agent_at(commit, agent_path) if commit else None
            out[name] = {
                "basis": "recovered_from_commit" if at else "unresolved",
                "recorded_hash_is": _what(digest, by_text),
                "recovered_from": commit[:8] if commit else None,
                "instrument_sha256": at,
                "instrument_commit": (by_agent[at]["commit"]
                                      if at in by_agent else None),
            }
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
