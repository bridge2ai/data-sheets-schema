"""Additive native authority admission; no native binary or provider calls (#5508)."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from data_sheets_schema import native_attribution_controller as v1
from data_sheets_schema import native_attribution_controller_v2 as v2
from data_sheets_schema import native_attribution_registration as old
from data_sheets_schema import native_attribution_registration_v2 as new
from data_sheets_schema import native_supervisor_authority_v2 as authority
from tests.test_native_attribution_controller import selected
from tests.test_native_source_attribution import case
from tests.test_source_attribution_preflight import inputs


@pytest.fixture
def isolated(selected):
    names = set(json.loads((v2.ROOT / v2.SOURCES_PATH).read_bytes())['modules']) | set(authority.ADDITIONAL)
    previous = {name: sys.modules.pop(name, None) for name in names}
    old_path = list(sys.path)
    try:
        yield selected
    finally:
        sys.path[:] = old_path
        for name, module in previous.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


def test_v2_registration_composition_and_supervisor(isolated):
    spec, old_raw, _, instruction, _ = isolated
    raw = new._encoded(new.registration(spec))
    assert new.verified(raw)[1]['schema_version'] == 2
    composition = v2.composition(raw, instruction)
    assert v2.verified_composition(new._encoded(composition)) == composition
    identity = authority.dependency_identity()
    assert identity['authority_version'] == 2
    assert identity['package_sources'] == new._code_pins()
    with authority.loaded_dependencies(identity) as modules:
        assert modules['prepare_registration'].__file__.endswith('prepare_registration_v2.py')
        assert modules['prepare_direct'].__file__.endswith('prepare_direct_v2.py')
    with pytest.raises(ValueError):
        new.verified(old_raw)
    with pytest.raises(ValueError):
        old.verified(raw)


def test_cross_version_manifest_and_source_bytes_refuse(isolated, monkeypatch, tmp_path):
    monkeypatch.setattr(v1, 'SOURCES_PATH', v2.SOURCES_PATH)
    with pytest.raises(ValueError, match='manifest changed'):
        v1.controller_sources()
    monkeypatch.setattr(v2, 'SOURCES_PATH', Path('src/data_sheets_schema/native_controller_sources_v1.json'))
    with pytest.raises(ValueError, match='manifest changed'):
        v2.controller_sources()


def test_v2_registration_cannot_name_v1(isolated):
    spec = isolated[0]
    value = new.registration(spec)
    value['controller_authority'] = {'version': 1, 'manifest': str(v1.SOURCES_PATH),
                                    'sha256': v1.SOURCES_SHA256, 'sources': v1.controller_sources()}
    with pytest.raises(ValueError, match='registration differs'):
        new.verified(new._encoded(value))


@pytest.mark.parametrize('changed_source', [
    'native_attribution_controller_v2.py', 'native_supervisor_authority_v2.py', 'api_runner.py'])
def test_package_and_supervisor_mutation_refuse(isolated, monkeypatch, changed_source):
    spec = isolated[0]
    raw = new._encoded(new.registration(spec))
    identity = authority.dependency_identity()
    pins = new._code_pins()
    pins['src/data_sheets_schema/' + changed_source] = '0'*64
    monkeypatch.setattr(new, '_code_pins', lambda: pins)
    with pytest.raises(ValueError, match='checker identity'):
        new.verified(raw)
    with pytest.raises(ValueError, match='dependency identity'):
        with authority.loaded_dependencies(identity):
            pytest.fail('mutated package was admitted')


def test_preparer_mutation_refuses_before_import(isolated, monkeypatch):
    real_sha = new._sha
    helper = (v2.ROOT/'notes/matched_cborg_2026-09-13/prepare_registration_v2.py').read_bytes()
    monkeypatch.setattr(new, '_sha', lambda raw: '0'*64 if raw == helper else real_sha(raw))
    with pytest.raises(ValueError, match='frozen native controller bytes changed'):
        v2.load_controls()


def test_v1_fixture_still_reconstructs_in_current_environment(selected):
    _, raw, _, _, composition = selected
    assert old.verified(raw)[1]['schema_version'] == 1
    assert v1.verified_composition(composition)['version'] == 1


def test_explicit_preparer_arguments(isolated):
    identity = authority.dependency_identity()
    with authority.loaded_dependencies(identity) as modules:
        direct = modules['prepare_direct'].parser()
        with pytest.raises(SystemExit):
            direct.parse_args(['--output', '/unused'])
        assert direct.parse_args(['--output', '/unused', '--project', 'NEUTRAL']).project == 'NEUTRAL'
        parser = modules['prepare_registration'].build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])
        args = parser.parse_args(['--projects', 'NEUTRAL', '--canary-order', 'NEUTRAL_agentic_rep2'])
        job = modules['prepare_registration'].new_job({'project': 'NEUTRAL'}, 'NEUTRAL_agentic_rep2',
            'agentic', 'Claude Code', 'claudecode_agent', 2, args)
        assert job['canary'] is True
        job = modules['prepare_registration'].new_job({'project': 'NEUTRAL'}, 'NEUTRAL_agentic_rep1',
            'agentic', 'Claude Code', 'claudecode_agent', 1, args)
        assert job['canary'] is False


def test_direct_preparation_pins_selected_version(isolated, tmp_path, monkeypatch):
    with authority.loaded_dependencies(authority.dependency_identity()) as modules:
        direct = modules['prepare_direct']
        for name in direct.FORBIDDEN_ENVIRONMENT:
            monkeypatch.delenv(name, raising=False)
        fake = tmp_path/'synthetic-version-only'
        fake.write_text("#!/bin/sh\necho '2.1.272 (Claude Code)'\n")
        fake.chmod(0o700)
        monkeypatch.setattr(direct, 'auth_evidence', lambda *args: {
            'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
            'subscriptionType': 'synthetic-fixture'})
        args = direct.parser().parse_args(['--project', 'CHORUS', '--output', str(tmp_path/'direct'),
            '--claude-executable', str(fake), '--cohort', 'authority_v2_offline_test'])
        value = json.loads(direct.build(args).read_bytes())
        pins = value['pinned_files']
        helper = v2.ROOT/'notes/matched_cborg_2026-09-13/prepare_registration_v2.py'
        assert pins[str(helper)] == new._sha(helper.read_bytes())
        assert str(helper.with_name('prepare_registration.py')) not in pins
        assert str(v2.ROOT/'notes/claudecode_direct/prepare_direct_v2.py') in pins


@pytest.mark.parametrize('mode', ['standalone', 'mixed'])
def test_standalone_direct_cli_selects_only_v2(mode):
    subprocess.run([sys.executable, '-B', str(v2.ROOT/'tests/fixtures/native_authority_v2_import.py'),
                    str(v2.ROOT), mode], check=True, timeout=30)
