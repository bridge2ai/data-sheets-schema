"""Pinned, ordinary local Python protocol fixture. Never a model runtime.

No caller argv/commands are accepted. The sole recipe is assembled by the
supervisor from its exact registered helper policy and neutral text artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import uuid


def main(argv=None):
    from data_sheets_schema import native_attempt_supervisor as supervisor
    from data_sheets_schema import native_attribution_registration as draft
    from data_sheets_schema.api_runner import RunSpec
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--input-format', required=True, choices=['stream-json'])
    args = parser.parse_args(argv)
    raw = Path(args.registration).read_bytes()
    if draft._sha(raw) != args.sha256:
        raise ValueError('neutral runtime registration bytes changed')
    # The parent verifies all authority immediately before Popen. The child
    # verifies these same selected bytes before interpreting its fixed recipe.
    value = supervisor.verified(raw)
    if value.get('execution') != supervisor.EXECUTION or value.get('recipe') != supervisor.RECIPE:
        raise ValueError('only the registered neutral local recipe is executable')
    composition_raw = Path(value['composition']).read_bytes()
    fixture_raw = Path(value['fixture']).read_bytes()
    if draft._sha(composition_raw) != value['composition_sha256'] or draft._sha(fixture_raw) != value['fixture_sha256']:
        raise ValueError('neutral recipe input changed')
    selected = draft._json(composition_raw)
    registration = draft._json(selected['registration_raw_json'])
    spec = RunSpec.from_render_spec(registration['render_spec'], project=registration['project'],
        method=registration['method'], label=registration['label'])
    steps = supervisor.recipe_steps(spec, selected['policy'], supervisor._fixture(fixture_raw))
    if draft._sha(draft._encoded(steps)) != value['steps_sha256']:
        raise ValueError('neutral recipe differs from registered sequence')
    runtime = supervisor._declaration(value['synthetic_runtime'])
    session = str(uuid.uuid5(uuid.NAMESPACE_URL, args.sha256))

    def send(event):
        print(json.dumps(event, ensure_ascii=False, allow_nan=False), flush=True)

    init = draft._json(sys.stdin.readline())
    callback = init['request']['hooks']['PreToolUse'][0]['hookCallbackIds'][0]
    send({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': init['request_id']}})
    draft._json(sys.stdin.readline())
    send({'type': 'system', 'subtype': 'init', 'model': runtime['model'],
        'apiKeySource': 'neutral_fixture_no_auth', 'claude_code_version': runtime['runtime_version'],
        'tools': ['Read', 'Write', 'Bash'], 'session_id': session, 'cwd': os.getcwd()})
    for number, step in enumerate(steps):
        identity, tool, inputs = 'neutral-tool-'+str(number), step['tool'], step['input']
        send({'type': 'assistant', 'session_id': session, 'message': {'id': identity, 'content': [
            {'type': 'tool_use', 'id': identity, 'name': tool, 'input': inputs}]}})
        request_id = 'neutral-request-'+str(number)
        send({'type': 'control_request', 'request_id': request_id, 'request': {
            'subtype': 'hook_callback', 'callback_id': callback, 'input': {
                'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_use_id': identity,
                'cwd': os.getcwd(), 'tool_input': inputs, 'effort': runtime['effort']}}})
        line = sys.stdin.readline()
        if not line:
            return 7
        response = draft._json(line).get('response')
        if not isinstance(response, dict) or response.get('request_id') != request_id or response.get('response') != {}:
            return 8
        try:
            if tool == 'Write':
                with Path(inputs['file_path']).open('x', encoding='utf-8') as stream:
                    stream.write(inputs['content'])
                code, text = 0, '{}'
            elif tool == 'Read':
                code, text = 0, Path(inputs['file_path']).read_text(encoding='utf-8')
            else:
                process = subprocess.run(shlex.split(inputs['command']), capture_output=True, text=True,
                                         timeout=value['deadline_seconds'])
                code, text = process.returncode, process.stdout
                if process.stderr:
                    print(process.stderr, file=sys.stderr, flush=True)
        except Exception as exc:
            code, text = 2, str(exc)
        send({'type': 'user', 'session_id': session, 'tool_use_result': {'exitCode': code, 'stdout': text}, 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': identity, 'is_error': code != 0, 'content': text}]}})
        if code != 0:
            return code
    send({'type': 'result', 'is_error': False, 'terminal_reason': 'completed', 'stop_reason': 'end_turn',
        'usage': runtime['usage'], 'modelUsage': runtime['model_usage'],
        'total_cost_usd': runtime['cost_usd'], 'permission_denials': []})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
