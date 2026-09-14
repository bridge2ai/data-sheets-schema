"""The registered 32k API rating must stream and account for a complete reply."""
import hashlib
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import anthropic
import httpx
import pytest

from data_sheets_schema.evaluation.evaluate_d4d_llm import D4DLLMEvaluator, LLMEvaluationConfig
from tests.judge_fixtures import judge_reply

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    'streaming_judge_budget', ROOT / 'notes/matched_cborg_2026-09-13/budgeted_cborg.py')
budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(budget)
PRICES = {'input': '0.000005', 'output': '0.000025',
          'cache_read': '0.0000005', 'cache_write': '0.00000625'}


def setup_judge(tmp_path, rubric, *, defect=None, guarded=True, streaming=True):
    calls = []
    replies = []

    def respond(request):
        body = json.loads(request.content)
        calls.append((request.url.path, body))
        if request.url.path.endswith('/count_tokens'):
            return httpx.Response(200, json={'input_tokens': 500})
        assert request.url.path == '/v1/messages'
        assert body['stream'] is True
        contract = json.loads(body['messages'][0]['content'].split('```json\n')[1].split('\n```')[0])
        reply = judge_reply(contract, rubric, 'EXTERNAL_CLINICAL', 'manual')
        text = json.dumps(reply)
        replies.append(text)
        events = [
            {'type': 'message_start', 'message': {'id': 'offline', 'type': 'message', 'role': 'assistant',
                'model': body['model'], 'content': [], 'stop_reason': None, 'stop_sequence': None,
                'usage': {'input_tokens': 17, 'output_tokens': 1}}},
            {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}},
            {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}},
            {'type': 'content_block_stop', 'index': 0},
            {'type': 'message_delta', 'delta': {'stop_reason': None if defect == 'reason' else 'end_turn',
                'stop_sequence': None}, 'usage': {'output_tokens': 2048}},
        ]
        if defect != 'stop':
            events.append({'type': 'message_stop'})
        wire = ''.join('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n' for event in events)
        return httpx.Response(200, content=wire, headers={'content-type': 'text/event-stream'})

    sdk = anthropic.Anthropic(api_key='offline', base_url='http://offline.invalid', max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    ledger = budget.Ledger(tmp_path / 'billing.json', manifest_sha256='offline-evaluation',
                           total_cap=200, attempt_cap=5)
    client = budget.CappedClient(sdk, ledger=ledger, attempt='one-rating', evidence=tmp_path / 'requests',
        model='claude-opus-5', prices=PRICES, verify=lambda: None) if guarded else sdk
    config = LLMEvaluationConfig(model='claude-opus-5', max_tokens=32000, stream=streaming,
        error_dir=tmp_path / 'errors', attempts_dir=tmp_path / 'accepted')
    evaluator = D4DLLMEvaluator(config, context={'human_subjects': False}, client=client)
    path = tmp_path / 'input.yaml'
    path.write_text('CoreDatasetCollection:\n  resources:\n    - id: urn:example:first\n    - id: urn:example:second\n')
    return evaluator, path, client, sdk, ledger, calls, replies


@pytest.mark.parametrize('rubric', ['rubric10', 'rubric20'])
def test_real_sdk_32k_stream_preserves_request_contract_and_settles(tmp_path, rubric):
    evaluator, path, client, sdk, ledger, calls, replies = setup_judge(tmp_path, rubric)
    try:
        result = evaluator.evaluate_file(path, 'EXTERNAL_CLINICAL', 'manual', rubric)[rubric]
        client.messages.require_active()
        assert [p for p, _ in calls] == ['/v1/messages/count_tokens', '/v1/messages']
        sent = calls[-1][1]
        assert sent['model'] == 'claude-opus-5' and sent['max_tokens'] == 32000
        assert 'temperature' not in sent
        assert sent['system'] == evaluator._build_system_prompt(rubric)
        assert path.read_text() in sent['messages'][0]['content']
        assert len(result['evaluation_scope']['units']) == 2
        meta = result['metadata']
        assert meta['d4d_file_hash'] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert meta['instrument_sha256'] == hashlib.sha256(sent['system'].encode()).hexdigest()
        assert meta['response_transport'] == 'streaming'
        state = json.loads(ledger.path.read_bytes())
        assert len(state['requests']) == 1 and state['requests'][0]['status'] == 'settled'
        assert Decimal(state['requests'][0]['cost_usd']) == Decimal('0.051285')
        accepted = list((tmp_path / 'accepted').glob('*.json'))
        assert len(accepted) == 1 and json.loads(accepted[0].read_bytes())['raw_response'] == replies[0]
        assert len(list((tmp_path / 'requests').rglob('response.json'))) == 1
    finally:
        sdk.close()


@pytest.mark.parametrize('rubric', ['rubric10', 'rubric20'])
@pytest.mark.parametrize('defect', ['stop', 'reason'])
def test_incomplete_stream_preserves_original_and_blocks_more_spending(tmp_path, rubric, defect):
    evaluator, path, client, sdk, ledger, calls, replies = setup_judge(tmp_path, rubric, defect=defect)
    try:
        with pytest.raises(RuntimeError, match='completion is unverified'):
            evaluator.evaluate_file(path, 'EXTERNAL_CLINICAL', 'manual', rubric)
        state = json.loads(ledger.path.read_bytes())
        assert len(state['requests']) == 1 and state['requests'][0]['status'] == 'pending'
        original = list((tmp_path / 'requests').rglob('response.json'))
        assert len(original) == 1
        assert json.loads(original[0].read_bytes())['content'][0]['text'] == replies[0]
        assert not (tmp_path / 'accepted').exists()
        with pytest.raises(budget.BudgetStop, match='previously stopped'):
            client.messages.create(model='claude-opus-5', max_tokens=1,
                                   messages=[{'role': 'user', 'content': 'forbidden later request'}])
        assert len(calls) == 2
    finally:
        sdk.close()


def test_unwrapped_stream_without_stop_is_not_accepted(tmp_path):
    evaluator, path, _, sdk, _, _, replies = setup_judge(tmp_path, 'rubric10', defect='stop', guarded=False)
    try:
        with pytest.raises(RuntimeError, match='Response saved'):
            evaluator.evaluate_file(path, 'EXTERNAL_CLINICAL', 'manual', 'rubric10')
        errors = list((tmp_path / 'errors').glob('*.json'))
        assert len(errors) == 1
        assert json.loads(errors[0].read_bytes())['response'] == replies[0]
        assert not (tmp_path / 'accepted').exists()
    finally:
        sdk.close()


def test_streaming_is_explicit_and_nonstreaming_limit_is_not_silently_changed(tmp_path):
    assert LLMEvaluationConfig().stream is False
    evaluator, path, _, sdk, _, calls, _ = setup_judge(tmp_path, 'rubric10', guarded=False, streaming=False)
    try:
        with pytest.raises(RuntimeError, match='Streaming is required'):
            evaluator.evaluate_file(path, 'EXTERNAL_CLINICAL', 'manual', 'rubric10')
        assert calls == []
    finally:
        sdk.close()
