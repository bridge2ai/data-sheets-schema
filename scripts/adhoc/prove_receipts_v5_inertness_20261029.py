#!/usr/bin/env python3
# Purpose: reproduce the reviewer's A13 inertness slices for N1/N3/N4, 2026-10-29.
# Inputs: read-only archived A13/reviewer corpus, local git objects, current source.
# Outputs: exact raw JSON under this worktree plus compact hashes/comparison ledger.
# Review: receipts_v5_562ca36b2_claude_review_2026-10-29; no provider or network calls.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REVIEW = Path("/private/tmp/claude-501/receipts-v5-IDc5")
BASE = REVIEW / "t_148c869dd"
OUT = ROOT / "notes/receipts_v5_merge_validation_2026-10-29"
PROBES = Path(__file__).with_name("receipts_v5_merge_probes_20261029")
RUNNER = Path(__file__).with_name("validate_receipts_v5_merge_20261029.py")
BASE_REV = "148c869dde865915221db847b2e89f15f319b365"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    assert path.stat().st_size > 0


def normal(raw, tree):
    # As in the independent review: normalize only the checkout's absolute path.
    return raw.replace(str(tree).encode(), b"<TREE>")


def run(kind, name, tree, canary=False):
    destination = OUT / "raw" / f"{kind}_{name}{'_canary' if canary else ''}.json"
    script = PROBES / {"corpus": "corpus_inert.py", "report": "report_inert.py",
                       "chorus": "chorus_v10_inert.py", "assembly": "assembly_probe.py"}[kind]
    command = [sys.executable, "-S", "-B", str(RUNNER), "--tree", str(tree), "--script", str(script)]
    if kind != "assembly":
        command += ["--", str(REVIEW / "chorus_v10" if kind == "chorus" else tree), str(destination)]
    if canary:
        prior = json.loads((REVIEW / f"{kind}_148c869dd.json").read_text())
        command += [next(key for key, row in prior.items()
                         if (row["block"] if kind == "corpus" else row["v8"] or {}).get("checked"))]
    env = dict(os.environ, GIT_DIR=str(REVIEW / "repo.git"), GIT_OPTIONAL_LOCKS="0",
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


def verify_base_source():
    # Pin the measured source/assembly code to git, not merely an archive directory name.
    paths = ["src/data_sheets_schema/" + name for name in (
        "receipts.py", "report_claims.py", "backfill_checks.py", "api_runner.py",
        "receipt_completion.py", "receipt_completion_policy.py", "shared_generation.py")]
    identities = {}
    for path in paths:
        expected = subprocess.check_output(["git", "show", f"{BASE_REV}:{path}"], cwd=ROOT)
        assert (BASE / path).read_bytes() == expected, path
        identities[path] = sha(expected)
    return identities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("canary", "full"))
    options = parser.parse_args()
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    identities = verify_base_source()
    if options.phase == "canary":
        counts = {}
        for kind in ("corpus", "report"):
            a, av = run(kind, "base", BASE, True)
            b, bv = run(kind, "head", ROOT, True)
            assert a == b, f"{kind} canary differs"
            row = next(iter(bv.values()))
            assert (row["block"] if kind == "corpus" else row["v8"])["checked"]
            counts[kind] = {"records": 1, "checked": True, "sha256": sha(a)}
        save(OUT / "canary.json", {"passed": True, "slices": counts, "base_source_sha256": identities})
        return
    assert json.loads((OUT / "canary.json").read_text())["passed"]
    out = {"base": BASE_REV, "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
           "python": sys.version, "executable": sys.executable, "base_source_sha256": identities,
           "normalization": "Only each checkout absolute path is replaced by <TREE>.",
           "v5": "off: no explicit v5 selection; RECEIPTS_V5_INSTRUMENT unset",
           "slices": {}}
    for kind in ("corpus", "report", "chorus", "assembly"):
        a, av = run(kind, "base", BASE)
        b, bv = run(kind, "head", ROOT)
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
            # Also prove we replayed exactly the reviewer's saved baseline rows/bytes.
            saved = normal((REVIEW / "corpus_148c869dd.json").read_bytes(), BASE)
            assert a == saved, "receipt corpus differs from reviewer's saved A13 output"
            entry["matches_reviewer_saved_baseline"] = True
        elif kind == "report":
            entry.update(records=len(bv), checked_v7=sum(bool((r["v7"] or {}).get("checked")) for r in bv.values()),
                         checked_v8=sum(bool((r["v8"] or {}).get("checked")) for r in bv.values()))
            assert a == (REVIEW / "report_148c869dd.json").read_bytes()
            entry["matches_reviewer_saved_baseline"] = True
        else:
            entry["runs"] = {}
            for label, row in bv["runs"].items():
                assert row["request_equals_saved_bytes"] and any(row["result_equals_saved"].values())
                entry["runs"][label] = {key: row[key] for key in (
                    "request_sha256", "request_equals_saved_bytes", "result_sha256", "result_equals_saved")}
                entry["runs"][label]["d37"] = [row["v4"]["slots"][key] for key in (
                    "with_receipt_at_receipt", "receiptable_at_receipt")]
        out["slices"][kind] = entry
        save(OUT / "inertness.json", out)
    save(OUT / "inertness.json", out)
    print("All four inertness comparisons passed.", flush=True)


if __name__ == "__main__":
    main()
