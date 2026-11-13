#!/usr/bin/env python3
"""Report helper-2 repairs and retained failures, 2026-11-12.
Inputs: assigned worktree, saved isolated-runner logs/JUnit and local Git blobs.
Outputs: helper-2 scratch audit JSON/search evidence and the lead handoff.
Serves claude-lead-helper2-observer-alias-and-test-repairs-20261112; no network.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
ROOT = E / 'codex-native-observer-alias-20261112'
SCRATCH = E / 'scratch-h2-observer-alias-20261112'
REPORT = E / 'codex-development-efficiency-20261111'
BASE = '5d63d0a77dc43c064cfc2b376355f98009dd5b6e'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
OBSERVER = 'src/data_sheets_schema/native_shared_observations.py'
PROTECTED = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(ROOT), *args])
def save(name, value):
    path = SCRATCH / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    return path
old = git('show', BASE + ':' + OBSERVER)
new = (ROOT / OBSERVER).read_bytes()
searches = []
for label, pattern in [('old-observer-hash', sha(old)), ('observer-references', 'native_shared_observations')]:
    command = ['rg', '--no-ignore', '--hidden', '-n', '-F', '-g', '!.git', pattern, '.']
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    assert result.returncode in (0, 1), result.stderr
    path = SCRATCH / (label + '.txt')
    path.write_bytes(result.stdout)
    searches.append({'command': command, 'cwd': str(ROOT), 'returncode': result.returncode,
        'output': str(path), 'sha256': sha(result.stdout), 'stderr': result.stderr.decode()})
pins = {str(path.relative_to(ROOT)): sha(path.read_bytes())
    for path in sorted((ROOT / 'src/data_sheets_schema').rglob('*'))
    if path.is_file() and path.suffix in ('.py', '.yaml', '.json')}
old_pins = dict(pins, **{OBSERVER: sha(old)})
def production(pins, before):
    rows = []
    for rel, digest in sorted(pins.items()):
        raw = old if before and rel == OBSERVER else (ROOT / rel).read_bytes()
        if rel.endswith('.py') and raw:
            module = '.'.join(Path(rel).with_suffix('').parts[1:]).removesuffix('.__init__')
            rows.append({'module': module, 'path': str(ROOT / rel), 'sha256': digest, 'bytes': len(raw)})
    return rows
protected = [{'path': p, 'current_sha256': sha((ROOT / p).read_bytes()),
    'candidate_sha256': sha(git('show', BASE + ':' + p)), 'main_sha256': sha(git('show', MAIN + ':' + p))}
    for p in PROTECTED]
assert all(row['current_sha256'] == row['candidate_sha256'] == row['main_sha256'] for row in protected)
cohorts = []
for directory in sorted((SCRATCH / 'tests').iterdir()):
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    root = ET.fromstring((directory / 'pytest.xml').read_bytes())
    counts = Counter()
    cases = []
    for case in root.iter('testcase'):
        status = next((kind for kind in ('failure', 'error', 'skipped') if case.find(kind) is not None), 'passed')
        counts[status] += 1
        cases.append({'id': case.get('classname') + '::' + case.get('name'), 'status': status,
            'message': None if status == 'passed' else case.find(status).get('message')})
    files = {name: sha((directory / name).read_bytes()) for name in
        ('pytest.log', 'pytest.xml', 'pytest-command.json', 'outcome.json', 'network.json', 'origins-before.json')}
    cohorts.append({'name': directory.name, 'counts': dict(counts), 'cases': cases,
        'outcome': outcome, 'files': files, 'directory': str(directory)})
status = git('status', '--short').decode()
assert not status.strip(), status
commits = git('log', '--reverse', '--format=%H %s', BASE + '..HEAD').decode().strip().splitlines()
assert len(commits) == 3
review_result = subprocess.run(['git', '-C', str(ROOT), 'diff', '--check', BASE, 'HEAD'], capture_output=True, text=True)
review = review_result.stdout
data = {'head': git('rev-parse', 'HEAD').decode().strip(), 'base': BASE, 'main_comparison': MAIN,
    'commits': commits, 'status': status, 'diff_check': review,
    'diff_stat': git('diff', '--stat', BASE, 'HEAD').decode(),
    'observer': {'path': OBSERVER, 'before_sha256': sha(old), 'after_sha256': sha(new)},
    'protected': protected, 'searches': searches, 'cohorts': cohorts,
    'derived_pin_impact': {
        'package_sources': {'before_sha256': sha(canon(old_pins)), 'after_sha256': sha(canon(pins))},
        'production_sources': {'before_sha256': sha(canon(production(old_pins, True))),
                               'after_sha256': sha(canon(production(pins, False)))},
        'scope': 'Static reproduction of package-source mapping and production-source list, holding worktree paths fixed. No authority is prepared or armed.'},
    'report_script': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())}}
audit = save('h2-audit.json', data)
lines = [
'# Helper 2 handoff: observer alias and test repairs', '',
'Implemented and locally committed Parts A, B and C. The observer now checks the declared returned label on assistant frames and the requested label on user/result frames, while keeping requested-model initialization. The focused capture assertions and new offline guard CLI test pass. Public completion is still unverified: the unchanged protected candidate fails during RunSpec construction before any assistant/tool-use frame, so this run cannot establish progress beyond G07-F6 in the full public lifetime.', '',
'No push, GitHub write, provider/model/native-binary invocation, cpu-monitoring diagnostic, private-composition arming, or pin update was performed. Existing capture component tests execute their scripted Python peer; the new CLI test permits only Git subprocesses. The primary checkout and helper 1 worktree were not edited.', '',
'## Local commits', '',
*['- ' + item for item in commits], '',
'Branch: `codex/native-observer-alias-20261112`. Worktree: `' + str(ROOT) + '`. Working tree is clean; the complete commit diff reports one cosmetic finding: `scripts/adhoc/run_native_h2_tests_20261112.py:419: new blank line at EOF`. Changes received a separate read-only diff review; the copied runner retains a trailing blank line, recorded here as H2-F1 and left for the lead to avoid rewriting the required three commits. No remote issue was filed because this assignment prohibits GitHub writes.', '',
'## Changes and source reading', '',
'Part A: `native_model_aliases.model_aliases` defines the closed requested/returned pair. `require_frame_models` requires the returned label on current assistant frames, rejects contradictory labels in either the frame or nested message, and retains optional labels for historical identical aliases. Trace now derives this pair once and applies that helper to its existing assistant/user/result frame set. `_initialization_from_rows` still requires `runtime.model`. Terminal modelUsage remains checked by the existing final gate; this partial-prefix observer does not replace it.', '',
'The other current frame checks already use this division: `native_shared_permissions._native_scope`, `native_gate_engine` terminal checking, `native_u4b_runtime._saved_probe`, and `native_u4b_probe_sequence` saved stream validation. Init and terminal modelUsage use the requested label; assistant frames and the local-provider request use the returned label. No peer or alias-helper behavior was changed.', '',
'Added observer coverage for returned labels at frame/message/both locations, wrong/null/opposite labels for assistant/user/result, missing current assistant labels, reversed initialization, and historical optional/equal labels.', '',
'Part B: a direct read calls full verified reconstruction followed by outer-claims without the recheck marker. The event lookup still asserts its original four-step trace. A changed review document fails in `_capture_manifest_root` through `validate_bundle` and `_review_document` before `_recheck_verified`, with exact text `review document differs from its pinned bytes` and trace `verified, mutated`. All other mutations retain the recheck assertion. The initial test edit used an incorrect expected error literal; its saved failing run is retained and the literal was corrected to the production message.', '',
'Part C: `test_native_generation_guard_v2.py` invokes the actual command body with fabricated retained capture evidence. It checks the supplied manifest and require_latest flag, genuine guard construction, output bytes and reported SHA-256, exclusive publication on repeat, and refusal of that older capture after a second durable unfinished claim without creating another output. Registration reconstruction and render metadata validation are explicit routing stubs; runtime, review/word validation, capture reconstruction, latest-claim enforcement and publication remain real. This is not full registration or account acceptance.', '',
'## Saved test results', '',
'All rows are extracted from saved JUnit files. Counts overlap across reruns and must not be summed as unique coverage. The initial one-test runner canary passed, with nonempty log/JUnit, source-origin witnesses, OS network-denial witness and verified cleanup; it did not prove public integration.', '',
'| Cohort | Passed | Failures | Errors | Skipped |', '| --- | ---: | ---: | ---: | ---: |']
for row in cohorts:
    counts = row['counts']
    lines.append('| ' + row['name'] + ' | ' + ' | '.join(str(counts.get(k, 0)) for k in ('passed', 'failure', 'error', 'skipped')) + ' |')
lines.extend(['', 'Evidence root: `' + str(SCRATCH / 'tests') + '`. Each cohort has command, JUnit, log, network, import-origin and outcome files. Full individual test identities and artifact hashes are in `' + str(audit) + '`.', '',
'## Public completion stopping point', '',
'The single requested completion test fails in `make_case` during `build_native_fixture` preparation, at `native_execution_registration_v2.py:254`: `RunSpec.__init__() got an unexpected keyword argument native_shared_generation_version`. No assistant frame, worker stage or saved completion is reached. The public-paths cohort uses the same three test modules as helper 1, serially with no xdist workers. Its failures are retained, not repaired.', '',
'Helper 1 ran public-paths on `scratch-native-main-integration-20261112/g07-c/tree`, as its saved bootstrap.json shows. This assignment starts from the protected candidate itself and prohibits private-composition arming. Therefore its earlier 60-pass/1-failure result is not an apples-to-apples baseline. The two alias integration setup errors also cite the protected RunSpec mismatch. The lead must rerun this observer commit in the separately authorized composition to establish full public completion. No later failure beyond the assistant frame has been observed or chased here.', '',
'## Pin and closure impact', '',
'Observer SHA-256 before: `' + sha(old) + '`. After: `' + sha(new) + '`.', '',
'The ignore-independent hidden-file-inclusive searches cover this entire new worktree, excluding only the Git pointer. No literal occurrence of the old observer SHA-256 was found. All observer-name references were retained in scratch. The controller source manifest does not pin this package module; scanner fixed-source dictionaries do not directly pin it. The existing stale scanner authority pin is unchanged and was not repaired or revalidated.', '',
'The following derived bindings move and require fresh lead-controlled evidence; none was updated:', '',
'- `dependencies.base.package_sources[src/data_sheets_schema/native_shared_observations.py]` changes to the new observer digest, and the containing dependency identity/hash and source_commit change.',
'- `permission_expectation.production_sources` includes every nonempty package Python source, so the observer row SHA-256/byte length, aggregate production SHA-256, expectation and dependent saved-probe/registration bindings change.',
'- Verified consumer graphs that reach Trace acquire its direct alias-helper import and observe changed observer bytes; their graph identities must be recomputed. The helper was already present in the full package roster. No fixed pure-graph pin was rewritten.',
'- Registrations, review/word/guard documents and saved execution evidence bound transitively to the previous source/dependency identity cannot be reused as current authority.', '',
'The audit JSON records static before/after package-source and production-source aggregate hashes with this worktree path held fixed. Those are audit calculations, not new authority or approval. Protected files remain byte-identical to both the assigned candidate and integrated main `' + MAIN + '`; all file hashes are in the audit.', '',
'## Handoff artifacts and limits', '',
'Audit: `' + str(audit) + '`, SHA-256 `' + sha(audit.read_bytes()) + '`.', '',
'Report helper left in the report worktree, uncommitted for the lead: `' + str(Path(__file__).resolve()) + '`, SHA-256 `' + sha(Path(__file__).read_bytes()) + '`. Repair/runner scripts are committed with Parts A and B under the assigned worktree scripts/adhoc directory.', '',
'No full suite, scanner clearance, real capture, real runtime, CI, native canary or full public completion is claimed. Work stops here for the lead to integrate and review the local commits; no pins or protected files should be silently refreshed.'])
body = '\n'.join(lines) + '\n'
assert chr(64) not in body
handoff = REPORT / 'notes/development_efficiency_20261111/handoffs/codex-h2-observer-alias-20261112.md'
handoff.write_text(body)
assert handoff.stat().st_size > 0
print(json.dumps({'handoff': str(handoff), 'sha256': sha(handoff.read_bytes()),
    'audit': str(audit), 'audit_sha256': sha(audit.read_bytes()),
    'test_counts': {r['name']: r['counts'] for r in cohorts}}, indent=2))
