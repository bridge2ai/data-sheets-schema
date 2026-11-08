"""U3-C v2 composition and closed live entry; no native/provider execution."""
from copy import deepcopy
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
import shlex
import sys

import pytest

from data_sheets_schema import api_runner
from data_sheets_schema import native_attribution_controller as legacy
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_controller_orchestration as orchestration
from data_sheets_schema import native_shared_controls_orchestration as control_loading
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_attribution_controller_v2 as inherited_v2
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_selection import declaration as synthetic_declaration, pin, save
from tests.utils.native_execution_carrier_v2 import execution_body


@pytest.fixture
def declaration(synthetic_declaration, monkeypatch):
    """Use committed schema roots across the real source-loader boundary.

    Other suites keep their small schema fixture. Here the ordinary bootstrap
    and freshly compiled api_runner must select the same installed schemas;
    no verified module or its constants are patched.
    """
    doc = synthetic_declaration
    roots = (
        ('full', 'Dataset', 'FULL_SCHEMA_PATH',
         'src/data_sheets_schema/schema/data_sheets_schema_all.yaml'),
        ('core', 'CoreDataset', 'CORE_SCHEMA_PATH',
         'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml'),
    )
    for kind, root_class, constant, relative in roots:
        # Undo this local synthetic fixture's tiny-schema bootstrap override.
        # These strings are the committed api_runner declarations.
        monkeypatch.setattr(api_runner, constant, relative)
        schema_path = (authority.ROOT / relative).resolve(strict=True)
        snapshot = capture_schema(schema_path, strict=True)
        doc['inputs'][kind + '_schema'] = {
            'root': str(schema_path), 'root_class': root_class,
            'sources': [{'name': str(name), **pin(path, raw)}
                        for name, path, raw in snapshot.sources],
        }
    save(doc)
    return doc


@pytest.fixture
def bound(inputs):
    preparation = registration.prepare(inputs['selection'], inputs['runtime_path'], **inputs['kwargs'])
    raw = c.canonical(preparation)
    instruction = inputs['root'] / 'u3c-instruction.md'
    instruction.write_bytes(preparation['registration']['instruction'].encode('utf-8'))
    return inputs, preparation, raw, instruction


def _files(root):
    return {str(path.relative_to(root)): c.sha(path.read_bytes())
            for path in root.rglob('*') if path.is_file()}


def test_real_v2_composition_roundtrip_joins_preparation_and_preserves_loader(bound, isolated_modules, monkeypatch):
    inputs, preparation, raw, instruction = bound
    before = _files(inputs['root'])
    old_path = list(sys.path)
    monkeypatch.setattr(legacy, 'load_controls', lambda: pytest.fail('v1 loader used'))
    value = orchestration.compose(raw, instruction_path=instruction)
    rebuilt, spec, selected = orchestration.reconstruct_composition(c.canonical(value))
    assert rebuilt == value
    assert orchestration.verified_composition(c.canonical(value)) == value
    assert value['authority_version'] == 2 and value['version'] == 1
    assert value['preparation_raw_json'].encode() == raw
    assert value['preparation_sha256'] == c.sha(raw)
    prepared = preparation['registration']
    for key in ('dependencies', 'render_spec', 'instruction_sha256', 'max_draft_checks', 'working_directory'):
        assert value[key] == prepared[key]
    assert value['selection_sha256'] == selected.registration.pin.sha256 == prepared['selection']['sha256']
    assert value['runtime_sha256'] == prepared['runtime']['sha256']
    assert value['runtime_raw_json'].encode() == inputs['runtime_path'].read_bytes()
    assert value['instruction_sha256'] == c.sha(instruction.read_bytes())
    assert spec.render_spec() == prepared['render_spec']
    assert spec.instruction.encode() == instruction.read_bytes()
    assert value['policy']['attribution_composition_version'] == 2
    assert value['policy']['native_shared_generation_version'] == 1
    assert 'write_paths' not in value['policy']['readonly_lookups']
    assert _files(inputs['root']) == before
    assert not Path(selected.role('stage_root')).exists()
    assert sys.path == old_path
    assert not isolated_modules.intersection(sys.modules)


