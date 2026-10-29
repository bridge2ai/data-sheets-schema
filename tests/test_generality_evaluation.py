"""F8: new instrument bytes, predecessor preservation and neutral offline pipeline."""
import json
import hashlib
from pathlib import Path
import re
import pytest
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from scripts.adhoc.generality_newproj_20261029 import run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('family,previous', [('rubric10', '3.0'), ('rubric20', '4.0')])
def test_general_instrument_uses_new_resources_and_keeps_predecessor(family, previous):
    old = select_semantic_instrument(family, previous)
    new = select_semantic_instrument(family, '5.0')
    hashes = json.loads((ROOT / 'tests/fixtures/generality/semantic_predecessors.json').read_bytes())['sha256']
    for field in ('definition_path', 'rubric_path', 'schema_path'):
        path = getattr(old, field)
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == hashes[path]
        assert path != getattr(new, field)
    text = (ROOT / new.definition_path).read_text() + (ROOT / new.rubric_path).read_text()
    assert not re.search(r'PhysioNet|FAIRhub|MGH|OT2OD032742|prefix is plausible|Bridge2AI|prefix unusual|NIH/NSF', text)
    assert 'unfamiliar prefix is not an error' in text
    assert 'Synthetic example' in text
    assert json.loads((ROOT / new.schema_path).read_bytes())['properties']['version']['const'] == '5.0'


def test_new_project_pipeline_accepts_only_declared_neutral_inputs(tmp_path):
    proof = run(tmp_path)
    assert proof['profile'] == 'neutral' and proof['model_calls'] == 0
    assert proof['synthetic_reply_contract_accepted']
