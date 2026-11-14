"""U3-J2 closed software-test profile refusals; never invoke a native binary."""
from copy import deepcopy
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from data_sheets_schema import native_runtime_profiles as profiles
from data_sheets_schema import native_shared_runtime_values as values
from data_sheets_schema import native_model_aliases as aliases


@pytest.fixture(autouse=True)
def no_process_or_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('profile validation must not invoke any executable')
    for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(os, 'system', forbidden)


@pytest.fixture
def runtime(tmp_path):
    root = tmp_path.resolve()
    peer = root / 'ordinary-python-peer'
    body = (Path(__file__).parent / 'fixtures/native_shared_execution/fake_cli.py').read_bytes()
    raw = ('#!' + sys.executable + ' -P\n').encode() + body
    peer.write_bytes(raw)
    peer.chmod(0o700)
    home = root / 'synthetic-home'
    home.mkdir()
    return {'route': values.ROUTE,
        'executable': {'path': str(peer), 'sha256': hashlib.sha256(raw).hexdigest(),
            'version': 'SYNTHETIC PYTHON SOFTWARE TEST', 'init_version': 'synthetic-python-1'},
        'model': profiles.SYNTHETIC_REQUESTED, 'auxiliary_models': [], 'effort': 'high',
        'limits': {'contextWindow': 900000, 'maxOutputTokens': 4000},
        'limits_basis': json.dumps({'kind': aliases.PROVISIONAL_KIND, 'version': 1,
            'profile': profiles.SYNTHETIC_PROFILE,
            'model_aliases': {'requested': profiles.SYNTHETIC_REQUESTED,
                              'returned': profiles.SYNTHETIC_RETURNED}}, sort_keys=True),
        'provider': profiles.SYNTHETIC_PROVIDER,
        'auth': {'loggedIn': False, 'authMethod': profiles.SYNTHETIC_PROFILE,
            'apiProvider': profiles.SYNTHETIC_PROVIDER, 'subscriptionType': profiles.SYNTHETIC_PROFILE,
            'expected_api_key_source': 'none'},
        'environment': {'PATH': '/usr/bin:/bin', 'HOME': str(home),
            'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', 'PYSTOW_HOME': str(root / 'attempt' / 'helper-cache'),
            'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'},
        'deadline_seconds': 900, 'budget_guard_usd': '1.0',
        'keep_awake': {'policy': 'not_applicable', 'host_platform': sys.platform,
            'basis': 'Ordinary Python software test; no native acceptance'}}


def test_explicit_synthetic_profile_is_distinct_and_registers_bash_timeout(runtime):
    original = deepcopy(runtime)
    assert profiles.require_synthetic(runtime) == original
    assert values.validate_runtime_v2(runtime) == original
    assert profiles.profile_name(runtime) == profiles.SYNTHETIC_PROFILE
    assert aliases.model_aliases(runtime) == {
        'requested': profiles.SYNTHETIC_REQUESTED, 'returned': profiles.SYNTHETIC_RETURNED}
    assert runtime == original
    assert runtime['deadline_seconds'] == 900
    raw = Path(runtime['executable']['path']).read_bytes()
    assert raw.split(b'\n', 1)[0] == ('#!' + sys.executable + ' -P').encode()
    assert b"timeout=int(os.environ['BASH_DEFAULT_TIMEOUT_MS']) / 1000" in raw
    assert hashlib.sha256(raw.split(b'\n', 1)[1]).hexdigest() == profiles.SYNTHETIC_PEER_SHA256
    with pytest.raises(ValueError, match='first-party'):
        values.validate_runtime(runtime)


@pytest.mark.parametrize('key', ['BASH_DEFAULT_TIMEOUT_MS', 'BASH_MAX_TIMEOUT_MS'])
@pytest.mark.parametrize('replacement', [None, '120000', '600001', 600000])
def test_registered_bash_timeout_is_required_exactly(runtime, key, replacement):
    if replacement is None:
        runtime['environment'].pop(key)
    else:
        runtime['environment'][key] = replacement
    with pytest.raises(ValueError):
        values.validate_runtime_v2(runtime)
    runtime['limits_basis'] = 'historical declaration'
    runtime['auth'].update(loggedIn=True, authMethod='claude.ai', apiProvider='firstParty')
    with pytest.raises(ValueError):
        values.validate_runtime_v2(runtime)