def test_exact_eighteen_helpers_and_readonly_grammar(bound, monkeypatch):
    _, _, raw, instruction = bound
    value = orchestration.compose(raw, instruction_path=instruction)
    commands = policy.helper_commands(value['policy'])
    assert set(commands) == policy.HELPERS and len(commands) == 18
    assert '--initial-structure' in shlex.split(commands['phase1_receipts'])
    assert '--strict' in shlex.split(commands['final_receipts'])
    monkeypatch.setattr(legacy, 'load_controls', lambda: pytest.fail('v1 loader used'))
    with control_loading.loaded_controls(value['dependencies']) as controls, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_policy',
                package_sources=value['dependencies']['base']['package_sources']) as verified_policy:
        assert verified_policy.classify_bash(commands['final_receipts'] + ' --write',
            value['policy']['python'], set(), value['policy'], classifier_projection=controls)[0] == 'not_prescribed'
        for name, command in commands.items():
            assert verified_policy.classify_bash(command, value['policy']['python'], set(), value['policy'], classifier_projection=controls)[0] == 'prescribed', name
            assert verified_policy.classify_bash(command + ' --unregistered', value['policy']['python'], set(), value['policy'], classifier_projection=controls)[0] == 'not_prescribed', name
        bundle = c.parse_selection(value['selection_raw_json'].encode())['inputs']['bundle']['path']
        for command, expected in ((shlex.join(['cat', bundle]), 'prescribed'),
                ('cat /unregistered/path', 'not_prescribed'),
                (shlex.join([value['policy']['python'], '-c', 'print(1)']), 'not_prescribed')):
            assert verified_policy.classify_bash(command, value['policy']['python'], set(), value['policy'], classifier_projection=controls)[0] == expected
    old_path = list(sys.path)
    with control_loading.loaded_controls(value['dependencies']) as controls, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_policy',
                package_sources=value['dependencies']['base']['package_sources']) as verified_policy:
        guidance = verified_policy.command_guidance(value['policy'], classifier_projection=controls)
    assert all(command in guidance for command in commands.values())
    assert sys.path == old_path


@pytest.mark.parametrize('change', ['none', 'missing_initial', 'missing_final', 'prefix', 'extra'])
def test_receipt_helper_table_requires_both_exact_names(native_spec, change):
    from data_sheets_schema import native_shared_render as render
    commands = {name: shlex.join(argv) for name, argv in render.commands(native_spec).items()}
    value = {'native_shared_generation_version': 1, 'attribution_composition_version': 2,
             'python': shlex.split(commands['draft'])[0], 'native_shared_helpers': commands,
             'attribution_command': commands['draft'], 'post_final_recorder': {'command': commands['recorder']}}
    if change == 'missing_initial':
        del commands['phase1_receipts']
    elif change == 'missing_final':
        del commands['final_receipts']
    elif change == 'prefix':
        commands['final_receipts_extra'] = commands.pop('final_receipts')
    elif change == 'extra':
        commands['receipt_anything'] = commands['final_receipts']
    if change == 'none':
        assert policy.helper_commands(value) == commands
    else:
        with pytest.raises(ValueError, match='helper command table'):
            policy.helper_commands(value)


@pytest.mark.parametrize('change', ['extra', 'authority', 'version', 'preparation_hash',
                                  'runtime_hash', 'render', 'policy', 'instruction'])
