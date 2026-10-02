"""Opt-in Q19 revision: resource identity and mechanical acceptance, not calibration.

Synthetic full-score rows are schema fixtures, not judgments of real datasets.
The human-readable lineage cases are normative examples awaiting independent
scientific/empirical review; this suite does not infer semantic scores.
"""
import copy
import hashlib
import json
import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation.validate import cli, main, validate_outputs
from data_sheets_schema.evaluation_context import context_digest, load_document
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.semantic_evidence_authority import authority_digest
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.semantic_scope import validate_scope
from tests.test_evaluation.test_semantic_evaluation_contract import _rubric20_record
from tests.test_evaluation.test_semantic_evidence import _groups, _item, _rescore

ROOT = Path(__file__).resolve().parents[2]
INSTRUMENT = select_semantic_instrument('rubric20', '4.0')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def sample(tmp_path):
    record = tmp_path / 'record.yaml'
    record.write_text('id: example:release\ndescription: Original measurements collected by Team A.\ncreators:\n- name: Team A\n')
    context = tmp_path / 'context.yaml'
    context.write_text('{}\n')
    document, digest = load_document(record)
    spec_raw = (ROOT / INSTRUMENT.rubric_path).read_bytes()
    contract = evaluation_contract('rubric20', yaml.safe_load(spec_raw), {}, document)
    result = _rubric20_record()
    result.update(version='4.0', applicability_context=contract['context'], evaluation_scope=contract['scope'],
                  metadata={'context_sha256': context_digest(contract['context']), 'input_sha256': digest,
                            'rubric_sha256': sha(spec_raw),
                            'instrument_sha256': sha((ROOT / INSTRUMENT.definition_path).read_bytes()),
                            'evidence_authority_sha256': authority_digest()})
    result['semantic_analysis']['issues_detected'] = []
    for _, items in _groups(result):
        for item in items:
            rule = contract['items'][f"Q{item['id']}"]
            score = rule['fixed_max_score'] if rule['applicable'] else None
            item.update(name=rule['name'], score=score, max_score=rule['fixed_max_score'],
                        applicable=rule['applicable'], applicability_status=rule['status'],
                        applicability_evidence=rule['evidence'], unit_scores=[{'path': '#', 'score': score,
                            'evidence': 'Synthetic contract fixture', 'cited': [], 'absent': [],
                            'counts': [], 'considered': []}])
    _rescore(result)
    return result, record, context


def accept(sample, tmp_path, *, version='4.0', definition=None):
    result, record, context = sample
    output = tmp_path / 'sample_evaluation.json'
    output.write_text(json.dumps(result))
    return validate_outputs([output], rubric='rubric20-semantic', semantic_version=version,
                            input_path=record, context_path=context,
                            definition_path=definition or ROOT / INSTRUMENT.definition_path)


@pytest.mark.parametrize('rubric', ['rubric10', 'rubric20', 'rubric10-semantic', 'rubric20-semantic'])
@pytest.mark.parametrize('version', ['2.0', '3.0'])
def test_released_resource_selection(rubric, version):
    selected = select_semantic_instrument(rubric, version)
    base = rubric.removesuffix('-semantic')
    assert selected.rubric_path == f'data/rubric/{base}.txt'
    assert selected.definition_path == f'.claude/agents/d4d-{base}-semantic.md'
    assert selected.schema_path == f'src/download/prompts/{base}_semantic_schema.json'
    assert bool(selected.evidence_authority_path) == (version == '3.0')


@pytest.mark.parametrize('rubric, version', [('rubric10', '4.0'), ('rubric20', '5.0'), ('../rubric20', '4.0'),
                                           ('rubric20', 4), ('rubric20', None), (None, '4.0')])
def test_no_unregistered_instrument_or_path_selection(rubric, version):
    with pytest.raises(ValueError):
        select_semantic_instrument(rubric, version)


def test_v4_is_immutable_and_explicitly_reuses_released_authority():
    assert INSTRUMENT == select_semantic_instrument('rubric20-semantic', '4.0')
    assert INSTRUMENT.evidence_authority_path == select_semantic_instrument('rubric20', '3.0').evidence_authority_path
    with pytest.raises(FrozenInstanceError):
        INSTRUMENT.version = '3.0'


