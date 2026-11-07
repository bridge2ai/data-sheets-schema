"""Round-3 review regressions; offline synthetic consumers, 2026-11-07."""
from copy import deepcopy
import inspect
import json
import sys
from types import ModuleType

import pytest

from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_contract as c
from tests.test_native_execution_verified_loader_v2 import graph_fixture, pin
from tests.test_native_execution_ci_v2 import (
    ci_evidence, local_ci_git, fabricated_authorizations, _event_records, _write,
    _authorization_kwargs, REPOSITORY_URL,
)

authority = registration.authority
NAME = 'data_sheets_schema.native_shared_registration'


def test_source_in_rows_accepts_github_shaped_check_runs(ci_evidence):
    raw, value, original, paths, local = ci_evidence
    records = _event_records(original, 'pull_request', local)
    # Synthetic API-shaped objects: head_sha belongs to the PR head; Actions'
    # tested merge is a separate declaration, not a fabricated check-run field.
    response = {'total_count': len(records['ci']['checks']), 'check_runs': [
        {'id': index, 'name': name, 'head_sha': local['source'],
         'status': 'completed', 'conclusion': 'success',
         'details_url': REPOSITORY_URL + '/actions/runs/1/job/' + str(index),
         'check_suite': {'id': 99, 'head_sha': local['source']},
         'app': {'slug': 'github-actions'}}
        for index, name in enumerate(records['ci']['checks'], 1)]}
    records['ci']['checks'] = {row['name']: {key: row[key] for key in
        ('head_sha', 'status', 'conclusion', 'details_url')} for row in response['check_runs']}
    assert records['ci']['tested_commit'] != local['source']
    _write(records, paths)
    assert registration._authorizations(raw, value, **_authorization_kwargs(paths))['ci'].raw == paths['ci'].read_bytes()


def test_package_guard_census_admits_shared_and_u2_dependencies(record_property):
    pins = authority.dependency_identity()['base']['package_sources']
    outcomes = {}
    for relative in sorted(pins):
        if not relative.endswith('.py'):
            continue
        name = relative[4:-3].replace('/', '.')
        if name.endswith('.__init__'):
            name = name[:-9]
        raw = (authority.ROOT / relative).read_bytes()
        if name == 'data_sheets_schema' or not raw:
            continue
        try:
            authority.refuse_legacy_consumer_imports(raw, name=name, package_sources=pins)
        except ValueError as exc:
            outcomes[name] = str(exc)
        else:
            outcomes[name] = 'accepted'
    record_property('guard_census', json.dumps(outcomes, sort_keys=True))
    for name in ('api_runner', 'native_shared_selection', 'native_attribution_controller_v2',
                 'native_attribution_registration_v2', 'native_supervisor_authority_v2'):
        assert outcomes['data_sheets_schema.' + name] == 'accepted'


@pytest.mark.parametrize('source', [
    b'from .native_execution_registration_v2 import selection\n',
    b'import data_sheets_schema.native_execution_registration_v2 as boundary\n',
    b'from . import native_execution_authority_v2\n',
])
def test_verifier_attribute_import_bypass_refuses(tmp_path, monkeypatch, source):
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: source})
    with pytest.raises(ValueError, match='cannot import verifier bootstrap boundary'):
        authority.refuse_legacy_consumer_imports(source, name=NAME, package_sources=pins)


@pytest.mark.parametrize('statement', [
    'import data_sheets_schema.synthetic_dependency as dependency',
    'from . import synthetic_dependency as dependency',
    'from .synthetic_dependency import value',
])
def test_every_import_form_replaces_cached_dependency(tmp_path, monkeypatch, statement):
    child = 'data_sheets_schema.synthetic_dependency'
    expression = 'value' if statement.endswith('import value') else 'dependency.value'
    source = (statement + '\nresult = ' + expression + '\n').encode()
    dependency = b'value = "verified source"\ncompile("1", "legitimate", "eval")\n'
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: source, child: dependency})
    cached = ModuleType(child)
    cached.value = 'unverified cached module'
    monkeypatch.setitem(sys.modules, child, cached)
    with authority.verified_source_module(NAME, path=tmp_path / 'src/data_sheets_schema/native_shared_registration.py',
            raw=source, sha256=pin(source), package_sources=pins) as module:
        assert module.result == 'verified source'
        assert authority.module_source_identity(sys.modules[child])['sha256'] == pin(dependency)
    assert sys.modules[child] is cached


