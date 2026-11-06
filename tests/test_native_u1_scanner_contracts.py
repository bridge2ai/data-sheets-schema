"""#4354 U1 scanner admission controls; offline source copies, 2026-11-06.

The foundation has no public CLI/controller yet. That boundary must still fail
explicitly after the validated dispatch has been derived successfully.
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


def test_native_route_requires_later_cli_consumer():
    with pytest.raises(scan.ConfigError, match='missing offline render CLI consumer'):
        scan.derive_native_shared_route(ROOT, scan._tree(ROOT / RUNNER))


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
