"""#4354 U1 scanner admission controls; offline source copies, 2026-11-06.

The complete v2 render route must derive; missing or altered consumers refuse.
"""
import ast

import pytest

from tests.test_generation_specificity_delegated import ROOT, RUNNER, fixture_root, scan, scopes


def test_native_dispatch_with_caller_docstring_derives_api_scopes():
    result = scopes(ROOT)
    assert result
    selected = scan._delegated_turn_selection(scan._tree(ROOT / RUNNER),
        ast.parse('spec.receipt_completion_version', mode='eval').body, ROOT)
    assert selected['runtime'] == 'api' and selected['cases']
    assert all(case['values']['native_shared_generation_version'] == 0
               for case in selected['cases'])
    assert any('native_shared_render.py:' in citation for citation in selected['evidence'])


@pytest.mark.parametrize('statement', ['pass', 'local = None', 'return None'])
def test_executable_validator_prefix_is_not_ignored(tmp_path, statement):
    root = fixture_root(tmp_path)
    path = root / 'src/data_sheets_schema/native_shared_render.py'
    source = path.read_text()
    marker = "    version = getattr(spec, 'native_shared_generation_version', 0)"
    assert source.count(marker) == 1
    path.write_text(source.replace(marker, '    ' + statement + '\n' + marker))
    with pytest.raises(scan.ConfigError, match='native selector does not reach'):
        scopes(root)


def _native_route_root(tmp_path):
    root = fixture_root(tmp_path)
    for relative in ('cli/prompt.py', 'native_execution_registration_v2.py',
                     'native_shared_controller.py'):
        path = root / 'src/data_sheets_schema' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / 'src/data_sheets_schema' / relative).read_bytes())
    return root


def test_native_complete_v2_route_derives():
    route = scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))
    assert route['cli'] == 'd4d prompt render-native-shared'
    assert route['enabled_values'] == [1]
    assert route['renderer'] == 26
    assert route['api_execute'] == 'refused before dry-run, locks or dispatch'
    assert route['model_calls_minimum'] is None
    assert any('native_execution_registration_v2.py:' in row for row in route['evidence'])


def test_native_route_requires_later_cli_consumer(tmp_path):
    root = _native_route_root(tmp_path)
    path = root / 'src/data_sheets_schema/cli/prompt.py'
    tree = ast.parse(path.read_text())
    tree.body = [n for n in tree.body if not isinstance(n, ast.FunctionDef)
                 or n.name != 'render_native_shared']
    path.write_text(ast.unparse(tree))
    with pytest.raises(scan.ConfigError, match='missing offline render CLI consumer'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


@pytest.mark.parametrize('relative,before,after', [
    ('cli/prompt.py', 'preparation.prepare(selection, runtime_declaration,', 'preparation.prepare(runtime_declaration, selection,'),
    ('cli/prompt.py', "text = body['instruction']", "text = 'unrelated instruction'"),
    ('cli/prompt.py', "destination.open('x'", "destination.open('w'"),
    ('native_execution_registration_v2.py', '_require_registered_input_spellings(spec)', 'pass'),
    ('native_execution_registration_v2.py', 'native_shared_generation_version=1', 'native_shared_generation_version=0'),
    ('native_execution_registration_v2.py', 'spec._native_shared_runtime_capture = runtime_capture', 'spec._native_shared_runtime_capture = None'),
    ('native_execution_registration_v2.py', 'instruction = spec.instruction', "instruction = 'unrelated instruction'"),
    ('native_execution_registration_v2.py', 'from . import native_shared_selection as selection', 'from . import native_shared_contract as selection'),
])
def test_native_v2_route_rejects_changed_producer(tmp_path, relative, before, after):
    root = _native_route_root(tmp_path)
    # Calibrate each mutation against the actual complete route.
    assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
    path = root / 'src/data_sheets_schema' / relative
    source = path.read_text()
    assert before in source
    path.write_text(source.replace(before, after, 1))
    with pytest.raises(scan.ConfigError, match='v2'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_native_route_cannot_omit_bc1_exclusion(tmp_path):
    root = fixture_root(tmp_path)
    path = root / 'src/data_sheets_schema/native_shared_render.py'
    source = path.read_text()
    marker = ",\n                'bounded_carry_version'):"
    assert source.count(marker) == 1
    path.write_text(source.replace(marker, "):", 1))
    with pytest.raises(scan.ConfigError, match='unsupported delegated admission prefix'):
        scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_only_leading_literal_docstring_is_ignored():
    body = ast.parse('"contract"\npass\n"not a docstring"').body
    result = scan._without_docstring(body)
    assert len(result) == 2 and isinstance(result[0], ast.Pass)
    assert result[1] is body[2]


@pytest.mark.parametrize('replacement', ['pass', '_require_registered_input_spellings(other)',
                                       '_require_registered_input_spellings(spec)\n    local = None'])
def test_phase_prefix_cannot_gain_unproved_work(tmp_path, replacement):
    root = fixture_root(tmp_path)
    path = root / RUNNER
    source = path.read_text()
    start = source.index('def build_phase(')
    before, after = source[:start], source[start:]
    after = after.replace('    _require_registered_input_spellings(spec)', '    ' + replacement, 1)
    path.write_text(before + after)
    with pytest.raises(scan.ConfigError, match='phase input invariant|prompt/phase route'):
        scan.derive_native_shared_route(root, scan._tree(path))
