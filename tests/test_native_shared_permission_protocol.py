"""C's six pure functions against the pinned, unedited historical oracle.

No native executable, provider, launcher or permission probe is invoked.
Successful results are byte comparisons; unknown-contract refusal deliberately
uses ValueError instead of importing the historical BudgetStop class.
"""
import ast
from copy import deepcopy
import inspect
import hashlib
import json
from pathlib import Path
import sys

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_permission_protocol as protocol
from data_sheets_schema import native_shared_permission_protocol_orchestration as orchestration
from tests.test_native_execution_authority_v2 import isolated_modules


# native_control.py rotated for the #6094 controller timing hooks (lead, 2026-11-13).
# Only the NativeControl class changed; CONTRACT, HISTORY_CONTRACT, INIT_ID, digest,
# initialize_frame and hook_output, which these tests compare, are byte-identical to
# the e53f9627 oracle (AST comparison of every top-level definition).
CONTROL_SHA = '25fa83e2bae763fccb378d6a041b1a2d02843c1d03c0e4fef6ded64c63fc2488'
POLICY_SHA = '99db1879752ea73fea0002ea5a3a2d8333365b4e3843abdab3e1a1f0008709cc'
PROTOCOL_NAME = 'data_sheets_schema.native_shared_permission_protocol'
PROTOCOL_PATH = 'src/data_sheets_schema/native_shared_permission_protocol.py'
SIGNATURES = {
    'history_contract': (), 'initialization_id': (), 'policy_digest': ('value',),
    'initialize_frame': ('pretool_control',), 'hook_output': ('classification', 'basis'),
    'permission_arguments': ('policy',),
}


def _wire(value):
    # Retain insertion order: a different frame/argv ordering is a parity failure.
    return json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode('utf-8')


@pytest.fixture
def historical(isolated_modules):
    identity = authority.dependency_identity()
    assert identity['base']['modules']['native_control']['sha256'] == CONTROL_SHA
    assert identity['base']['modules']['native_command_policy']['sha256'] == POLICY_SHA
    with authority.loaded_dependencies(identity):
        control, policy = sys.modules['native_control'], sys.modules['native_command_policy']
        assert authority.module_source_identity(control)['sha256'] == CONTROL_SHA
        assert authority.module_source_identity(policy)['sha256'] == POLICY_SHA
        yield control, policy, sys.modules['budgeted_cborg'].BudgetStop


def test_history_contract_and_initialization_frames_match_pinned_bytes(historical):
    control, _, _ = historical
    assert _wire(protocol.history_contract()) == _wire(control.HISTORY_CONTRACT)
    assert protocol.initialization_id() == control.INIT_ID
    for contract in (None, control.CONTRACT, control.HISTORY_CONTRACT,
                     dict(reversed(list(control.HISTORY_CONTRACT.items())))):
        before = deepcopy(contract)
        assert _wire(protocol.initialize_frame(contract)) == _wire(control.initialize_frame(contract))
        assert contract == before
    first = protocol.history_contract()
    first['version'] = -1
    first['extra'] = 'caller owned'
    assert _wire(protocol.history_contract()) == _wire(control.HISTORY_CONTRACT)
    frame = protocol.initialize_frame(protocol.history_contract())
    frame['request']['hooks']['PreToolUse'][0]['hookCallbackIds'].append('foreign')
    assert _wire(protocol.initialize_frame(protocol.history_contract())) == _wire(
        control.initialize_frame(control.HISTORY_CONTRACT))


def test_policy_digest_matches_pinned_sorted_ascii_json(historical):
    control, _, _ = historical
    values = [{}, {'z': 1, 'a': ['é', '東京', '😀', '\\', '\n']},
              {'nested': {'b': False, 'a': None}, 'mixed': [1, 1.0, True]},
              control.CONTRACT, control.HISTORY_CONTRACT]
    for value in values:
        before = deepcopy(value)
        assert protocol.policy_digest(value) == control.digest(value)
        assert value == before
    first = {'z': 'é', 'a': 1}
    second = {'a': 1, 'z': 'é'}
    assert protocol.policy_digest(first) == protocol.policy_digest(second)
    # A UTF-8/non-ASCII canonicalizer would yield a different digest here.
    utf8_digest = hashlib.sha256(json.dumps(first, ensure_ascii=False, sort_keys=True,
                                           separators=(',', ':')).encode()).hexdigest()
    assert protocol.policy_digest(first) != utf8_digest


