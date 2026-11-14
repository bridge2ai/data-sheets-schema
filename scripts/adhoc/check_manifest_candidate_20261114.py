"""Focused candidate integration evidence and handoff, 2026-11-14.

Inputs: accepted manifest merge and candidate 087a8d954, explicit unit cohorts.
Outputs: immutable scanner exports, focused results, identity ledger and the
assigned continuation handoff. No live matrices, scanner edits or publication.
Serves the lead's claude-lead-codex196-manifest-integrate-20261114 assignment.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BEFORE = 'b91ecef876170603653ad300d0e6566ae2995f16'
CANDIDATE = '087a8d954c20c1640f99683179047aaa32139e3d'
MERGE = '3f19ff532355fdc72a99ff5b3256d231568605f3'
SCRATCH = ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation'
OUT = SCRATCH / 'candidate-integration'
SKILL = '.claude/skills/d4d-generation-specificity-audit'
HANDOFF = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-native-manifest-integration-20261114.md'
PROTECTED = ('src/data_sheets_schema/shared_generation.py',
             'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml',
             'tests/utils/run_spec_boundary_contracts.json')
CI_ONLY = {
    'tests/test_native_environment_cost.py': 'live installed manifest write and cost measurement',
    'tests/test_native_environment_dependencies.py': 'real installed dependency censuses',
    'tests/test_native_environment_dispatch.py': 'full registration fixture and live dispatch boundary',
    'tests/test_native_execution_registration_v2.py': 'remaining tests using inputs, prepared or execution fixtures',
    'tests/test_native_shared_registration.py': 'full execution registration fixture',
    'tests/test_native_canary_packet_builder.py::test_real_chorus_prefix': 'real builder prefix and installed manifest',
    'tests/test_native_canary_packet_rehearsal.py::test_synthetic_preparation_roundtrips_without_production_authority': 'real builder and installed manifest roundtrip',
    'tests/test_native_packet_full_chain.py': 'full packet chain',
    'tests/test_native_all_project_prefix.py': 'all project prefix matrix',
}


def git(*args, check=True):
    return subprocess.run(['git', '--no-replace-objects', *args], cwd=ROOT,
                          capture_output=True, check=check)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def load(path):
    return json.loads(path.read_bytes())


def head():
    return git('rev-parse', 'HEAD').stdout.decode().strip()


def frozen():
    assert not git('status', '--porcelain').stdout, 'source must be committed and clean'
    assert git('merge-base', '--is-ancestor', MERGE, 'HEAD', check=False).returncode == 0
    return head()


def nodes(path, exclude=()):
    tree = ast.parse((ROOT / path).read_bytes())
    return [path + '::' + item.name for item in tree.body
            if isinstance(item, ast.FunctionDef) and item.name.startswith('test_')
            and item.name not in exclude]


def cohorts():
    return {
        'canary': ['tests/test_native_environment_manifest.py::test_generate_has_sorted_semantic_inventory'],
        'manifest': ['tests/test_native_environment_manifest.py'],
        'boundaries': ['tests/test_native_environment_modes.py', 'tests/test_native_shared_capture_split.py'],
        'registration': ['tests/test_native_environment_registration.py'] + [
            'tests/test_native_execution_registration_v2.py::' + name for name in (
                'test_bad_authority_envelope_refuses_before_input_capture',
                'test_duplicate_json_refuses_before_dependency_loading',
                'test_approval_parser_captures_exact_fabricated_bytes_without_writes',
                'test_approval_parser_refuses_each_fabricated_authority_mismatch')],
        'builder': nodes('tests/test_native_canary_packet_builder.py', ('test_real_chorus_prefix',))
            + nodes('tests/test_native_canary_packet_rehearsal.py', ('test_synthetic_preparation_roundtrips_without_production_authority',))
            + ['tests/test_native_probe_drafts.py'],
        'scanner': ['tests/' + name + '.py' for name in (
            'test_native_environment_scanner_modes', 'test_native_u1_scanner_contracts',
            'test_native_u3l_scanner', 'test_native_u5_scanner',
            'test_native_u5_scanner_comparison', 'test_native_d128_scanner_comparison',
            'test_native_h1_scanner_authority', 'test_native_u4b_a5_scanner',
            'test_native_generation_guard_v2', 'test_native_generation_frontdoor',
            'test_native_u3d_guard_contract', 'test_native_u4b_a3_frontdoor',
            'test_generation_specificity_skill', 'test_generation_specificity_delegated')],
    }


def cohort_out(name):
    # The existing isolated runner admits only direct children of SCRATCH.
    return SCRATCH / ('candidate-integration-' + name)


def cohort(name):
    commit = frozen()
    if name != 'canary':
        proof = load(cohort_out('canary') / 'outcome.json')
        assert proof['returncode'] == 0 and proof['cleanup_verified']
        assert (cohort_out('canary') / 'pytest.xml').stat().st_size > 0
    command = [str(SCRATCH / 'declared-dependencies/bin/python'), '-S', '-P', '-B',
               str(ROOT / 'scripts/adhoc/run_manifest_continuation_tests_20261114.py'),
               '--tree', str(ROOT), '--out', str(cohort_out(name)), '--workers', '1',
               '--timeout-seconds', '1200', *cohorts()[name]]
    save(OUT / (name + '-launch.json'), {'command': command, 'head': commit})
    result = subprocess.run(command, cwd=ROOT)
    assert frozen() == commit, 'source changed during cohort'
    return result.returncode


def pins(raw):
    """Read literal pin entries without importing or executing the scanner."""
    result = {}
    for node in ast.parse(raw).body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        for key, value in zip(node.value.keys, node.value.values):
            if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                    and isinstance(value, ast.Constant) and isinstance(value.value, str)
                    and len(value.value) == 64):
                for name in names:
                    result[name + ':' + key.value] = value.value
    return result


def audit():
    commit = frozen()
    snapshots = {}
    for label, revision in (('accepted', BEFORE), ('candidate', CANDIDATE), ('merged', commit)):
        raw = git('show', revision + ':' + SKILL + '/scan.py').stdout
        snapshots[label] = {'commit': revision, 'scanner_sha256': sha(raw), 'pins': pins(raw)}
    changes = []
    for key, value in snapshots['merged']['pins'].items():
        a = snapshots['accepted']['pins'].get(key)
        b = snapshots['candidate']['pins'].get(key)
        if a != value or b != value:
            relative = key.split(':', 1)[1]
            path = ROOT / relative
            changes.append({'entry': key, 'accepted': a, 'candidate': b,
                            'merged': value, 'actual': sha(path.read_bytes()) if path.is_file() else None})
    identities = []
    for relative in (*PROTECTED, 'src/data_sheets_schema/native_environment_manifest.py',
                     'src/data_sheets_schema/native_execution_authority_v2.py',
                     'src/data_sheets_schema/native_shared_authority_wire.py',
                     'src/data_sheets_schema/native_shared_capture_orchestration.py',
                     'src/data_sheets_schema/native_controller_sources.json',
                     'src/data_sheets_schema/native_controller_sources_v2.json',
                     'tests/fixtures/native_d128_approved.json'):
        values = {label: sha(git('show', revision + ':' + relative).stdout)
                  for label, revision in (('accepted', BEFORE), ('candidate', CANDIDATE), ('merged', commit))}
        identities.append({'path': relative, **values})
        if relative in PROTECTED or relative.endswith('native_d128_approved.json') or 'native_controller_sources' in relative:
            assert len(set(values.values())) == 1, relative
    for parent in (BEFORE, CANDIDATE):
        (OUT / ('scanner-diff-' + parent[:9] + '.patch')).write_bytes(
            git('diff', parent, commit, '--', SKILL + '/scan.py').stdout)
    check = git('diff', '--check', CANDIDATE, commit, check=False)
    assert check.returncode == 0, check.stdout
    inherited = git('diff', '--check', BEFORE, CANDIDATE, check=False)
    save(OUT / 'audit.json', {'head': commit, 'merge': MERGE,
         'merge_parents': git('show', '-s', '--format=%P', MERGE).stdout.decode().strip().split(),
         'snapshots': snapshots, 'pin_changes': changes, 'identities': identities,
         'cohorts': cohorts(), 'ci_only': CI_ONLY,
         'candidate_relative_whitespace_check': check.returncode,
         'inherited_candidate_whitespace': inherited.stdout.decode()})
    print(json.dumps({'head': commit, 'pin_changes': changes, 'identities': identities}, indent=2))


def compare():
    commit = frozen()
    sys.path.insert(0, str(ROOT))
    from scripts.adhoc import native_u5_inputs_20261108 as inputs
    from tests.test_native_d128_scanner_comparison import scan
    from tests.test_native_u5_scanner_comparison import require_scanner_inventory
    from scripts.adhoc.run_manifest_continuation_tests_20261114 import network_witness
    save(OUT / 'scanner-network.json', network_witness())
    exports = OUT / 'exports'
    exports.mkdir()
    inputs.SCRATCH = exports
    selected = {}
    for name, revision in (('candidate', CANDIDATE), ('merged', commit)):
        label = 'scanner-candidate-' + revision[:9]
        inputs.materialize(label, revision, inputs.BASE_SCAN_PATHS)
        tree, manifest = inputs.checked_scanner_input(label, revision)
        require_scanner_inventory(manifest)
        selected[name] = (tree, manifest, label)
    tool = selected['merged'][0] / SKILL / 'scan.py'
    assets = {name: sha((tool.parent / name).read_bytes()) for name in ('scan.py', 'tokens.yaml', 'exceptions.yaml')}
    runs = {}
    for name, (source, manifest, label) in selected.items():
        run = scan(source, manifest, tool, assets, OUT / ('scan-' + name))
        runs[name] = {key: value for key, value in run.items() if key != 'arrays'}
        runs[name]['array_counts'] = None if run['arrays'] is None else {
            key: len(value) for key, value in run['arrays'].items()}
        inputs.checked_scanner_input(label, manifest['commit'])
        print(json.dumps({'scan': name, **runs[name]}), flush=True)
    assert frozen() == commit
    assert assets == {name: sha((tool.parent / name).read_bytes()) for name in assets}
    save(OUT / 'comparison.json', {'head': commit, 'candidate': CANDIDATE,
         'same_tool_assets': assets, 'runs': runs,
         'complete': all(run['derivation_complete'] for run in runs.values()),
         'scope': 'same committed scanner and configuration over both immutable committed source exports; held pins unchanged'})


def report():
    commit = frozen()
    audit_data, comparison = load(OUT / 'audit.json'), load(OUT / 'comparison.json')
    assert audit_data['head'] == comparison['head'] == commit
    results = []
    for name in cohorts():
        outcome = load(cohort_out(name) / 'outcome.json')
        plan = load(cohort_out(name) / 'plan.json')
        assert plan['source_commit'] == commit
        suites = ET.parse(cohort_out(name) / 'pytest.xml').getroot()
        cases = list(suites.iter('testcase'))
        failures = [{'node': case.get('classname') + '.' + case.get('name'),
                     'message': element.get('message'), 'detail': element.text}
                    for case in cases for element in case if element.tag in ('failure', 'error')]
        skipped = sum(case.find('skipped') is not None for case in cases)
        results.append({'name': name, 'tests': len(cases), 'passed': len(cases) - len(failures) - skipped,
                        'failed': len(failures), 'skipped': skipped, 'failures': failures,
                        'returncode': outcome['returncode'], 'seconds': outcome['seconds'],
                        'cleanup_verified': outcome['cleanup_verified'], 'output': str(cohort_out(name))})
    save(OUT / 'results.json', results)
    resolutions = load(OUT / 'resolutions.json')
    source = 'src/data_sheets_schema/native_environment_manifest.py'
    old = audit_data['snapshots']['merged']['pins']['_NATIVE_V3_RENDER_SOURCES:' + source]
    new = next(row['merged'] for row in audit_data['identities'] if row['path'] == source)
    lines = ['# Candidate integration continuation — 2026-11-14', '',
        f"**Answer: merged candidate `{CANDIDATE}` into the manifest branch at `{MERGE}`; final tested head `{commit}`.**",
        'Focused cohorts only, one worker. The existing-check interpretation is confirmed. No long live-boundary or full-registration matrix ran for this integration.', '',
        f"**Pending manifest scanner identity proposal:** `{old}` → `{new}`. This binds the accepted full/light implementation and remains unapplied. Neither scanner source nor controller pins were changed to make a check pass.", '',
        '| Focused cohort | Passed | Failed | Skipped | Exit | Seconds | Cleanup verified |',
        '|---|---:|---:|---:|---:|---:|---|']
    for row in results:
        lines.append(f"| {row['name']} | {row['passed']} | {row['failed']} | {row['skipped']} | {row['returncode']} | {row['seconds']:.3f} | {row['cleanup_verified']} |")
    lines += ['', 'The first canary invocation was refused before test startup because the existing runner requires outputs to be direct children of the assigned scratch root. The helper was corrected and committed before the real canary and every subsequent cohort. The refused invocation is retained in canary-invocation.json.', '',
              'The canary used the same launcher, isolated dependency environment, network/native denial, output hierarchy and one-worker mode as the later cohorts. Its nonempty JUnit and verified cleanup were checked before subsequent cohorts. It proves that path and persistence for one synthetic unit; it does not prove live census timing or full registration.', '',
              '## Merge resolution and preserved boundaries', '']
    for row in resolutions:
        lines.append(f"- `{row['path']}`: {row['conflict_hunks']} conflict hunks. {row['resolution']}")
    lines += ['- Scanner merged without conflicts. Candidate runtime pin rotations and the previously reviewed v3 templates and authority identity are retained; no overlapping pin needed recomputation.',
              '- All four protected files, both controller source manifests and the D128 approval fixture are byte-identical across both parents and the tested head.',
              '- The diff against the candidate passes the whitespace check. Existing candidate whitespace findings are saved in the audit and were not edited.', '',
              '## Scanner identity ledger', '',
              'This table covers every literal scanner pin entry differing from either parent. New means absent in that parent. These are retained merge identities, except the pending manifest proposal above.', '',
              '| Entry | Accepted parent | Candidate parent | Retained merged pin | Actual merged file |',
              '|---|---|---|---|---|']
    for row in audit_data['pin_changes']:
        lines.append('| ' + ' | '.join('`' + str(row[key] or 'new') + '`' for key in ('entry', 'accepted', 'candidate', 'merged', 'actual')) + ' |')
    lines += ['', 'Reasons: runtime values retain the required Bash timeout keys and validator; runtime profiles retain the synthetic peer identity and 2700-second synthetic deadline. Execution authority retains the accepted import-path restoration before fresh census. The v3 wire and manifest entries retain the reviewed structural contract; the manifest implementation now needs the pending identity above. The H1 authority reference and exact v3 mode-forwarding templates are preserved in the saved candidate-relative scanner diff.', '',
              'Scanner tool identity also differs from historical D128 approval. These identities are evidence for review, not authority to rewrite the finite D128 fixture.', '',
              '| Scanner source | SHA-256 |', '|---|---|']
    for name, snapshot in audit_data['snapshots'].items():
        lines.append(f"| {name} | `{snapshot['scanner_sha256']}` |")
    lines += ['', '## D128 effect against the current candidate', '',
              'The exact same committed merged scanner and configuration ran against immutable committed exports of the candidate and tested head. Full inventory manifests and post-scan byte checks are saved. No proposed pin was substituted for this comparison.', '']
    for name, row in comparison['runs'].items():
        lines += [f"- {name}: exit {row['returncode']}; derivation complete `{row['derivation_complete']}`; array counts `{row['array_counts']}`.",
                  '```text', row['stderr'].strip(), '```']
    lines += ['', 'An incomplete derivation has no finding arrays; it is not zero findings or D128 acceptance. The held manifest pin blocks the merged v3 route, and the candidate authority uses its prior identity. The current exact historical D128 asset gate therefore remains a hold. A complete finite finding comparison requires the lead to decide the proposed manifest identity and the historical-versus-current scanner authority closure; no approval fixture was updated here.', '',
              '## Focused failures', '']
    for row in results:
        for failure in row['failures']:
            lines.append('- `' + failure['node'] + '`: ' + str(failure['message']).replace('\n', ' ')[:1200])
    lines += ['', 'Complete failure details, including refusals under held pins, are in results.json and each cohort JUnit/log. The proposed-identity scanner controls remain isolated unit tests; they do not rotate the committed scanner pin.', '',
              '## CI-only evidence still required', '']
    for path, reason in CI_ONLY.items():
        assert (ROOT / path.split('::')[0]).exists(), path
        lines.append(f'- `{path}` — {reason}.')
    lines += ['- The prefix fix stage-module restructuring is owned elsewhere; full live callback, recording, dispatch, acceptance and gate integration must be judged in CI after integration. No new wrapper was added to helpers that previously had no manifest check.', '',
              '## Reproducible evidence', '',
              f'- Evidence root: `{OUT}`.',
              f'- Merge/conflict provenance: `{OUT / "merge-start.json"}` and `{OUT / "resolutions.json"}`.',
              f'- Identity ledger: `{OUT / "audit.json"}`; focused results: `{OUT / "results.json"}`; same-tool comparison: `{OUT / "comparison.json"}`.',
              f'- Source helpers: `{ROOT / "scripts/adhoc/integrate_manifest_candidate_20261114.py"}` and `{Path(__file__).resolve()}`.',
              '- Reproduction: invoke the check helper with `cohort canary`, then `cohort manifest`, `cohort boundaries`, `cohort registration`, `cohort builder`, `cohort scanner`, using the declared-dependencies Python with `-S -P -B`. Run `audit`, and run `compare` with the canary venv Python under its saved network-denied sandbox. Run `report` last. All outputs are exclusive-create and require a fresh assigned evidence directory for replay.',
              '- Tables above are generated from saved JSON/JUnit by this committed report helper. No GitHub write, push, provider or native binary call occurred. Findings are handed to the lead for issue filing and publication.', '',
              '---', '', 'Earlier accepted continuation follows unchanged.', '']
    text = '\n'.join(lines)
    assert chr(64) not in text
    original = HANDOFF.read_bytes()
    (OUT / 'handoff-before.md').write_bytes(original)
    HANDOFF.write_bytes(text.encode() + original)
    raw = HANDOFF.read_bytes()
    assert raw.endswith(original) and raw.startswith(text.encode())
    save(OUT / 'handoff-identity.json', {'path': str(HANDOFF), 'sha256': sha(raw),
         'bytes': len(raw), 'previous_sha256': sha(original), 'head': commit})
    print(json.dumps(load(OUT / 'handoff-identity.json'), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('cohort', 'audit', 'compare', 'report'))
    parser.add_argument('name', nargs='?', choices=tuple(cohorts()))
    args = parser.parse_args()
    if args.action == 'cohort':
        assert args.name
        return cohort(args.name)
    assert args.name is None
    {'audit': audit, 'compare': compare, 'report': report}[args.action]()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
