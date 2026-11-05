#!/usr/bin/env python3
# Purpose: preserve audit arrays, exact diffs and test counts for #5483 J-a, 2026-11-05.
# Inputs: local validation JSON/XML/logs and Git diff; output: assigned external report.
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = Path('/private/tmp/issue-j-a-20261105')
REPORT = ROOT.parent / 'plans/reviews/issue_j_a_2026-11-05.md'
before = json.loads((OUT/'before.json').read_text())
after = json.loads((OUT/'after.json').read_text())
jb = {'notes/claudecode_direct/prepare_direct.py', 'notes/matched_cborg_2026-09-13/prepare_registration.py'}
assert len(before['violations']) == 24
assert len(after['violations']) == 9
assert after['violations'] == [v for v in before['violations'] if v['path'] in jb]

def model(data):
    if isinstance(data, dict):
        if 'model_facing_modules' in data:
            return data['model_facing_modules']
        for value in data.values():
            found = model(value)
            if found is not None:
                return found
    return None

bm, am = model(before), model(after)
for key in ('derived', 'listed_not_derived', 'derived_not_listed'):
    assert bm[key] == am[key], key
print('Verified: 24 -> 9; remaining objects and model derivation unchanged', flush=True)
for label, data in [('before', before), ('after', after)]:
    (OUT/(label+'-findings.json')).write_text(json.dumps(data['violations'], indent=2)+'\n')
suite = ET.parse(OUT/'tests.xml').getroot()
counts = {key: sum(int(s.get(key, 0)) for s in suite.iter('testsuite')) for key in ('tests','failures','errors','skipped')}
assert counts['failures'] == counts['errors'] == 0
execution = json.loads((OUT/'tests.execution.json').read_text())
collection = json.loads((OUT/'collect.execution.json').read_text())
assert execution['exit_code'] == collection['exit_code'] == 0
collection_count = [line for line in (OUT/'collect.log').read_text().splitlines() if 'tests collected in' in line][-1]
diff = subprocess.check_output(['git', 'diff', '6d6031792', '--', 'notes/ci_timing_refresh_2026-11-04/README.md', 'scripts/adhoc/d41_request_parity_20261026.py', 'scripts/adhoc/profile_admission_r3_20261104.py', 'scripts/adhoc/retain_d41_legacy_evidence_20261029.py', 'scripts/adhoc/wave5_5210_fixture_20261028.py', 'tests/test_d41_request_parity.py'], cwd=ROOT, text=True)
changed = set(subprocess.check_output(['git','diff','--name-only','6d6031792'],cwd=ROOT,text=True).splitlines())
other = set(subprocess.check_output(['git','diff','--name-only','6d6031792','d0974d4bc'],cwd=ROOT,text=True).splitlines())
assert not changed & other, changed & other
text = '''# Issue J-a — local completion, 2026-11-05

Tasks 1–5 executed in `codex-issue-j-a`, branch `codex/issue-j-a-helpers-20261105`, from `6d6031792e914088823a5204f09fac6c6c1106f6`. No fetch, push, gh, network, provider calls or PR creation. Stop after task 5; landing remains deferred until after #5213.

## Audit and scope

Baseline: full scanner on a `git archive` of the base, exit 1, 24 findings.
After: full scanner on the edited worktree, exit 1, exactly nine findings.
An earlier after-audit overlapped removal of the fixture and exited 2 because the discovered file disappeared. It was discarded and rerun after removal; the completed audit supplies the array below.
The after array equals the baseline array filtered to the two J-b preparers, field for field and in order. The model-facing `derived` mapping (including its reasons), `listed_not_derived`, and `derived_not_listed` are unchanged. No scanner, exception, assertion, production pin, run directory or ATTIC edits. Changed tracked paths have no intersection with local #5213 merge `d0974d4bc` versus this base.

## Changes and reasons

- Parity helper: project, partition and context path are required caller inputs, threaded through the fixture, capture subprocess and CLI. Format and scope use the selected project. The existing test supplies its original CHORUS values; real SDK serialization remains offline MockTransport.
- Evidence retention: select the sole attempt directory from evidence, assert exactly one directory, then preserve the original diagnostic-copy checks. Missing or ambiguous attempts refuse.
- Admission profiler: require `--case`, forward it to the worker, and retain it in environment/profile evidence. The README supplies the original node ID.
- Wave5 fixture: remove only the generated copy. Before removal, moved the original to scratch and ran the unchanged generator with `--prepare-fixture`. `cmp` succeeded; both files have SHA-256 `64b8061fc6df32d7a1dbd14a1cec1a4c11857334a85310efd461be0a597db174`. The original test source hash printed by the generator was `1cf90e19274cccbd1fff2f41dab3a03ce726109198e839e5c14443c2f544ed08`. The generator remains unchanged.
- Three provenance scripts retain the bounded edit recipe, deadline-controlled validation commands and this report construction under `scripts/adhoc/`.

## Consumer checks and validation

Ignore-independent (`rg -uu`) searches covered this worktree, then bounded Python/YAML searches in tests, CI and notes. The only direct test consumer of these helpers is `tests/test_d41_request_parity.py`; no test or CI workflow refers to the generated fixture. Its only executable consumer is the retained `derive_5210_wire_baseline_20261028.py`, which recreates and verifies it. Historical evidence references remain preserved. Other worktrees were not searched.

Validation uses the existing primary-checkout Python 3.13 venv, with this worktree's src/root and the existing fairscape submodule on PYTHONPATH. No installation. Pytest runs serially, each with a 3600-second process-group deadline, credential filtering and plugin autoload disabled. The parity helper itself refuses sockets and uses MockTransport. No historical profiling campaign was launched.

'''
text += f"Focused suite: {counts}; elapsed {execution['seconds']:.2f}s. Includes all of `test_d41_request_parity.py`, `test_generation_specificity_skill.py`, `test_neutral_generation_schema.py`, `test_profiles.py`, and `test_external_dataset_onboarding.py`.\n\nCollection: {collection_count}; exit 0. `git diff --check` passed.\n\n"
text += '## Before finding array\n\n```json\n'+json.dumps(before['violations'],indent=2)+'\n```\n\n## After finding array\n\n```json\n'+json.dumps(after['violations'],indent=2)+'\n```\n\n'
text += '## Exact per-file diff\n\n```diff\n'+diff+'\n```\n\n'
text += '## Evidence locations\n\nFull audit JSON/Markdown, extracted arrays, test XML, logs and execution JSON remain at `/private/tmp/issue-j-a-20261105/` (temporary; the arrays and diff are preserved above). Committed provenance scripts: `scripts/adhoc/apply_issue_j_a_20261105.py`, `scripts/adhoc/issue_j_a_validation_20261105.py`, `scripts/adhoc/report_issue_j_a_20261105.py`.\n'
REPORT.write_text(text)
assert REPORT.stat().st_size > 0
print(REPORT)
print(counts)
print('exact remaining findings and model derivation verified')