def test_hook_frames_and_permission_argv_match_pinned_bytes(historical):
    control, policy, _ = historical
    for classification, basis in [('prescribed', 'ignored'), ('not_prescribed', 'é 東京'),
                                  ('refused', 'quoted "text" and \\path\nline')]:
        assert _wire(protocol.hook_output(classification, basis)) == _wire(
            control.hook_output(classification, basis))
    for rules in ([], ['Read', 'Write'], ['Write', 'Read', 'Write'],
                  ['Bash(python -c "print(é)")', 'Read(東京/*)', 'Bash(a\\(b\\))']):
        declaration = {'allowed_tools': list(rules), 'unrelated': 'not serialized'}
        before = deepcopy(declaration)
        actual = protocol.permission_arguments(declaration)
        assert _wire(actual) == _wire(policy.permission_arguments(declaration))
        assert json.loads(actual[-1]) == {'permissions': {'allow': rules}}
        assert actual[:3] == ['--input-format', 'stream-json', '--settings']
        assert declaration == before


def test_unknown_contracts_preserve_refusal_without_legacy_exception_import(historical):
    control, _, BudgetStop = historical
    changed = deepcopy(control.HISTORY_CONTRACT)
    changed['version'] = True
    extra = {**control.HISTORY_CONTRACT, 'extra': None}
    missing = deepcopy(control.HISTORY_CONTRACT)
    missing.pop('matcher')
    wrong_type = {**control.HISTORY_CONTRACT, 'initialize_timeout_seconds': 30.0}
    for contract in ({}, [], 'history', changed, extra, missing, wrong_type,
                     {**control.HISTORY_CONTRACT, 'event': object()}):
        with pytest.raises(BudgetStop, match='^missing or changed native control contract$'):
            control.initialize_frame(contract)
        with pytest.raises(ValueError, match='^missing or changed native control contract$'):
            protocol.initialize_frame(contract)


def test_protocol_has_exact_six_signatures_and_self_contained_private_imports():
    exported = {name for name, value in vars(protocol).items()
                if not name.startswith('_') and callable(value)}
    assert exported == set(SIGNATURES)
    for name, parameters in SIGNATURES.items():
        function = vars(protocol)[name]
        assert function.__module__ == PROTOCOL_NAME
        signature = inspect.signature(function, follow_wrapped=False)
        assert tuple(signature.parameters) == parameters
        assert all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
                   and p.default is inspect.Parameter.empty
                   for p in signature.parameters.values())
    tree = ast.parse(Path(protocol.__file__).read_bytes())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name in {'copy', 'hashlib', 'json'} and alias.asname
                       and alias.asname.startswith('_') for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 and node.module in {'__future__', 'copy', 'hashlib', 'json'}
            assert all(alias.name != '*' and (node.module == '__future__'
                       or alias.asname and alias.asname.startswith('_')) for alias in node.names)


def test_protocol_is_in_package_digest_closure_and_loaded_from_exact_source(isolated_modules):
    identity = authority.dependency_identity()
    digest = identity['base']['package_sources'][PROTOCOL_PATH]
    path = authority.ROOT / PROTOCOL_PATH
    raw = authority._verified_source_bytes(path, digest)
    graph = authority.refuse_legacy_consumer_imports(
        raw, name=PROTOCOL_NAME, package_sources=identity['base']['package_sources'])
    assert graph == {PROTOCOL_NAME: digest}
    previous = sys.modules.get(PROTOCOL_NAME)
    with authority.verified_source_module(PROTOCOL_NAME, path=path, raw=raw, sha256=digest) as loaded:
        assert loaded is not previous
        assert authority.module_source_identity(loaded) == {
            'name': PROTOCOL_NAME, 'path': str(path), 'sha256': digest}
        assert loaded.__cached__ is None
        assert loaded.history_contract() == protocol.history_contract()
    assert sys.modules.get(PROTOCOL_NAME) is previous


def test_real_protocol_projection_checks_lifetime_and_exact_signatures(isolated_modules):
    identity = authority.dependency_identity()
    with orchestration.loaded_protocol(identity) as projected:
        for name, parameters in SIGNATURES.items():
            signature = inspect.signature(getattr(projected, name))
            assert tuple(signature.parameters) == parameters
        assert projected.history_contract() == protocol.history_contract()
        assert projected.initialization_id() == protocol.initialization_id()
        assert projected.policy_digest({'é': 1}) == protocol.policy_digest({'é': 1})
        assert projected.initialize_frame(None) == protocol.initialize_frame(None)
        assert projected.hook_output('prescribed', 'basis') == {}
        assert projected.permission_arguments({'allowed_tools': ['Read']}) == (
            protocol.permission_arguments({'allowed_tools': ['Read']}))
        retained = projected.history_contract
    with pytest.raises(ValueError, match='scope is closed'):
        retained()


