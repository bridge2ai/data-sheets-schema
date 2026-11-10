"""Write #5517 evidence/report and one coordination status entry, 2026-11-08.

Inputs: committed proposal, local bundles, and completed bounded pytest XML.
Outputs: scratch audit/patch, the brief's report, and one STATUS entry. Offline.
Run only after committing and completing the separate read-only review.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import yaml

from context_evidence_5517 import BASE, CHANGES, ROOT, sources

SCRATCH = ROOT.parent / "scratch-codex-5517"
REPORT = ROOT.parent / "plans/reviews/codex_5517_2026-11-08.md"
STATUS = ROOT.parent.parent / "data-sheets-schema/notes/coordination/STATUS.md"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


assert git("branch", "--show-current").strip() == "codex/5517-context-evidence-20261108"
assert not git("status", "--porcelain").strip(), "commit the full proposal first"
head = git("rev-parse", "HEAD").strip()
allowed = {f"data/context/{p}_context.yaml" for p in ("ai_readi", "chorus", "cm4ai", "kids_first", "voice", "voice_pediatric")}
allowed |= {"tests/test_context_evidence_verbatim.py", "scripts/adhoc/context_evidence_5517.py", "scripts/adhoc/run_context_evidence_5517_tests.py", "scripts/adhoc/report_context_evidence_5517.py"}
changed = set(git("diff", "--name-only", BASE, head).splitlines())
assert changed <= allowed, changed - allowed
audit = []
bundles = {}
for path in sorted((ROOT / "data/context").glob("*_context.yaml")):
    project = path.stem.removesuffix("_context")
    bundle_path, bundle, manifest = sources(project)
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    assert digest == manifest["bundle_sha256"]
    bundles[project] = {"path": str(bundle_path.relative_to(ROOT)), "sha256": digest}
    old = yaml.safe_load(git("show", f"{BASE}:{path.relative_to(ROOT)}"))
    new = yaml.safe_load(path.read_text())
    for predicate in new:
        assert old[predicate]["value"] == new[predicate]["value"]
        def literal(value):
            body = re.sub(r"^(?:\[(?:chunks:|curator_assertion:)[^]]+\]\s*)+", "", value)
            return bool(body) and body in bundle
        audit.append({"project": project, "predicate": predicate, "current_string": old[predicate]["evidence"], "proposed_string": new[predicate]["evidence"], "baseline_verbatim": literal(old[predicate]["evidence"]), "proposal_verbatim": literal(new[predicate]["evidence"]), "disposition": "needs human authoring of a full literal quotation; no verdict on truth or applicability"})
for project, predicate, flag, *_ in CHANGES[:10]:
    assert flag.casefold() not in sources(project)[1].casefold(), (project, flag)
assert "HeLa" not in (ROOT / "data/context/cm4ai_context.yaml").read_text()
assert not re.search(r"\bHeLa\b", sources("cm4ai")[1], flags=re.I)
counts = {}
for name in ("canary-final", "focused-final", "literal-final"):
    suite = ET.parse(SCRATCH / f"{name}.xml").getroot().find("testsuite")
    counts[name] = {key: int(suite.get(key)) for key in ("tests", "failures", "errors", "skipped")}
    counts[name]["passed"] = counts[name]["tests"] - sum(counts[name][k] for k in ("failures", "errors", "skipped"))
evidence = {"base": BASE, "commit": head, "bundles": bundles, "test_counts": counts, "contexts": audit}
(SCRATCH / "audit.json").write_text(json.dumps(evidence, indent=2) + "\n")
(SCRATCH / "proposal.patch").write_text(git("diff", "--binary", BASE, head))
assert all(not row["proposal_verbatim"] and not row["baseline_verbatim"] for row in audit)
text = f"""# #5517 applicability evidence proposal — 2026-11-08

Local commit: `{head}` on `codex/5517-context-evidence-20261108`.
Baseline: `{BASE}`. **Proposal only; not ready for integration.** Owner review remains #2912.

The patch addresses all 10 absent-term flags, all 4 near-empty c002 citations, and all 11 additional uncited-term flags in the lead's 2026-11-05 review pack. The table below records the complete old/new strings, exact bundle snippets, file/line/chunk locations and confidence. All 42 applicability values and both D52 owner-decision strings are preserved. No rubric, instruction, source bundle, manifest, historical decision record or protected pin was edited.

The five study bundles resolve through `data/preprocessed/source_manifest.yaml`, the context-declared chunk manifests and their `bundle` paths under `data/preprocessed/concatenated`. KIDS_FIRST is an external holdout, absent from the study manifest: its context declares `notes/matched_cborg_2026-09-13/kids_first/chunks.yaml`, whose bundle is the sibling `KIDS_FIRST_preprocessed.txt`. All six bundle SHA256 values match those manifests; exact paths/hashes are in `audit.json`.

HeLa is already absent from the baseline CM4AI context; no redundant correction was made. A direct whole-file, case-insensitive word search of the declared CM4AI bundle also found no HeLa. The ten originally flagged spellings are absent case-insensitively from their entire declared bundles. These checks read the explicit files, including all their contents regardless of ignore rules; they do not infer absence from a tracked-files-only search.

