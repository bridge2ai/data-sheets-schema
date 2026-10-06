"""Finite source-only selector proofs; no generation/package import (#4503)."""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'
spec = importlib.util.spec_from_file_location('delegated_scanner', SOURCE)
scan = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)
RUNNER = 'src/data_sheets_schema/api_runner.py'
SHARED = 'src/data_sheets_schema/shared_generation.py'
MODES = 'src/data_sheets_schema/source_heading_runtime.py'
FILES = (RUNNER, SHARED, MODES, 'src/data_sheets_schema/receipt_completion.py',
         'src/data_sheets_schema/typed_audit_runtime.py')


def fixture_root(tmp_path):
    for name in FILES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    return tmp_path


def scopes(root):
    return scan._plan_scopes(scan._tree(root / RUNNER), scan._module_constants(root / RUNNER), root=root)


def test_actual_delegated_families_and_description_are_derived():
    existing_modules = {name for name in sys.modules if name == 'data_sheets_schema'
                        or name.startswith('data_sheets_schema.')}
    consts = scan._module_constants(ROOT / RUNNER)
    result = scan.derive_followups(scan._tree(ROOT / RUNNER), list(consts['PHASES']), consts, root=ROOT)
    receipt = result['full_receipt_completion']['selection']
    actual = {(c['values']['receipt_completion_version'], c['values']['shared_generation_version'],
               tuple(c['renderers']), tuple(c['conditions'])) for c in receipt['cases']}
    assert actual == {
        (1, 0, (8,), ('generic_v7', 'generic_v8', 'generic_v9')),
        (2, 1, (25,), ('generic_v10',)),
        (3, 2, (27,), ('generic_v10_source_heading_routing_v1', 'generic_v10_source_heading_span_v1')),
    }
    legacy = [c for c in receipt['cases'] if c['values']['receipt_completion_version'] == 1]
    assert {(c['values']['api_playbook_version'], c['values']['removal_repair_version']) for c in legacy} == {(0,0),(0,1),(1,0),(1,1)}
    for phase in ('typed_audit_worker', 'typed_audit_omission', 'typed_audit_integration'):
        selected = result[phase]
        assert selected['selection']['renderers'] == [25, 27]
        assert selected['via'][0]['replacement']['phase'] == 'audit'
        assert all(row['runtime'] == 'api' for row in selected['selection']['cases'])
    assert any('source_heading_runtime.py:' in path for path in receipt['evidence'])
    assert {name for name in sys.modules if name == 'data_sheets_schema'
            or name.startswith('data_sheets_schema.')} == existing_modules


@pytest.mark.parametrize('name,before,after', [
    (SHARED, 'spec.runtime != "Claude API (direct)" or ', ''),
    (SHARED, 'spec.api_playbook_version != 3', 'spec.api_playbook_version != 2'),
    (SHARED, 'version not in (0, 1, 2)', 'version not in (0, 1, 2, 3)'),
    (SHARED, 'version = getattr(spec, "shared_generation_version", 0)', 'version = getattr(spec, "shared_generation_version", 1)'),
    (SHARED, 'spec.condition not in MODES.values()', 'check_condition(spec.condition)'),
    (SHARED, 'from .source_heading_runtime import MODES', 'from .foreign import MODES'),
    (SHARED, '    if version == 2:', '    if version == 2:\n        return None'),
    (RUNNER, '            select(self)', '            select(other)'),
    (RUNNER, '            select(self)', '            select = replacement\n            select(self)'),
    (RUNNER, '        select_shared(self)', '        pass'),
    (RUNNER, 'self.receipt_completion_version == 3 and self.shared_generation_version != 2', 'False'),
    (RUNNER, 'self.render_version == 25 and self.shared_generation_version != 1', 'False'),
    (RUNNER, 'self.shared_generation_version not in (0, 1, 2)', 'self.shared_generation_version not in (0, 1, 2, 3)'),
    (RUNNER, 'shared_generation_version: int = 0', 'shared_generation_version: int = 1'),
    (RUNNER, '        select_shared(self)', '        self.shared_generation_version = 0\n        select_shared(self)'),
    (MODES, "'declared_heading_spans_v1': 'generic_v10_source_heading_span_v1',", "'declared_heading_spans_v1': 'foreign',"),
    (MODES, "MAX_CAPTURE = 64_000_000", "MODES.update({'extra':'foreign'})\nMAX_CAPTURE = 64_000_000"),
    (SHARED, '{spec.receipt_completion_version} before core', '{spec.project} before core'),
    (SHARED, '{spec.receipt_completion_version} before core', '{len(spec.project)} before core'),
    (SHARED, '{spec.receipt_completion_version} before core', '{spec.receipt_completion_version!r} before core'),
    (SHARED, '{spec.receipt_completion_version} before core', '{spec.receipt_completion_version:03} before core'),
    (SHARED, "f'{RECEIPT_PHASE}: receipt completion", "f'{RECEIPT_PHASE}{spec.receipt_completion_version}: receipt completion"),
])
def test_unknown_or_unbound_selector_changes_refuse(tmp_path, name, before, after):
    root = fixture_root(tmp_path)
    path = root / name
    text = path.read_text()
    assert before in text
    path.write_text(text.replace(before, after))
    with pytest.raises(scan.ConfigError, match='not derived'):
        scopes(root)


