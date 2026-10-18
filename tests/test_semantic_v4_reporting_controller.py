"""Version-4 selection stays explicit through reporting and offline execution.

Synthetic CLI transport exercises the real validator and definition challenge;
none of these fixtures are scientific calibration or invoke a model service.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import agent_pin
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.semantic_evidence_reporting import issue_taxonomy, render_issue_taxonomy
from tests.test_reference_rescore import (
    environment as legacy_environment, runner, events, fake_cli, current_record, REAL_ROOT,
)
from tests.test_evaluation.test_semantic_evidence_reporting import _real_rating, issue

SELECTED = select_semantic_instrument('rubric20', '4.0')
Q19 = yaml.safe_load((REAL_ROOT / SELECTED.rubric_path).read_bytes())['d4d_evaluation_rubric']['rubric'][18]['name']


def upgrade(doc, manifest):
    doc['version'] = '4.0'
    for group in doc['categories']:
        for question in group['questions']:
            if question['id'] == 19:
                question['name'] = Q19
    instrument = manifest['instruments']['rubric20-semantic']
    doc['metadata'].update(instrument_sha256=instrument['definition_sha256'],
                           rubric_sha256=manifest['pinned_files'][instrument['rubric']])
    return doc


@pytest.fixture
def v4_environment(tmp_path, monkeypatch):
    root, manifest, job, doc = legacy_environment.__wrapped__(tmp_path, monkeypatch, SimpleNamespace(param=20))
    instrument = manifest['instruments'][job['rubric']]
    for rel in (SELECTED.definition_path, SELECTED.rubric_path, SELECTED.schema_path):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_ROOT / rel, root / rel)
        manifest['pinned_files'][rel] = runner.digest(root / rel)
    instrument.update(version='4.0', agent=SELECTED.agent, definition=SELECTED.definition_path,
                      definition_sha256=manifest['pinned_files'][SELECTED.definition_path],
                      rubric=SELECTED.rubric_path, schema=SELECTED.schema_path,
                      predecessor_definition=runner.V4_PREDECESSOR,
                      predecessor_sha256=runner.V4_PREDECESSOR_SHA256)
    job['agent'] = SELECTED.agent
    # Use actual challenge functions, not the legacy fixture's stubbed echo.
    monkeypatch.setattr(runner, 'spawn_preamble', agent_pin.spawn_preamble)
    monkeypatch.setattr(runner, 'verify_echo', agent_pin.verify_echo)
    monkeypatch.setattr(agent_pin, 'agent_path', lambda name: root / '.claude/agents' / f'{name}.md')
    predecessor = runner.registered_predecessor(instrument, manifest)
    instrument['preamble'] = agent_pin.spawn_preamble(job['agent'], predecessor_text=predecessor)
    runner.write_json(runner.PLAN / 'manifest.json', manifest)
    return root, manifest, job, upgrade(doc, manifest)


def trace_for(doc, manifest, job):
    trace = events(doc)
    predecessor = runner.registered_predecessor(manifest['instruments'][job['rubric']], manifest)
    expected = agent_pin.challenge(job['agent'], predecessor_text=predecessor)['expected']
    trace[0]['message']['content'][0]['text'] = expected
    command = trace[0]['message']['content'][1]['input']['command']
    trace[0]['message']['content'][1]['input']['command'] = command.replace(
        '.claude/agents/d4d-rubric20-semantic.md', SELECTED.definition_path) + ' --semantic-version 4.0'
    trace.insert(0, {'type': 'system', 'subtype': 'init', 'cwd': '__ISOLATED__'})
    return trace


@pytest.mark.parametrize('context_value', [None, True, False])
def test_explicit_v4_executes_real_isolated_validator_and_pinned_challenge(v4_environment, context_value):
    root, manifest, job, doc = v4_environment
    if context_value is not None:
        job['applicability_context'] = {'human_subjects': context_value}
        revised = current_record(root / job['input'], 20, job['applicability_context'])
        for key in ('rubric', 'project', 'method', 'label', 'd4d_file', 'model'):
            revised[key] = doc[key]
        revised['metadata'].update(doc['metadata'])
        from data_sheets_schema.evaluation_context import context_digest
        revised['metadata']['context_sha256'] = context_digest(revised['applicability_context'])
        doc = upgrade(revised, manifest)
        runner.write_json(runner.PLAN / 'manifest.json', manifest)
    runner.verify_frozen(manifest)
    prompt = runner.job_prompt(manifest, job)
    assert 'Use version 4.0' in prompt and '--semantic-version 4.0' in prompt
    trace = trace_for(doc, manifest, job)
    assert trace[1]['message']['content'][0]['text'] not in prompt
    cli = fake_cli(root / 'fake-claude', doc, trace, run_validator=True)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt['status'] == 'passed', receipt
    assert json.loads((root / job['output']).read_bytes()) == doc


@pytest.mark.parametrize('mutation', ['missing_predecessor', 'different_predecessor', 'wrong_pin', 'changed_bytes',
                                     'missing_selector_pin', 'old_agent', 'old_schema', 'different_definition_sha'])
def test_bad_v4_registration_is_rejected_before_any_cli_call(v4_environment, mutation):
    root, manifest, job, doc = v4_environment
    instrument = manifest['instruments'][job['rubric']]
    if mutation == 'missing_predecessor':
        instrument.pop('predecessor_definition')
    elif mutation == 'different_predecessor':
        instrument['predecessor_definition'] = '.claude/agents/d4d-rubric10-semantic.md'
    elif mutation == 'wrong_pin':
        manifest['pinned_files'][runner.V4_PREDECESSOR] = 'f' * 64
    elif mutation == 'changed_bytes':
        (root / runner.V4_PREDECESSOR).write_text('Different easy predecessor\n')
    elif mutation == 'missing_selector_pin':
        manifest['pinned_files'].pop('src/data_sheets_schema/semantic_instrument.py')
    elif mutation == 'old_agent':
        job['agent'] = 'd4d-rubric20-semantic'
    elif mutation == 'old_schema':
        instrument['schema'] = 'src/download/prompts/rubric20_semantic_schema.json'
    else:
        instrument['definition_sha256'] = 'f' * 64
    with pytest.raises(ValueError):
        runner.run_job(manifest, job, '/must-not-execute')
    assert not (root / job['output']).exists()
    assert not (runner.PLAN / 'attempts').exists()


@pytest.mark.parametrize('echo', ['preamble', 'released_v3'])
def test_new_version_rejects_stale_echo_even_after_claimed_validation(v4_environment, echo):
    root, manifest, job, doc = v4_environment
    trace = trace_for(doc, manifest, job)
    instrument = manifest['instruments'][job['rubric']]
    trace[1]['message']['content'][0]['text'] = (instrument['preamble'] if echo == 'preamble'
                                               else (root / runner.V4_PREDECESSOR).read_text())
    path = root / 'candidate.json'
    path.write_text(json.dumps(doc))
    with pytest.raises(agent_pin.StaleAgentDefinition):
        runner.validate_candidate(path, job, manifest, trace)


@pytest.mark.parametrize('change', ['omit_version', 'version_three', 'old_definition'])
def test_claimed_validator_must_attest_selected_v4_invocation(v4_environment, change):
    root, manifest, job, doc = v4_environment
    trace = trace_for(doc, manifest, job)
    block = trace[1]['message']['content'][1]['input']
    if change == 'omit_version':
        block['command'] = block['command'].removesuffix(' --semantic-version 4.0')
    elif change == 'version_three':
        block['command'] = block['command'].replace('--semantic-version 4.0', '--semantic-version 3.0')
    else:
        block['command'] = block['command'].replace(SELECTED.definition_path, runner.V4_PREDECESSOR)
    path = root / 'candidate.json'
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='successfully validate'):
        runner.validate_candidate(path, job, manifest, trace)


def v4_report_fixture(tmp_path):
    path, inp, context = _real_rating(tmp_path)
    doc = json.loads(path.read_bytes())
    doc['version'] = '4.0'
    for group in doc['categories']:
        for question in group['questions']:
            if question['id'] == 19:
                question['name'] = Q19
    doc['metadata'].update(instrument_sha256=runner.digest(REAL_ROOT / SELECTED.definition_path),
                           rubric_sha256=runner.digest(REAL_ROOT / SELECTED.rubric_path))
    path.write_text(json.dumps(doc))
    return path, inp, context


def test_v4_report_recomputes_evidence_and_names_its_declared_taxonomy(tmp_path):
    from report_semantic_comparison import report
    from tests.test_evaluation.test_semantic_evidence import _row
    path, inp, context = v4_report_fixture(tmp_path)
    text = report([path], evidence_inputs={path: inp}, evidence_contexts={path: context})
    assert 'evaluator-declared v4' in text and 'No mechanical evidence findings' in text
    doc = json.loads(path.read_bytes())
    _row(doc, 'Q1', counts=[{'path': 'creators', 'claimed': 38}])
    path.write_text(json.dumps(doc))
    text = report([path], evidence_inputs={path: inp}, evidence_contexts={path: context})
    assert '1 error(s)' in text and 'count\\_mismatch' in text


@pytest.mark.parametrize('evidence', [{'cited': [{'path': 'creators', 'quoted': 'Fake quote'}]},
                                     {'cited': [{'path': 'creators', 'quote': 42}]},
                                     {'counts': [{'path': 'creators', 'claimed': '1'}]}])
def test_malformed_v4_is_not_reported_clean(tmp_path, evidence):
    from report_semantic_comparison import report
    path, inp, context = v4_report_fixture(tmp_path)
    doc = json.loads(path.read_bytes())
    doc['categories'][0]['questions'][0]['unit_scores'][0].update(evidence)
    path.write_text(json.dumps(doc))
    for inputs, contexts in (({}, {}), ({path: inp}, {path: context})):
        text = report([path], evidence_inputs=inputs, evidence_contexts=contexts)
        assert 'invalid v4 output structure' in text and 'not established' in text
        assert 'No mechanical evidence findings' not in text


def test_v4_taxonomy_never_uses_legacy_regex():
    doc = {'rubric': 'rubric20-semantic', 'version': '4.0',
           'semantic_analysis': {'issues_detected': [issue()]}}
    classified = issue_taxonomy(doc, legacy_classifier=lambda _: pytest.fail('legacy fallback'))
    assert classified['basis'] == 'evaluator_declared_v4'
    assert classified['category_counts'] == {'attribution': 1}
    assert 'evaluator-declared v4' in render_issue_taxonomy(doc)
    doc['semantic_analysis']['issues_detected'][0].pop('category')
    with pytest.raises(ValueError):
        issue_taxonomy(doc, legacy_classifier=lambda _: pytest.fail('legacy fallback'))
    doc['rubric'] = 'rubric10-semantic'
    with pytest.raises(ValueError, match='unsupported'):
        issue_taxonomy(doc)


@pytest.mark.parametrize('version', [[], {}])
@pytest.mark.parametrize('with_input', [False, True])
def test_malformed_version_retains_controlled_report_behavior(tmp_path, version, with_input):
    from report_semantic_comparison import report
    path, inp, context = v4_report_fixture(tmp_path)
    doc = json.loads(path.read_bytes())
    doc['version'] = version
    path.write_text(json.dumps(doc))
    before = path.read_bytes()
    kwargs = {'evidence_inputs': {path: inp}, 'evidence_contexts': {path: context}} if with_input else {}
    text = report([path], **kwargs)
    assert 'No mechanical evidence findings' not in text
    assert '0 error(s)' not in text
    if with_input:
        assert 'invalid declaration' in text and 'not run' in text
    assert path.read_bytes() == before
