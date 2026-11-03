"""F4: BC1 joins existing effect summaries without hiding text or unknown calls."""
import pytest

from tests import test_generation_specificity_skill as specificity


@pytest.mark.parametrize('module', ['bc1_runtime', 'bc1_context', 'bc1_audit',
                                    'bc1_codec', 'bc1_selection', 'bc1_registration'])
def test_bc1_summary_retains_project_text_and_refuses_unknown_receivers(tmp_path, module):
    flow, scan = specificity.TestModelFacingDerivation, specificity.scan
    runner = specificity.PRECISION_RUNNER.replace('from pathlib import Path\n',
        f'from pathlib import Path\nfrom data_sheets_schema import {module}\n')
    runner = runner.replace('system=prompts_4085.SYSTEM', f'system={module}.render()')
    source = ('from external_mutator import unknown\n'
              'def render():\n'
              '    parts = []\n'
              '    parts.append("Describe the CHORUS cohort from its source records.")\n'
              '    return "".join(parts)\n')
    modules = {**specificity.PRECISION_MODULES, 'schema_semantics': '', 'receipt_completion_policy': '', module: source}
    root = flow._root(str(tmp_path), runner, modules)
    derived, spans, _ = flow._derive(root)
    assert module in derived
    assert ('CHORUS', 4) in flow._violations(root, f'src/data_sheets_schema/{module}.py', derived, spans)
    (root / f'src/data_sheets_schema/{module}.py').write_text(
        source.replace('    return', '    unknown(parts)\n    return'))
    with pytest.raises(scan.ConfigError, match='unsupported effect'):
        flow._derive(root)


@pytest.mark.parametrize('change', ['foreign_import', 'rebound_serializer', 'unknown_option'])
def test_bc1_linkml_summary_requires_the_exact_import_and_operation(tmp_path, change):
    flow, scan = specificity.TestModelFacingDerivation, specificity.scan
    runner = specificity.PRECISION_RUNNER.replace('from pathlib import Path\n',
        'from pathlib import Path\nfrom data_sheets_schema import bc1_context\n')
    runner = runner.replace('system=prompts_4085.SYSTEM', 'system=bc1_context._core_catalog(None)')
    source = ('def _core_catalog(snapshot):\n'
              '    from linkml_runtime.dumpers import json_dumper\n'
              '    slot = {"text": "Describe the CHORUS cohort from its source records."}\n'
              '    return json_dumper.dumps(slot)\n')
    root = flow._root(str(tmp_path), runner, {**specificity.PRECISION_MODULES,
        'schema_semantics': '', 'receipt_completion_policy': '', 'bc1_context': source})
    derived, _, _ = flow._derive(root)
    assert 'bc1_context' in derived
    changes = {
        'foreign_import': source.replace('linkml_runtime.dumpers', 'external_serializer'),
        'rebound_serializer': source.replace('    return', '    json_dumper.dumps = unknown\n    return'),
        'unknown_option': source.replace('dumps(slot)', 'dumps(slot, default=unknown)'),
    }
    (root / 'src/data_sheets_schema/bc1_context.py').write_text(changes[change])
    with pytest.raises(scan.ConfigError):
        flow._derive(root)