def test_supported_literal_changes_are_read_not_hardcoded(tmp_path):
    root = fixture_root(tmp_path)
    for name in (RUNNER, SHARED):
        path = root / name
        import re
        path.write_text(re.sub(r'\b27\b', '28', path.read_text()))
    result = scopes(root)['full_receipt_completion']['selection']
    assert result['renderers'] == [8, 25, 28]
    assert {c['renderers'][0] for c in result['cases'] if c['values']['receipt_completion_version'] == 3} == {28}


def test_missing_source_root_cannot_use_expected_tuple_fallback():
    tree = scan._tree(ROOT / RUNNER)
    with pytest.raises(scan.ConfigError, match='not derived'):
        scan._plan_scopes(tree, scan._module_constants(ROOT / RUNNER))


def template_fixture(root):
    runner = '''def resolve_prompt(spec):
    body = prompt_body(spec.base_prompt)
    if spec.guide_version:
        from data_sheets_schema.api_playbook import adapt_template
        body = adapt_template(body, version=spec.guide_version)
    return body
'''
    (root / RUNNER).parent.mkdir(parents=True, exist_ok=True)
    (root / RUNNER).write_text(runner)
    for name in (SHARED, 'src/data_sheets_schema/api_playbook.py'):
        (root / name).write_bytes((ROOT / name).read_bytes())
    constants = scan._module_constants(ROOT / SHARED)
    assets = {version: constants[key] for version, key in ((2,'API_POLICY'), (3,'ROUTING_API_POLICY'))}
    for name in assets.values():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes((ROOT / name).read_bytes())
    table = scan.condition_table(ROOT)
    body = (ROOT / table['prompts'][table['current']]).read_text().split('## Prompt body',1)[1]
    return body, assets


def test_actual_policy_versions_derive_distinct_asset_bytes(tmp_path):
    body, assets = template_fixture(tmp_path)
    results = {}
    for version, name in assets.items():
        selected = {'cases': [{'values': {'guide_version': version}}]}
        result, evidence = scan._selected_template(tmp_path, scan._tree(tmp_path / RUNNER), selected, body)
        assert evidence['version'] == version and evidence['policy_asset'] == name
        assert result.startswith((tmp_path / name).read_text().split('## Prompt body',1)[1].strip())
        results[version] = result
    assert results[2] != results[3]
    # The originally supported one-version grammar retains identical output.
    path = tmp_path / 'src/data_sheets_schema/api_playbook.py'
    text = path.read_text().replace('if version in (2, 3):', 'if version == 2:').replace(
        'captured_assets(version=version - 1)[API_POLICY if version == 2 else ROUTING_API_POLICY]',
        'captured_assets()[API_POLICY]')
    path.write_text(text)
    result, _ = scan._selected_template(tmp_path, scan._tree(tmp_path / RUNNER),
        {'cases': [{'values': {'guide_version':2}}]}, body)
    assert result == results[2]


