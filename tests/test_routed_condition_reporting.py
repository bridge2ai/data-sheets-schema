"""Captured selection attribution and launcher scope; no model executions."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import socket

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, provenance, runs, shared_generation as shared
from data_sheets_schema.cli import cli
from data_sheets_schema.constants import PROJECTS
from tests.test_source_heading_runtime_api import draft_files, selected_spec  # noqa: F401


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})


@pytest.fixture(scope='module', params=['declared_heading_spans_v1', 'captured_json_values_v1'])
def routed(request, tmp_path_factory, draft_files):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
        spec = selected_spec(tmp_path_factory.mktemp(request.param), draft_files, mode=request.param)
        spec.bind_api_header_values(api._model_settings())
        render = spec.render_spec()
        record = {'run': {key: getattr(spec, key) for key in ('project', 'arm', 'method', 'label', 'condition')},
                  'prompts': provenance.prompt_facts(spec.prompt_files, spec.instruction, render)}
        record['run']['generation_id'] = 'synthetic-reporting-only'
        record['shared_generation'] = {'protocol': 'shared_generation_v2',
            'generation_id': record['run']['generation_id'],
            'authority': {'registration': deepcopy(render['shared_generation_registration'])},
            'routing': {'generation_id': record['run']['generation_id'],
                        'registration_sha256': render['shared_generation_registration']['sha256']}}
        return spec, record


def repin(record, mutate):
    spec = record['prompts']['request']['spec']
    pin = spec['shared_generation_registration']
    value = json.loads(pin['raw_json'])
    mutate(value)
    raw = shared.canonical(value)
    pin.update(raw_json=raw.decode(), sha256=hashlib.sha256(raw).hexdigest())
    record['shared_generation']['authority']['registration'] = deepcopy(pin)
    record['shared_generation']['routing']['registration_sha256'] = pin['sha256']


@pytest.mark.parametrize('a,b,expected,comparable', [
    ('generic_v9', 'generic_v10_source_heading_routing_v1', ['base', 'routing'], False),
    ('generic_v10', 'generic_v10_source_heading_routing_v1', ['routing'], True),
    ('generic_v10_source_heading_routing_v1', 'generic_v10_source_heading_span_v1', ['routing'], True),
    ('generic_v9', 'generic_v10', ['base'], True),
])
def test_routing_axis_is_reported(a, b, expected, comparable):
    assert api.condition_delta(a, b) == expected
    assert api.comparable_conditions(a, b) is comparable
    assert api.condition_delta(a, b, {'a'*64}, {'b'*64}) == [*expected, 'assembly']
    if len(expected) > 1:
        assert 'routing' in api.confounded_note(a, b)


def test_real_registered_request_attributes_route_without_live_authorities(routed, tmp_path, monkeypatch):
    spec, record = routed
    original = deepcopy(record)
    def refuse(*a, **k):
        pytest.fail('historical attribution must not reopen or revalidate current resources')
    with monkeypatch.context() as patch:
        patch.setattr(shared, 'descriptor', refuse)
        patch.setattr(shared, 'parse_registration', refuse)
        patch.setattr(Path, 'read_bytes', refuse)
        patch.setattr(Path, 'resolve', refuse)
        assert runs._recorded_routing_condition(record) == (spec.condition, None)
        assert runs.condition_contradiction(record, spec.label) is None
        assert runs.condition_unfalsifiable(record, spec.label) is False
    assert record == original
    folder = tmp_path / f'{spec.method}_core' / spec.label
    folder.mkdir(parents=True)
    (folder / f'{spec.project}_provenance.yaml').write_text(yaml.safe_dump(record))
    assert runs.condition_of(spec.method, spec.label, spec.project, concat_dir=tmp_path) == spec.condition


def test_shared_prompt_alone_cannot_attest_routing(routed):
    spec, original = routed
    record = deepcopy(original)
    record['prompts'].pop('request')
    record.pop('shared_generation')
    assert runs._recorded_routing_condition(record) == (None, None)
    assert runs.condition_contradiction(record, spec.label) is None
    assert runs.condition_unfalsifiable(record, spec.label) is True
    assert runs.condition_from_prompt_paths([str(api.GENERIC_PROMPT_V10)]) == 'generic_v10'


@pytest.mark.parametrize('mutation', ['raw-pin', 'mode', 'selected-condition', 'run', 'receipt', 'policy',
    'assets', 'generation', 'null-summary', 'null-spec', 'null-authority', 'tuple-bool', 'descriptor-bool',
    'null-admission', 'null-request', 'list-request', 'empty-request', 'request-arm'])
def test_corrupt_or_crossed_selected_metadata_is_not_silently_base(routed, mutation):
    spec, original = routed
    record = deepcopy(original)
    request = record['prompts']['request']['spec']
    if mutation == 'raw-pin': request['shared_generation_registration']['sha256'] = '0'*64
    elif mutation == 'mode': repin(record, lambda v: v['routing'].update(mode='other'))
    elif mutation == 'selected-condition': repin(record, lambda v: v['selection'].update(condition='generic_v10'))
    elif mutation == 'run': repin(record, lambda v: v['run'].update(project='OTHER'))
    elif mutation == 'receipt': repin(record, lambda v: v['receipt'].update(condition='generic_v10'))
    elif mutation == 'policy': request['api_playbook_sha256'] = '0'*64
    elif mutation == 'assets': request['shared_generation_assets'] = {}
    elif mutation == 'generation': record['shared_generation']['generation_id'] = 'foreign'
    elif mutation == 'null-summary': record['shared_generation'] = None
    elif mutation == 'null-spec': record['prompts']['request']['spec'] = None
    elif mutation == 'null-authority': record['shared_generation']['authority'] = None
    elif mutation == 'tuple-bool': request['shared_generation_version'] = True
    elif mutation == 'descriptor-bool': repin(record, lambda v: v['selection'].update(version=True))
    elif mutation == 'null-admission': record['shared_generation']['routing'] = None
    elif mutation in ('null-request', 'list-request', 'empty-request'):
        record.pop('shared_generation')
        record['prompts']['request'] = {'null-request': None, 'list-request': [], 'empty-request': {}}[mutation]
    elif mutation == 'request-arm': request['arm'] = 'de_novo' if spec.arm != 'de_novo' else 'augmented'
    result = runs.condition_contradiction(record, spec.label)
    assert result and 'selected routing' in result['disagrees_with'] and result['declared'] is False


@pytest.mark.parametrize('omitted', ['summary', 'admission'])
def test_missing_optional_summaries_do_not_invent_a_contradiction(routed, omitted):
    spec, original = routed
    record = deepcopy(original)
    if omitted == 'summary':
        record.pop('shared_generation')
    else:
        record['shared_generation'].pop('routing')
    assert runs._recorded_routing_condition(record) == (spec.condition, None)
    assert runs.condition_contradiction(record, spec.label) is None


@pytest.mark.parametrize('payload', ['{"x":1,"x":2}', '{"x":1e999}', '{"x":NaN}',
                                  '{"x":'+'['*102+'0'+']'*102+'}'])
def test_recorded_registration_json_has_finite_closed_resource_behavior(routed, payload):
    spec, original = routed
    record = deepcopy(original)
    pin = record['prompts']['request']['spec']['shared_generation_registration']
    pin.update(raw_json=payload, sha256=hashlib.sha256(payload.encode()).hexdigest())
    assert runs.condition_contradiction(record, spec.label)['disagrees_with']['selected routing']


def test_observed_base_and_run_claim_remain_independent(routed):
    spec, original = routed
    record = deepcopy(original)
    other = next(c for c in api.SOURCE_HEADING_CONDITIONS if c != spec.condition)
    record['run']['condition'] = other
    assert runs.condition_contradiction(record, spec.label)['disagrees_with']['selected routing'] == spec.condition
    record = deepcopy(original)
    record['prompts']['files'] = [{'path': str(api.GENERIC_PROMPT_V9)}]
    assert runs.condition_contradiction(record, spec.label)['disagrees_with']['hashed prompt'] == 'generic_v9'


@pytest.mark.parametrize('condition', sorted(api.SOURCE_HEADING_CONDITIONS))
def test_label_prefix_is_not_an_extra_condition_but_separate_tokens_are(condition):
    assert runs.condition_from_label(f'2026-10-06_{condition}_rep1') == condition
    assert runs.condition_from_label(f'2026-10-06-{condition.replace("_", "-")}-rep1') == condition
    for extra in ('generic_v10', 'generic_v9', 'generic_v99', 'tuned', 'generic'):
        assert runs.condition_from_label(f'{condition}--{extra}') is None
        assert runs.condition_from_label(f'{extra}--{condition}') is None


def test_api_only_receipt_tuple_never_becomes_native_or_default(routed):
    spec, _ = routed
    assert spec.writes_receipt and spec.receipt_completion_version == 3
    for runtime in ('Claude Code', 'Claude Code (direct)', 'Codex CLI'):
        with pytest.raises(ValueError, match='explicit routing/API27/playbook3/receipt3 tuple'):
            replace(spec, runtime=runtime)
    with pytest.raises(ValueError, match='routing/API27 requires shared generation 2'):
        replace(spec, shared_generation_version=0)
    with pytest.raises(ValueError, match='explicit routing/API27/playbook3/receipt3 tuple'):
        replace(spec, receipt_completion_version=0)
    with pytest.raises(ValueError, match='immutable registration'):
        replace(spec, shared_generation_registration=None)


@pytest.mark.parametrize('command', ['render-prompt', 'plan', 'run', 'batch'])
def test_condition_help_qualifies_api_only_selection(command):
    result = CliRunner().invoke(cli, ['api', command, '--help'])
    assert result.exit_code == 0
    text = ' '.join(result.output.split())
    assert 'registered API27/shared2/playbook3/receipt3' in text
    assert 'do not support native/direct launchers' in text


def test_real_registered_instructions_preserve_project_and_request_scope(routed, tmp_path):
    spec, _ = routed
    projects = tuple(dict.fromkeys((*PROJECTS, 'VOICE_PEDIATRIC')))
    for project in projects:
        directory = tmp_path / project; directory.mkdir()
        reg = json.loads(spec.shared_generation_registration)
        reg['registration_path'] = str(directory / 'registration.json')
        reg['run']['project'] = project; reg['inputs']['project'] = project
        raw = shared.canonical(reg); Path(reg['registration_path']).write_bytes(raw)
        selected = replace(spec, project=project, out_dir=directory/'output', shared_generation_registration=raw.decode())
        instruction = selected.instruction
        assert str(selected.bundle) in instruction
        assert selected.writes_receipt
        for other in projects:
            if other != project:
                assert re.search(rf'\b{re.escape(other)}\b', instruction) is None
                assert f'{other}_preprocessed.txt' not in instruction
        assert set(re.findall(r'data/preprocessed/concatenated/[\w.-]+', instruction)) <= {str(selected.bundle)}
        phase = api.build_phase(selected, 'full', carry={})
        shared.require_routing_context(selected, phase.messages)
