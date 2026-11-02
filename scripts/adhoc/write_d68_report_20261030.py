#!/usr/bin/env python3
"""D68-D70/#5212 review items 1-9: final evidence report, 2026-10-30.

Inputs: complete coverage, phase/failure ledgers, resolved findings and census.
Output: the owner's explicitly requested external Markdown report. Refuses an
incomplete gate, unclassified failure, dirty tracked tree or protected-path edit.
No tests, provider calls, Git remotes or other external writes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tag", required=True)
parser.add_argument("--notes-tag", required=True)
parser.add_argument("--d41-run", required=True)
parser.add_argument("--repair-run", required=True)
parser.add_argument("--focused-run", required=True)
parser.add_argument("--census-tag", default="final")
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
expected_output = ROOT.parent / "plans/reviews/d41_legacy_impl_d68_d70_2026-10-30.md"
assert args.output.resolve() == expected_output.resolve()

def git(*words):
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0"}
    return subprocess.check_output(["git", "--no-replace-objects", *words], cwd=ROOT, env=env, text=True).strip()

head = git("rev-parse", "HEAD")
git("diff", "--exit-code", "HEAD")
git("merge-base", "--is-ancestor", "20def9d63", head)
protected = ["src/data_sheets_schema/shared_generation.py",
             "src/download/prompts/canonical_hashes.yaml", "STATUS.md", "data", "notes/decisions"]
git("diff", "--exit-code", "f5e78ff02", head, "--", *protected)
allowed_source = {"src/data_sheets_schema/" + name for name in (
    "api_runner.py", "latch_journal.py", "usage_ledger.py", "canary.py",
    "evaluation/registered_eval_runner.py")}
changed_paths = git("diff", "--name-only", "f5e78ff02", head).splitlines()
assert all(name in allowed_source or name.startswith(("tests/", "scripts/adhoc/", "notes/reviews/"))
           for name in changed_paths), changed_paths
helpers = sorted((ROOT / "scripts/adhoc").glob("*d68*2026103*"))
helpers += [ROOT / "scripts/adhoc/d70_corpus_eligibility_20261030.py",
            ROOT / "scripts/adhoc/d41_legacy_controls_20261029.py"]
git("ls-files", "--error-unmatch", "--", *(str(path.relative_to(ROOT)) for path in helpers))
summary = json.loads((ROOT / ".d68-validation/validation-summary.json").read_text())
audit = summary["specificity"]
assert audit["violations"] == 112 and audit["introduced_since_d9"] == 1
assert audit["violation_files_changed_from_d9"] == audit["inherited_unchanged_from_design"] == [
    "scripts/adhoc/retain_d41_legacy_evidence_20261029.py"]
coverage = summary["final_coverage"]
assert coverage["tag"] == args.tag and coverage["complete"]
assert not coverage["reused_jobs"], "LR12 requires a complete gate on the final production source"
git("merge-base", "--is-ancestor", "50bc50af6", coverage["head"])
tested_packet = git("merge-base", head, coverage["head"])
git("diff", "--exit-code", tested_packet, head, "--", "src", "tests", "utils", ".github")
evidence = ROOT / "notes/reviews/d41_legacy_impl_d68_d70_evidence_20261030"
failures = json.loads((evidence / "failure-ledger.json").read_text())
resolved = json.loads((evidence / "resolved-findings.json").read_text())
assert all(row["also_failed_on_d9"] for row in failures)
assert len(resolved) == 13 and {row["finding"] for row in resolved} == {"LR9", "LR10", "LR11", "LR12", "LR13"}
assert all(row["resolution_verified"] for row in resolved)
manifest = json.loads((evidence / "manifest.json").read_text())
assert manifest and all(row["bytes"] > 0 for row in manifest.values())
for name, row in manifest.items():
    assert Path(name).name == name
    raw = (evidence / name).read_bytes()
    assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"], name
git("ls-files", "--error-unmatch", "--", *(str((evidence / name).relative_to(ROOT))
    for name in ["manifest.json", *manifest]))
jobs = [(row["name"], Path(row["report"]).parent.name) for row in coverage["job_reports"]]
notes = json.loads((ROOT / ".d68-validation/merge/.d68-validation" / f"{args.notes_tag}-notes.json").read_text())
jobs += [(row["name"], f"{args.notes_tag}-{row['name']}") for row in notes["runs"]]
jobs += [("D41 dedicated suites", args.d41_run), ("Repaired cases", args.repair_run),
         ("D68/D70 focused checks", args.focused_run)]

def link(label, path):
    return f"[{label}]({path})"

lines = ["# D68–D70 implementation packet, 2026-10-30", "",
    f"Final packet head: `{head}`. Report generated {datetime.now(timezone.utc).isoformat()}.", "",
    "Implementation is complete. The serial CI selections and baseline controls have finished. "
    "The full gate remains red: every remaining failed test phase has retained d9 evidence; "
    "the twelve introduced test-setup/assertion failures and the verifier layout regression "
    "have explicit, passing replacements. "
    "This is offline validation on native macOS/Python 3.13.12, using CI's test selections, "
    "not an assertion that Linux/Python 3.12 CI ran.", "",
    f"Branch: `{git('branch', '--show-current')}`; a fast-forward descendant of `20def9d63`. "
    f"The final tested scratch merge is `{coverage['head']}`, including the requested target "
    f"`50bc50af6`. Its tested packet ancestor is `{tested_packet}`. Subsequent packet commits "
    "do not change production code, tests, utilities or workflow files. No push, GitHub operation, "
    "provider call or remote Git operation was performed.", "",
    "## Decisions and review requirements", "",
    "- **D68 / review 1, 6, 8, 9:** Option 3. Public execution refuses legacy residue before "
    "sidecar locks, with repeated guards at internal execution, accounting preparation, "
    "ledger mutation and physical-call boundaries. `resume=False` is no escape. C1's whole "
    "tree, including hidden locks, directories, file identities and mtimes, is unchanged. "
    "A fresh ordinary label remains the normal generation route; changing a label over "
    "surviving legacy bytes cannot overwrite that evidence.",
    "- **D69 / review 2, 4:** A journal-less `_legacy` account binds provenance in memory. "
    "An optional validated acknowledgement is disclosed without appending a journal, "
    "rewriting the ledger, spending or refunding `report_regate`. P3/P4/P5 cover public, "
    "internal, preparation, write, spend and `begin_call` entry points, both resume values, "
    "plus CLI refusal. Previously adopted legacy histories also refuse execution.",
    "- **D68 / review 1:** `verify_completed_legacy` is a separate read-only generic-v6 "
    "verifier. It checks positive age, record conformance, instruction/schema/file bindings, "
    "ledger/index input identities, observed accounting, surviving reasoning/snapshots and "
    "current output validation. An explicit root mapping reads unchanged portable captures, "
    "including default split full/core directories. Inventory covers selected-project "
    "artifacts and bound inputs; unrelated projects do not affect verification. "
    "Its envelope is always evidence-only, campaign-ineligible, with unknown historical "
    "accounting completeness and zero new calls. Guarded-history and shared-v2/receipt "
    "controllers are rejected; they have no recovery fallback.",
    "- **D70 / review 3, 4:** Canary baseline/offline verdicts and registered evaluation "
    "reject a missing integrity block on positively post-D41 records or records whose age "
    "is unestablished. Existing integrity blocks retain their original full validation. "
    "Pre-D41 records retain their historical eligibility; quality counts are unchanged.",
    "- **Review 5:** Superseded by the owner's Option 3. No import, recovery authorization "
    "event or new spending command is implemented.",
    "- **Review 9:** Execute-path logic stays in existing `ROUTING_CODE` files. "
    "`shared_generation.py`, canonical pins, decision records, STATUS and existing data/run "
    "directories were not edited. A21 needs a registration constructed after this routing "
    "code lands, followed by request-parity validation.", "",
    "The declared D41 boundary is `8ab03fda923d2c8caa9a2e65e558be73e92500e9`, committed "
    "`2026-10-25T22:11:01-07:00`, derived locally with:", "",
    "```text", "git log --all --diff-filter=A --format='%H %cI' -- src/data_sheets_schema/latch_journal.py", "```", "",
    "A locally resolved descendant is post-D41, even with an earlier claimed timestamp. "
    "A resolved non-descendant in a complete, nonshallow graph establishes pre-D41 age. "
    "Otherwise only a timezone-aware `record_generated_at` strictly before the boundary "
    "establishes pre-D41 age. An unresolved commit without that timestamp is **age "
    "unestablished**. Missing journals or integrity blocks never establish age. Git "
    "resolution disables lazy fetching and replacement objects and is not cached by "
    "mutable ref spelling.", "",
    "The read-only command prints its verification envelope to stdout. Replace the "
    "three paths below with absolute paths; the original root is the prefix recorded "
    "inside the unchanged capture:", "",
    "```text",
    "python -B scripts/adhoc/verify_d68_legacy_20261030.py /capture/record.yaml --evidence-root /capture --recorded-root /original/root",
    "```", "",
    "## Fixtures and changed assertions", "",
    "Plain, manifest-checked before-trees for i1, i2 and C1–C8 are committed under "
    "`tests/fixtures/pre_d41/`. i1 is completed with its original ledger; i2 is interrupted "
    "with its original ledger. An additional `split` capture uses the actual f8 default "
    "full/core layout, without post-generation provenance rewriting. C4 is call 3's "
    "prepared journal-less ledger. Both completed "
    "i1 and C7 verify read-only; all execution attempts refuse without calls or tree "
    "changes. The f8 generator remains outside CI, pinned to "
    "`f8c5ac73caba610d40c49aaceddb31ead3590a72`. C5/C6 preserve the historical hand-written "
    "controls and are explicitly distinguished from production-emitted captures.", "",
    link("Each of the eight original tests has an individual rewrite/retirement disposition", ROOT / "tests/fixtures/pre_d41/README.md") + ".", "",
    "The owner's three named flips (review 7) are:", "",
    "1. `test_missing_ledger_legacy_history_never_becomes_a_clean_resume`: its final fresh "
    "restart now refuses instead of creating a clean generation.",
    "2. `test_legacy_account_requires_explicit_unverifiable_baseline`: provenance preview "
    "and acknowledged inspection are read-only; acknowledgement never permits spending.",
    "3. `test_clean_or_legacy_integrity_does_not_fabricate_a_new_quality_measurement`: "
    "removing the block requires positive pre-D41 age to remain eligible; unknown age is "
    "ineligible without changing the quality measurement.", "",
    "Other current-generation fixtures now establish their guarded account before "
    "synthetic partial outputs. The abandoned-row and output-lock expectations were "
    "aligned with the pre-lock legacy refusal. LR9–LR11 below retain the additional "
    "assertion/setup changes discovered by the full gate.", "",
    "## Committed-record census", "",
    "Every Git-tracked YAML blob containing a generation provenance record was inspected "
    "from each ref; this census is independent of Git ignore rules. Before/after applies "
    "the old and new **runtime-integrity eligibility** predicates to each identical record, "
    "not all separate scientific-quality or registration prerequisites. Added fixture "
    "records explain the different corpus sizes.", "",
    "| Corpus/ref | Records | Pre-D41 | Post-D41 | Unestablished | Canary before → after | Evaluation before → after |",
    "|---|---:|---:|---:|---:|---:|---:|"]
for name in ("base", "packet", "merge"):
    census = json.loads((evidence / f"corpus-{name}-{args.census_tag}.json").read_text())
    if name != "base":
        target = head if name == "packet" else coverage["head"]
        git("diff", "--exit-code", census["ref"], target, "--", "*.yaml", "*.yml",
            "src/data_sheets_schema/latch_journal.py", "src/data_sheets_schema/canary.py",
            "src/data_sheets_schema/evaluation/registered_eval_runner.py")
    counts = census["counts"]
    assert not census["parse_errors"] and counts["v8_records"] == 22 and counts["v8_changes"] == 0
    age = counts["age"]
    lines.append(f"| {name} / `{census['ref'][:12]}` | {counts['records']} | {age.get('pre-D41', 0)} | "
                 f"{age.get('post-D41', 0)} | {age.get('age unestablished', 0)} | "
                 f"{counts['before']['canary']} → {counts['after']['canary']} | "
                 f"{counts['before']['evaluation']} → {counts['after']['evaluation']} |")
lines += ["", "All **22 committed v8 comparators are unchanged** in every census. The one "
    "post-D41 record already has a valid integrity block. Later test/helper/evidence "
    "commits add no provenance YAML and do not change these classifications.", "",
    "## Serial validation", "",
    "Provider credentials were removed before imports; the launcher and OS sandbox "
    "deny external network and remote Git commands, while allowing local fake transports. "
    "All pytest basetemps are under this worktree within `d4d-executions`. Superseded "
    "or interrupted preliminary runs are excluded from final coverage. Launcher "
    "canaries persisted nonempty reports and passed before fanout. The repaired cases "
    "had their own one-case canary on the nested scratch merge, followed by all thirteen "
    "cases. These are offline behavior/persistence checks, not live-provider evidence.", "",
    f"CI collection: **{coverage['expected']} tests, zero collection errors**. Exact "
    "selection and teardown multisets account for the complete six ordinary shards "
    "and four required routing lanes. Whole-tree collection has 17 errors; every file "
    "and error line matches the original d9 archive (11 FAIRSCAPE imports, three "
    "parent-scope package-resolution errors, two renderer dependencies and one obsolete "
    "downloader blocked offline).", "",
    "| Job | Passed | Call failures | Setup/teardown errors | Skipped | Selected |",
    "|---|---:|---:|---:|---:|---:|"]
for label, name in jobs:
    row = summary["runs"][name]
    counts = row["phases"]
    assert not row["collection_errors"]
    errors = counts.get("setup:failed", 0) + counts.get("teardown:failed", 0)
    skips = sum(counts.get(f"{phase}:skipped", 0) for phase in ("setup", "call", "teardown"))
    lines.append(f"| {label} | {counts.get('call:passed', 0)} | {counts.get('call:failed', 0)} | "
                 f"{errors} | {skips} | {row['selected']} |")
lines += ["", "All six ordinary shards, four routing lanes and supplemental notes jobs "
    "were rerun after the LR12 production correction. The final coverage does not reuse "
    "the earlier production snapshot's jobs. Tested heads and exact phase selections "
    "are retained in `coverage.json`. No test phase is silently replaced or omitted.", "",
    "The edit boundary required nested validation worktrees. Existing root-selection "
    "guards choose the enclosing checkout; native isolation, prompt pinning and "
    "evaluation challenge discovery also encounter this layout. A request to create "
    "sibling validation directories received no approval, so no such directory was "
    "created. These guards can prevent downstream behavior from being exercised; the "
    "recorded failures are not claimed as a green normal-environment CI result.", "",
    "## Every remaining failure and its baseline evidence", "",
    link("Exact failed test IDs, phases and d9 evidence", evidence / "failures.md") + "; " +
    link("machine-readable failure ledger", evidence / "failure-ledger.json") + ". "
    "Paired full traces are retained in the `failure-comparison-*.json` artifacts. "
    "Same-name failures alone were not treated as cause equivalence: the paired causes "
    "were reviewed. Fresh controls use unchanged `d9b69d84d` under the same restrictions. "
    "The original d9 archive and its exact collection failures are retained separately; "
    "the original full run was already red.", "",
    "Remaining groups include nested-root CLI/corpus/receipt checks; native isolation "
    "and incomplete local control sessions; missing evaluation-definition predecessors; "
    "prompt/resource/cache placement; protected-data writes and stale corpus checks; "
    "process-inspection/liveness restrictions; and inherited report-wire parity. "
    "The per-test ledger is authoritative for membership and baseline source. V8 "
    "receipt CLI failures at the root guard are distinct from the unchanged D70 census.", "",
    "## Review issue records and dispositions", "",
    "GitHub issue creation was forbidden by the offline instruction. These local "
    "records preserve the findings for the lead; review passes were read-only and "
    "separate from fixes.", "",
    "- **LR1:** Preserve D57 diagnostic redaction at the earlier pre-lock guard; fixed, "
    "with unverified digests explicitly unsuitable as resume anchors.",
    "- **LR2:** Verify the final report's independent hash, not only the intermediate; "
    "fixed with a modified-report negative control.",
    "- **LR3:** Bind ledger/index inputs and reject abandoned or incomplete accounting; "
    "fixed with independent input-drift negatives.",
    "- **LR4:** Avoid mistaking positively foreign guarded ledger/journal state for "
    "selected legacy residue; fixed and covered by flat-identity controls.",
    "- **LR5:** A new label must not overwrite foreign unguarded legacy evidence; fixed "
    "with whole-tree i1/i2/C4/C7 negatives and adopted-history execution refusal.",
    "- **LR6:** Recognize older foreign progress only when both label and generation "
    "bind positive guarded history; fixed, with a label-only negative.",
    "- **LR7:** Delegate uppercase/short/symbolic commit resolution to Git and avoid "
    "caching mutable refs; fixed with real local ancestry/ref-movement tests.",
    "- **LR8:** Keep live process logs inside pytest basetemp to avoid observer-induced "
    "checkout-preservation failures; fixed and verified by a dedicated whole-checkout "
    "logging canary. An earlier failed positional-worktree probe accidentally overlapped "
    "a short baseline notes canary; both were excluded and replaced by serial runs.",
    "- **LR9:** Nine new CLI tests stopped at the independent nested cwd guard. They now "
    "select the guard's actual checkout root from the test module location, preserving "
    "absolute fixture paths, no-provider traps and whole-tree assertions. All nine "
    "replacement cases passed on the scratch merge.",
    "- **LR10:** The old public-boundary test expected orphan-output continuation. Its "
    "d9 version passes; D68/D69 intentionally replace it with pre-lock refusal in both "
    "resume modes, zero execution and unchanged whole tree. Both replacements pass.",
    "- **LR11:** The profile-repair test wrote orphan output before preparing accounting. "
    "Its d9 version passes; the current-generation fixture now prepares its guarded "
    "account first, retaining the real fake repair and exact profile-digest assertion. "
    "The repaired case passes.",
    "- **LR12:** The verifier assumed a flat output directory and inspected unrelated "
    "files under its evidence root. An authentic f8 default-layout capture reproduces "
    "the old failure. Declared full/core paths now validate independently; inventory "
    "covers selected project artifacts and bound inputs. Split-layout, unrelated-project "
    "and selected-file symlink regressions pass with whole-tree preservation.",
    "- **LR13:** A synthetic current record without accounting expected the old "
    "historical-recovery message. Its d9 assertion passes; the replacement test names "
    "its actual post-D41 age, expects the earlier journal-less inspection-only refusal, "
    "and strengthens preservation from four files to the whole temporary tree. It "
    "retains zero calls and absent ledger/journal assertions and passes.", "",
    link("Original failed phases and verified replacements", evidence / "resolved-findings.json") + ".", "",
    "The specificity scan has 112 inherited findings: 111 occur in files unchanged "
    "from d9; the remaining finding is in `retain_d41_legacy_evidence_20261029.py`, "
    "unchanged from the design commit. No new project-keyed "
    "production behavior was introduced. The full scan is not described as green.", "",
    "## Retained artifacts", "",
    link("Evidence manifest with byte sizes and SHA-256 hashes", evidence / "manifest.json") + "; " +
    link("complete phase ledger", evidence / "phase-ledger.json") + "; " +
    link("coverage and tested-head accounting", evidence / "coverage.json") + ".", "",
    "Raw reports, logs and scratch worktrees remain under `.d68-validation/`. All "
    "helper scripts are committed under `scripts/adhoc/`, including the f8 generator, "
    "offline launcher, baseline reproduction, corpus census, comparison, retention "
    "and this report generator. No branch or evidence cleanup was performed.", ""]
args.output.write_text("\n".join(lines))
assert args.output.stat().st_size > 0 and head in args.output.read_text()
print(json.dumps({"report": str(args.output), "head": head,
                  "bytes": args.output.stat().st_size, "failed_phases_retained": len(failures)}))
