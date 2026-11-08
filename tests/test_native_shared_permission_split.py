"""D's permission boundary and executable requirements for C round four.

The real C protocol is required. No substitute module, fabricated control
carrier, or historical fallback is installed by these tests.
"""
import ast
import importlib
import inspect
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONSUMER = ROOT / 'src/data_sheets_schema/native_shared_permissions.py'


def test_permission_consumer_has_no_verifier_or_legacy_import_even_deferred():
    tree = ast.parse(CONSUMER.read_text())
    forbidden = {
        'native_execution_registration_v2', 'native_execution_authority_v2',
        'native_execution', 'native_execution_registration', 'native_execution_authority',
        'native_supervisor', 'native_attempt_supervisor', 'native_supervisor_authority',
        'native_attribution_registration', 'native_attribution_controller',
        'native_shared_permission_orchestration',
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.rsplit('.', 1)[-1] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or '').rsplit('.', 1)[-1])
            imported.update(alias.name for alias in node.names)
    assert not imported & forbidden
    assert 'native_shared_permission_protocol' in imported
    assert 'native_shared_runtime_values' in imported


def test_permission_consumer_requires_explicit_current_inputs():
    from data_sheets_schema import native_shared_permissions as consumer
    signature = inspect.signature(consumer.verify_saved_probe)
    assert tuple(signature.parameters) == ('raw_manifest', 'expected', 'controls', 'controller_sources')
    for name in ('expected', 'controls', 'controller_sources'):
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        consumer.verify_saved_probe(b'{}', expected={})


def test_permission_consumer_rejects_lookalike_controls_before_evidence():
    from data_sheets_schema import native_shared_permissions as consumer
    with pytest.raises(ValueError, match='fixed pure-control projection'):
        consumer.verify_saved_probe(b'{}', expected={}, controls={}, controller_sources={})


def test_real_c_permission_protocol_has_the_six_approved_signatures():
    """Intentionally fails until the genuine C-owned implementation lands."""
    protocol = importlib.import_module('data_sheets_schema.native_shared_permission_protocol')
    expected = {
        'history_contract': (),
        'initialization_id': (),
        'policy_digest': ('value',),
        'initialize_frame': ('pretool_control',),
        'hook_output': ('classification', 'basis'),
        'permission_arguments': ('policy',),
    }
    exported_functions = {name for name, value in vars(protocol).items()
                          if not name.startswith('_') and callable(value)}
    assert exported_functions == set(expected)
    for name, parameters in expected.items():
        signature = inspect.signature(getattr(protocol, name))
        assert tuple(signature.parameters) == parameters
        for parameter in signature.parameters.values():
            assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            assert parameter.default is inspect.Parameter.empty


def _source_shape():
    """Parser input only: never executed, loaded or installed as C's module."""
    return (
        'def history_contract():\n    pass\n'
        'def initialization_id():\n    pass\n'
        'def policy_digest(value):\n    pass\n'
        'def initialize_frame(pretool_control):\n    pass\n'
        'def hook_output(classification, basis):\n    pass\n'
        'def permission_arguments(policy):\n    pass\n'
    )


def test_protocol_source_shape_parser_accepts_only_metadata_without_execution(monkeypatch):
    from data_sheets_schema import native_shared_permission_orchestration as orchestration
    import builtins

    def no_execution(*args, **kwargs):
        pytest.fail('source-shape inspection executed code')

    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'exec', no_execution)
        assert orchestration._validate_protocol_source(_source_shape().encode()) is None


@pytest.mark.parametrize('before,after', [
    ('def policy_digest(value):\n    pass\n', ''),
    ('def policy_digest(value):', 'def policy_digest(other):'),
    ('def policy_digest(value):', 'def policy_digest(value=None):'),
    ('def policy_digest(value):', 'def policy_digest(value, /):'),
    ('def policy_digest(value):', 'def policy_digest(*, value):'),
    ('def policy_digest(value):', 'def policy_digest(*value):'),
    ('def policy_digest(value):', 'def policy_digest(**value):'),
    ('def policy_digest(value):', 'async def policy_digest(value):'),
    ('def policy_digest(value):', '@replacement\ndef policy_digest(value):'),
    ('def policy_digest(value):', 'def extra(value):\n    pass\ndef policy_digest(value):'),
    ('def policy_digest(value):', 'def policy_digest(value):\n    pass\ndef policy_digest(value):'),
])
def test_protocol_source_rejects_changed_callable_signature_or_roster(before, after):
    from data_sheets_schema import native_shared_permission_orchestration as orchestration
    source = _source_shape().replace(before, after)
    with pytest.raises(ValueError, match='roster|signature'):
        orchestration._validate_protocol_source(source.encode())


@pytest.mark.parametrize('body', [
    'import data_sheets_schema.native_execution_authority_v2',
    'from .native_execution_registration import validate_runtime',
    'from data_sheets_schema import native_shared_contract',
    'import importlib as loader',
    'from builtins import __import__ as load',
    'from json import *',
    '__import__("data_sheets_schema.native_execution")',
    'load = __import__',
    '__builtins__["__import__"]("data_sheets_schema.native_execution")',
    'getattr(json, "loads")',
    'json.__dict__["__builtins__"]',
    'exec("import data_sheets_schema.native_execution")',
    'loader.import_module("data_sheets_schema.native_execution")',
    'module.__loader__.exec_module(module)',
])
def test_protocol_source_checks_deferred_imports_and_dynamic_loading(body):
    from data_sheets_schema import native_shared_permission_orchestration as orchestration
    source = _source_shape() + 'def _deferred():\n    ' + body + '\n'
    with pytest.raises(ValueError, match='import|loading|reflection'):
        orchestration._validate_protocol_source(source.encode())
