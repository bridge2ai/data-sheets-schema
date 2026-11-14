"""U1 before/after render evidence, fixed offline inputs (#4354)."""
from dataclasses import replace
import os
from pathlib import Path
import pytest
from data_sheets_schema import api_runner as api
from tests.test_shared_generation_selection import external, offline, registration_for, selected_spec
from tests.test_source_heading_runtime_api import draft_files, selected_spec as routing_spec
from tests.test_bc1_selection import registered as bc1_selected, simulated_hooks


def record(name, spec):
    spec.run_date = '2026-11-06'
    if spec._replay_only:
        spec._api_header_values = api.request_header_values(api._model_settings(spec.condition))
    else:
        spec.bind_api_header_values(api._model_settings(spec.condition))
    raw = spec.instruction.encode()
    if 'U1_PARITY_OUTPUT' not in os.environ:
        pytest.skip('explicit before/after artifact run only')
    folder = Path(os.environ['U1_PARITY_OUTPUT'])
    folder.mkdir(exist_ok=True)
    (folder / (name + '.txt')).write_bytes(raw)
    assert raw

@pytest.mark.parametrize('condition', ['generic', 'tuned', *['generic_v' + str(n) for n in range(2, 10)]])
def test_existing_conditions(external, condition):
    record(condition, replace(external, condition=condition, _replay_only=condition == 'tuned'))

def test_shared_v1(external):
    record('generic_v10', selected_spec(external, registration_for(external)))

@pytest.mark.parametrize('mode', ['declared_heading_spans_v1', 'captured_json_values_v1'])
def test_shared_v2(tmp_path, draft_files, mode):
    record(mode, routing_spec(tmp_path, draft_files, mode=mode))

def test_bc1(bc1_selected):
    record('bc1', bc1_selected)
