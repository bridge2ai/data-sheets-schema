"""D-owned adapter edges stay separate from host orchestration (U3-D r9).

This source-level boundary covers deferred imports too. Transitive C acceptance
is a separate, still executable integration requirement, not certified here.
"""
import ast
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1] / 'src' / 'data_sheets_schema'
FORBIDDEN = {
    'native_execution_registration_v2', 'native_execution_authority_v2',
    'native_execution', 'native_execution_registration', 'native_execution_authority',
    'native_supervisor', 'native_attempt_supervisor', 'native_supervisor_authority',
    'native_attribution_registration', 'native_attribution_controller',
    'native_execution_gates', 'native_supervisor_gates', 'native_attribution_results',
    'native_shared_results_orchestration', 'native_shared_publication_orchestration',
}


@pytest.mark.parametrize('module', ['native_gate_engine', 'native_shared_gates',
    'native_shared_gate_primitives', 'native_shared_runtime_values',
    'native_shared_results', 'native_shared_publication'])
def test_consumer_owns_no_deferred_verifier_legacy_or_orchestration_import(module):
    tree = ast.parse((PACKAGE / (module + '.py')).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.rsplit('.', 1)[-1] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.rsplit('.', 1)[-1])
            imported.update(alias.name for alias in node.names)
    assert imported.isdisjoint(FORBIDDEN), sorted(imported & FORBIDDEN)


@pytest.mark.parametrize(('module', 'moved', 'retained'), [
    ('native_shared_publication', {'publish_derived', '_replace_journal'},
        {'proposal_publications', '_physical_destination'}),
    ('native_shared_results', {'capture', 'prepare', 'check_capture', 'write_report',
        'require_saved_basis', 'incomplete_capture'},
        {'Snapshot', '_member', '_captured_selection', 'rebuild', 'validate_file_basis', '_read_pool'}),
    ('native_shared_gates', {'capture'}, {'check', 'tool_history', 'current_evidence'}),
])
def test_consumer_has_no_effect_forwarding_entry_points(module, moved, retained):
    tree = ast.parse((PACKAGE / (module + '.py')).read_text())
    definitions = {node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    imported = {alias.asname or alias.name for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert definitions.isdisjoint(moved)
    assert imported.isdisjoint(moved)
    assert retained <= definitions
