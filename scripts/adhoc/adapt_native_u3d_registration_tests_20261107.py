#!/usr/bin/env python3
"""Adapt recovered U3-D tests to genuine U3-A/C v2 inputs, 2026-11-07.

Inputs: recovered permission/registration tests in this assigned worktree.
Outputs: those test files only; no tests, native programs or network are run.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / 'tests/test_native_shared_permissions.py'
s = p.read_text()
s = s.replace('from data_sheets_schema import native_attribution_controller as composition',
    'from data_sheets_schema import native_attribution_controller_v2 as composition\n'
    'from data_sheets_schema import native_execution_authority_v2 as authority\n'
    'from data_sheets_schema import native_execution_registration_v2 as execution_v2\n'
    'from data_sheets_schema import native_shared_controller as shared_controller\n'
    'from data_sheets_schema import native_shared_registration as shared_registration')
s = s.replace('from data_sheets_schema import native_attribution_registration as draft\n', '')
s = s.replace('from tests.test_native_attempt_supervisor import make_case\n', '')
s = s.replace('from tests.test_native_shared_contract import selection as selection_fixture',
    'from tests.test_native_execution_registration_v2 import inputs, isolated_modules\n'
    'from tests.test_native_shared_render import native_spec\n'
    'from tests.test_native_shared_selection import declaration')
s = s.replace("    native = composition.load_controls()['native_control']", "    with authority.loaded_dependencies(authority.dependency_identity()) as controls:\n"
    "        return _fabricated_manifest(expected, selected, neutral_root, source_raw, controls)\n\n\n"
    "def _fabricated_manifest(expected, selected, neutral_root, source_raw, controls):\n"
    "    native = controls['native_control']")
s = s.replace('case, composition.load_controls())', 'case, controls)')
start = s.index("@pytest.fixture(scope='module')\ndef fixture(")
end = s.index('\n\n@pytest.fixture(autouse=True)', start)
s = s[:start] + '''@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    """Build genuine S/R/preparation/C once; only the saved observations are synthetic."""
    root = tmp_path_factory.mktemp('fabricated-shared-permission').resolve()
    isolation = isolated_modules.__wrapped__()
    names = next(isolation)
    try:
        with pytest.MonkeyPatch.context() as patch:
            from data_sheets_schema import api_runner as api
            patch.setattr(api, 'CONCAT_DIR', root / 'outputs')
            doc = declaration.__wrapped__(root, patch)
            spec = native_spec.__wrapped__(doc, root, patch)
            source = inputs.__wrapped__(spec, names, root, patch)
            runtime = c.strict_json(source['runtime_path'].read_bytes())
            runtime['budget_guard_usd'] = '01.50'
            source['runtime_path'].write_bytes(c.canonical(runtime))
            prepared = execution_v2.prepare(source['selection'], source['runtime_path'], **source['kwargs'])
            instruction = root / 'instruction.md'
            instruction.write_bytes(prepared['registration']['instruction'].encode())
            composed = shared_controller.compose(c.canonical(prepared), instruction_path=instruction)
            _, replay, capture = shared_controller.reconstruct_composition(c.canonical(composed))
            selected = capture.document()
            expected = shared_registration.permission_expectation(runtime, composed, replay,
                'Synthetic saved observations only.' + command_policy.command_guidance(composed['policy']),
                root / 'future-config', authority.dependency_identity())
            source_raw = capture.raw(selected['inputs']['bundle']['path'])
            value = fabricated_manifest(expected, selected, root / 'isolated-probes', source_raw)
            yield {'root': root, 'expected': expected, 'selection': selected,
                'manifest': value, 'source_raw': source_raw}
    finally:
        isolation.close()
''' + s[end:]
s = s.replace("    monkeypatch.setattr(subprocess, 'Popen', forbidden)",
    "    def git_only(argv, *args, **kwargs):\n"
    "        if not isinstance(argv, (list, tuple)) or Path(argv[0]).name != 'git' or kwargs.get('shell'):\n"
    "            return forbidden()\n"
    "        return _REAL_POPEN(argv, *args, **kwargs)\n"
    "    monkeypatch.setattr(subprocess, 'Popen', git_only)")
s = s.replace("('auxiliary_models',['synthetic-model'])", "('auxiliary_models',['synthetic-native-model'])")
p.write_text(s)

p = ROOT / 'tests/test_native_shared_registration.py'
s = p.read_text().replace('from data_sheets_schema import native_execution_authority as authority',
    'from data_sheets_schema import native_execution_authority_v2 as authority\n'
    'from data_sheets_schema import native_execution_registration_v2 as execution_v2\n'
    'from tests.test_native_execution_registration_v2 import inputs, isolated_modules')
s = s.replace('    spec, runtime, instruction = bound', '    source, prepared, preparation_raw, instruction = bound\n'
    "    runtime = source['runtime_path']")
s = s.replace("argv[0] == 'git'", "Path(argv[0]).name == 'git'")
s = s.replace('selected = composition.compose(spec, runtime_path=runtime, instruction_path=instruction, max_draft_checks=3)',
    'selected = composition.compose(preparation_raw, instruction_path=instruction)\n'
    '    _, spec, cap = composition.reconstruct_composition(c.canonical(selected))')
s = s.replace('    cap = spec._native_shared_generation_capture\n', '')
s = s.replace("'max_draft_checks': 3", "'max_draft_checks': prepared['registration']['max_draft_checks']")
s = s.replace('    assert registration.verified(raw) == value',
    "    body = value['registration']\n"
    "    assert value['authority_version'] == 2\n"
    "    assert registration.verified_v2_body(c.canonical(body),\n"
    "        preparation_raw=body['preparation_raw_json'].encode()) == body\n"
    "    assert registration.verified(raw) == body\n"
    "    value = body")
s = s.replace("value['kind'] == c.KINDS['execution']", "value['kind'] == execution_v2.EXECUTION_KIND")
s = s.replace("selected['max_draft_checks'] == 3", "selected['max_draft_checks'] == 2")
p.write_text(s)
