"""U5 source-only v2 CLI/producer proofs, 2026-11-08; no generation imports.

Fixtures preserve the real route, then change one authority/dataflow edge.
They prove source derivation only, never the absent protected U1 installation.
"""
import pytest

from tests.test_generation_specificity_delegated import ROOT, RUNNER, scan
from tests.test_native_u1_scanner_contracts import _native_route_root

CLI = 'src/data_sheets_schema/cli/prompt.py'
PREPARER = 'src/data_sheets_schema/native_execution_registration_v2.py'
STAGE = 'src/data_sheets_schema/native_shared_stage/__init__.py'


def copied_route(tmp_path):
    # The complete source-bound U3-F2 authority closure is part of the proof.
    return _native_route_root(tmp_path)


@pytest.mark.parametrize('relative,before,after', [
    (CLI, '@prompt.command("render-native-shared")', '@wrap_consumer\n@prompt.command("render-native-shared")'),
    (CLI, 'native_execution_registration_v2 as preparation', 'foreign_preparer as preparation'),
    (CLI, 'preparation.prepare(selection, runtime_declaration, job_id=job_id,',
     'preparation.prepare(runtime_declaration, selection, job_id=job_id,'),
    (CLI, 'job_id=job_id,', 'job_id="other-job",'),
    (CLI, "run_date=run_date.strftime('%Y-%m-%d'),", 'run_date="2026-01-01",'),
    (CLI, 'max_draft_checks=max_draft_checks)', 'max_draft_checks=1)'),
    (CLI, "body = envelope['registration']", "body = envelope['other']"),
    (CLI, "text = body['instruction']", "text = 'replacement instruction'"),
    (CLI, "stream.write(text)", "stream.write('replacement instruction')"),
    (CLI, '        body = envelope', '        preparation.prepare = replacement\n        body = envelope'),
    (CLI, '    raw = text.encode', '    launch()\n    raw = text.encode'),
    (PREPARER, 'from . import native_shared_selection as selection', 'from . import foreign_selection as selection'),
    (PREPARER, 'captured = selection.capture(selection_path)', 'captured = selection.capture(runtime_path)'),
    (PREPARER, 'native_shared_generation_version=1,', 'native_shared_generation_version=0,'),
    (PREPARER, 'spec._native_shared_runtime_capture = runtime_capture', 'spec._native_shared_runtime_capture = replacement'),
    (PREPARER, 'spec._native_shared_max_draft_checks = max_draft_checks', 'spec._native_shared_max_draft_checks = 1'),
    (PREPARER, '    instruction = spec.instruction', '    instruction = "replacement instruction"'),
    (PREPARER, "'instruction': instruction,", "'instruction': 'replacement',"),
    (PREPARER, '    return _envelope(body, dependencies)', '    return _envelope({}, dependencies)'),
    (PREPARER, "controls['prepare_registration_v2'].envelope(body)", "controls['prepare_registration_v2'].envelope({})"),
    (PREPARER, 'VERSION = 2', 'VERSION = 1'),
])
def test_v2_route_refuses_one_changed_producer_or_consumer(tmp_path, relative, before, after):
    root = copied_route(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['enabled_values'] == [1]
    path = root / relative
    source = path.read_text()
    assert source.count(before) == 1
    path.write_text(source.replace(before, after))
    with pytest.raises(scan.ConfigError, match='v2 render|v2 preparation|v2 producer'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('binding', ['prepare = lambda *args: {}',
                                    'def prepare(*args):\n    return {}',
                                    'prepare.__code__ = replacement',
                                    'setattr(prepare, "__code__", replacement)',
                                    'selection = replacement'])
def test_v2_route_refuses_rebound_preparer_authority(tmp_path, binding):
    root = copied_route(tmp_path)
    path = root / PREPARER
    path.write_text(path.read_text() + '\n' + binding + '\n')
    with pytest.raises(scan.ConfigError, match='v2 render|v2 preparation|v2 producer'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('mutation', [
    'selection.capture = replacement',
    'authority.loaded_dependencies = replacement',
    'c.canonical = replacement',
    "c.HARD_LIMITS['input_bytes'] = 1",
    'del selection.capture',
    "setattr(selection, 'capture', replacement)",
    "delattr(authority, 'loaded_dependencies')",
    'alias = selection\nalias.capture = replacement',
    'alias = selection.capture\nalias.__code__ = replacement',
    "alias = c.HARD_LIMITS\nalias['input_bytes'] = 1",
    "selection.__dict__['capture'] = replacement",
    "vars(selection)['capture'] = replacement",
    "c.HARD_LIMITS.update({'input_bytes': 1})",
    "setattr(Path, 'cwd', replacement)",
    'alias = validate_runtime\nalias.__code__ = replacement',
])
def test_v2_route_refuses_imported_authority_mutations_and_escapes(tmp_path, mutation):
    root = copied_route(tmp_path)
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))['enabled_values'] == [1]
    path = root / PREPARER
    path.write_text(path.read_text() + '\n' + mutation + '\n')
    with pytest.raises(scan.ConfigError, match='v2 preparation imported authority'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def copied_procedure(tmp_path):
    for relative in (STAGE, 'src/data_sheets_schema/native_shared_receipts.py',
                     'src/data_sheets_schema/typed_audit.py',
                     'src/data_sheets_schema/audit_omissions.py',
                     'src/data_sheets_schema/native_shared_render.py'):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


def test_stage_package_and_private_options_derive_current_response_roster(tmp_path):
    root = copied_procedure(tmp_path)
    result = scan.derive_native_shared_procedure(root)
    assert result['protocol_responses']['formula'] == 'R + W + 2'
    assert result['model_calls_minimum'] is None
    assert [stage['kind'] for stage in result['stages']] == [
        'receipt', 'worker', 'omission', 'integration']
    # Calibrated refusal: retain the original private-association check with a
    # real broken consumer instead of asserting the now-repaired producer fails.
    path = root / STAGE
    source = path.read_text()
    before = "max_request_bytes=limits['max_request_bytes'], **self.options)"
    assert source.count(before) == 1
    path.write_text(source.replace(before, before.replace('**self.options', '**{}'), 1))
    with pytest.raises(scan.ConfigError, match='native packet lacks its fixed private receipt-catalog association'):
        scan.derive_native_shared_procedure(root)


def test_stage_package_wrong_relative_import_does_not_derive(tmp_path):
    root = copied_procedure(tmp_path)
    path = root / STAGE
    source = path.read_text()
    before = 'from .. import native_shared_receipts as nr'
    assert source.count(before) == 1
    path.write_text(source.replace(before, 'from . import native_shared_receipts as nr'))
    with pytest.raises(scan.ConfigError, match='missing fixed producer import nr'):
        scan.derive_native_shared_procedure(root)


def test_stage_procedure_never_falls_back_to_legacy_module(tmp_path):
    root = copied_procedure(tmp_path)
    path = root / STAGE
    legacy = root / 'src/data_sheets_schema/native_shared_stage.py'
    legacy.write_bytes(path.read_bytes())
    path.unlink()
    with pytest.raises(scan.ConfigError, match='cannot be read or parsed'):
        scan.derive_native_shared_procedure(root)
