"""Structural BC1 dispatch witnesses for integration BG-1, 2026-11-03."""
import ast

import pytest

from tests.test_generation_specificity_delegated import (
    RUNNER, fixture_root, scan, scopes,
)

DISPATCH = ('    if selected := _bc1(spec):\n'
            '        return selected.run(spec, carry=carry, client=client, settings=settings, usage=usage)\n')


@pytest.fixture
def entry_probe(tmp_path, monkeypatch):
    root = fixture_root(tmp_path)
    helpers = [root / f'src/data_sheets_schema/{name}.py'
               for name in ('typed_audit_runtime', 'bc1_runtime')]
    monkeypatch.setattr(scan, '_package_closure', lambda *_: helpers)
    tree = scan._tree(root / RUNNER)
    funcs, selected = scan._function_defs(tree), scopes(root)
    path = helpers[0]

    def derive():
        return scan._helper_followups(root, tree, funcs, {'_call_with_usage'}, selected)

    return path, derive


def assert_dispatch_derived(path, derive):
    rows = [via for row in derive().values() for via in row['via']
            if via.get('bounded_carry_version') == 1]
    assert rows
    entry = next(n for n in ast.parse(path.read_text()).body
                 if isinstance(n, ast.FunctionDef) and n.name == 'run')
    dispatch = next(n for n in entry.body if isinstance(n, ast.If)
                    and isinstance(n.test, ast.NamedExpr))
    citation = f'src/data_sheets_schema/typed_audit_runtime.py:{dispatch.lineno}'
    assert all(citation in via['dispatch_evidence'] for via in rows)


@pytest.mark.parametrize('extra', ['', '    from .other_guard import check\n    check(spec)\n'],
                         ids=['integrated', 'guard_prefix'])
def test_integrated_dispatch_derives_and_cites_its_actual_line(entry_probe, extra):
    path, derive = entry_probe
    source = path.read_text()
    assert source.count(DISPATCH) == 1
    path.write_text(source.replace(DISPATCH, extra + DISPATCH))
    assert_dispatch_derived(path, derive)


@pytest.mark.parametrize('prefix,reason', [
    ('    local = None\n', 'prefix Assign'),
    ('    return None\n', 'prefix Return'),
    ('    refuse_legacy_execution((local := spec))\n', 'prefix.*NamedExpr'),
    ('    if spec:\n        return None\n', 'prefix If'),
    ('    from .foreign import other as spec\n', 'dispatch name.*spec.*rebound'),
    ('    from .foreign import other as _bc1\n', 'dispatch.*changed|dispatch name.*_bc1.*rebound'),
])
def test_unsupported_dispatch_prefix_refuses_by_name(entry_probe, prefix, reason):
    path, derive = entry_probe
    assert_dispatch_derived(path, derive)  # Every hostile case has a positive control.
    source = path.read_text()
    path.write_text(source.replace(DISPATCH, prefix + DISPATCH))
    with pytest.raises(scan.ConfigError, match=reason):
        derive()


def test_duplicated_dispatch_refuses(entry_probe):
    path, derive = entry_probe
    assert_dispatch_derived(path, derive)
    source = path.read_text()
    path.write_text(source.replace(DISPATCH, DISPATCH + DISPATCH))
    with pytest.raises(scan.ConfigError, match='exactly one BC1 dispatch.*2'):
        derive()


@pytest.mark.parametrize('name', ['spec', 'carry', 'client', 'settings', 'usage', 'selected'])
def test_dispatch_names_cannot_be_rebound_later(entry_probe, name):
    path, derive = entry_probe
    assert_dispatch_derived(path, derive)
    source = path.read_text()
    path.write_text(source.replace(DISPATCH, DISPATCH + f'    {name} = None\n'))
    with pytest.raises(scan.ConfigError, match=f'dispatch name.*{name}.*rebound'):
        derive()
