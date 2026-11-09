"""Ordinary Python test peer. No model, native/auth or provider implementation.

Every Bash helper is an actual selected local command. Stage answers are
explicitly synthetic declarations over actual current outer request bytes.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_selection as selected
from data_sheets_schema import source_review
from data_sheets_schema.native_shared_controller import captured_execution_body
from data_sheets_schema.native_model_aliases import model_aliases
from data_sheets_schema.native_runtime_profiles import require_synthetic


class _NeutralAnswers:
    """Answer exact current outer requests; perform no file or runtime effects."""
    def __init__(self, selection, full_raw, quote):
        self.selection = selection
        self.full_raw = full_raw
        self.quote = quote

    def __call__(self, request_raw):
        from data_sheets_schema import native_shared_contract as c
        value = c.strict_json(request_raw, max_bytes=self.selection.bounds()['max_request_bytes'])
        c.exact(value, {'request_sha256', 'payload'}, 'fixture outer request')
        payload = value['payload']
        c.exact(payload, c.OUTER_REQUEST_KEYS, 'fixture outer payload')
        if value['request_sha256'] != c.sha(c.canonical(payload)):
            raise ValueError('fixture outer request hash differs')
        if payload['selection']['sha256'] != self.selection.registration.pin.sha256:
            raise ValueError('fixture request selected a different authority')
        if payload['owner_context']['original_full_yaml'].encode() != self.full_raw:
            raise ValueError('fixture request selected different full bytes')
        if payload['generation_context'] != self.selection.generation_context():
            raise ValueError('fixture request selected different generation context')
        return self.answer_inner(payload['cursor']['kind'], payload['inner_request'])

    def answer_inner(self, kind, inner):
        """Pure reply construction, separately usable by data conformance checks."""
        from data_sheets_schema import native_shared_contract as c
        if kind == 'receipt':
            return c.canonical({'rereceipt': [
                {'path': path, 'unsupported': True,
                 'reason': 'Synthetic receipt uncertainty; independent review required.'}
                for path in inner['requested_paths']]})
        if kind == 'worker':
            shared = json.loads(inner['payload']['shared_context'])
            stage = json.loads(inner['payload']['stage'])
            if shared['original_full'].encode() != self.full_raw:
                raise ValueError('fixture worker full differs')
            paths = stage['assignment']['paths']
            values = []
            for row in stage['inventory']['values']:
                if row['path'] not in paths:
                    continue
                values.append({'path': row['path'], 'claims': [{
                    'text': row['text'], 'verdict': 'supported', 'attributed_to': [],
                    'claim_status': 'fact', 'source_status': 'fact',
                    'evidence': [dict(self.quote)],
                    'reason': 'The fictional source explicitly declares this value and relationship; this is not scientific scoring.'}]})
            return c.canonical({'findings': [], 'summary': 'Synthetic declared review only.',
                'source_review': {'artifact': 'original_full', 'sha256': c.sha(self.full_raw), 'values': values}})
        if kind == 'omission':
            return c.canonical({'format': 'omission_inventory_v1',
                'request_sha256': inner['request_sha256'], 'chunks': [
                    {'chunk': row['chunk'], 'status': 'no_omission',
                     'reason': 'No additional synthetic candidate declared.', 'candidates': []}
                    for row in inner['payload']['chunks']]})
        if kind == 'integration':
            return c.canonical({'kind': 'audit_integration_v2',
                'proposal_index_sha256': inner['index']['sha256'],
                'retain_other_rows_from_index_sha256': inner['index']['sha256'],
                'row_replacements': [], 'finding_decisions': [], 'new_findings': [],
                'summary': 'Synthetic declared integration only.', 'omission_dispositions': []})
        raise ValueError('fixture has no answer for cursor kind ' + str(kind))


class _OmissionAnswers:
    """Answer exact current outer requests; perform no file or runtime effects."""
    def __init__(self, selection, full_raw, quote):
        self.selection = selection
        self.full_raw = full_raw
        self.quote = quote

    def __call__(self, request_raw):
        from data_sheets_schema import native_shared_contract as c
        value = c.strict_json(request_raw, max_bytes=self.selection.bounds()['max_request_bytes'])
        c.exact(value, {'request_sha256', 'payload'}, 'fixture outer request')
        payload = value['payload']
        c.exact(payload, c.OUTER_REQUEST_KEYS, 'fixture outer payload')
        if value['request_sha256'] != c.sha(c.canonical(payload)):
            raise ValueError('fixture outer request hash differs')
        if payload['selection']['sha256'] != self.selection.registration.pin.sha256:
            raise ValueError('fixture request selected a different authority')
        if payload['owner_context']['original_full_yaml'].encode() != self.full_raw:
            raise ValueError('fixture request selected different full bytes')
        if payload['generation_context'] != self.selection.generation_context():
            raise ValueError('fixture request selected different generation context')
        return self.answer_inner(payload['cursor']['kind'], payload['inner_request'])

    def answer_inner(self, kind, inner):
        """Pure reply construction, separately usable by data conformance checks."""
        from data_sheets_schema import native_shared_contract as c
        if kind == 'receipt':
            return c.canonical({'rereceipt': [
                {'path': path, 'unsupported': True,
                 'reason': 'Synthetic receipt uncertainty; independent review required.'}
                for path in inner['requested_paths']]})
        if kind == 'worker':
            shared = json.loads(inner['payload']['shared_context'])
            stage = json.loads(inner['payload']['stage'])
            if shared['original_full'].encode() != self.full_raw:
                raise ValueError('fixture worker full differs')
            paths = stage['assignment']['paths']
            values = []
            for row in stage['inventory']['values']:
                if row['path'] not in paths:
                    continue
                values.append({'path': row['path'], 'claims': [{
                    'text': row['text'], 'verdict': 'supported', 'attributed_to': [],
                    'claim_status': 'fact', 'source_status': 'fact',
                    'evidence': [dict(self.quote)],
                    'reason': 'The fictional source explicitly declares this value and relationship; this is not scientific scoring.'}]})
            return c.canonical({'findings': [], 'summary': 'Synthetic declared review only.',
                'source_review': {'artifact': 'original_full', 'sha256': c.sha(self.full_raw), 'values': values}})
        if kind == 'omission':
            rows = [{'chunk': row['chunk'], 'status': 'no_omission',
                     'reason': 'No additional fictional candidate declared.', 'candidates': []}
                    for row in inner['payload']['chunks']]
            target = next(row for row in inner['payload']['chunks'] if row['source'] == 'neutral.txt')
            prefix = inner['request_sha256'][:16]
            quote = 'The fictional description also states: release notes are illustrative and optional.'
            candidates = [{'id': f'fixture-{prefix}-{index}', 'kind': 'omission',
                'source': 'neutral.txt', 'quote': quote,
                'target': {'owner': '', 'slot_chain': ['description']},
                'missing_information': ['Illustrative release notes.', 'Optional release notes.',
                    'An intentionally redundant proposed detail.'][index],
                'scope_basis': 'Explicit fictional fixture declaration; novelty and support remain unverified.'}
                for index in range(3)]
            next(row for row in rows if row['chunk'] == target['chunk']).update(status='omission', candidates=candidates)
            return c.canonical({'format': 'omission_inventory_v1',
                'request_sha256': inner['request_sha256'], 'chunks': rows})
        if kind == 'integration':
            candidates = inner['omission_check']['declared_candidates']
            if len(candidates) != 3:
                raise ValueError('variant requires exactly its three captured candidates')
            # Derive identity and evidence only from this actual captured request.
            candidates = sorted(candidates, key=lambda row: row['id'])
            evidence = [{'source': row['source'], 'chunk': row['chunk'], 'quote': row['quote']}
                        for row in candidates]
            dispositions = [{'candidate_id': row['id'], 'action': 'retain' if i < 2 else 'drop',
                'reason': 'Invented mechanical disposition; no scientific adjudication.',
                'evidence': [] if i < 2 else [evidence[i]]} for i, row in enumerate(candidates)]
            finding = {'severity': 'medium', 'record': 'full', 'slot': 'description',
                'issue': 'Merged fictional release-note omission declarations.', 'kind': 'omission',
                'omission_candidates': [row['id'] for row in candidates[:2]], 'evidence': [evidence[0]]}
            return c.canonical({'kind': 'audit_integration_v2',
                'proposal_index_sha256': inner['index']['sha256'],
                'retain_other_rows_from_index_sha256': inner['index']['sha256'],
                'row_replacements': [], 'finding_decisions': [], 'new_findings': [finding],
                'summary': 'Invented merged/dropped declarations; scientific validity unverified.',
                'omission_dispositions': dispositions})
        raise ValueError('fixture has no answer for cursor kind ' + str(kind))


def _write_file(path, content):
    """Emulate the granted Write's parent creation, without prepopulating data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main():
    attempt = Path(os.environ['CLAUDE_CONFIG_DIR']).parent
    value = captured_execution_body((attempt / 'registration.json').read_bytes())
    runtime = value['runtime']
    require_synthetic(runtime)
    aliases = model_aliases(runtime)
    assert os.getcwd() == value['working_directory']
    assert sys.argv[1:] == value['argv'][1:]
    assert all(os.environ.get(k) == v for k, v in value['environment'].items())
    assert not any(k in os.environ for k in ('ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'CBORG_API_KEY'))
    composition = c.strict_json(value['composition_raw_json'].encode(), max_bytes=c.HARD_LIMITS['request_bytes'])
    selection = selected.capture(c.parse_selection(composition['selection_raw_json'].encode())['registration_path'])
    root = Path(composition['instruction_path']).parent
    fixture = c.strict_json((root / 'synthetic-seeds.json').read_bytes(), max_bytes=c.HARD_LIMITS['request_bytes'])
    if fixture['answer_fixture'] == 'neutral':
        answers_type = _NeutralAnswers
    elif fixture['answer_fixture'] == 'omission':
        answers_type = _OmissionAnswers
    else:
        raise ValueError('unknown synthetic native answer fixture')
    full = fixture['full'].encode(); receipt = fixture['receipt']
    quote = {'source': 'neutral.txt', 'chunk': fixture['chunk_id'], 'quote': fixture['source_text'].strip()}
    answer = answers_type(selection, full, quote)
    paths = composition['render_spec']['agentic_artifact_paths']
    commands = composition['policy']['native_shared_helpers']
    session = '43540000-0000-4000-8000-000000000001'
    number = 0
    def send(event):
        print(json.dumps(event, allow_nan=False), flush=True)
    init = json.loads(sys.stdin.readline())
    callback = init['request']['hooks']['PreToolUse'][0]['hookCallbackIds'][0]
    send({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': init['request_id']}})
    json.loads(sys.stdin.readline())
    send({'type': 'system', 'subtype': 'init', 'model': runtime['model'], 'apiKeySource': 'none',
        'claude_code_version': runtime['executable']['init_version'], 'tools': ['Read', 'Write', 'Bash'],
        'session_id': session, 'cwd': os.getcwd()})

    def tool(name, inputs, allowed=(0,)):
        nonlocal number
        number += 1
        identity = 'shared-test-' + str(number)
        send({'type': 'assistant', 'session_id': session, 'message': {'model': aliases['returned'], 'content': [
            {'type': 'tool_use', 'id': identity, 'name': name, 'input': inputs}]}})
        request_id = 'callback-' + identity
        send({'type': 'control_request', 'request_id': request_id, 'request': {'subtype': 'hook_callback',
            'callback_id': callback, 'input': {'hook_event_name': 'PreToolUse', 'tool_name': name,
                'tool_use_id': identity, 'cwd': os.getcwd(), 'tool_input': inputs, 'effort': runtime['effort']}}})
        line = sys.stdin.readline()
        if not line: raise RuntimeError('test peer was stopped before callback grant')
        response = json.loads(line)['response']
        if response.get('request_id') != request_id or response.get('response') != {}:
            raise RuntimeError('test peer callback denied')
        if name == 'Bash':
            proc = subprocess.run(shlex.split(inputs['command']), capture_output=True, text=True, timeout=180)
            code, text = proc.returncode, proc.stdout
            if proc.stderr: print(proc.stderr, file=sys.stderr, flush=True)
            metadata = {'exitCode': code, 'stdout': text}
        elif name == 'Read':
            text = Path(inputs['file_path']).read_text()
            lines = text.split('\n')
            metadata = {'type': 'text', 'file': {'filePath': inputs['file_path'], 'content': text,
                'numLines': len(lines), 'startLine': 1, 'totalLines': len(lines)}}
            code, text = 0, '\n'.join(f'{i}\t{line}' for i, line in enumerate(lines, 1))
        elif name == 'Write':
            path = Path(inputs['file_path']); existed = path.exists()
            old = path.read_text() if existed else None
            _write_file(path, inputs['content'])
            metadata = {'type': 'update' if existed else 'create', 'filePath': str(path),
                'content': inputs['content'], 'originalFile': old, 'userModified': False, 'structuredPatch': []}
            code, text = 0, ('The file ' + str(path) + ' has been updated successfully.' if existed
                            else 'File created successfully at: ' + str(path))
        else: raise AssertionError(name)
        send({'type': 'user', 'session_id': session, 'tool_use_result': metadata, 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': identity, 'is_error': bool(code), 'content': text}]}})
        if code not in allowed: raise RuntimeError('genuine selected helper failed: ' + str(inputs))
        return code, text
    def helper(name, allowed=(0,)):
        return tool('Bash', {'command': commands[name]}, allowed)
    def read(path): return tool('Read', {'file_path': str(path)})
    def write(path, text): return tool('Write', {'file_path': str(path), 'content': text})

    for role in ('bundle', 'chunk_manifest', 'source_manifest'):
        read(selection.document()['inputs'][role]['path'])
    helper('chunk_check'); helper('source_scope')
    write(paths['full'], fixture['full']); write(paths['receipt'], receipt)
    for name in ('full_schema', 'full_terms', 'phase1_receipts'): helper(name)

    def advance_to(boundary):
        for _ in range(40):
            _, text = helper('advance')
            result = json.loads(text)
            state = result['state']
            if state == boundary: return
            if state == 'awaiting_response':
                journal = json.loads(Path(selection.role('journal')).read_bytes())
                records = [json.loads(Path(pin['path']).read_bytes()) for pin in journal['records']]
                admitted = [row for row in records if row['record_type'] == 'request_admitted'][-1]['payload']
                request_path = admitted['request']['path']
                read(request_path)
                request_raw = Path(request_path).read_bytes()
                payload = json.loads(request_raw)['payload']
                write(payload['response']['path'], answer(request_raw).decode())
            elif state not in ('request_ready', 'receipt_zero_work'):
                raise AssertionError('unexpected actual stage state ' + state)
        raise AssertionError('bounded synthetic peer exceeded its stage loop')
    advance_to('await_core')
    for name in ('derive_core', 'core_schema', 'pair', 'original_source_inventory'): helper(name)
    advance_to('assembly_complete')
    helper('audit_evidence')
    for name in ('derive_final_core', 'full_schema', 'full_terms', 'core_schema', 'pair', 'final_receipts', 'final_scope', 'final_source_inventory'):
        helper(name)
    inventory = source_review.inventory(fixture['full'], 'final_full')
    review = {'artifact': 'final_full', 'sha256': inventory['sha256'], 'values': [
        {'path': row['path'], 'claims': [{'text': row['text'], 'verdict': 'supported',
            'attributed_to': ['neutral.txt'], 'claim_status': 'fact', 'source_status': 'fact',
            'evidence': [quote], 'reason': 'Explicit fictional source declaration, not a scientific assessment.'}]}
        for row in inventory['values']]}
    report = '# Reconciliation\n\nSynthetic values retained.\n\n## Evidence assertions\n```json\n' + json.dumps(
        {'claims': [], 'source_review': review}) + '\n```\n'
    if fixture['correction']:
        bad = report.replace('"attributed_to": ["neutral.txt"]', '"attributed_to": ["neutral"]', 1)
        assert bad != report
        write(paths['report'], bad)
        code, _ = helper('draft', (1,)); assert code == 1
        helper('final_source_inventory')
    write(paths['report'], report)
    helper('draft'); helper('final_evidence'); helper('recorder')
    send({'type': 'result', 'session_id': session, 'is_error': False, 'terminal_reason': 'completed', 'stop_reason': 'end_turn',
        'usage': {'input_tokens': 10, 'output_tokens': 2, 'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0},
        'modelUsage': {runtime['model']: {'inputTokens': 10, 'outputTokens': 2, 'cacheReadInputTokens': 0,
            'cacheCreationInputTokens': 0, **runtime['limits']}}, 'total_cost_usd': 0, 'permission_denials': []})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
