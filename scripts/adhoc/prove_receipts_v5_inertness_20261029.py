#!/usr/bin/env python3
# Purpose: reproduce A13 inertness after R4/R6, 2026-10-29.
# Inputs: pinned local git objects, committed baseline hashes, current source.
# Outputs: exact raw JSON under this worktree plus compact hashes/comparison ledger.
# Review: receipts_v5_fixes_claude_rereview_2026-10-29, R4/R6; offline only.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "notes/receipts_v5_merge_validation_2026-10-29"
OUT = EVIDENCE / "r4_r6"
PROBES = Path(__file__).with_name("receipts_v5_merge_probes_20261029")
RUNNER = Path(__file__).with_name("validate_receipts_v5_merge_20261029.py")
BASE_REV = "148c869dde865915221db847b2e89f15f319b365"
CANARY_REV = "5457b71b4bc2cd6879146d7d9dfab08e56d5a2c7"
CANARY_RECORD = ("data/d4d_concatenated/claudecode_api_core/"
                 "2026-09-12_claude-opus-5-api-generic-v9_rep1/CHORUS_provenance.yaml")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT,
                                   env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0"})


def rebuild_inputs(scratch):
    """Materialize immutable local inputs, never a prior session's temp tree."""
    base = scratch / "a13"
    base.mkdir()
    archive = scratch / "a13.tar"
    git("archive", "--format=tar", f"--output={archive}", BASE_REV)
    assert archive.stat().st_size > 0
    subprocess.run(["tar", "-xf", str(archive), "-C", str(base)], check=True)
    archive.unlink()
    chorus = scratch / "chorus_v10"
    for label in ("2026-10-20a", "2026-10-22a"):
        run_label = label + "_claude-opus-5-api-generic-v10_rep1"
        core = f"data/d4d_concatenated/claudecode_api_core/{run_label}"
        names = ["CHORUS_coverage_receipt.yaml", "intermediate/CHORUS_coverage_receipt.yaml",
                 "intermediate/CHORUS_full.yaml"]
        names += [f"intermediate/CHORUS_receipt_completion_{kind}.json"
                  for kind in ("inputs", "request", "response", "result")]
        if label == "2026-10-20a":
            names.append("intermediate/CHORUS_receipt_completion_result_2.json")
        sources = {f"core/{name}": f"{core}/{name}" for name in names}
        sources["full/CHORUS_d4d.yaml"] = f"data/d4d_concatenated/claudecode_api/{run_label}/CHORUS_d4d.yaml"
        for name, source in sources.items():
            path = chorus / label / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = git("show", f"{CANARY_REV}:{source}")
            assert raw
            path.write_bytes(raw)
            assert path.read_bytes() == raw
    print(f"Rebuilt A13 with git archive and canaries from {CANARY_REV} in {scratch}", flush=True)
    return base, chorus


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    assert path.stat().st_size > 0


def normal(raw, tree):
    # As in the independent review: normalize only the checkout's absolute path.
    return raw.replace(str(tree).encode(), b"<TREE>")


def run(kind, name, tree, chorus, canary=False):
    destination = OUT / "raw" / f"{kind}_{name}{'_canary' if canary else ''}.json"
    script = PROBES / {"corpus": "corpus_inert.py", "report": "report_inert.py",
                       "chorus": "chorus_v10_inert.py", "assembly": "assembly_probe.py"}[kind]
    command = [sys.executable, "-S", "-B", str(RUNNER), "--tree", str(tree), "--script", str(script)]
    if kind != "assembly":
        command += ["--", str(chorus if kind == "chorus" else tree), str(destination)]
    if canary:
        command += [CANARY_RECORD]
    env = dict(os.environ, GIT_DIR=git("rev-parse", "--absolute-git-dir").decode().strip(),
               GIT_WORK_TREE=str(tree), GIT_OPTIONAL_LOCKS="0",
               GIT_NO_LAZY_FETCH="1", PYTHONDONTWRITEBYTECODE="1")
    env.pop("RECEIPTS_V5_INSTRUMENT", None)
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    if kind == "assembly":
        destination.write_text(result.stdout)
    (OUT / "raw" / f"{destination.stem}.log").write_text(result.stdout + result.stderr)
    raw = destination.read_bytes()
    assert raw
    value = json.loads(raw)
    if kind in {"corpus", "report"}:
        assert len(value) == (1 if canary else {"corpus": 54, "report": 335}[kind]), (kind, len(value))
        assert not any("error" in row for row in value.values())
        if kind == "report":
            assert not any("error" in (row[v] or {}) for row in value.values() for v in ("v7", "v8"))
    print(f"{kind} {name} {'canary' if canary else 'full'} persisted {len(raw)} bytes", flush=True)
    return normal(raw, tree), value


