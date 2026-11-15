"""Write the evidence-backed census handoff, 2026-11-15 public-stale task.

Inputs: completed summary, JUnit, cost and collection artifacts. Outputs: local
review narrative and a new top section in the assigned lead handoff.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
scratch = Path(sys.argv[1]).resolve()
handoff = Path(sys.argv[2]).resolve()
data = json.loads((root / 'notes/reviews/census_ruling_20261115.json').read_text())
cost_path = scratch / 'ruling-runs/canaries/test_installed_manifest_modes_0/manifest-cost.json'
cost = json.loads(cost_path.read_text())
canaries = list(ET.parse(scratch / 'ruling-runs/canaries.xml').getroot().iter('testcase'))
failures = [case.find('failure') for case in canaries if case.find('failure') is not None]
diagnostic = 'consumed source differs from the reviewed commit: src/data_sheets_schema/native_environment_manifest.py'
assert len(failures) == 2 and all(diagnostic in row.text for row in failures)
rerun = list(ET.parse(scratch / 'ruling-runs/commit-boundary.xml').getroot().iter('testcase'))
rerun_failures = [case.find('failure').text for case in rerun]
assert sum(diagnostic in text for text in rerun_failures) == 1
assert sum('ancestor changed during environment census: /Users/marcin' in text for text in rerun_failures) == 1
assert data['tests']['focused'] == {'cases': 278, 'failures': 0, 'errors': 0, 'skipped': 0}
collection = (scratch / 'ruling-final-collection.log').read_text()
collected = re.search(r'(\d+) tests collected, (\d+) errors', collection).groups()
before, after = data['before'], data['after']
first = 'native_environment_manifest.py:write'
pin = data['pin_proposal']
title = '# Census ruling implemented; source-commit proof blocks the complete after measurement'
status = subprocess.run(['git', 'status', '--short', '--untracked-files=all'], cwd=root,
                        check=True, capture_output=True, text=True).stdout
paths = sorted({line[3:] for line in status.splitlines()} | {
    'notes/reviews/census_ruling_handoff_20261115.md'})
table = (root / 'notes/reviews/census_ruling_20261115.md').read_text()
measurements = {row['operation']: row for row in cost['measurements']}
body = f'''{title}

The approved implementation is present, but uncommitted because Git could not create the worktree index lock. The complete local baseline make_case took {before['timing']['make_case_seconds']:.3f} seconds. A complete after time and capture-to-launch interval are not available: the patched run stopped at the unchanged source-commit proof after {after['watchdog']['elapsed']:.3f} seconds. Its first manifest write completed in {after['first_phase_seconds'][first]:.3f} seconds, compared with {before['first_phase_seconds'][first]:.3f} seconds for the baseline's first write. This is a measured phase improvement, not a demonstrated whole-case speedup or successful public launch.

At baseline make_case return, capture-to-ready was {before['timing']['capture_to_ready_seconds']:.3f} seconds, leaving {before['timing']['freshness_margin_at_ready_seconds']:.3f} seconds against the unchanged {before['timing']['max_age_seconds']} second maximum age. That is not the capture-to-dispatch interval. The patched public correction canary refused before capture or launch at the same uncommitted-source proof, so its freshness margin remains unmeasured.

Validation: {data['tests']['focused']['cases']} focused manifest, mode, registration-shape, guard and adversarial tests passed. The final-source installed-environment cost canary passed: write {measurements['write']['wall_seconds']:.3f} seconds with one generation, cached full verification {measurements['full_reuse']['wall_seconds']:.3f} seconds with no generation, and light verification {measurements['light']['wall_seconds']:.3f} seconds with no generation. The first real registration and public correction canaries both refused the uncommitted source. On rerun, registration confirmed that refusal; the public case instead refused a changed /Users/marcin ancestor identity during generation. This operational sensitivity is recorded without weakening the settled check. Do not report the complete registration matrix or public lifetime as passing; the failed canaries did not authorize an expensive matrix fan-out. Collection found {collected[0]} tests and the {collected[1]} expected missing FAIRSCAPE-model collection errors. Scanner checks had {data['tests']['scanner']['cases'] - data['tests']['scanner']['failures']} passes and {data['tests']['scanner']['failures']} failures attributable to its unchanged manifest pin.

Pin proposal only: in .claude/skills/d4d-generation-specificity-audit/scan.py, the v3 entry for {pin['path']} should change from {pin['old_sha256']} to {pin['new_sha256']}. The scanner was not edited. The new digest was computed from the actual production file, not the temporary candidate.

Implemented behavior: each generate or light census has a fresh context-local directory resolver. It caches directory resolution by path string, records directory and symlink identities and symlink targets, and rechecks them before returning. Every included hashed payload is still opened, sized and hashed during full generation; fresh metadata/RECORD reads and the unowned scan remain. No live census survives a call. Write captures the first successful generation's file fingerprints, checks them with a fresh light census, persists the exact canonical manifest, seeds only an absent full-memo key, and invokes full verification to reread the persisted pin and run another live census. The key includes implementation content identity, and the loaded implementation refuses source drift. Existing successful fingerprints and cached refusals cannot be replaced by recreating an identical manifest pin.

Adversarial coverage includes mid-census ancestor replacement, symlink retargeting, same-size edits, metadata and RECORD changes, an added unowned file, changed implementation bytes, changes after generation and during publication, census disposal, ancestor reuse counts, and preservation of existing memo verdicts. A separate read-only review found the initial candidate's overwrite of existing memo entries; it was corrected and regression-tested. The lead should file the issue record in notes/reviews/census_ruling_findings_20261115.md. This helper made no GitHub write.

The first fixture's 15 verify calls are retained: one after manifest publication; two around preparation; six during composition; and six during reconstruction. Each composition operation calls verify_preparer before and after rendering. Each verify_preparer checks the declared pin and invokes preparation, whose two checks bracket fresh input/source/render work. The first check binds the declared pin; the later checks prove the live path and reconstruction still agree. These are distinct before/after boundaries, not proven identical checks in one step. Each project's preparation follows this path, and native_shared_registration_orchestration._recheck_verified explicitly forces full verification again at dispatch. No call was removed. The complete baseline make_case recorded {before['phases']['native_environment_manifest.py:verify']['calls']} verify calls; the original 15-call observation described its first fixture only.

Timing scope: both measurements used the existing isolated venv and the same phase profiler from the assigned worktree. The baseline source commit and source digest are saved in before-ruling-canonical/source-commit.txt and source-sha256.txt. Baseline early phases overlapped small candidate validation jobs, and host contention varies; do not infer a controlled overall speedup ratio from the first-write comparison. Earlier failed harness runs are retained: a relative interpreter spelling refused canonical-path validation; a candidate runner briefly included its script directory in the import inventory; and creating a sibling scratch directory during a census correctly refused its changed ancestor identity. These are not passing timing results. No primary venv, freshness value, deadline, window, fixture capture order, protected file, prompt pin or controller pin changed. No native binary, provider, production capture, launch, push or GitHub write occurred.

The first two real canaries and the after profile refused with:

```text
{diagnostic}
```

The first canary run also reported that this helper created the summary report files under notes during the run. The individual cost assertion passed and both source-bound tests reached the source-commit refusal, but that run is not a clean whole-suite result. A second run of only the source-bound canaries, with report writing paused, removed that notes warning. Registration again refused at the source-commit proof; the public case instead refused during its first full generation because /Users/marcin changed identity during the census. The diagnostic does not identify the changed stat field or the actor. The required full ancestor identity check includes directory timestamps and therefore can conservatively refuse broader filesystem activity. This behavior was not weakened. The operational finding is recorded for the lead alongside the fixed memo finding; the full public lifetime remains unverified.

Commit attempt: git add returned Operation not permitted while creating /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.git/worktrees/codex-public-stale-20261115/index.lock. Per the assignment, there was no escalation or alternative-index workaround. The lead needs to commit the listed files, review and apply the scanner pin proposal, then rerun the after profile and public/registration canaries in fresh scratch locations. That remaining integration work is required before claiming the original stale-launch problem is resolved.

Files left on codex/public-stale-20261115:

'''
body += ''.join('- ' + path + '\n' for path in paths)
body += '\n' + table
body += f'''
Reproduction and retained evidence:

- scripts/adhoc/implement_census_resolution_20261115.py records the transformation from the original pinned source; it refuses another input hash. Do not rerun it in place on the already-patched source.
- scripts/adhoc/profile_public_stale_20261115.py supplies the external process-group watchdog and phase measurement. The watchdog command arrays and return codes are saved in each run.log.
- scripts/adhoc/measure_public_census_20261115.py observes make_case and launch boundaries without changing gates.
- scripts/adhoc/test_census_candidate_20261115.py validated the generated candidate while the baseline source remained unchanged. Its temporary generated file is under the ignored .temp/census directory; the producer is retained on the branch.
- scripts/adhoc/summarize_census_ruling_20261115.py generates notes/reviews/census_ruling_20261115.json and its Markdown phase table from saved logs.
- scripts/adhoc/write_census_handoff_20261115.py generates this new handoff section from that summary, JUnit and cost evidence.
- Scratch root: {scratch}
- Successful cost artifact: {cost_path}
- Focused JUnit: {scratch / 'ruling-focused.xml'}
- Canary JUnit: {scratch / 'ruling-runs/canaries.xml'}
- Public timing artifact: {scratch / 'ruling-runs/public-timing.jsonl'}
- Canary rerun JUnit: {scratch / 'ruling-runs/commit-boundary.xml'}
- Canary rerun timing: {scratch / 'ruling-runs/commit-boundary-timing.jsonl'}
- Scanner JUnit: {scratch / 'ruling-runs/scanner.xml'}
- Final collection log: {scratch / 'ruling-final-collection.log'}

The JSON summary records SHA-256 values for the retained timing and test evidence. The public timing artifact has no launch-entry record because preparation refused before that boundary.
'''
assert chr(64) not in body
local = root / 'notes/reviews/census_ruling_handoff_20261115.md'
local.write_text(body)
for path in paths:
    assert (root / path).exists(), path
old = handoff.read_text()
marker = '\n<!-- prior handoff -->\n'
if old.startswith(title):
    old = old.split(marker, 1)[1]
assert chr(64) not in old
handoff.write_text(body + marker + old)
assert handoff.stat().st_size > 0
print(str(handoff))
print(hashlib.sha256(handoff.read_bytes()).hexdigest())