FISMA/HMB-specific claims are removed, retaining the supported consent/policy requirement. HPO-coded is conservatively removed without changing the owner's false ML-training decision; the table records that HPO mapping itself is supported. The HGSC URL supports the sequencing-partner citation, but its expanded institutional name still needs human authoring. VOICE geography is removed pending release-specific review: the uncited North American occurrence concerns 12 institutions, not the asserted five-site release. Pediatric MFCC wording comes from the pediatric release itself, rather than citing adult v3 documentation merely because it contains the acronym. The IRB paraphrase uses the direct approval statement, not a generic IRB over-enrollment rule.

## Literal evidence acceptance remains blocked

The existing `tests/test_evaluation_context_files.py:79` checker validates chunk IDs and selected regression terms, not verbatim support. The new `tests/test_context_evidence_verbatim.py` checks every predicate's complete evidence body against its declared, hash-verified bundle. It strips only leading citation/curator metadata, performs no case folding, token matching, fuzzy matching, skip, xfail or grandfather exemption, and asserts the six-project/seven-predicate inventory. Mutation tests reject fabricated extensions and case changes.

**All 42 baseline and proposed full narrative strings fail literal matching.** Every one is explicitly classified as **needs human authoring** in `audit.json`, with old and proposed strings. Exact supporting snippets for the bounded corrections are not proof that each whole narrative is a quotation or is entailed. Replacing all narratives (including owner-authored interpretations) with quotations is left for #2912; the new strict gate intentionally remains red rather than falsely accepting token overlap. Thus the requested test is supplied, but a passing full-literal acceptance gate is not achieved. Do not merge this proposal as a green correction.

## Pins and validation

The human decision record `notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md:22` pins normalized digests for all six contexts. Those pins remain untouched, so its existing synchronization test fails after the proposal. The explicit-path search (including ignored files) of that record, `src/download/prompts/canonical_hashes.yaml` and `notes/matched_cborg_2026-09-17_v10t/registration.public.json` is saved as `pin-references.txt`; it is not an exhaustive claim about all historical registrations. The v10t registration names the separate Kids First `applicability.yaml`. The lead's issue note states that A21 pins the CHORUS omission context, not these applicability files. No pins were rotated and no registration identity was recalculated.

Final canary: {counts['canary-final']['passed']} passed. Final focused suite: {counts['focused-final']['passed']} passed, {counts['focused-final']['failures']} failed (the preserved historical digest table). Final strict suite: {counts['literal-final']['passed']} passed, {counts['literal-final']['failures']} failed (six projects, covering all 42 narrative strings). No errors or skips. Counts overlap at the checker mutation test and must not be added as distinct tests. Logs and JUnit XML are in `{SCRATCH}`. Earlier iterations are preserved separately. Full repository tests were not run.

Interpreter: existing primary `.venv/bin/python`, Python 3.13.12. Every pytest used absolute `PYTHONPATH={ROOT}/src:{ROOT}`, at most `-n 2`, a process-group 3600-second supervisor, scratch-only basetemp/TMPDIR and no pytest cache. The quiet lock was absent before each run; the supervisor also checks during execution and terminates its own group if it appears. No quiet-window interruption occurred. The canary exercised the same launcher/environment/concurrency and its nonempty log/XML and one passing testcase were inspected before the focused runs. CHORUS and then AI_READI context-write canaries were inspected before the corresponding bulk applications. No provider/native-agent execution, network, fetch, push, gh, installation or external message occurred.

## Read-only review and handoff

A separate read-only pass inspected the final context and helper/test diffs, preserved decisions, source snippets, changed-path allowlist, test failures and patch whitespace. The known limitations are the existing #5517/#2912 human-authoring work and the intentionally unchanged digest pins; they are not silently fixed or represented as a clean integration gate. Online issue/PR actions are deferred by the explicit offline/no-push instruction. No new independent defect was identified in this bounded pass. The broad initial local search was unnecessarily expansive; it completed without changing files and was replaced by explicit file reads.

Scratch contains `proposal.patch`, `audit.json`, `reviewer-table.md`, `pin-references.txt`, and all test artifacts. Reproduction helpers are committed under `scripts/adhoc/`: `context_evidence_5517.py`, `run_context_evidence_5517_tests.py`, and `report_context_evidence_5517.py`. The final helper writes this report and exactly one STATUS entry; it refuses a duplicate. Stopped after the required handoff.

"""
text += (SCRATCH / "reviewer-table.md").read_text()
REPORT.write_text(text)
assert REPORT.stat().st_size > 1000 and head in REPORT.read_text()
status = STATUS.read_text()
marker = "**codex #5517 context-evidence proposal**"
assert marker not in status, "refusing duplicate STATUS entry"
assert status.count("### codex\n") == 1
now = datetime.now(timezone.utc).isoformat(timespec="seconds")
entry = f"\n- {now} {marker}: local commit `{head}` on `codex/5517-context-evidence-20261108`; 25 flags reviewed with verbatim snippets, all applicability values/owner decisions preserved. Proposal NOT ready for integration: focused 24 passed/1 historical-pin failure; strict 2 passed/6 project failures (42 narratives need human authoring). Pins/protected files untouched; offline, no native execution/push/gh; bounded -n 2 checks. Report: `d4d-executions/plans/reviews/codex_5517_2026-11-08.md`; all scratch/evidence in `scratch-codex-5517`. Owner #2912 review required; stopped.\n"
status = status.replace("### codex\n", "### codex\n" + entry, 1)
STATUS.write_text(status)
assert STATUS.read_text().count(marker) == 1
print(f"Report verified: {REPORT}; exactly one STATUS entry written; commit {head}")