def test_deep_v1_import_refuses_before_loading(tmp_path, monkeypatch):
    source = b'from . import first\n'
    pins = graph_fixture(tmp_path, monkeypatch, {
        NAME: source, 'data_sheets_schema.first': b'from .second import value\n',
        'data_sheets_schema.second': b'from .native_execution_registration import verified\n'})
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        authority.refuse_legacy_consumer_imports(source, name=NAME, package_sources=pins)


def test_deferred_dependency_v1_import_refuses_when_called(tmp_path, monkeypatch):
    source = b'from .first import deferred\n'
    legacy = 'data_sheets_schema.native_execution_registration'
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: source,
        'data_sheets_schema.first': b'def deferred():\n    from .native_execution_registration import verified\n    return verified\n',
        legacy: b'def verified(): pass\n'})
    monkeypatch.setitem(sys.modules, legacy, ModuleType(legacy))
    with authority.verified_source_module(NAME,
            path=tmp_path / 'src/data_sheets_schema/native_shared_registration.py',
            raw=source, sha256=pin(source), package_sources=pins) as module:
        with pytest.raises(ValueError, match='forbidden v1 execution authority'):
            module.deferred()


@pytest.mark.parametrize('target', ['synthetic_dynamic', 'native_execution_registration'])
def test_dependency_runtime_import_is_source_loaded_or_v1_refused(tmp_path, monkeypatch, target):
    source = b'from .first import result\n'
    child = 'data_sheets_schema.' + target
    dependency = ('import importlib\nresult = importlib.import_module(' + repr(child) + ')\n').encode()
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: source,
        'data_sheets_schema.first': dependency, child: b'value = "pinned dynamic dependency"\n'})
    cached = ModuleType(child)
    monkeypatch.setitem(sys.modules, child, cached)
    context = authority.verified_source_module(NAME,
        path=tmp_path / 'src/data_sheets_schema/native_shared_registration.py',
        raw=source, sha256=pin(source), package_sources=pins)
    if target == 'native_execution_registration':
        with pytest.raises(ValueError, match='forbidden v1 execution authority'), context:
            pytest.fail('runtime v1 import was admitted')
    else:
        with context as module:
            assert module.result.value == 'pinned dynamic dependency'
            assert authority.module_source_identity(module.result)['sha256'] == pins['src/' + child.replace('.', '/') + '.py']
    assert sys.modules[child] is cached


@pytest.mark.parametrize('source', [
    b'import sys\ndef echo():\n    return sys._getframe(1).f_locals["body"]\n',
    b'import inspect as i\nframe = i.currentframe()\n',
    b'from sys import modules as loaded\nvalue = loaded["anything"]\n',
    b'import sys\nvalue = sys.modules\n',
    b'def f(): pass\nf.__signature__ = None\n',
])
def test_consumer_owned_introspection_lint(tmp_path, monkeypatch, source):
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: source})
    with pytest.raises(ValueError, match='lint forbids introspection or signature assignment'):
        authority.refuse_legacy_consumer_imports(source, name=NAME, package_sources=pins)


def test_assigned_signature_cannot_spoof_interface():
    module = ModuleType(NAME)
    def forwarding(*args, **kwargs):
        return kwargs
    forwarding.__module__ = NAME
    forwarding.__signature__ = inspect.Signature([
        inspect.Parameter('body', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter('fresh', inspect.Parameter.KEYWORD_ONLY),
        inspect.Parameter('extra_protected', inspect.Parameter.KEYWORD_ONLY)])
    module.execution_paths_v2 = forwarding
    with pytest.raises(ValueError, match='consumer interface mismatch'):
        registration._signature(module, 'execution_paths_v2', ('body',), ('fresh', 'extra_protected'))


def test_wire_commit_proof_precedes_any_helper_loading(monkeypatch):
    value = {'authority_version': 2,
        'controller_sources_sha256': authority.neutral.composition.SOURCES_SHA256,
        'registration': {'schema_version': 2}}
    identity = {'uncommitted': 'fixture'}
    monkeypatch.setattr(authority, 'dependency_identity', lambda: deepcopy(identity))
    observed = []
    def refuse(actual):
        assert actual == identity
        observed.append('commit proof')
        raise ValueError('uncommitted fixture refused')
    monkeypatch.setattr(authority, 'require_committed', refuse)
    monkeypatch.setattr(authority, 'loaded_dependencies',
        lambda *args: pytest.fail('helper code ran before commit proof'))
    with pytest.raises(ValueError, match='uncommitted fixture refused'):
        registration._wire(c.canonical(value))
    assert observed == ['commit proof']