def test_old_instrument_bytes_have_not_changed():
    pins = json.loads((ROOT / 'tests/fixtures/semantic_v4/released_asset_hashes.json').read_bytes())
    for path, digest in pins.items():
        assert sha((ROOT / path).read_bytes()) == digest, path


def test_only_q19_changes_and_all_original_weights_remain():
    old = yaml.safe_load((ROOT / 'data/rubric/rubric20.txt').read_bytes())
    new = yaml.safe_load((ROOT / INSTRUMENT.rubric_path).read_bytes())
    old_q = old['d4d_evaluation_rubric']['rubric']
    new_q = new['d4d_evaluation_rubric']['rubric']
    assert len(new_q) == 20
    assert old_q[:18] + old_q[19:] == new_q[:18] + new_q[19:]
    assert old_q[18]['field'] == new_q[18]['field']
    replacement = copy.deepcopy(new)
    replacement['d4d_evaluation_rubric']['rubric'][18] = old_q[18]
    assert replacement == old
    assert sum(1 if q['score_type'] == 'pass_fail' else 5 for q in new_q) == 88
    assert set(new_q[18]['scoring']) == {0, 3, 5}


def test_agent_and_spec_have_identical_q19_anchors_and_assessment():
    questions = yaml.safe_load((ROOT / INSTRUMENT.rubric_path).read_bytes())['d4d_evaluation_rubric']['rubric']
    agent = (ROOT / INSTRUMENT.definition_path).read_text()
    headings = dict((int(n), title) for n, title in re.findall(r'^#### Question (\d+): (.+)$', agent, re.M))
    assert headings == {q['id']: q['name'] for q in questions}
    q = questions[18]
    for score in (0, 3, 5):
        assert f"- **{score}:** {q['scoring'][score]}" in agent
    assert f"**Description:** {q['description']}" in agent
    assert f"**Assessment:** {q['assessment']}" in agent
    old = (ROOT / '.claude/agents/d4d-rubric20-semantic.md').read_text()
    for number in list(range(1, 19)) + [20]:
        pattern = rf'#### Question {number}:.*?(?=\n---\n|\n## )'
        assert re.search(pattern, old, re.S).group() == re.search(pattern, agent, re.S).group()
    assert '--semantic-version 4.0' in agent
    assert INSTRUMENT.rubric_path in agent
    assert INSTRUMENT.definition_path in agent
    assert '"version": "4.0"' in agent


def test_anchors_distinguish_content_from_representation_and_supporting_metadata():
    q = yaml.safe_load((ROOT / INSTRUMENT.rubric_path).read_bytes())['d4d_evaluation_rubric']['rubric'][18]
    text = ' '.join([q['description'], q['assessment'], *q['scoring'].values()])
    for clause in ('Partial lineage without a change log also earns 3', 'in any representation',
                   'initial release or original acquisition', 'no machine-traversable',
                   'absence alone does not cap', 'bibliography of sources',
                   "borrow a sibling's evidence", 'unexplained material modality',
                   'name the specific source', 'does not additionally require version history'):
        assert clause in text
    assert 'Full provenance graph' not in text
    assert 'meaningful' in text.lower()


@pytest.mark.parametrize('value', [True, False, None])
def test_q19_always_applies_even_without_processing(value):
    specification = yaml.safe_load((ROOT / INSTRUMENT.rubric_path).read_bytes())
    rule = evaluation_contract('rubric20', specification, {'data_processing': value}, {'id': 'x'})['items']['Q19']
    assert rule['applicable'] is True
    assert rule['fixed_max_score'] == rule['max_score'] == 5


def test_v4_requires_trusted_opt_in_and_preserves_input_bytes(sample, tmp_path, capsys):
    before = tuple(p.read_bytes() for p in sample[1:])
    assert accept(sample, tmp_path) == 0
    assert accept(sample, tmp_path, version='3.0') == 1
    assert 'requires instrument version 3.0' in capsys.readouterr().out
    assert before == tuple(p.read_bytes() for p in sample[1:])