@pytest.mark.parametrize('shebang', ['missing_safe_path', 'foreign_interpreter', 'extra_options'])
def test_synthetic_peer_refuses_changed_startup_even_with_recomputed_hash(runtime, shebang):
    """Data-only mutation check: no interpreter or peer is invoked."""
    peer = Path(runtime['executable']['path'])
    body = peer.read_bytes().split(b'\n', 1)[1]
    header = {'missing_safe_path': '#!' + sys.executable,
              'foreign_interpreter': '#!' + sys.executable + '-unregistered -P',
              'extra_options': '#!' + sys.executable + ' -P -S'}[shebang]
    raw = (header + '\n').encode() + body
    peer.write_bytes(raw)
    runtime['executable']['sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match='exact Python test peer'):
        profiles.require_synthetic(runtime)


@pytest.mark.parametrize('fixture_file,peer_class', [
    ('native_shared_fixture.py', '_NeutralAnswers'),
    ('native_shared_omission_fixture.py', '_OmissionAnswers'),
])
def test_pinned_answer_classes_preserve_original_ast(fixture_file, peer_class):
    """Read code as data; neither the peer nor test fixture modules are imported."""
    root = Path(__file__).parent
    original_tree = ast.parse((root / fixture_file).read_bytes())
    peer_tree = ast.parse((root / 'fixtures/native_shared_execution/fake_cli.py').read_bytes())
    original = [node for node in original_tree.body
                if isinstance(node, ast.ClassDef) and node.name == '_Answers']
    embedded = [node for node in peer_tree.body
                if isinstance(node, ast.ClassDef) and node.name == peer_class]
    assert len(original) == len(embedded) == 1
    embedded[0].name = '_Answers'  # The sole permitted AST normalization.
    assert ast.dump(embedded[0], include_attributes=False) == ast.dump(original[0], include_attributes=False)


def test_pinned_peer_never_imports_test_code_and_guards_before_fixture_selection():
    peer = Path(__file__).parent / 'fixtures/native_shared_execution/fake_cli.py'
    tree = ast.parse(peer.read_bytes())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split('.')[0] != 'tests' for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 and (node.module or '').split('.')[0] != 'tests'
        elif isinstance(node, ast.Attribute):
            assert not (isinstance(node.value, ast.Name) and node.value.id == 'sys'
                        and node.attr == 'path'), 'the pinned peer must not alter import discovery'
        elif isinstance(node, ast.Name):
            assert node.id not in {'__import__', 'eval', 'exec', 'compile'}
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    runtime_index = next(index for index, node in enumerate(main.body)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'runtime'
                                              for target in node.targets))
    expected = ast.parse("runtime = value['runtime']\nrequire_synthetic(runtime)").body
    assert [ast.dump(node, include_attributes=False) for node in main.body[runtime_index:runtime_index + 2]] == [
        ast.dump(node, include_attributes=False) for node in expected]
    assert runtime_index == 2  # attempt path, captured value, then immediate runtime guard.


@pytest.mark.parametrize('mutation', ['neutral_answer', 'omission_answer', 'trailing_byte'])
def test_repinning_changed_answer_code_or_peer_bytes_never_admits(runtime, mutation):
    """A caller-supplied executable hash cannot authorize changed peer behavior."""
    peer = Path(runtime['executable']['path'])
    before = peer.read_bytes()
    if mutation == 'neutral_answer':
        after = before.replace(b'No additional synthetic candidate declared.', b'Changed neutral declaration.', 1)
    elif mutation == 'omission_answer':
        after = before.replace(b'Invented merged/dropped declarations; scientific validity unverified.',
                               b'Changed omission declaration.', 1)
    else:
        after = before + b'\n'
    assert after != before
    ast.parse(after)  # The refusal is identity, not invalid Python syntax.
    peer.write_bytes(after)
    runtime['executable']['sha256'] = hashlib.sha256(after).hexdigest()
    with pytest.raises(ValueError, match='exact Python test peer'):
        profiles.require_synthetic(runtime)