def test_rehashed_or_mutated_composition_refuses(bound, change):
    inputs, _, raw, instruction = bound
    value = orchestration.compose(raw, instruction_path=instruction)
    if change == 'extra': value['accepted'] = True
    elif change == 'authority': value['authority_version'] = True
    elif change == 'version': value['version'] = 2
    elif change == 'preparation_hash': value['preparation_sha256'] = '0' * 64
    elif change == 'runtime_hash': value['runtime_sha256'] = '0' * 64
    elif change == 'render': value['render_spec']['reasoning_effort'] = 'low'
    elif change == 'policy':
        value['policy']['native_shared_helpers']['draft'] += ' --unregistered'
        value['policy_sha256'] = c.sha(c.canonical(value['policy']))
    else: instruction.write_bytes(instruction.read_bytes() + b'\nchanged\n')
    before = _files(inputs['root'])
    with pytest.raises(ValueError):
        orchestration.verified_composition(c.canonical(value))
    assert _files(inputs['root']) == before


@pytest.mark.parametrize('change', ['selection', 'runtime', 'executable'])
def test_composition_reconstruction_rechecks_current_authorities(bound, change):
    inputs, _, raw, instruction = bound
    value = orchestration.compose(raw, instruction_path=instruction)
    if change == 'selection':
        doc = c.strict_json(inputs['selection'].read_bytes())
        doc['run']['label'] = 'changed-selection'
        inputs['selection'].write_bytes(c.canonical(doc))
    elif change == 'runtime':
        runtime = deepcopy(inputs['runtime'])
        runtime['model'] = 'changed-runtime'
        inputs['runtime_path'].write_bytes(c.canonical(runtime))
    else:
        inputs['executable'].write_bytes(b'changed fingerprint')
    before = _files(inputs['root'])
    with pytest.raises(ValueError):
        orchestration.reconstruct_composition(c.canonical(value))
    assert _files(inputs['root']) == before


def _execution_wire():
    """Only a parser fixture; deliberately not a valid execution registration."""
    return {'authority_version': 2, 'controller_sources_sha256': controller.wire.CONTROLLER_SOURCES_SHA256,
            'registration': execution_body()}


def test_captured_parsers_are_pure_and_do_not_grant_verification(bound, monkeypatch):
    _, preparation, raw, _ = bound
    execution = _execution_wire()
    wire = c.canonical(execution)
    def forbidden(*args, **kwargs):
        pytest.fail('captured parser performed live I/O or verification')
    monkeypatch.setattr(registration, 'verify_preparer', forbidden)
    monkeypatch.setattr(registration, 'verified', forbidden)
    monkeypatch.setattr(authority, 'dependency_identity', forbidden)
    for name in ('read_bytes', 'read_text', 'open', 'resolve', 'cwd', 'absolute'):
        monkeypatch.setattr(Path, name, forbidden)
    assert controller.captured_preparation_body(raw) == preparation['registration']
    assert controller.captured_execution_body(wire) == execution['registration']


@pytest.mark.parametrize('change', ['outer_version', 'bool', 'manifest', 'extra', 'inner_version',
                                  'kind', 'scope', 'gates', 'unwrapped', 'missing', 'inner_extra'])
def test_captured_execution_parser_refuses_foreign_wire(change):
    value = _execution_wire()
    if change == 'outer_version': value['authority_version'] = 1
    elif change == 'bool': value['authority_version'] = True
    elif change == 'manifest': value['controller_sources_sha256'] = '0' * 64
    elif change == 'extra': value['verified'] = True
    elif change == 'inner_version': value['registration']['schema_version'] = True
    elif change == 'kind': value['registration']['kind'] = 'd4d_native_attribution_execution_registration'
    elif change == 'scope': value['registration']['execution'] = 'approved'
    elif change == 'gates': value['registration']['execution_gates'].pop()
    elif change == 'missing': value['registration'].pop('permission_observations')
    elif change == 'inner_extra': value['registration']['accepted'] = True
    else: value = value['registration']
    with pytest.raises(ValueError):
        controller.captured_execution_body(c.canonical(value))