@pytest.mark.parametrize('mutation, message', [
    ('missing_array', 'counts'), ('missing_authority', 'evidence_authority_sha256'),
    ('forged_authority', 'authority'), ('old_rubric', 'another rubric'),
    ('old_name', 'item name'), ('wrong_input', 'input'), ('wrong_context', 'context'),
    ('scope_omission', 'scope'), ('version_downgrade', 'requires instrument version 4.0'),
    ('unknown_absence', 'unknown_absence_name'), ('false_absence', 'absent_path_populated'),
    ('false_quote', 'quote_not_found'), ('false_count', 'count_mismatch'),
    ('no_deduction_evidence', 'missing_structured_evidence'), ('invalid_taxonomy', 'invented'),
])
def test_v4_cannot_bypass_released_acceptance_gates(sample, tmp_path, capsys, mutation, message):
    result = sample[0]
    row = _item(result, 'Q19')['unit_scores'][0]
    if mutation == 'missing_array': row.pop('counts')
    elif mutation == 'missing_authority': result['metadata'].pop('evidence_authority_sha256')
    elif mutation == 'forged_authority': result['metadata']['evidence_authority_sha256'] = '0' * 64
    elif mutation == 'old_rubric': result['metadata']['rubric_sha256'] = sha((ROOT / 'data/rubric/rubric20.txt').read_bytes())
    elif mutation == 'old_name': _item(result, 'Q19')['name'] = 'Data Integrity, Provenance Graph, and Quality'
    elif mutation == 'wrong_input': result['metadata']['input_sha256'] = '0' * 64
    elif mutation == 'wrong_context': sample[2].write_text('data_processing: false\n')
    elif mutation == 'scope_omission': result['evaluation_scope']['units'] = []
    elif mutation == 'version_downgrade': result['version'] = '3.0'
    elif mutation == 'unknown_absence': row['absent'] = [{'path': 'made_up_lineage'}]
    elif mutation == 'false_absence': row['absent'] = [{'path': 'description'}]
    elif mutation == 'false_quote': row['cited'] = [{'path': 'description', 'quote': 'never said this'}]
    elif mutation == 'false_count': row['counts'] = [{'path': 'creators', 'claimed': 9}]
    elif mutation == 'no_deduction_evidence':
        _item(result, 'Q19')['score'] = row['score'] = 3
        _rescore(result)
    else:
        result['semantic_analysis']['issues_detected'] = [{'type': 'invented', 'category': 'temporal_version',
            'severity': 'low', 'description': 'Fixture', 'recommendation': 'Fixture',
            'fields_involved': [], 'item_ids': [], 'score_effect': 'noted_only'}]
    assert accept(sample, tmp_path) == 1
    assert message in capsys.readouterr().out


def test_v4_rejects_self_consistent_hash_of_old_definition(sample, tmp_path, capsys):
    old = ROOT / '.claude/agents/d4d-rubric20-semantic.md'
    sample[0]['metadata']['instrument_sha256'] = sha(old.read_bytes())
    assert accept(sample, tmp_path, definition=old) == 1
    assert 'not the selected semantic version-4' in capsys.readouterr().out


def test_partial_lineage_is_a_valid_middle_band_with_evidence(sample, tmp_path):
    item = _item(sample[0], 'Q19')
    item['score'] = item['unit_scores'][0]['score'] = 3
    item['unit_scores'][0]['cited'] = [{'path': 'description', 'quote': 'collected by Team A'}]
    item['no_issue_reason'] = 'Acquisition responsibility is explicit but source-to-release relationship is incomplete.'
    _rescore(sample[0])
    assert accept(sample, tmp_path) == 0