@pytest.mark.parametrize('mutation', [
    'production_model', 'real_auth', 'real_provider', 'logged_in', 'real_subscription',
    'provider_key', 'deadline', 'budget', 'auxiliary', 'keep_awake', 'account_home',
    'secure_storage', 'inherited_key', 'different_peer', 'wrong_shebang', 'hard_link',
    'symlink', 'home_artifact', 'missing_profile', 'unknown_profile', 'wrong_alias'])
def test_synthetic_cannot_name_real_account_executable_or_loosen_bounds(runtime, tmp_path, mutation):
    changed = deepcopy(runtime)
    binary = Path(changed['executable']['path'])
    if mutation == 'production_model':
        changed['model'] = aliases.REQUESTED
    elif mutation == 'real_auth':
        changed['auth']['authMethod'] = 'claude.ai'
    elif mutation == 'real_provider':
        changed['provider'] = 'firstParty'
    elif mutation == 'logged_in':
        changed['auth']['loggedIn'] = True
    elif mutation == 'real_subscription':
        changed['auth']['subscriptionType'] = 'max'
    elif mutation == 'provider_key':
        changed['auth']['expected_api_key_source'] = 'ANTHROPIC_API_KEY'
    elif mutation == 'deadline':
        changed['deadline_seconds'] = 21600
    elif mutation == 'budget':
        changed['budget_guard_usd'] = '90'
    elif mutation == 'auxiliary':
        changed['auxiliary_models'] = ['other']
    elif mutation == 'keep_awake':
        changed['keep_awake']['policy'] = 'macos_iokit_ims_v1'
    elif mutation == 'account_home':
        changed['environment']['HOME'] = str(tmp_path.resolve())
    elif mutation == 'secure_storage':
        changed['environment']['CLAUDE_SECURESTORAGE_CONFIG_DIR'] = str(tmp_path.resolve())
    elif mutation == 'inherited_key':
        changed['environment']['ANTHROPIC_API_KEY'] = 'invented-key'
    elif mutation in ('different_peer', 'wrong_shebang'):
        raw = (b'#!/bin/sh\nexit 0\n' if mutation == 'different_peer' else
               b'#!/bin/sh\n' + binary.read_bytes().split(b'\n', 1)[1])
        binary.write_bytes(raw)
        changed['executable']['sha256'] = hashlib.sha256(raw).hexdigest()
    elif mutation == 'hard_link':
        os.link(binary, tmp_path / 'second-link')
    elif mutation == 'symlink':
        link = tmp_path / 'peer-link'
        link.symlink_to(binary)
        changed['executable']['path'] = str(link)
    elif mutation == 'home_artifact':
        (Path(changed['environment']['HOME']) / '.claude.json').write_text('{}')
    else:
        basis = json.loads(changed['limits_basis'])
        if mutation == 'missing_profile':
            del basis['profile']
        elif mutation == 'unknown_profile':
            basis['profile'] = 'other'
        else:
            basis['model_aliases']['returned'] = aliases.RETURNED
        changed['limits_basis'] = json.dumps(basis)
    with pytest.raises(ValueError):
        profiles.require_synthetic(changed)


@pytest.mark.parametrize('basis', ['historical text', '{}', '{"profile":"production"}'])
def test_reserved_synthetic_labels_never_fall_back_to_production(runtime, basis):
    runtime['limits_basis'] = basis
    with pytest.raises(ValueError, match='explicit synthetic'):
        profiles.profile_name(runtime)


def test_legacy_production_validation_and_profile_bytes_unchanged(runtime):
    old = deepcopy(runtime)
    old['model'] = 'historical-native-fixture-model'
    old['provider'] = 'historical-provider'
    old['limits_basis'] = 'historical declaration'
    old['auth'] = {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
        'subscriptionType': 'max', 'expected_api_key_source': 'none'}
    old['deadline_seconds'] = 21600
    old['budget_guard_usd'] = '90'
    current = deepcopy(old)
    old['environment'].pop('PYSTOW_HOME')
    old['environment'].pop('BASH_DEFAULT_TIMEOUT_MS')
    old['environment'].pop('BASH_MAX_TIMEOUT_MS')
    before = values._encoded(old)
    assert profiles.profile_name(old) == profiles.PRODUCTION_PROFILE
    assert profiles.require_production(old) is old
    assert values._encoded(values.validate_runtime(old)) == before
    with pytest.raises(ValueError, match='environment'):
        values.validate_runtime_v2(old)
    assert values.validate_runtime_v2(current) == current


