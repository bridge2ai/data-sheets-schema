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


def native_fixture_root(tmp_path):
    """Real API sources with the combined native admission shape only.

    On the future combined tree use its actual native module. Standalone CI
    uses this small inert native-validator source; neither route imports it.
    The separate author evidence also exercises all six immutable c9da files.
    """
    root = fixture_root(tmp_path)
    native = 'src/data_sheets_schema/native_shared_render.py'
    if (ROOT / native).is_file():
        (root / native).write_bytes((ROOT / native).read_bytes())
        return root
    runner = root / RUNNER
    text = runner.read_text().replace('    shared_generation_version: int = 0',
        '    native_shared_generation_version: int = 0\n    shared_generation_version: int = 0')
    text = text.replace('        from data_sheets_schema.native_source_attribution import validate as validate_native_attribution',
        '        from .native_shared_render import validate_spec as validate_native_shared\n        validate_native_shared(self)\n        from data_sheets_schema.native_source_attribution import validate as validate_native_attribution')
    text = text.replace('self.condition == "generic_v10" and self.shared_generation_version != 1:',
        'self.condition == "generic_v10" and self.shared_generation_version != 1 and self.native_shared_generation_version != 1:')
    runner.write_text(text)
    shared = root / SHARED
    shared.write_text(shared.read_text().replace('    if not version:\n',
        "    if not version:\n        if getattr(spec, 'native_shared_generation_version', 0):\n            from .native_shared_render import validate_spec\n            validate_spec(spec)\n            return None\n",1))
    (root / native).write_text('''def validate_spec(spec):
    version = getattr(spec, 'native_shared_generation_version', 0)
    registration = getattr(spec, 'native_shared_generation_registration', None)
    if type(version) is not int or version not in (0, 1):
        raise ValueError('native version')
    if not version:
        if registration is not None or spec.render_version == 26:
            raise ValueError('native selector required')
        return None
    if (spec.condition != 'generic_v10' or type(spec.render_version) is not int
            or spec.render_version != 26 or spec.runtime != 'Claude Code (direct)'):
        raise ValueError('native tuple')
    for key in ('native_source_attribution_version', 'shared_generation_version',
                'api_playbook_version', 'receipt_completion_version', 'removal_repair_version'):
        if type(getattr(spec, key)) is not int or getattr(spec, key) != 0:
            raise ValueError('native cannot mix API axes')
    return None
''')
    return root


def test_combined_native_domain_proves_inactive_api_cases(tmp_path):
    root = native_fixture_root(tmp_path)
    selected = scopes(root)['full_receipt_completion']['selection']
    assert selected['renderers'] == [8, 25, 27]
    assert all(case['values']['native_shared_generation_version'] == 0 for case in selected['cases'])
    assert len(selected['cases']) == 6
    assert any('native_shared_render.py:' in path for path in selected['evidence'])
    by_version = {(case['values']['receipt_completion_version'], tuple(case['conditions']))
                  for case in selected['cases']}
    assert by_version == {(1, ('generic_v7', 'generic_v8', 'generic_v9')),
        (2, ('generic_v10',)),
        (3, ('generic_v10_source_heading_routing_v1', 'generic_v10_source_heading_span_v1'))}


@pytest.mark.parametrize('name,before,after', [
    (RUNNER, 'validate_native_shared(self)', 'unproved(self)'),
    (RUNNER, 'validate_native_shared(self)', 'validate_native_shared(other)'),
    (RUNNER, '        validate_native_shared(self)', '        if self.native_shared_generation_version:\n            validate_native_shared(self)'),
    (RUNNER, 'from .native_shared_render import validate_spec as validate_native_shared',
     'from .foreign import validate_spec as validate_native_shared'),
    (RUNNER, 'native_shared_generation_version: int = 0', 'native_shared_generation_version: int = 1'),
    (RUNNER, 'and self.native_shared_generation_version != 1:', 'and self.native_shared_generation_version == 1:'),
    (RUNNER, 'and self.native_shared_generation_version != 1:', 'and self.native_shared_generation_version != 2:'),
    ('src/data_sheets_schema/native_shared_render.py', 'version not in (0, 1)', 'version not in (0, 1, 2)'),
    ('src/data_sheets_schema/native_shared_render.py', "'shared_generation_version',", ''),
    ('src/data_sheets_schema/native_shared_render.py', "'receipt_completion_version',", ''),
    ('src/data_sheets_schema/native_shared_render.py', "    for key in ('native_source_attribution_version',", "    return None\n    for key in ('native_source_attribution_version',"),
    ('src/data_sheets_schema/native_shared_render.py', 'def validate_spec(spec):', '@foreign\ndef validate_spec(spec):'),
    ('src/data_sheets_schema/native_shared_render.py', 'def validate_spec(spec):', 'type = lambda value: int\ndef validate_spec(spec):'),
])
def test_native_exclusion_needs_the_actual_early_validated_domain(tmp_path, name, before, after):
    root = native_fixture_root(tmp_path)
    path = root / name
    text = path.read_text()
    assert before in text
    path.write_text(text.replace(before, after))
    with pytest.raises(scan.ConfigError, match='not derived'):
        scopes(root)
