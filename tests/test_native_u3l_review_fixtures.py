"""Retained U3-F review outcomes under the U3-L scanner, 2026-11-09 (#4354).

Each case scans a fresh committed composition export. The frozen mutations and
outcomes come from scratch-u3f-review; neither that runner nor generation code
is imported. F3d and B2 have separately versioned current expectations; their
historical N1 and #5657 gaps remain in the frozen fixture.
"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import time

import pytest

from scripts.adhoc import native_u5_inputs_20261108 as inputs
from tests.test_native_d128_scanner_comparison import approval, encoded
from tests.test_native_u5_scanner_comparison import require_scanner_inventory


FIXTURE = Path(__file__).with_name('fixtures') / 'native_u3l_review_cases.json'
FIXTURE_SHA256 = '2f2ef674466c3c86e84ded2f52dd61f30ec9b298e718f85c247ce7213713c552'
SOURCE_SHA256 = 'bb16457c501ceb9638ab344bccb548a9e721ca61924c5cc327b439ab83aabf40'
SKILL = '.claude/skills/d4d-generation-specificity-audit'
CASE_NAMES = (
    'F0', 'F1_event_parser_token', 'F2a_envelope_control_token',
    'F2b_v2_envelope_token', 'F2c_v2_envelope_branch', 'F3a_stage_branch',
    'F3a2_stage_branch_no_options', 'F3b_stage_options_subscript',
    'F3c_stage_main_branch', 'F3d_module_helper_print', 'B1_typed_alias_restored',
    'B2_typed_container_alias_token', 'B3_typed_container_direct_token',
)
REFUSALS = {
    'F1_event_parser_token': 'native event parser transport source changed',
    'F2a_envelope_control_token':
        'v2 envelope authority source changed: notes/matched_cborg_2026-09-13/prepare_registration_v2.py',
    'F2b_v2_envelope_token': 'unsupported v2 render producer: _envelope',
    'F2c_v2_envelope_branch': 'unsupported v2 render producer: _envelope',
    'F3a_stage_branch': 'native packet options are replaced, mutated or aliased',
    'F3b_stage_options_subscript': 'native packet options are replaced, mutated or aliased',
    'B1_typed_alias_restored': 'unsupported effect on model-text local container (nested or copied receiver alias)',
}
ALL_GATES = ['api', 'deterministic', 'github_assistant', 'native_agentic']
PRINT = "print('Note: this is the CHORUS dataset; prefer CHORUS naming.')"
HINT = "return 'Treat this record as the CHORUS cohort.' if project else ''"
PLANTED = {
    'F3a2_stage_branch_no_options': (
        'src/data_sheets_schema/native_shared_stage/__init__.py',
        [('code_branch', "if getattr(selection, 'project', None) == 'CHORUS':")], ALL_GATES),
    'F3c_stage_main_branch': (
        'src/data_sheets_schema/native_shared_stage/__main__.py',
        [('code_branch', "if 'CHORUS' in args.registration:"),
         ('string_literal', PRINT), ('string_literal', PRINT)], ['native_agentic']),
    'F3d_module_helper_print': (
        'src/data_sheets_schema/source_attribution_preflight.py',
        [('string_literal', PRINT), ('string_literal', PRINT)], []),
    'B2_typed_container_alias_token': (
        'src/data_sheets_schema/project_hints.py', [('string_literal', HINT)], []),
    'B3_typed_container_direct_token': (
        'src/data_sheets_schema/project_hints.py', [('string_literal', HINT)], ALL_GATES),
}
KNOWN_GAPS = {'F3d_module_helper_print': 'N1', 'B2_typed_container_alias_token': '#5657'}

# These complete objects come from the saved H1 audit, not the scan under test.
# Keep the frozen fixture and D128 approval unchanged; current expectations
# preserve the historical gap while checking its subsequently reviewed repair.
F3D_CURRENT_VIOLATION = {
    'approaches': ['api', 'native_agentic', 'deterministic', 'github_assistant'],
    'category': 'gc_project',
    'code': False,
    'context': 'string_literal',
    'exception': None,
    'gates_in': ['native_agentic'],
    'line': 174,
    'match': 'CHORUS',
    'model_facing': True,
    'path': 'src/data_sheets_schema/source_attribution_preflight.py',
    'pattern': 'CHo?RUS',
    'role': 'model_facing',
    'snippet': PRINT,
    'status': 'live',
    'violation': True,
}
B2_CURRENT_VIOLATION = {
    'approaches': ['api', 'native_agentic', 'deterministic', 'github_assistant'],
    'category': 'gc_project',
    'code': False,
    'context': 'string_literal',
    'exception': None,
    'gates_in': ['api', 'deterministic', 'github_assistant', 'native_agentic'],
    'line': 5,
    'match': 'CHORUS',
    'model_facing': True,
    'model_text_function': 'project_hint() (its value reaches _derive_uncached())',
    'path': 'src/data_sheets_schema/project_hints.py',
    'pattern': 'CHo?RUS',
    'role': 'model_facing',
    'snippet': HINT,
    'status': 'live',
    'violation': True,
}
CURRENT_EXPECTATIONS = {
    'F3d_module_helper_print': {
        'version': 2,
        'historical_known_gap': 'N1',
        'historical_expected_exit': 1,
        'historical_expected_violations': 9,
        'expected_exit': 1,
        'expected_violations': 11,
        'extra_violations': [F3D_CURRENT_VIOLATION, F3D_CURRENT_VIOLATION],
        'evidence_name': 'codex-h1-retained-gap-finding-20261112.json',
        'evidence_sha256': 'a74ce1bbbf8df2855ef0608d0d9446ad9fd432848e599df4594d8b7a3bde5f7a',
    },
    'B2_typed_container_alias_token': {
        'version': 2,
        'historical_known_gap': '#5657',
        'historical_expected_exit': 1,
        'historical_expected_violations': 9,
        'expected_exit': 1,
        'expected_violations': 10,
        'extra_violations': [B2_CURRENT_VIOLATION],
        'evidence_name': 'codex-h1-retained-container-finding-20261112.json',
        'evidence_sha256': '3661f9ec60752c9a7aafe12d0683f8683c4be622b3eb075760a2125db950b28b',
    },
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _cases():
    raw = FIXTURE.read_bytes()
    assert _sha(raw) == FIXTURE_SHA256, 'retained review fixture changed'
    value = json.loads(raw)
    assert value['kind'] == 'native_u3l_retained_review_fixtures' and value['version'] == 1
    assert value['source_sha256'] == SOURCE_SHA256
    cases = value['cases']
    assert tuple(case['name'] for case in cases) == CASE_NAMES
    assert {case['name']: case['known_gap'] for case in cases if case['known_gap']} == KNOWN_GAPS
    return cases


def _apply_edits(tree, case, expected):
    mutations = []
    for relative, before, after in case['edits']:
        name = PurePosixPath(relative)
        assert not name.is_absolute() and '..' not in name.parts
        path = tree / relative
        after = after.encode('utf-8')
        if before is None:
            assert relative not in expected and not os.path.lexists(path)
            original = None
            changed = after
            with path.open('xb') as stream:
                stream.write(changed)
            path.chmod(0o644)
        else:
            assert relative in expected and path.is_file() and not path.is_symlink()
            original = path.read_bytes()
            before = before.encode('utf-8')
            assert before != after and original.count(before) == 1, relative
            changed = original.replace(before, after, 1)
            path.write_bytes(changed)
        assert path.read_bytes() == changed and changed, relative
        expected[relative] = dict(sha256=_sha(changed), bytes=len(changed),
                                  mode=stat.S_IMODE(path.stat().st_mode))
        mutations.append(dict(path=relative, before_sha256=None if original is None else _sha(original),
                              after_sha256=_sha(changed), bytes=len(changed)))
    return mutations


def _require_unchanged_tree(tree, expected):
    """Inspect ignored and hidden entries too; only exact fixture edits may differ."""
    actual = set()
    for parent, directories, files in os.walk(tree, followlinks=False):
        assert all(not (Path(parent) / name).is_symlink() for name in directories)
        for name in files:
            path = Path(parent) / name
            relative = path.relative_to(tree).as_posix()
            assert relative in expected and not path.is_symlink(), relative
            info = path.stat()
            assert stat.S_ISREG(info.st_mode), relative
            row = dict(sha256=_sha(path.read_bytes()), bytes=info.st_size,
                       mode=stat.S_IMODE(info.st_mode))
            assert row == expected[relative], relative
            actual.add(relative)
    assert actual == set(expected)


def _require_complete_outcome(tree, case, document, baseline_rows):
    for name in ('hits', 'violations', 'test_dependencies'):
        assert type(document[name]) is list and all(type(row) is dict for row in document[name])
    baseline = Counter(encoded(row) for row in baseline_rows)
    observed = Counter(encoded(row) for row in document['violations'])
    assert not baseline - observed, 'one or more complete D128 baseline violations changed or disappeared'
    current = CURRENT_EXPECTATIONS.get(case['name'])
    expected = current if current is not None else case
    assert len(document['violations']) == expected['expected_violations']
    extra = observed - baseline
    name = case['name']
    if name == 'F0':
        assert observed == baseline
        return []
    relative, contexts, gates = PLANTED[name]
    if current is not None:
        gates = current['extra_violations'][0]['gates_in']
    snippets = {snippet for _, snippet in contexts}
    planted = [hit for hit in document['hits'] if hit['path'] == relative
               and hit['match'] == 'CHORUS' and hit['snippet'] in snippets]
    assert Counter((hit['context'], hit['snippet']) for hit in planted) == Counter(contexts)
    lines = (tree / relative).read_text(encoding='utf-8').splitlines()
    for hit in planted:
        matching = [index + 1 for index, line in enumerate(lines) if line.strip() == hit['snippet']]
        assert matching == [hit['line']]
        assert hit['category'] == 'gc_project' and hit['gates_in'] == gates
    if current is not None:
        assert current['version'] == 2
        assert case['known_gap'] == current['historical_known_gap']
        assert case['expected_exit'] == current['historical_expected_exit']
        assert case['expected_violations'] == current['historical_expected_violations']
        expected_extra = current['extra_violations']
        assert [encoded(hit) for hit in planted] == [encoded(hit) for hit in expected_extra]
        assert extra == Counter(encoded(hit) for hit in expected_extra)
        assert [encoded(hit) for hit in document['violations']] == [
            encoded(hit) for hit in baseline_rows + expected_extra]
    elif name in KNOWN_GAPS:
        assert case['known_gap'] == KNOWN_GAPS[name]
        assert observed == baseline and not extra
        assert all(hit['role'] == 'run_shaping' and hit['model_facing'] is False
                   and hit['violation'] is False and hit['gates_in'] == [] for hit in planted)
    else:
        assert case['known_gap'] is None
        assert all(hit['role'] == 'model_facing' and hit['violation'] is True for hit in planted)
        assert extra == Counter(encoded(hit) for hit in planted)
    return planted


@pytest.mark.parametrize('case', _cases(), ids=lambda case: case['name'])
def test_retained_review_outcome(tmp_path, monkeypatch, case):
    baseline_rows = approval()['exact_violations']
    assert len(baseline_rows) == 9
    current = CURRENT_EXPECTATIONS.get(case['name'])
    expected_outcome = current if current is not None else case
    output = tmp_path / 'scanner'
    output.mkdir()
    evidence = dict(fixture=case['name'], fixture_sha256=FIXTURE_SHA256,
                    retained_source_sha256=SOURCE_SHA256,
                    expected_exit=expected_outcome['expected_exit'],
                    expected_violations=expected_outcome['expected_violations'],
                    historical_expected_exit=case['expected_exit'],
                    historical_expected_violations=case['expected_violations'],
                    historical_known_gap=case['known_gap'],
                    current_expectation=current,
                    known_gap=case['known_gap'], status='incomplete', derivation_complete=False,
                    finding_arrays_available=False, violation_count=None)
    try:
        head = inputs.git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
        exports = tmp_path / 'exports'
        exports.mkdir()
        monkeypatch.setattr(inputs, 'SCRATCH', exports)
        label = 'scanner-candidate-' + head[:9]
        inputs.materialize(label, head, inputs.BASE_SCAN_PATHS)
        tree, manifest = inputs.checked_scanner_input(label, head)
        require_scanner_inventory(manifest)
        expected = {name: dict(sha256=row['sha256'], bytes=row['bytes'], mode=int(row['mode'], 8) & 0o777)
                    for name, row in manifest['files'].items()}
        evidence.update(commit=head, commit_tree=manifest['commit_tree'],
                        input_path_mask=manifest['path_mask'], input_entry_count=manifest['entry_count'],
                        input_total_blob_bytes=manifest['total_blob_bytes'], root=str(tree),
                        mutations=_apply_edits(tree, case, expected))
        tool = tree / SKILL / 'scan.py'
        assets = {name: row['sha256'] for name, row in manifest['files'].items()
                  if name.startswith(SKILL + '/')}
        command = [sys.executable, '-P', '-B', str(tool), '--root', str(tree),
                   '--report', str(output / 'scan.md'), '--json', str(output / 'scan.json'),
                   '--tokens', str(tool.with_name('tokens.yaml')),
                   '--exceptions', str(tool.with_name('exceptions.yaml')), '--full-json']
        env = {key: os.environ[key] for key in ('PATH', 'HOME', 'TMPDIR', 'VIRTUAL_ENV') if key in os.environ}
        env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PIP_NO_INDEX='1', UV_OFFLINE='1')
        evidence.update(command=command, tool_assets_sha256=assets, timeout_seconds=600)
        started = time.monotonic()
        try:
            completed = subprocess.run(command, cwd=tree, env=env, capture_output=True, timeout=600)
        except subprocess.TimeoutExpired as error:
            (output / 'stdout.txt').write_bytes(error.stdout or b'')
            (output / 'stderr.txt').write_bytes(error.stderr or b'')
            evidence['timed_out'] = True
            raise
        finally:
            evidence['seconds'] = time.monotonic() - started
        (output / 'stdout.txt').write_bytes(completed.stdout)
        (output / 'stderr.txt').write_bytes(completed.stderr)
        evidence['returncode'] = completed.returncode
        _require_unchanged_tree(tree, expected)
        evidence['input_bytes_and_inventory_stable'] = True
        assert inputs.git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == head
        assert completed.returncode == expected_outcome['expected_exit'], completed.stderr.decode(errors='replace')
        if completed.returncode == 2:
            stderr = completed.stderr.decode('utf-8')
            assert 'configuration error (exit 2, the scan did not happen)' in stderr
            assert REFUSALS[case['name']] in stderr
            assert not (output / 'scan.json').exists()
            evidence['status'] = 'retained_configuration_refusal'
        else:
            report = output / 'scan.json'
            assert report.is_file() and report.stat().st_size > 0
            document = json.loads(report.read_bytes())
            evidence.update(derivation_complete=True, finding_arrays_available=True,
                            violation_count=len(document['violations']),
                            arrays_sha256={name: _sha(encoded(document[name]))
                                           for name in ('hits', 'violations', 'test_dependencies')})
            evidence['planted_hits'] = _require_complete_outcome(tree, case, document, baseline_rows)
            evidence['status'] = ('current_reviewed_expectation' if current is not None else
                                  'retained_known_gap' if case['known_gap'] else 'retained_complete_outcome')
    except Exception as error:
        evidence['failure'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        evidence['output_sha256'] = {path.name: _sha(path.read_bytes()) for path in output.iterdir()
                                    if path.is_file() and path.name != 'run.json'}
        (output / 'run.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
