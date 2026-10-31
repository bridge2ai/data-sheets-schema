#!/usr/bin/env python3
"""#5212 round-three report, 2026-10-31: summarize retained offline evidence.

Inputs: pytest phase names and census comparison under scratch-5212fix.
Outputs: compact scratch JSON and the explicitly requested review report.
Paths in generated evidence are repository-relative or scratch-relative.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
REPORT = ROOT.parent / "plans/reviews/d41_legacy_impl_d68_d70_2026-10-30.md"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--phases", nargs="+", required=True)
parser.add_argument("--final-phases", nargs="+", required=True)
parser.add_argument("--census", required=True)
parser.add_argument("--prefix", default="r3-final")
args = parser.parse_args()


def git(*command):
    return subprocess.check_output(["git", *command], cwd=ROOT, text=True).strip()


def relative(value):
    return (str(value).replace(str(SCRATCH), "scratch-5212fix").replace(str(ROOT) + "/", "")
        .replace(str(ROOT.parent) + "/", "d4d-executions/")
        .replace(str(ROOT.parent.parent / "data-sheets-schema") + "/", "repo/"))


head = git("rev-parse", "HEAD")
main = git("rev-parse", "origin/main")
phases = []
artifact_censuses = []
for name in args.phases:
    path = SCRATCH / name / "d73-result.json"
    raw = path.read_bytes()
    result = json.loads(raw)
    failures = [r for r in result["reports"] if r["outcome"] == "failed"]
    final = name in args.final_phases
    if final:
        assert result["environment"]["head"] == head, (name, "not final commit")
    counts = Counter(r["outcome"] for r in result["reports"] if r["when"] == "call")
    skips = [r for r in result["reports"] if r["outcome"] == "skipped"]
    phases.append({"name": name, "head": result["environment"]["head"], "final": final,
        "exit_code": result["exit_code"], "selected": len(result["selected"]),
        "call_outcomes": dict(counts), "skipped": len(skips),
        "collection_errors": result["collection_errors"],
        "failures": [{**r, "message": relative(r.get("message", ""))} for r in failures],
        "command": [relative(s) for s in result["command"]],
        "raw_report": relative(path), "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "passed_by_file": dict(Counter(r["nodeid"].split("::", 1)[0] for r in result["reports"]
                                       if r["when"] == "call" and r["outcome"] == "passed"))})
    if final:
        for path in sorted((SCRATCH / name).glob("*/artifact-census.json")):
            if path.parent.is_symlink():
                continue
            artifact_censuses.append({"phase": name, "case": path.parent.name,
                "source": relative(path), **json.loads(path.read_text())})
census = json.loads((SCRATCH / args.census).read_text())
assert census["after_head"] == head
protected = git("diff", "--name-only", "c9567e3c3", head, "--", "data",
    "src/data_sheets_schema/shared_generation.py", "src/download/prompts/canonical_hashes.yaml",
    "notes/coordination/STATUS.md")
assert not protected
assert not git("diff", "--name-only") and not git("diff", "--cached", "--name-only")
compaction = json.loads((ROOT / "notes/reviews/d73_5212_evidence_20261031/compaction.json").read_text())
summary = {"head": head, "main": main, "commits": git("log", "--reverse", "--format=%H %s",
    "c9567e3c3..HEAD").splitlines(), "phases": phases, "census": census,
    "protected_path_changes": [], "evidence_compaction": compaction,
    "artifact_censuses": artifact_censuses}
destination = SCRATCH / (args.prefix + ".json")
destination.write_text(json.dumps(summary, indent=2) + "\n")
lines = [f"# D68–D70 / D73 round-three implementation: `{head}`", "",
    f"Local main remains `{main}`. No additional main merge was needed.",
    "All validation below uses complete pinned git archives with isolated HEAD/index metadata and local object alternates. "
    "The pinned FAIRSCAPE submodule is restored from local Git. Provider keys are removed; the OS sandbox blocks external network. "
    "Tests run serially except the single requested ordinary xdist shard and its one-node canary. "
    "The local platform is macOS/Python 3.13.12, not GitHub's Ubuntu/Python 3.12.", "",
    "Commits since the reviewed merge:", "", *[f"- `{item}`" for item in summary["commits"]], "",
    "| Finding | Disposition |", "|---|---|",
    "| Codex 1 / Claude A | Removed the writer-name allowlist. Every regular file/symlink with the selected prefix or dot-prefix is a candidate. Real guarded controller runs discover their artifact sets; every singleton is refused in both modes with zero calls and an unchanged tree. Actual atomic temporaries, context admission/refusal/collisions, routing captures and incomplete completion output are covered. All 26 before-fix missed-writer regressions fail on c9567e3c3. |",
    "| Codex 2 | Guarded P_X, P_reconcile and VOICE_PEDIATRIC siblings are disambiguated in flat and split layouts. Unattributed or conflicting ownership refuses and names the files/new-label remedy. README explicitly accepts ambiguous phase-name collisions. |",
    "| Codex 3 | Ownership is per artifact: explicit identities, validated journal histories and exact path/hash bindings. Foreign metadata cannot suppress unrelated ledgers, archives or partial deliveries. Mixed/ambiguous JSONL remains residue. |",
    "| Codex 4 | No Git resolution/topology caches remain. Local object arrival and new shallow boundaries are retested in one process. Evaluation dispatch rechecks eligibility using the provenance bytes already bound in its prepared plan. |",
    "| Codex 5 | Read-only guards precede repair derivation, readdress snapshots, call recovery/activation, receipt counting/saving, typed packet saving and receipt recovery/publication. Authentic c7 controls check refusal, zero calls and whole-tree preservation. Receipt publication temporaries now include the project prefix. |",
    "| Codex 6 | Batch preflights every selected identity before acquiring its coordination lock; execute retains the per-run guard. The negative batch test forbids both acquisition and dispatch. |",
    "| Codex 7 | baseline_for and report_basis report each unknown-age baseline on stderr as eligible. Returned metric values/counts are unchanged. |",
    "| Coverage caveats | Added negative midnight/missing-accounting and portable-reasoning cases, a real guarded index-publication interruption control, and real prepare rejection of a post-D41 record with no integrity block. Missing guarded accounting now refuses before lock writes. |",
    "| Claude B | Fresh and completed execute results include record_age in checks; batch verdicts therefore carry the same informational field as offline verdicts. |",
    "| Claude C | The residue guard, verifier, shared no-resume check and historical intermediate fallback use owned_artifacts. An existing generation-bound intermediate index remains authoritative. |",
    "| Claude D | The old shard plan is gzip-compressed; validation paths are normalized. Original evidence bytes and hashes remain in scratch. New full plans/logs/reports remain outside Git. |", "",
    "The verifier remains explicitly limited to generic_v6 API records with a structured request spec (D73(b)). "
    "There is no recovery spending, adoption authorization, project-specific branch or new ROUTING_CODE module.", "",
    "#5212 must land as a merge commit so the declared D41 boundary remains an ancestor of the landing commit.", "",
    "The complete inventory includes coordination locks. Execution's repeated startup checks recognize only empty locks "
    "exclusively created and currently held by that invocation, with matching canonical path/inode/mtime. "
    "Pre-existing, released, changed or replaced locks remain residue; verifier inventory has no lock exemption. "
    "A new identity can require a new output directory when old sidecars have no positive owner binding.", "",
    "Fixture changes preserve their original downstream assertions: foreign-output and torn-abandoned-journal fixtures "
    "now bind the individual artifacts; wire-test stubs carry complete run/path identity; the foreign midnight-date control "
    "uses an ordinary separate output label. The four previously accepted D73(c) flips remain disclosed in the fixture README.", "",
    "| Phase | Source | Passed | Call failures | Skips | Collection errors | Selected |", "|---|---|---:|---:|---:|---:|---:|"]
for phase in phases:
    counts = phase["call_outcomes"]
    lines.append(f"| {phase['name']} | `{phase['head'][:9]}`{' final' if phase['final'] else ' historical'} | "
        f"{counts.get('passed', 0)} | {counts.get('failed', 0)} | {phase['skipped']} | "
        f"{len(phase['collection_errors'])} | {phase['selected']} |")
lines += ["", "Phase counts overlap; they are not summed as unique tests. Raw reports, exact arguments, "
    f"hashes and per-file counts: `{relative(destination)}`.", "",
    "The before-fix 26 failures are expected defect witnesses on c9567e3c3. Exploratory "
    "runs also found a batch-test mock target typo, three torn-journal fixtures lacking "
    "per-file ownership, an exact missing-ledger diagnostic mismatch, and a shared "
    "unknown-output expectation superseded by the earlier D69 refusal. Those were "
    "corrected before final validation. The interrupted focused-c run is partial evidence only.", "",
    "The exploratory broad run found ten additional interactions introduced by the complete inventory. "
    "The intermediate-sibling fixture now initializes guarded foreign history; the flat-label fixture "
    "binds its report; the D55 launch stub initializes accounting while its new locks are held. "
    "The three predecessor-activation parameters and the publication/acknowledgement case bind their "
    "predecessor's lock paths, preserving all recovery assertions. The concurrency case expects "
    "inspection-only for an unbound foreign label; both split/flat cases preserve direct physical-lock "
    "exclusion and add unchanged-tree public refusals. Their original nodes are rerun on c9567e3c3 "
    "in broad-base for base evidence; the README discloses every change. "
    "A separate directory-alias regression fails before the canonical-path fix; edited/released locks "
    "remain residue. Raw phase results below distinguish exploratory failures from final results.", "",
    "An additional inverse-prefix check exposed a false acceptance in both resume modes: "
    "guarded P history was treating an unattributed P_X artifact as foreign to selected P_X. "
    "A broader namespace now proves nothing by itself; explicit per-artifact identity/path/hash "
    "attribution remains available. Both before-fix controls are retained as shorter-before.", "",
    "The exploratory ordinary shard additionally exposed eight batch-cost nodes. "
    "Three pending-call cases, inherited by a second class, now use real guarded ledger writes; "
    "two unkeyed-row cost controls retain their exact accounting assertions on guarded generations. "
    "The renamed zero-cost control states that scope. A new journal-less legacy-label case "
    "requires refusal, no lock acquisition/dispatch and an unchanged tree. No guard is mocked. "
    "The original full batch-cost file is retained as batch-base evidence on c9567e3c3.", "",
    "Final-archive artifact censuses (separate runs can overlap):", ""]
for census_row in artifact_censuses:
    lines.append(f"- `{census_row['phase']}/{census_row['case']}`: "
        f"{census_row['singletons']} artifacts, {census_row['refusal_checks']} refusal checks.")
lines += ["", "Corpus census (every committed generation/derived record):", ""]
for label in ("before", "after"):
    counts = census[label]
    ages = {kind: counts['age'].get(kind, 0) for kind in
            ("pre-D41", "post-D41", "age unestablished")}
    lines.append(f"- {label}: {counts['records']} records; ages `{json.dumps(ages, sort_keys=True)}`; "
        f"canary eligible {counts['after']['canary']}; evaluation eligible {counts['after']['evaluation']}; "
        f"v8 records {counts['v8_records']}.")
lines += ["- Round-three per-record eligibility changes: 0. V8 comparator changes: 0.", "",
    "Remaining failures in final-commit phases:", ""]
remaining = [r for p in phases if p["final"] for r in p["failures"]]
lines += [f"- `{r['nodeid']}` ({r['when']}): {r['message']}" for r in remaining] or ["None."]
lines += ["", "No protected source pins, shared_generation.py, live data/ runs, ATTIC or STATUS were edited. "
    "No provider, network, remote Git, push or gh operation was used. "
    "Only one ordinary shard of four was requested; the other shards and the actual CI platform remain unverified locally.", ""]
if REPORT.exists():
    prior = REPORT.read_bytes()
    backup = SCRATCH / ("report-before-round3-" + hashlib.sha256(prior).hexdigest()[:12] + ".md")
    if not backup.exists():
        backup.write_bytes(prior)
REPORT.write_text("\n".join(lines))
assert REPORT.stat().st_size and destination.stat().st_size
print(json.dumps({"head": head, "report": relative(REPORT), "summary": relative(destination),
                  "final_failures": len(remaining)}, indent=2))