@pytest.mark.parametrize('before,after', [
    ('if version in (2, 3):', 'if version in (2, 3, 4):'),
    ('if version in (2, 3):', 'if allowed(version):'),
    ('captured_assets(version=version - 1)', 'captured_assets(version=version)'),
    ('API_POLICY if version == 2 else ROUTING_API_POLICY', 'API_POLICY'),
    ('API_POLICY if version == 2 else ROUTING_API_POLICY', 'ROUTING_API_POLICY if version == 2 else API_POLICY'),
    ('from .shared_generation import captured_assets, API_POLICY, ROUTING_API_POLICY',
     'from .shared_generation import captured_assets, API_POLICY\n        from .foreign import ROUTING_API_POLICY'),
])
def test_policy_route_changes_cannot_hide_behind_version_names(tmp_path, before, after):
    body, _ = template_fixture(tmp_path)
    path = tmp_path / 'src/data_sheets_schema/api_playbook.py'
    text = path.read_text()
    assert before in text
    path.write_text(text.replace(before, after))
    with pytest.raises(scan.ConfigError, match='not derived'):
        scan._selected_template(tmp_path, scan._tree(tmp_path / RUNNER),
            {'cases': [{'values': {'guide_version':3}}]}, body)


@pytest.mark.parametrize('name,addition', [
    (SHARED, '\nselect = lambda spec: None\n'),
    (SHARED, '\ndef select(spec):\n    return None\n'),
    (SHARED, '\nfrom builtins import print as select\n'),
    (SHARED, '\nclass select: pass\n'),
    (MODES, '\n_alias = MODES\n_alias.clear()\n'),
    (MODES, '\ndef _clear(table):\n    table.clear()\n_clear(MODES)\n'),
    (MODES, '\nfrom builtins import dict as MODES\n'),
    (MODES, '\ndef MODES(): pass\n'),
    (MODES, '\nclass MODES: pass\n'),
    (RUNNER, '\n_alias = RECEIPT_CONDITIONS\n'),
    (RUNNER, '\nfrom builtins import tuple as AGENTIC_RUNTIMES\n'),
])
def test_effective_export_and_literal_container_escapes_refuse(tmp_path, name, addition):
    root = fixture_root(tmp_path)
    path = root / name
    path.write_text(path.read_text() + addition)
    with pytest.raises(scan.ConfigError, match='not derived'):
        scopes(root)


@pytest.mark.parametrize('name,before,after', [
    (SHARED, 'def select(spec)', '@foreign\ndef select(spec)'),
    (SHARED, 'def descriptor(', '@foreign\ndef descriptor('),
    (RUNNER, 'SOURCE_HEADING_CONDITIONS = ', 'frozenset = lambda items: ()\nSOURCE_HEADING_CONDITIONS = '),
    (MODES, "MODES = {", "MODES = {'captured_json_values_v1': 'discarded',"),
])
def test_decorated_or_shadowed_authorities_refuse(tmp_path, name, before, after):
    root = fixture_root(tmp_path)
    path = root / name
    text = path.read_text()
    assert before in text
    path.write_text(text.replace(before, after))
    with pytest.raises(scan.ConfigError, match='not derived'):
        scopes(root)


@pytest.mark.parametrize('name,addition', [
    (SHARED, '\ngetattr = lambda obj, name, default=None: default\n'),
    (SHARED, '\ntype = lambda value: str\n'),
    (SHARED, '\nint = str\n'),
    (SHARED, '\nstr = int\n'),
    (RUNNER, '\ntype = lambda value: int\n'),
    (RUNNER, '\nfrom builtins import str as int\n'),
])
def test_selector_builtin_identity_is_proved_in_its_source_module(tmp_path, name, addition):
    root = fixture_root(tmp_path)
    path = root / name
    path.write_text(path.read_text() + addition)
    with pytest.raises(scan.ConfigError, match='not derived'):
        scopes(root)
