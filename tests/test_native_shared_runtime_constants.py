"""Neutral U1 render constants: value parity without changing frozen v1."""
import ast
from pathlib import Path

import pytest

from data_sheets_schema import native_execution_registration as legacy
from data_sheets_schema import native_shared_contract as contract
from data_sheets_schema import native_shared_render as render
from data_sheets_schema import native_shared_runtime_constants as constants


def _runtime():
    value = dict.fromkeys(constants.RUNTIME_KEYS)
    value.update(route=constants.ROUTE, model='synthetic-model', provider='synthetic-provider',
                 effort='high', limits={'contextWindow': 4096, 'maxOutputTokens': 512})
    return value


def test_neutral_runtime_constants_equal_frozen_v1_values():
    assert type(constants.ROUTE) is type(legacy.ROUTE) is str
    assert constants.ROUTE == legacy.ROUTE
    assert type(constants.RUNTIME_KEYS) is type(legacy.RUNTIME_KEYS) is set
    assert constants.RUNTIME_KEYS == legacy.RUNTIME_KEYS
    assert constants.RUNTIME_KEYS is not legacy.RUNTIME_KEYS


def test_render_runtime_uses_neutral_values_without_v1_import():
    tree = ast.parse(Path(render.__file__).read_bytes())
    runtime = next(node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == '_runtime')
    imported = [node for node in ast.walk(runtime) if isinstance(node, ast.ImportFrom)]
    assert len(imported) == 1
    assert imported[0].module == 'native_shared_runtime_constants'
    assert {alias.name for alias in imported[0].names} == {'ROUTE', 'RUNTIME_KEYS'}
    value = _runtime()
    assert render._runtime(contract.canonical(value), 'synthetic-provider', 'high') == value


@pytest.mark.parametrize('change', ['missing', 'extra', 'route', 'provider', 'effort', 'limits'])
def test_neutral_extraction_keeps_render_runtime_refusals(change):
    value = _runtime()
    if change == 'missing':
        value.pop('auth')
    elif change == 'extra':
        value['foreign'] = True
    elif change == 'limits':
        value['limits']['maxOutputTokens'] = value['limits']['contextWindow'] + 1
    else:
        value[change] = 'foreign'
    with pytest.raises(ValueError):
        render._runtime(contract.canonical(value), 'synthetic-provider', 'high')
