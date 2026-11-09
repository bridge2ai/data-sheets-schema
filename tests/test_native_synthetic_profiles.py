"""U3-J2 closed software-test profile refusals; never invoke a native binary."""
from copy import deepcopy
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
    raw = ('#!' + sys.executable + '\n').encode() + body
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
            'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'},
        'deadline_seconds': 900, 'budget_guard_usd': '1.0',
        'keep_awake': {'policy': 'not_applicable', 'host_platform': sys.platform,
            'basis': 'Ordinary Python software test; no native acceptance'}}


def test_explicit_synthetic_profile_is_distinct_and_preserves_900_180(runtime):
    original = deepcopy(runtime)
    assert profiles.require_synthetic(runtime) == original
    assert values.validate_runtime_v2(runtime) == original
    assert profiles.profile_name(runtime) == profiles.SYNTHETIC_PROFILE
    assert aliases.model_aliases(runtime) == {
        'requested': profiles.SYNTHETIC_REQUESTED, 'returned': profiles.SYNTHETIC_RETURNED}
    assert runtime == original
    assert runtime['deadline_seconds'] == 900
    raw = Path(runtime['executable']['path']).read_bytes()
    assert b'timeout=180)' in raw
    assert hashlib.sha256(raw.split(b'\n', 1)[1]).hexdigest() == profiles.SYNTHETIC_PEER_SHA256
    with pytest.raises(ValueError, match='first-party'):
        values.validate_runtime(runtime)


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
    before = values._encoded(old)
    assert profiles.profile_name(old) == profiles.PRODUCTION_PROFILE
    assert profiles.require_production(old) is old
    assert values._encoded(values.validate_runtime(old)) == before
    assert values._encoded(values.validate_runtime_v2(old)) == before


def test_real_preparation_refuses_synthetic_before_constructing_selection(runtime, tmp_path, monkeypatch):
    from data_sheets_schema import native_execution_registration_v2 as preparation
    def forbidden(*args, **kwargs):
        pytest.fail('real preparation must refuse before constructing selection')
    monkeypatch.setattr(preparation, '_prepare', forbidden)
    path = tmp_path / 'runtime.json'
    path.write_text(json.dumps(runtime))
    with pytest.raises(ValueError, match='real native entry refuses'):
        preparation.prepare('unused', str(path), job_id='unused', run_date='2026-11-09', max_draft_checks=3)


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