def test_real_preparation_refuses_synthetic_before_constructing_selection(runtime, tmp_path, monkeypatch):
    from data_sheets_schema import native_execution_registration_v2 as preparation
    def forbidden(*args, **kwargs):
        pytest.fail('real preparation must refuse before constructing selection')
    monkeypatch.setattr(preparation.selection, 'capture', forbidden)
    path = tmp_path / 'runtime.json'
    path.write_text(json.dumps(runtime))
    with pytest.raises(ValueError, match='real native entry refuses'):
        preparation.prepare('unused', str(path), job_id='unused', run_date='2026-11-09', max_draft_checks=3)


@pytest.mark.parametrize('marker', ['model', 'provider', 'auth', 'profile', 'kind'])
def test_malformed_historical_basis_exception_never_downgrades_synthetic_markers(marker):
    value = {'model': 'other-historical-model', 'limits_basis': '{not previously interpreted'}
    if marker == 'model':
        value['model'] = profiles.SYNTHETIC_REQUESTED
    elif marker == 'provider':
        value['provider'] = profiles.SYNTHETIC_PROVIDER
    elif marker == 'auth':
        value['auth'] = {'subscriptionType': profiles.SYNTHETIC_PROFILE}
    elif marker == 'profile':
        value['limits_basis'] = '{"profile":"synthetic-software-test"'
    else:
        value['limits_basis'] = '{"kind":"' + aliases.KIND + '"'
    with pytest.raises(ValueError):
        aliases.model_aliases(value)


def test_real_registration_refuses_before_observation(runtime, monkeypatch):
    from data_sheets_schema import native_shared_registration_orchestration as registration
    monkeypatch.setattr(registration, '_registration_body', lambda *a, **k: {'runtime': runtime})
    def forbidden(*args, **kwargs):
        pytest.fail('real registration must refuse before observation')
    monkeypatch.setattr(registration, '_observed_envelope', forbidden)
    with pytest.raises(ValueError, match='real native entry refuses'):
        registration.registration('unused', 'unused')


def test_real_launch_refuses_before_loading_guard(runtime, monkeypatch):
    from data_sheets_schema import native_shared_execution_orchestration as execution
    from data_sheets_schema import native_subscription_admission as admission
    monkeypatch.setattr(execution.registration, 'verified', lambda raw: {'runtime': runtime})
    def forbidden(*args, **kwargs):
        pytest.fail('real launch must refuse before loading guard')
    monkeypatch.setattr(admission, 'load_current', forbidden)
    with pytest.raises(ValueError, match='real native entry refuses'):
        execution.launch(b'{}', review_path='unused', ci_path='unused', launch_word_path='unused',
                         subscription_guard_path='unused', subscription_guard_sha256='unused')


def test_real_capture_refuses_before_authority_or_reservation(runtime, tmp_path, monkeypatch):
    from data_sheets_schema import native_subscription_capture as capture
    from data_sheets_schema import native_launch_review as review
    monkeypatch.setattr(review, 'registration_fields', lambda raw: {'runtime': runtime})
    def forbidden(*args, **kwargs):
        pytest.fail('real capture must refuse before authority/reservation')
    monkeypatch.setattr(capture, '_authority', forbidden)
    with pytest.raises(ValueError, match='real native entry refuses'):
        capture.capture_subscription(registration_raw=b'{}', review_bundle_raw=b'{}',
            launch_word_raw=b'{}', directory=str(tmp_path.resolve() / 'capture'))


@pytest.mark.parametrize('entry', ['observation', 'permission'])
def test_real_probe_producers_refuse_synthetic(runtime, entry):
    from data_sheets_schema import native_u4b_probe_sequence as probe
    with pytest.raises(ValueError, match='real native entry refuses'):
        if entry == 'observation':
            probe.produce_observation(b'{}', runtime)
        else:
            probe.produce_bound_probe(b'{}', {'runtime': runtime})