def test_captured_execution_allows_only_named_optional_origin_field_without_io(monkeypatch):
    value = _execution_wire()
    # Pure shape parsing is deliberately not validation of this declaration.
    value['registration']['receipt_origin_reporting'] = {'version': 1}
    raw = c.canonical(value)
    def forbidden(*args, **kwargs):
        pytest.fail('captured optional-field parsing performed live verification')
    monkeypatch.setattr(registration, 'verified', forbidden)
    monkeypatch.setattr(registration, 'verify_preparer', forbidden)
    monkeypatch.setattr(authority, 'dependency_identity', forbidden)
    for name in ('read_bytes', 'read_text', 'open', 'resolve', 'cwd', 'absolute'):
        monkeypatch.setattr(Path, name, forbidden)
    assert controller.captured_execution_body(raw) == value['registration']


def test_callback_requires_fresh_full_outer_admission_before_any_live_dependency(monkeypatch, isolated_modules):
    raw = c.canonical(_execution_wire())
    calls = []
    def refuse(value, *, classifier_projection):
        with authority.loaded_verified_package_module('data_sheets_schema.native_shared_controls',
                package_sources=authority.dependency_identity()['base']['package_sources']) as source_controls:
            assert source_controls.require_controls(classifier_projection) is classifier_projection
        calls.append(value)
        raise ValueError('full U3-D execution consumer remains absent')
    monkeypatch.setattr(registration, 'verified', refuse)
    monkeypatch.setattr(orchestration, 'reconstruct_composition',
                        lambda *a: pytest.fail('live construction preceded full E verification'))
    with pytest.raises(ValueError, match='U3-D execution consumer remains absent'):
        orchestration.CallbackAdapter(b'not reached', execution={}, registration_raw=raw)
    assert calls == [raw]


def test_pure_execution_prefix_cannot_open_real_callback_route(bound):
    _, _, raw, instruction = bound
    composition = orchestration.compose(raw, instruction_path=instruction)
    wire = _execution_wire()
    with pytest.raises(ValueError):
        orchestration.CallbackAdapter(c.canonical(composition), execution=wire['registration'],
                                   registration_raw=c.canonical(wire))


def test_live_phase_decision_is_reconstructed_on_every_observation():
    adapter = object.__new__(orchestration.CallbackAdapter)
    calls = []
    class Run:
        def decision(self):
            calls.append('decision')
            return object()
    def current(endpoints):
        calls.append(endpoints)
        return Run()
    adapter._run = current
    first = adapter._phase_state((1, 2))
    second = adapter._phase_state((1, 2))
    assert calls == [(1, 2), 'decision', (1, 2), 'decision']
    assert first[0] is not second[0] and first[1] is not second[1]


