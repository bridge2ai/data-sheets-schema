"""#4354 U1 scanner admission controls; offline source copies, 2026-11-06.

The installed offline CLI is source-derived separately from execution admission.
A copied source fixture without that consumer must still fail explicitly.
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


def test_native_route_derives_actual_offline_v2_cli_consumer():
    result = scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))
    assert result['cli'] == 'd4d prompt render-native-shared'
    assert result['enabled_values'] == [1] and result['renderer'] == 26
    assert result['runtime_binding']['path'].endswith('/native_execution_registration_v2.py')
    assert 'separate acceptance gates' in result['runtime_binding']['basis']
    assert any(row.startswith('src/data_sheets_schema/cli/prompt.py:') for row in result['evidence'])
    assert any(row.startswith('src/data_sheets_schema/native_execution_registration_v2.py:')
               for row in result['evidence'])


def test_native_route_refuses_explicit_missing_cli_consumer(tmp_path):
    root = fixture_root(tmp_path)
    relative = 'src/data_sheets_schema/cli/prompt.py'
    tree = ast.parse((ROOT / relative).read_text())
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name == 'render_native_shared']
    assert len(matches) == 1
    tree.body.remove(matches[0])
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_text(ast.unparse(tree))
    with pytest.raises(scan.ConfigError, match='missing offline render CLI consumer'):
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
