"""U3-C v2 composition and closed live entry; no native/provider execution."""
from copy import deepcopy
from pathlib import Path
import shlex
import sys

import pytest

from data_sheets_schema import native_attribution_controller as legacy
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_execution_registration_v2 as registration
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_selection import declaration


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
    value = controller.compose(raw, instruction_path=instruction)
    rebuilt, spec, selected = controller.reconstruct_composition(c.canonical(value))
    assert rebuilt == value
    assert controller.verified_composition(c.canonical(value)) == value
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
    value = controller.compose(raw, instruction_path=instruction)
    commands = policy.helper_commands(value['policy'])
    assert set(commands) == policy.HELPERS and len(commands) == 18
    assert '--initial-structure' in shlex.split(commands['phase1_receipts'])
    assert '--strict' in shlex.split(commands['final_receipts'])
    monkeypatch.setattr(legacy, 'load_controls', lambda: pytest.fail('v1 loader used'))
    with controller.authority.loaded_dependencies(value['dependencies']) as controls:
        for name, command in commands.items():
            assert policy.classify_bash(command, value['policy']['python'], set(), value['policy'], controls)[0] == 'prescribed', name
            assert policy.classify_bash(command + ' --unregistered', value['policy']['python'], set(), value['policy'], controls)[0] == 'not_prescribed', name
        bundle = c.parse_selection(value['selection_raw_json'].encode())['inputs']['bundle']['path']
        for command, expected in ((shlex.join(['cat', bundle]), 'prescribed'),
                ('cat /unregistered/path', 'not_prescribed'),
                (shlex.join([value['policy']['python'], '-c', 'print(1)']), 'not_prescribed')):
            assert policy.classify_bash(command, value['policy']['python'], set(), value['policy'], controls)[0] == expected
    old_path = list(sys.path)
    guidance = policy.command_guidance(value['policy'])
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
    value = controller.compose(raw, instruction_path=instruction)
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
        controller.verified_composition(c.canonical(value))
    assert _files(inputs['root']) == before


@pytest.mark.parametrize('change', ['selection', 'runtime', 'executable'])
def test_composition_reconstruction_rechecks_current_authorities(bound, change):
    inputs, _, raw, instruction = bound
    value = controller.compose(raw, instruction_path=instruction)
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
        controller.reconstruct_composition(c.canonical(value))
    assert _files(inputs['root']) == before


def _execution_wire():
    """Only a parser fixture; deliberately not a valid execution registration."""
    return {'authority_version': 2, 'controller_sources_sha256': controller.inherited.SOURCES_SHA256,
            'registration': {'schema_version': 2, 'kind': registration.EXECUTION_KIND,
                'execution': registration.EXECUTION_SCOPE,
                'execution_gates': list(registration.EXECUTION_GATES)}}


def test_captured_parsers_are_pure_and_do_not_grant_verification(bound, monkeypatch):
    _, preparation, raw, _ = bound
    execution = _execution_wire()
    wire = c.canonical(execution)
    def forbidden(*args, **kwargs):
        pytest.fail('captured parser performed live I/O or verification')
    monkeypatch.setattr(registration, 'verify_preparer', forbidden)
    monkeypatch.setattr(registration, 'verified', forbidden)
    monkeypatch.setattr(controller.authority, 'dependency_identity', forbidden)
    for name in ('read_bytes', 'read_text', 'open', 'resolve', 'cwd', 'absolute'):
        monkeypatch.setattr(Path, name, forbidden)
    assert controller.captured_preparation_body(raw) == preparation['registration']
    assert controller.captured_execution_body(wire) == execution['registration']


@pytest.mark.parametrize('change', ['outer_version', 'bool', 'manifest', 'extra', 'inner_version',
                                  'kind', 'scope', 'gates', 'unwrapped'])
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
    else: value = value['registration']
    with pytest.raises(ValueError):
        controller.captured_execution_body(c.canonical(value))


def test_callback_requires_fresh_full_outer_admission_before_any_live_dependency(monkeypatch):
    raw = c.canonical(_execution_wire())
    calls = []
    def refuse(value):
        calls.append(value)
        raise ValueError('full U3-D execution consumer remains absent')
    monkeypatch.setattr(registration, 'verified', refuse)
    monkeypatch.setattr(controller, 'reconstruct_composition',
                        lambda *a: pytest.fail('live construction preceded full E verification'))
    with pytest.raises(ValueError, match='U3-D execution consumer remains absent'):
        controller.CallbackAdapter(b'not reached', execution={}, registration_raw=raw)
    assert calls == [raw]


def test_pure_execution_prefix_cannot_open_real_callback_route(bound):
    _, _, raw, instruction = bound
    composition = controller.compose(raw, instruction_path=instruction)
    wire = _execution_wire()
    with pytest.raises(ValueError):
        controller.CallbackAdapter(c.canonical(composition), execution=wire['registration'],
                                   registration_raw=c.canonical(wire))


def test_live_phase_decision_is_reconstructed_on_every_observation():
    adapter = object.__new__(controller.CallbackAdapter)
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