def test_input_only_composition_matches_complete_verified_live_body_without_io(bound, monkeypatch):
    """Real preparation and captures; the pure replay never rediscovers authority."""
    _, preparation, preparation_raw, instruction_path = bound
    value = orchestration.compose(preparation_raw, instruction_path=instruction_path)
    _, spec, current = orchestration.reconstruct_composition(c.canonical(value))
    captured = dict(prepared=preparation['registration'], spec=spec, current=current,
        runtime=spec._native_shared_runtime_capture,
        instruction=orchestration.read_regular(str(instruction_path), 'instruction',
            max_bytes=c.HARD_LIMITS['request_bytes']).captured,
        controller_sources=value['controller_sources'], command_argv=orchestration.render.commands(spec),
        repository=value['working_directory'],
        output_directories=tuple(str(Path(spec._agentic_artifact_paths[key]).parent.resolve())
                                 for key in ('full', 'core', 'report')),
        python=value['python'], python_version=value['python_version'])
    raw = c.canonical(value)

    def forbidden(*args, **kwargs):
        pytest.fail('input-only composition rediscovered live authority')

    # Source loading and its final pin checks are orchestration I/O. Keep them
    # outside the trapped interval; only the actual pure calls run inside it.
    with control_loading.loaded_controls(value['dependencies']) as controls, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_controller',
                package_sources=value['dependencies']['base']['package_sources']) as verified_controller, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_selection',
                package_sources=value['dependencies']['base']['package_sources']) as verified_selection, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_evidence',
                package_sources=value['dependencies']['base']['package_sources']) as verified_evidence, \
            authority.loaded_verified_package_module('data_sheets_schema.agentic_runtime',
                package_sources=value['dependencies']['base']['package_sources']) as verified_toolchain:
        # command_policy imports this dependency lazily. Its real verified
        # source load belongs before the no-I/O interval, just like controller.
        assert authority.module_source_identity(verified_toolchain)['name'] == 'data_sheets_schema.agentic_runtime'
        # Exact capture classes belong to the same verified package scope as
        # the consumer. Fresh capture must preserve every field and byte.
        scoped_current = verified_selection.capture(preparation['registration']['selection']['path'])
        scoped_runtime = verified_evidence.read_regular(
            captured['runtime'].pin.path, 'runtime_declaration',
            max_bytes=c.HARD_LIMITS['input_bytes']).captured
        scoped_instruction = verified_evidence.read_regular(
            captured['instruction'].pin.path, 'instruction',
            max_bytes=c.HARD_LIMITS['request_bytes']).captured
        assert asdict(scoped_current) == asdict(current)
        assert asdict(scoped_runtime) == asdict(captured['runtime'])
        assert asdict(scoped_instruction) == asdict(captured['instruction'])
        original_runtime = spec._native_shared_runtime_capture
        scoped_captured = dict(captured, current=scoped_current, runtime=scoped_runtime,
                               instruction=scoped_instruction)
        with monkeypatch.context() as patch:
            patch.setattr(spec, '_native_shared_generation_capture', scoped_current)
            patch.setattr(spec, '_native_shared_runtime_capture', scoped_runtime)
            patch.setattr(registration, 'verify_preparer', forbidden)
            patch.setattr(registration, 'verified', forbidden)
            patch.setattr(authority, 'dependency_identity', forbidden)
            for name in ('read_bytes', 'read_text', 'open', 'resolve', 'cwd', 'absolute'):
                patch.setattr(Path, name, forbidden)
            assert verified_controller.compose(preparation_raw, classifier_projection=controls, **scoped_captured) == value
            rebuilt, returned_spec, returned_current = verified_controller.reconstruct_composition(
                raw, classifier_projection=controls, **scoped_captured)
            assert rebuilt == value and returned_spec is spec and returned_current is scoped_current
            assert verified_controller.verified_composition(raw, classifier_projection=controls, **scoped_captured) == value
            with pytest.raises(TypeError, match='classifier_projection'):
                verified_controller.reconstruct_composition(raw, **scoped_captured)
            for forged in (None, {}, dict(controls), object()):
                with pytest.raises(ValueError, match='projection'):
                    verified_controller.reconstruct_composition(raw, classifier_projection=forged, **scoped_captured)
                with pytest.raises(ValueError, match='projection'):
                    verified_controller.policy.classify_bash('cat', value['policy']['python'], set(), value['policy'],
                                         classifier_projection=forged)
        assert spec._native_shared_generation_capture is current
        assert spec._native_shared_runtime_capture is original_runtime
    with pytest.raises(ValueError, match='scope is closed|not minted by the active loader'):
        verified_controller.reconstruct_composition(raw, classifier_projection=controls, **captured)


