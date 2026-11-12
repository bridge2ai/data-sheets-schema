"""Issues 5994/5995: strict CLI routing follows reconstructed run authority.

The CLI, policy selection, captured native selection, receipt assessment and
both floor predicates are real. Neither block_for nor the recorded receipt
entrypoints are replaced by the native tests. Native tests
supply only _recorded_run and _receipt_assessment at the orchestration boundary,
plus artifact-path lookup. The supplied run has a real captured selection, but
its observer history is not reconstructed here. These are CLI regressions, not
public completion, observed execution or native/provider acceptance evidence.
API cases read actual receipt/bundle/manifest/full/provenance files.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import canary
from data_sheets_schema import native_shared_capture_orchestration as capture
from data_sheets_schema import native_shared_contract as contract
from data_sheets_schema import native_shared_receipts as native_receipts
from data_sheets_schema import native_shared_selection as native_selection
from data_sheets_schema import receipt_completion_policy as policy
from data_sheets_schema import receipts as rc
from data_sheets_schema.cli import receipts as cli
from tests.test_native_shared_selection import declaration, pin, save  # noqa: F401
from tests.test_receipt_completion_policy import declaration as api_declaration
from tests.test_receipt_completion_policy import disk as api_disk  # noqa: F401
from tests.test_receipt_completion_policy import registration as api_registration
from tests.test_receipts import BUNDLE, FULL, _manifest_and_texts, _receipt


PENDING = {'state': 'pending', 'mode': 'diagnostic_pilot'}
REGISTERED = {'state': 'registered', 'numerator': 1, 'denominator': 1}


@pytest.fixture
def route_spies(monkeypatch):
    """Observe real calls and retain snapshots; do not replace their decisions."""
    calls = {'blocks': [], 'native': [], 'api': []}
    actual_block = rc.block_for
    actual_native = native_receipts.final_receipt_floors
    actual_api = cli.strict_failure

    def block(*args, **kwargs):
        value = actual_block(*args, **kwargs)
        calls['blocks'].append({'value': value, 'before': deepcopy(value)})
        return value

    def native(block, selected):
        calls['native'].append({'block': deepcopy(block), 'selection': selected})
        return actual_native(block, selected)

    def api(block):
        calls['api'].append(deepcopy(block))
        return actual_api(block)

    monkeypatch.setattr(rc, 'block_for', block)
    monkeypatch.setattr(native_receipts, 'final_receipt_floors', native)
    monkeypatch.setattr(cli, 'strict_failure', api)
    return calls


def checked_cli_block(calls):
    assert len(calls['blocks']) == 1
    observed = calls['blocks'][0]
    assert observed['value'] == observed['before'], 'CLI mutated its source receipt assessment'
    assert observed['value']['checked'] is True
    return observed['value']


@pytest.fixture
def native_recorded_case(declaration, monkeypatch, route_spies):
    """Construct policy before capture; simulate only recorded reconstruction."""
    def prepare(*, floor=None, structural_failure=False, uncovered=False, invalid=None,
                cli_run_updates=None, reconstructed_selection_mismatch=False):
        manifest, texts = _manifest_and_texts()
        for name, raw in (('bundle', BUNDLE.encode()), ('chunk_manifest', contract.canonical(manifest))):
            path = Path(declaration['inputs'][name]['path'])
            path.write_bytes(raw)
            declaration['inputs'][name] = pin(path, raw)
        policy_path = Path(declaration['receipt_policy']['path'])
        registration = contract.strict_json(policy_path.read_bytes())
        registration['coverage_floor'] = deepcopy(PENDING if floor is None else floor)
        policy_raw = contract.canonical(registration)
        policy_path.write_bytes(policy_raw)
        declaration['receipt_policy'] = pin(policy_path, policy_raw)
        save(declaration)
        selected = native_selection.capture(declaration['registration_path'])
        reconstructed_selection = selected
        if reconstructed_selection_mismatch:
            # A second, genuinely captured selection tests the consumer's
            # explicit-selection comparison. No captured object is mutated.
            other = deepcopy(declaration)
            other['registration_id'] = 'different-reconstructed-selection'
            other['registration_path'] = str(Path(declaration['registration_path']).with_name('other-selection.json'))
            save(other)
            reconstructed_selection = native_selection.capture(other['registration_path'])
        requested_run = {**declaration['run'], **(cli_run_updates or {})}
        render = policy.native_render_declaration(selected)
        chosen = policy.select_policy(render)
        full = deepcopy(FULL)
        if uncovered:
            full['license'] = 'CC-BY'
        receipt = _receipt(manifest['bundle_md5'])
        if structural_failure:
            receipt['chunks'][0]['status'] = 'pending'
        def build_assessment():
            block = rc.check(receipt, manifest, texts, full, manifest['bundle_md5'],
                             deepcopy(full), instrument_version=4)
            block.update(expected=True, native_receipt_stage='final', final_stage_complete=True,
                native_stage_completion_history_sha256='a' * 64,
                coverage_floor=native_receipts.floor(block['slots'], selected),
                native_shared_receipt_policy=dict(chosen['identity']))
            block[policy.BLOCK_KEY] = policy.block_identity(chosen)
            return block

        assessment = build_assessment()
        project = requested_run['project']
        root = Path(declaration['registration_path']).parent / 'recorded-output'
        root.mkdir()
        paths = {'full': root / f'{project}_d4d.yaml',
                 'receipt': root / f'{project}_coverage_receipt.yaml',
                 'provenance': root / f'{project}_provenance.yaml', 'core_dir': root}
        paths['full'].write_text(yaml.safe_dump(full))
        paths['receipt'].write_text(yaml.safe_dump(receipt))
        record = {'run': deepcopy(declaration['run']), 'prompts': {'request': {'spec': deepcopy(render)}},
            'inputs': {'bundle_path': declaration['inputs']['bundle']['path'],
                'bundle_md5': manifest['bundle_md5'], 'receipt_expected': True},
            'receipts': deepcopy(assessment)}
        if invalid == 'record-selection-hash':
            record['prompts']['request']['spec']['native_shared_generation_registration']['sha256'] = '0' * 64
        elif invalid == 'missing-record-selection':
            del record['prompts']['request']['spec']['native_shared_generation_registration']
        elif invalid == 'lost-declaration':
            del record['prompts']
            # A native marker can force refusal, never create authority.
            record['native_shared_generation'] = {'fixture': 'recorded reconstruction boundary'}
        elif invalid not in (None, 'reconstruction-refusal'):
            raise ValueError('Unknown boundary fixture mutation')
        paths['provenance'].write_text(yaml.safe_dump(record))
        run = SimpleNamespace(selection=reconstructed_selection)
        boundary_calls = []
        deliveries = []

        def recorded_run(spec, loaded_record):
            boundary_calls.append('recorded_run')
            assert spec is None
            assert loaded_record == record
            # This is a supplied reconstruction boundary, not an observer or
            # history validator. Its selection and declaration are real.
            if invalid == 'reconstruction-refusal':
                raise ValueError('supplied recorded boundary refused its invalid saved selection')
            assert policy.select_policy(record=loaded_record) == chosen
            return run

        def receipt_assessment(reconstructed, *, full_path, receipt_path):
            boundary_calls.append('receipt_assessment')
            assert reconstructed is run
            assert Path(full_path) == paths['full'] and Path(receipt_path) == paths['receipt']
            block = build_assessment()
            deliveries.append({'value': block, 'before': deepcopy(block)})
            return block, None, None

        def run_paths(method, label, name):
            # The path boundary deliberately delivers the stored record even
            # for a conflicting requested run in the identity-refusal tests.
            assert (method, label, name) == tuple(requested_run[key] for key in ('method', 'label', 'project'))
            return paths

        def selected_paths(path):
            assert str(path) == declaration['registration_path']
            return paths

        monkeypatch.setattr(capture, '_recorded_run', recorded_run)
        monkeypatch.setattr(capture, '_receipt_assessment', receipt_assessment)
        monkeypatch.setattr(capture, 'selected_receipt_paths', selected_paths)
        monkeypatch.setattr(cli, '_run_paths', run_paths)
        preserved = {path: path.read_bytes() for path in
            (paths['full'], paths['receipt'], paths['provenance'], policy_path,
             Path(declaration['registration_path']), Path(declaration['inputs']['bundle']['path']),
             Path(declaration['inputs']['chunk_manifest']['path']))}

        def invoke(with_selection=False):
            args = ['check', '--method', requested_run['method'], '--label', requested_run['label'],
                    '--project', requested_run['project'], '--strict']
            if with_selection:
                args.extend(['--native-shared-selection', declaration['registration_path']])
            result = CliRunner().invoke(cli.receipts, args)
            assert {path: path.read_bytes() for path in preserved} == preserved
            return result

        return SimpleNamespace(invoke=invoke, selected=selected, assessment=assessment,
            boundary_calls=boundary_calls, calls=route_spies, paths=paths, deliveries=deliveries,
            reconstructed_selection=reconstructed_selection)

    return prepare


@pytest.mark.parametrize('with_selection', [False, True], ids=['record-only', 'explicit-selection'])
@pytest.mark.parametrize('case,floor,structural_failure,uncovered,exit_code,state,passed', [
    ('pending', PENDING, False, False, 0, 'pending', False),
    ('pending-structural-failure', PENDING, True, False, 1, 'pending', False),
    ('registered-pass', REGISTERED, False, False, 0, 'passed', True),
    ('registered-fail', REGISTERED, False, True, 1, 'failed', False),
], ids=['pending', 'pending-structural-failure', 'registered-pass', 'registered-fail'])
def test_recorded_native_cli_uses_selected_final_floors(native_recorded_case, with_selection,
        case, floor, structural_failure, uncovered, exit_code, state, passed):
    case_data = native_recorded_case(floor=floor, structural_failure=structural_failure, uncovered=uncovered)
    result = case_data.invoke(with_selection=with_selection)
    assert len(case_data.deliveries) == 1
    delivered = case_data.deliveries[0]
    assert delivered['value'] == delivered['before']
    block = delivered['value']
    assert block['checked'] is True
    assert block['coverage_floor'] == case_data.assessment['coverage_floor']
    assert block['coverage_floor']['state'] == state
    assert block['coverage_floor']['passed'] is passed
    assert f'registered receipt coverage: {state}' in result.output
    assert result.exit_code == exit_code, result.output
    if exit_code == 0:
        assert result.exception is None
    else:
        assert isinstance(result.exception, SystemExit), repr(result.exception)
    assert case_data.boundary_calls == ['recorded_run', 'receipt_assessment']
    assert case_data.calls['native'], 'Recorded native selection did not reach the native final predicate'
    assert not case_data.calls['api'], 'A native record reached the generic API strict predicate'
    for observed in case_data.calls['native']:
        assert type(observed['selection']) is contract.NativeSelectionCapture
        assert observed['selection'].registration.raw == case_data.selected.registration.raw
        assert observed['selection'].receipt_policy.raw == case_data.selected.receipt_policy.raw
    structural = {key: value for key, value in canary.receipt_floors(block).items()
                  if key != 'registered receipt coverage'}
    assert bool(any(structural.values())) is structural_failure
    if state == 'pending':
        assert block['coverage_floor']['passed'] is False
        assert canary.receipt_floors(block)['registered receipt coverage'] == 1


@pytest.mark.parametrize('invalid', ['record-selection-hash', 'missing-record-selection',
                                    'reconstruction-refusal', 'lost-declaration'])
def test_invalid_recorded_native_selection_refuses_without_api_fallback(native_recorded_case, invalid):
    case_data = native_recorded_case(invalid=invalid)
    result = case_data.invoke()
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    assert 'refused' in result.output
    assert case_data.deliveries == []
    for observed in case_data.calls['blocks']:
        assert observed['value']['checked'] is False
    assert case_data.calls['native'] == []
    assert case_data.calls['api'] == []
    assert case_data.boundary_calls == (['recorded_run'] if invalid == 'reconstruction-refusal' else [])


@pytest.fixture
def api_recorded_case(api_disk, tmp_path, monkeypatch, route_spies):
    def prepare(*, floor, uncovered=False, spec_updates=None):
        if uncovered:
            full = yaml.safe_load(api_disk['full_path'].read_text())
            full['license'] = 'CC-BY'
            api_disk['full_path'].write_text(yaml.safe_dump(full))
        selected = api_declaration(api_registration(deepcopy(floor)))
        selected.update(deepcopy(spec_updates or {}))
        paths = {'core_dir': tmp_path, 'full': api_disk['full_path'],
                 'receipt': api_disk['receipt'], 'provenance': tmp_path / 'P_provenance.yaml'}
        record = {'run': {'method': 'claudecode_api', 'label': 'L', 'project': 'P'},
            'inputs': {'bundle_path': str(api_disk['bundle']),
                'bundle_md5': api_disk['record_bundle_md5'], 'receipt_expected': True,
                'chunks': {'path': str(api_disk['manifest'])}},
            'prompts': {'request': {'spec': selected}}}
        paths['provenance'].write_text(yaml.safe_dump(record))
        monkeypatch.setattr(cli, '_run_paths', lambda *_: paths)
        native_boundaries = []

        def forbidden_native(*args, **kwargs):
            native_boundaries.append('native reconstruction')
            pytest.fail('API provenance reached native reconstruction')

        monkeypatch.setattr(capture, 'recorded_receipt_block', forbidden_native)
        monkeypatch.setattr(capture, 'live_receipt_block', forbidden_native)
        # The planned recorded companion must stay unreachable from API too;
        # this negative sentinel does not provide a fake successful companion.
        monkeypatch.setattr(capture, 'recorded_receipt_assessment', forbidden_native, raising=False)
        preserved = {path: path.read_bytes() for path in
            (paths['full'], paths['receipt'], paths['provenance'], api_disk['bundle'], api_disk['manifest'])}

        def invoke(extra=(), *, strict=True):
            args = ['check', '--method', 'claudecode_api', '--label', 'L', '--project', 'P']
            if strict:
                args.append('--strict')
            result = CliRunner().invoke(cli.receipts, [*args, *extra])
            assert {path: path.read_bytes() for path in preserved} == preserved
            return result

        return SimpleNamespace(invoke=invoke, calls=route_spies, record=record, paths=paths,
            native_boundaries=native_boundaries)

    return prepare


@pytest.mark.parametrize('floor,uncovered,exit_code,state,passed', [
    (PENDING, False, 1, 'pending', False),
    (REGISTERED, False, 0, 'passed', True),
    (REGISTERED, True, 1, 'failed', False),
], ids=['pending-stays-strict', 'registered-pass', 'registered-fail'])
def test_recorded_api_cli_retains_generic_strict_route(api_recorded_case, floor, uncovered,
        exit_code, state, passed):
    case_data = api_recorded_case(floor=floor, uncovered=uncovered)
    result = case_data.invoke()
    block = checked_cli_block(case_data.calls)
    assert block['coverage_floor']['state'] == state
    assert block['coverage_floor']['passed'] is passed
    chosen = policy.select_policy(record=case_data.record)
    assert block['coverage_floor'] == policy.evaluate_floor(block['slots'], chosen)
    assert f'registered receipt coverage: {state}' in result.output
    assert result.exit_code == exit_code, result.output
    assert case_data.calls['api'] and case_data.calls['native'] == []
    assert case_data.native_boundaries == []
    assert 'native receipt stage' not in result.output


def test_native_selection_flag_cannot_override_api_record(api_recorded_case, declaration):
    case_data = api_recorded_case(floor=PENDING)
    result = case_data.invoke(['--native-shared-selection', declaration['registration_path']])
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    assert 'native receipt selection refused' in result.output
    assert case_data.calls['blocks'] == [] and case_data.calls['native'] == [] and case_data.calls['api'] == []
    assert case_data.native_boundaries == []


def test_matching_native_cli_names_cannot_override_api_policy(api_recorded_case, declaration, monkeypatch):
    """A colliding destination must refuse on policy, beyond the method check."""
    case_data = api_recorded_case(floor=PENDING)
    monkeypatch.setattr(capture, 'selected_receipt_paths', lambda _: case_data.paths)
    before = case_data.paths['provenance'].read_bytes()
    result = CliRunner().invoke(cli.receipts, ['check', '--method', declaration['run']['method'],
        '--label', declaration['run']['label'], '--project', declaration['run']['project'], '--strict',
        '--native-shared-selection', declaration['registration_path']])
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    assert 'native receipt declaration refused' in result.output
    assert 'differs from the record declaration' in result.output
    assert case_data.paths['provenance'].read_bytes() == before
    assert case_data.calls['blocks'] == [] and case_data.calls['native'] == [] and case_data.calls['api'] == []
    assert case_data.native_boundaries == []


@pytest.mark.parametrize('strict', [True, False], ids=['strict-refuses', 'non-strict-reports-unchecked'])
def test_malformed_saved_api_policy_keeps_unchecked_cli_semantics(api_recorded_case, strict):
    case_data = api_recorded_case(floor=REGISTERED,
        spec_updates={'receipt_completion_policy_sha256': '0' * 64})
    result = case_data.invoke(strict=strict)
    assert result.exit_code == (1 if strict else 0), result.output
    if strict:
        assert isinstance(result.exception, SystemExit), repr(result.exception)
    else:
        assert result.exception is None, repr(result.exception)
    assert len(case_data.calls['blocks']) == 1
    observed = case_data.calls['blocks'][0]
    assert observed['value'] == observed['before']
    assert observed['value']['expected'] is True
    assert observed['value']['checked'] is False
    assert 'receipt policy selection refused' in observed['value']['reason']
    assert 'unchecked' in result.output
    assert 'coverage_floor' not in observed['value']
    assert case_data.calls['native'] == [] and case_data.calls['api'] == []
    assert case_data.native_boundaries == []


def test_exact_integer_disabled_native_axis_keeps_valid_api_route(api_recorded_case):
    case_data = api_recorded_case(floor=REGISTERED,
        spec_updates={'native_shared_generation_version': 0})
    assert type(case_data.record['prompts']['request']['spec']['native_shared_generation_version']) is int
    result = case_data.invoke()
    assert result.exit_code == 0 and result.exception is None, result.output
    block = checked_cli_block(case_data.calls)
    assert block['coverage_floor']['state'] == 'passed'
    assert block['coverage_floor']['passed'] is True
    assert block['coverage_floor'] == policy.evaluate_floor(block['slots'], policy.select_policy(record=case_data.record))
    assert case_data.calls['api'] and case_data.calls['native'] == []
    assert case_data.native_boundaries == []
    assert 'native receipt stage' not in result.output


@pytest.mark.parametrize('strict', [True, False], ids=['strict', 'non-strict'])
@pytest.mark.parametrize('spec_updates', [
    {'native_shared_generation_version': False},
    {'native_shared_generation_registration': {'sha256': '0' * 64, 'raw_json': '{}'}},
], ids=['boolean-false-is-not-disabled', 'partial-native-selection'])
def test_invalid_native_demand_cannot_fall_back_to_api(api_recorded_case, strict, spec_updates):
    case_data = api_recorded_case(floor=REGISTERED, spec_updates=spec_updates)
    result = case_data.invoke(strict=strict)
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    assert 'native' in result.output and 'refused' in result.output
    assert case_data.calls['blocks'] == [], 'Invalid native authority reached the API block reader'
    assert case_data.calls['native'] == [] and case_data.calls['api'] == []
    assert case_data.native_boundaries == []


@pytest.mark.parametrize('cli_run_updates', [
    {'method': 'claudecode_api'}, {'label': 'another-label'}, {'project': 'OTHER'},
], ids=['method', 'label', 'project'])
def test_record_only_native_selection_must_match_requested_run(native_recorded_case, cli_run_updates):
    case_data = native_recorded_case(cli_run_updates=cli_run_updates)
    result = case_data.invoke(with_selection=False)
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    assert 'native' in result.output and 'refused' in result.output
    assert case_data.calls['native'] == [], 'Conflicting run identity reached the native floor predicate'
    assert case_data.calls['api'] == [], 'Conflicting native run identity reached the API predicate'


def test_explicit_selection_must_equal_fresh_recorded_selection(native_recorded_case):
    case_data = native_recorded_case(reconstructed_selection_mismatch=True)
    assert type(case_data.reconstructed_selection) is contract.NativeSelectionCapture
    assert case_data.reconstructed_selection.registration.raw != case_data.selected.registration.raw
    # Keep the policy identical so policy-only comparison cannot satisfy this
    # test: the explicit and freshly reconstructed selection must also agree.
    assert case_data.reconstructed_selection.receipt_policy.raw == case_data.selected.receipt_policy.raw
    result = case_data.invoke(with_selection=True)
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    assert 'native' in result.output and 'refused' in result.output
    assert case_data.boundary_calls[0] == 'recorded_run'
    assert case_data.calls['native'] == [], 'A different reconstructed selection reached the final predicate'
    assert case_data.calls['api'] == []


def test_recorded_companion_returns_independent_blocks_from_one_reconstruction(native_recorded_case):
    case_data = native_recorded_case()
    saved_record = yaml.safe_load(case_data.paths['provenance'].read_text())
    result = capture.recorded_receipt_assessment(record=saved_record,
        full_path=case_data.paths['full'], receipt_path=case_data.paths['receipt'])
    assert result.selection is case_data.selected
    original_raw = result.raw
    first = result.block()
    assert first == case_data.assessment
    first['coverage_floor']['passed'] = True
    first['coverage_floor']['state'] = 'passed'
    first['slots']['with_receipt'] = 0
    second = result.block()
    assert first != second
    assert second == case_data.assessment
    assert second['coverage_floor']['state'] == 'pending'
    assert second['coverage_floor']['passed'] is False
    assert result.raw == original_raw == contract.canonical(case_data.assessment)
    assert case_data.boundary_calls == ['recorded_run', 'receipt_assessment']
    assert len(case_data.deliveries) == 1
    assert case_data.deliveries[0]['value'] == case_data.deliveries[0]['before'] == case_data.assessment
    assert case_data.calls == {'blocks': [], 'native': [], 'api': []}