def verify_base_source(base):
    # Pin the measured source/assembly code to git, not merely an archive directory name.
    paths = ["src/data_sheets_schema/" + name for name in (
        "receipts.py", "report_claims.py", "backfill_checks.py", "api_runner.py",
        "receipt_completion.py", "receipt_completion_policy.py", "shared_generation.py")]
    identities = {}
    for path in paths:
        expected = git("show", f"{BASE_REV}:{path}")
        assert (base / path).read_bytes() == expected, path
        identities[path] = sha(expected)
    return identities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("canary", "full"))
    options = parser.parse_args()
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codex-v5r6-", dir=os.environ["TMPDIR"]) as scratch:
        base, chorus = rebuild_inputs(Path(scratch))
        prove(options.phase, base, chorus)


def prove(phase, base, chorus):
    identities = verify_base_source(base)
    # Each invocation proves one real unit on the same rebuilt inputs and launcher
    # before the full replay. A stale canary.json cannot authorize a new batch.
    counts = {}
    for kind in ("corpus", "report"):
        a, av = run(kind, "base", base, chorus, True)
        b, bv = run(kind, "head", ROOT, chorus, True)
        assert a == b, f"{kind} canary differs"
        row = next(iter(bv.values()))
        assert (row["block"] if kind == "corpus" else row["v8"])["checked"]
        counts[kind] = {"records": 1, "checked": True, "sha256": sha(a)}
    save(OUT / "canary.json", {"passed": True, "slices": counts, "base_source_sha256": identities})
    if phase == "canary":
        return
    saved_baseline = json.loads((EVIDENCE / "validation.json").read_text())["inertness"]
    out = {"base": BASE_REV, "head": git("rev-parse", "HEAD").decode().strip(),
           "base_tree": "rebuilt with git archive in TMPDIR at run time", "canary_inputs_commit": CANARY_REV,
           "python": sys.version, "executable": sys.executable, "base_source_sha256": identities,
           "normalization": "Only each checkout absolute path is replaced by <TREE>.",
           "v5": "off: no explicit v5 selection; RECEIPTS_V5_INSTRUMENT unset",
           "slices": {}}
    for kind in ("corpus", "report", "chorus", "assembly"):
        a, av = run(kind, "base", base, chorus)
        b, bv = run(kind, "head", ROOT, chorus)
        if kind == "assembly":
            keys = ("v10_sg1_r25", "r24_rc1", "r8_rc1", "descriptor_v1")
            assert {k: av[k] for k in keys} == {k: bv[k] for k in keys}
            out["slices"][kind] = {"equal": True, "identities": {k: bv[k] for k in keys},
                                   "N11_routing_sg2_r27": {"base": av["routing_sg2_r27"],
                                                           "head": bv["routing_sg2_r27"]}}
            continue
        assert a == b, f"{kind} differs (raw files retained)"
        entry = {"equal": True, "base_sha256": sha(a), "head_sha256": sha(b), "bytes": len(a)}
        if kind == "corpus":
            entry.update(records=len(bv), checked=sum(bool(r["block"].get("checked")) for r in bv.values()),
                         snapshots=sum(bool(r.get("has_snapshot")) for r in bv.values()))
        elif kind == "report":
            entry.update(records=len(bv), checked_v7=sum(bool((r["v7"] or {}).get("checked")) for r in bv.values()),
                         checked_v8=sum(bool((r["v8"] or {}).get("checked")) for r in bv.values()))
        else:
            entry["runs"] = {}
            for label, row in bv["runs"].items():
                assert row["request_equals_saved_bytes"] and any(row["result_equals_saved"].values())
                entry["runs"][label] = {key: row[key] for key in (
                    "request_sha256", "request_equals_saved_bytes", "result_sha256", "result_equals_saved")}
                entry["runs"][label]["d37"] = [row["v4"]["slots"][key] for key in (
                    "with_receipt_at_receipt", "receiptable_at_receipt")]
        assert sha(a) == saved_baseline[kind]["base_sha256"], f"{kind} differs from committed A13 baseline hash"
        entry["matches_committed_baseline_hash"] = True
        out["slices"][kind] = entry
        save(OUT / "inertness.json", out)
    save(OUT / "inertness.json", out)
    print("All four inertness comparisons passed.", flush=True)


if __name__ == "__main__":
    main()