@pytest.mark.parametrize('failure', ['changed_capture', 'consumer_exception'])
def test_verified_handoff_refuses_changed_capture_and_restores_spec(bound, monkeypatch, failure):
    """Negative orchestration seams; real producers run before fault injection."""
    _, _, raw, instruction = bound
    positive = orchestration.compose(raw, instruction_path=instruction)
    assert orchestration.verified_composition(c.canonical(positive)) == positive
    original_loader = authority.loaded_verified_package_module
    original_commands = orchestration.render.commands
    before = []
    injected = []

    def commands(spec):
        before.append((spec, spec._native_shared_generation_capture,
                       spec._native_shared_runtime_capture))
        return original_commands(spec)

    @contextmanager
    def injected_loader(name, *, package_sources):
        with original_loader(name, package_sources=package_sources) as module:
            if failure == 'changed_capture' and name == 'data_sheets_schema.native_shared_selection':
                class ChangedCapture:
                    @staticmethod
                    def capture(path):
                        captured = module.capture(path)
                        assert len(captured.authority) > 1
                        changed = replace(captured, authority=tuple(reversed(captured.authority)))
                        assert asdict(changed) != asdict(captured)
                        injected.append('changed_capture')
                        return changed
                yield ChangedCapture
            elif failure == 'consumer_exception' and name == 'data_sheets_schema.native_shared_controller':
                class FailingConsumer:
                    @staticmethod
                    def compose(preparation_raw, **captures):
                        assert preparation_raw == raw
                        assert captures['spec']._native_shared_generation_capture is captures['current']
                        assert captures['spec']._native_shared_runtime_capture is captures['runtime']
                        injected.append('consumer_exception')
                        raise ValueError('deliberate pure consumer exception')
                yield FailingConsumer
            else:
                yield module

    monkeypatch.setattr(orchestration.render, 'commands', commands)
    monkeypatch.setattr(authority, 'loaded_verified_package_module', injected_loader)
    expected = ('capture changed across verified source handoff' if failure == 'changed_capture'
                else 'deliberate pure consumer exception')
    with pytest.raises(ValueError, match=expected):
        orchestration.compose(raw, instruction_path=instruction)
    assert injected == [failure] and before
    for spec, original_current, original_runtime in before:
        assert spec._native_shared_generation_capture is original_current
        assert spec._native_shared_runtime_capture is original_runtime


def test_neutral_captured_wire_vocabulary_equals_unchanged_a_contract():
    wire = controller.wire
    assert wire.VERSION == registration.VERSION
    assert wire.CONTROLLER_SOURCES_SHA256 == inherited_v2.SOURCES_SHA256
    assert wire.PREPARATION_KIND == registration.PREPARATION_KIND
    assert wire.PREPARATION_SCOPE == registration.PREPARATION_SCOPE
    assert wire.PREPARATION_KEYS == registration._PREPARATION_KEYS
    assert wire.EXECUTION_KIND == registration.EXECUTION_KIND
    assert wire.EXECUTION_SCOPE == registration.EXECUTION_SCOPE
    assert wire.EXECUTION_KEYS == registration.EXECUTION_KEYS
    assert wire.EXECUTION_GATES == registration.EXECUTION_GATES


@pytest.mark.parametrize('change', ['valid', 'optional', 'missing', 'extra', 'bool_version',
                                  'foreign_kind', 'foreign_scope', 'gate_order', 'missing_gate'])
def test_neutral_execution_shape_matches_a_acceptance_and_refusal_messages(change):
    body = _execution_wire()['registration']
    if change == 'optional': body['receipt_origin_reporting'] = {'version': 1}
    elif change == 'missing': body.pop('permission_observations')
    elif change == 'extra': body['accepted'] = True
    elif change == 'bool_version': body['schema_version'] = True
    elif change == 'foreign_kind': body['kind'] = 'foreign'
    elif change == 'foreign_scope': body['execution'] = 'approved'
    elif change == 'gate_order': body['execution_gates'].reverse()
    elif change == 'missing_gate': body['execution_gates'].pop()
    outcomes = []
    for check in (registration._closed_execution, controller.wire.closed_execution):
        try:
            outcomes.append(('accepted', check(deepcopy(body))))
        except ValueError as exc:
            outcomes.append(('refused', str(exc)))
    assert outcomes[0] == outcomes[1]
    assert outcomes[0][0] == ('accepted' if change in ('valid', 'optional') else 'refused')