def test_cli_and_historical_discovery_select_v4_contract(sample, tmp_path):
    assert accept(sample, tmp_path) == 0
    output = tmp_path / 'sample_evaluation.json'
    argv = ['--file', str(output), '--rubric', 'rubric20-semantic', '--input', str(sample[1]),
            '--agent-definition', str(ROOT / INSTRUMENT.definition_path), '--context', str(sample[2])]
    assert cli(argv) == 1
    assert cli(argv + ['--semantic-version', '4.0']) == 0
    assert main(eval_base=tmp_path) == 0
    _item(sample[0], 'Q19')['unit_scores'][0].pop('counts')
    output.write_text(json.dumps(sample[0]))
    assert main(eval_base=tmp_path) == 1


def test_v4_definition_discriminates_from_released_v3_without_fabricated_history():
    from data_sheets_schema.agent_pin import challenge_between, _normalise
    old = (ROOT / '.claude/agents/d4d-rubric20-semantic.md').read_text()
    new = (ROOT / INSTRUMENT.definition_path).read_text()
    ask = challenge_between(new, old)
    assert ask is not None and _normalise(ask['expected']) not in _normalise(old)
    assert ask['expected'] not in ask['prefix']
    registry = json.loads((ROOT / '.claude/agents/_preimages.json').read_text())
    assert registry['agents'][INSTRUMENT.agent]['previous_text'] is None


def test_agent_worked_example_is_accepted_after_only_definition_placeholder_replacement(tmp_path):
    agent = (ROOT / INSTRUMENT.definition_path).read_text()
    result = json.loads(re.search(r'```json\n(.*?)\n```', agent, re.S)[1])
    result['metadata']['instrument_sha256'] = sha(agent.encode())
    record = tmp_path / 'example.yaml'
    record.write_text('id: https://example.org/synthetic-dataset\n')
    context = tmp_path / 'context.yaml'
    context.write_text(yaml.safe_dump(result['applicability_context']))
    assert accept((result, record, context), tmp_path) == 0


def test_v4_collection_scope_keeps_na_and_per_resource_minimum(tmp_path, capsys):
    from tests.test_evaluation.test_semantic_context_scope import record
    result, input_path = record(tmp_path, 'rubric20')
    result['version'] = '4.0'
    result['metadata'].update(rubric_sha256=sha((ROOT / INSTRUMENT.rubric_path).read_bytes()),
                              instrument_sha256=sha((ROOT / INSTRUMENT.definition_path).read_bytes()))
    item = _item(result, 'Q19')
    item['name'] = 'Data Integrity, Provenance, and Quality'
    item['score'] = item['unit_scores'][1]['score'] = 3
    item['no_issue_reason'] = 'Synthetic lower-coverage resource.'
    _rescore(result)
    sample = result, input_path, input_path.with_name('caller-context.yaml')
    assert _item(result, 'Q15')['applicable'] is False
    assert accept(sample, tmp_path) == 0
    item['score'] = 5
    _rescore(result)
    assert accept(sample, tmp_path) == 1
    assert 'Q19.score' in capsys.readouterr().out
    item['score'] = 3
    result['evaluation_scope']['units'].pop()
    for _, items in _groups(result):
        for one in items:
            one['unit_scores'].pop()
    assert accept(sample, tmp_path) == 1


def test_v4_cannot_borrow_parent_evidence_for_child(tmp_path, capsys):
    from tests.test_evaluation.test_semantic_context_scope import record
    result, input_path = record(tmp_path, 'rubric20')
    result['version'] = '4.0'
    result['metadata'].update(rubric_sha256=sha((ROOT / INSTRUMENT.rubric_path).read_bytes()),
                              instrument_sha256=sha((ROOT / INSTRUMENT.definition_path).read_bytes()))
    item = _item(result, 'Q19')
    item['name'] = 'Data Integrity, Provenance, and Quality'
    input_path.write_text(input_path.read_text().replace('  resources:', '  description: Parent lineage only\n  resources:'))
    result['metadata']['input_sha256'] = sha(input_path.read_bytes())
    item['unit_scores'][0]['cited'] = [{'path': 'description', 'quote': 'Parent lineage only'}]
    assert accept((result, input_path, input_path.with_name('caller-context.yaml')), tmp_path) == 1
    assert 'cited_path_unresolved' in capsys.readouterr().out