@pytest.fixture
def protocol_source(tmp_path, monkeypatch):
    """Actual source-loader path with a private copy; never edit the checkout.

    These fixtures test loader refusals, not committed execution admission.
    A's exact byte loader and the production C validation stay unmodified.
    """
    original = Path(protocol.__file__).read_bytes()
    root = tmp_path / 'protocol-source'
    path = root / PROTOCOL_PATH
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(authority, 'ROOT', root)

    def create(raw=original):
        path.write_bytes(raw)
        return {'base': {'package_sources': {PROTOCOL_PATH: hashlib.sha256(raw).hexdigest()}}}
    return original, path, create


@pytest.mark.parametrize('change', ['missing', 'extra', 'default', 'keyword_only',
                                  'positional_only', 'wrong_name', 'deferred_import',
                                  'public_import', 'dynamic_import'])
def test_protocol_loader_refuses_changed_signature_roster_or_imports(protocol_source, change):
    original, _, create = protocol_source
    replacements = {
        'missing': (b'def policy_digest(value):', b'def _policy_digest(value):'),
        'extra': (b'def policy_digest(value):', b'def extra():\n    return None\n\ndef policy_digest(value):'),
        'default': (b'def policy_digest(value):', b'def policy_digest(value=None):'),
        'keyword_only': (b'def policy_digest(value):', b'def policy_digest(*, value):'),
        'positional_only': (b'def policy_digest(value):', b'def policy_digest(value, /):'),
        'wrong_name': (b'def policy_digest(value):', b'def policy_digest(other):'),
        'deferred_import': (b'def history_contract():',
            b'def history_contract():\n    import data_sheets_schema.native_execution_authority_v2'),
        'public_import': (b'import json as _json', b'import json'),
        'dynamic_import': (b'def history_contract():',
            b'def history_contract():\n    __builtins__["__import__"]("os")'),
    }
    raw = original.replace(*replacements[change])
    assert raw != original
    identity = create(raw)
    with pytest.raises(ValueError, match='roster|signature|private imports|dynamic loading'):
        with orchestration.loaded_protocol(identity):
            pytest.fail('invalid protocol was exposed to a consumer')


@pytest.mark.parametrize('change', ['missing_pin', 'digest', 'source'])
def test_protocol_loader_refuses_substituted_source_or_pin(protocol_source, change):
    original, path, create = protocol_source
    identity = create()
    if change == 'missing_pin':
        identity['base']['package_sources'].clear()
    elif change == 'digest':
        identity['base']['package_sources'][PROTOCOL_PATH] = '0' * 64
    else:
        path.write_bytes(original + b'\n# source replaced after capture\n')
    with pytest.raises(ValueError, match='declared source closure|source bytes differ from their pin'):
        with orchestration.loaded_protocol(identity):
            pytest.fail('substituted source or pin reached the consumer')


@pytest.mark.parametrize('change', ['missing', 'extra', 'signature', 'function', 'constant', 'source'])
def test_protocol_projection_refuses_mutation_before_use(protocol_source, change):
    original, path, create = protocol_source
    identity = create()
    with pytest.raises(ValueError, match='identity or callable code changed|signature differs|constant changed|source bytes differ'):
        with orchestration.loaded_protocol(identity) as projected:
            module = sys.modules[PROTOCOL_NAME]
            if change == 'missing':
                del module.hook_output
            elif change == 'extra':
                module.extra = module.hook_output
            elif change == 'signature':
                module.policy_digest.__defaults__ = (None,)
            elif change == 'function':
                module.hook_output = lambda classification, basis: {}
            elif change == 'constant':
                # Equal by Python numeric equality; distinct by the JSON contract.
                module._HISTORY_CONTRACT['version'] = 3.0
            else:
                path.write_bytes(original + b'\n# changed during source scope\n')
            projected.history_contract()


def test_protocol_projection_rechecks_successful_call_after_midcall_function_mutation(protocol_source):
    _, _, create = protocol_source
    with pytest.raises(ValueError, match='identity or callable code changed'):
        with orchestration.loaded_protocol(create()) as projected:
            module = sys.modules[PROTOCOL_NAME]

            class MutatingRules(dict):
                def __getitem__(self, key):
                    module.hook_output = lambda classification, basis: {}
                    return super().__getitem__(key)

            # The original source-defined permission_arguments executes normally,
            # but its argument mutates another protocol function during the call.
            projected.permission_arguments(MutatingRules(allowed_tools=['Read']))
            pytest.fail('mid-call protocol mutation escaped the after-call check')
