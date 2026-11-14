"""Native receipt/read-window reporting is diagnostic, including shell reads."""
import json
import pytest
from data_sheets_schema.native_gate_engine import receipt_observation


@pytest.mark.parametrize('tool,failed,unopened', [('Read', False, 0), ('Read', True, 1), ('Bash', False, 1)])
def test_native_receipt_and_manifest_are_actually_consumed(tmp_path, tool, failed, unopened):
    bundle, receipt, manifest, transcript = [tmp_path / name for name in
                                           ('bundle.txt', 'receipt.json', 'chunks.json', 'transcript.jsonl')]
    bundle.write_text('first\nsecond\n')
    receipt.write_text(json.dumps({'chunks': [{'id': 'c1'}]}))
    manifest.write_text(json.dumps({'chunks': [{'id': 'c1', 'lines': [1, 2]}]}))
    tool_input = {'file_path': str(bundle), 'offset': 1, 'limit': 2} if tool == 'Read' else {'command': 'cat ' + str(bundle)}
    events = [{'type': 'assistant', 'message': {'id': 'a', 'role': 'assistant', 'content': [
        {'type': 'tool_use', 'id': 't1', 'name': tool, 'input': tool_input}]}},
        {'type': 'user', 'message': {'role': 'user', 'content': [
            {'type': 'tool_result', 'tool_use_id': 't1', 'is_error': failed, 'content': 'first\nsecond\n'}]}},
        {'type': 'result', 'usage': {'input_tokens': 1, 'output_tokens': 1,
            'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}}]
    transcript.write_text(''.join(json.dumps(row) + '\n' for row in events))
    result = receipt_observation(transcript, bundle, receipt, manifest)
    assert result['receipt_chunks_total'] == 1
    assert result['receipt_chunks_unopened'] == unopened
    assert result['receipt_chunks_unopened_basis'] == {
        'mode': 'reported_only', 'receipt': 'original_phase1_receipt',
        'reads': 'successful_file_tool_windows', 'permitted_shell_reads_count_as_unopened': True}
    from data_sheets_schema.native_execution_authority_v2 import dependency_identity
    from data_sheets_schema.native_execution_capabilities import loaded_capabilities
    with loaded_capabilities(dependency_identity()) as controls:
        assert controls.gate_members['observation_problems'](result) == []


def test_native_gate_passes_both_captured_receipt_and_manifest():
    # AST integration check complements the real observation tests without
    # substituting a passing full runtime gate or constructing a fake RunSpec.
    import ast
    from pathlib import Path
    from data_sheets_schema import native_gate_engine
    tree = ast.parse(Path(native_gate_engine.__file__).read_text())
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'observed')
    call = next(node for node in ast.walk(function) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == 'receipt_observation')
    assert ast.unparse(call.args[2]) == "projected(spec._agentic_artifact_paths['receipt'])"
    assert ast.unparse(call.args[3]) == 'projected(spec.chunk_manifest)'


@pytest.mark.parametrize('mutation', ['drop_marker', 'count', 'drop_observation'])
def test_new_registered_report_cannot_remove_marker_or_change_count(mutation):
    from copy import deepcopy
    from data_sheets_schema.native_shared_results_orchestration import _require_reported_receipts
    fresh = {'checked': True, 'passed': True, 'problems': [], 'observation': {
        'receipt_chunks_unopened': 2, 'receipt_chunks_unopened_basis': {'mode': 'reported_only'}}}
    old = deepcopy(fresh)
    if mutation == 'drop_marker': del old['observation']['receipt_chunks_unopened_basis']
    elif mutation == 'count': old['observation']['receipt_chunks_unopened'] = 0
    else: del old['observation']
    runtime = {'limits_basis': '{"kind":"d4d_native_u4b_runtime_basis","version":1}'}
    with pytest.raises(ValueError, match='observation differs'):
        _require_reported_receipts(old, fresh, runtime)


# The pinned v1 and v2 closures intentionally share bare module names. Isolate
# each case from collection imports and earlier v1 cases without relaxing the
# production origin check (including deliberate foreign imports in test bodies).
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: E402,F401
import pytest as _origin_pytest  # noqa: E402

pytestmark = _origin_pytest.mark.usefixtures("isolated_modules")
