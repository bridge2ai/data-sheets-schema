"""Exercise actual native Bash permissions with a scripted local provider.

No provider key is read. All responses and token counts are synthetic. Stub
CLI/validator modules print markers, so even an incorrectly admitted negative
case cannot change corpus selections or contact ontology services. The freeze
program exercises real exclusive writes to synthetic files inside the probe.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace

import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from budgeted_cborg import Ledger
from native_proxy import NativeProxy
from run_native_canary import execute_child, verified_executable, sha, command_history
from native_command_policy import build_command_policy, command_guidance, permission_arguments
from data_sheets_schema import api_runner, chunking


def fixture(work):
    bundle = work / 'source.txt'
    bundle.write_text('Synthetic external clinical cohort protocol.\n' * 12)
    manifest = work / "source child's manifest.yaml"
    manifest.write_text(yaml.safe_dump({'projects': {'EXTERNAL': {
        'bundle': str(bundle), 'sources': [{'id': 'protocol', 'source_type': 'documentation', 'priority': 1}]}},
        'naming': {'EXTERNAL': {'canonical_label': 'External cohort'}}}))
    chunks, _ = chunking.write_manifest_for(bundle)
    spec = api_runner.RunSpec(project='EXTERNAL', arm='baseline', method='claudecode_agent',
        bundle=bundle, manifest=manifest, chunk_manifest=chunks, out_dir=work / 'outputs',
        label='offline-native-permissions', condition='generic_v9', profile='neutral',
        render_version=12, runtime='Claude Code')
    instruction = work / 'instruction.md'
    instruction.write_text(spec.instruction)
    job = {'id': 'EXTERNAL_agentic_rep1', 'instruction': str(instruction),
        'manifest': str(manifest), 'bundle': str(bundle), 'render_spec': spec.render_spec(),
        'output_directories': [str(spec.full_path.parent), str(spec.core_path.parent)],
        'outputs': {'full': str(spec.full_path), 'core': str(spec.core_path), 'report': str(spec.report_path)}}
    for path in (spec.full_path, spec.core_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('id: https://example.org/offline\n')
    spec.report_path.write_text('Synthetic offline report.\n')
    stubs = {
        'linkml/__init__.py': '', 'linkml/validator/__init__.py': '',
        'linkml/validator/cli.py': 'def cli(): print("SCHEMA_STUB_OK")\n',
        'linkml_term_validator/__init__.py': '',
        'linkml_term_validator/cli.py': 'def main(): print("TERMS_STUB_OK")\n',
        'data_sheets_schema/__init__.py': '',
        'data_sheets_schema/cli.py': 'print("CLI_STUB_OK")\n',
        'data_sheets_schema/source_review.py': 'print("SOURCE_REVIEW_STUB_OK")\n',
        'data_sheets_schema/identifiers.py': 'def uriorcurie_slots(): return set()\n',
        'data_sheets_schema/grounding.py': 'def check_run(*args): return {"checked": True, "distinct": 1, '
            '"findings": [{"kind": "absent", "identifier": "example:offline"}]}\n',
        'data_sheets_schema/report_claims.py': 'def declared_slots(): return set()\n'
            'def check_report(*args): return {"findings": ["REPORT_STUB_OK"]}\n',
    }
    for name, content in stubs.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    policy = build_command_policy(job, sys.executable, work)
    return job, policy


def cases_for(job, policy):
    cases = [{'id': f'program_{i}', 'command': command, 'allow': True}
             for i, command in enumerate(policy['command_examples'])]
    cli = [policy['python'], '-m', 'data_sheets_schema.cli']
    for i, path in enumerate(policy['manifest_paths']):
        cases.append({'id': f'manifest_{i}', 'allow': True,
                      'command': shlex.join([*cli, '--manifest', path, 'receipts', 'check'])})
    cases.append({'id': 'roster_without_manifest', 'allow': True,
                  'command': shlex.join([*cli, 'agents', 'playbook'])})
    cases.append({'id': 'module', 'allow': True, 'command': shlex.join([
        policy['python'], '-m', 'data_sheets_schema.source_review', '--record', job['outputs']['full']])})
    # dontAsk also admits the runtime's built-in read-only commands, even
    # when no explicit Bash grant names them (#2049).
    cases.extend([
        {'id': 'builtin_readonly_pipeline', 'allow': True,
         'command': shlex.join(['grep', '-n', 'Synthetic', job['bundle']]) + ' | head -1'},
        {'id': 'builtin_readonly_count', 'allow': True,
         'command': shlex.join(['wc', '-l', job['bundle']])},
        {'id': 'readonly_quoted_manifest', 'allow': True,
         'command': shlex.join(['grep', '-n', 'EXTERNAL', job['manifest']])},
        {'id': 'readonly_sed_window', 'allow': True,
         'command': shlex.join(['sed', '-n', '1,2p', job['bundle']])},
        {'id': 'readonly_head_tail', 'allow': True,
         'command': shlex.join(['head', '-n', '2', job['bundle']]) + ' | tail -n 1'},
        {'id': 'readonly_cat', 'allow': True,
         'command': shlex.join(['cat', job['bundle']])},
        {'id': 'readonly_regex', 'allow': True,
         'command': shlex.join(['grep', '-n', r'^Synthetic.*\.$', job['bundle']])},
        {'id': 'readonly_no_match', 'allow': True,
         'command': shlex.join(['grep', '-n', 'NOT_PRESENT_IN_FIXTURE', job['bundle']])},
    ])
    bad = {
        'outside_roster': [*cli, '--manifest', job['manifest'], 'runs', 'select'],
        'other_manifest': [*cli, '--manifest', '/another/manifest.yaml', 'runs', 'list'],
        'arbitrary_python': [policy['python'], '-c', 'print("ARBITRARY")'],
    }
    report = next(p['code'] for p in policy['programs'] if 'check_report' in p['code'])
    bad['modified_program'] = [policy['python'], '-c', report + '\nprint("EXTRA")']
    bad['other_record'] = [policy['python'], '-c', report.replace(job['outputs']['full'], '/another/record.yaml')]
    cases.extend({'id': name, 'allow': False, 'command': shlex.join(argv)} for name, argv in bad.items())
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--claude-executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--project-settings-mode', choices=('broad', 'absent'), default='broad',
                        help='Probe with broad project grants (default) or without project settings')
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    work = root / 'work'
    work.mkdir()
    # Existing project settings must not widen the registered policy when
    # permissions move from --allowedTools to inline JSON settings.
    if args.project_settings_mode == 'broad':
        settings = work / '.claude'
        settings.mkdir()
        for name in ('settings.json', 'settings.local.json'):
            (settings / name).write_text(json.dumps({'permissions': {'allow': ['Bash']}}))
    job, policy = fixture(work)
    cases = cases_for(job, policy)
    (root / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    (root / 'policy.json').write_text(json.dumps(policy, indent=2) + '\n')
    cli = str(args.claude_executable.resolve(strict=True))
    pin = {'claude_executable': cli, 'pinned_files': {cli: sha(cli)}}
    calls = []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        n = sum(bool(call.get('tools')) for call in calls)
        if not body.get('tools'):
            block = {'type': 'text', 'text': 'Offline permission probe'}
        elif n <= len(cases):
            case = cases[n - 1]
            block = {'type': 'tool_use', 'id': case['id'], 'name': 'Bash',
                     'input': {'command': case['command'], 'description': 'Synthetic offline permission case'}}
        else:
            block = {'type': 'text', 'text': 'OFFLINE_COMPLETE'}
        tool = block['type'] == 'tool_use'
        start = {**block, 'input' if tool else 'text': {} if tool else ''}
        delta = ({'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])} if tool
                 else {'type': 'text_delta', 'text': block['text']})
        events = [
            {'type': 'message_start', 'message': {'id': f'offline_{len(calls)}', 'type': 'message',
                'role': 'assistant', 'model': body['model'], 'content': [], 'stop_reason': None,
                'stop_sequence': None, 'usage': {'input_tokens': 100, 'output_tokens': 0}}},
            {'type': 'content_block_start', 'index': 0, 'content_block': start},
            {'type': 'content_block_delta', 'index': 0, 'delta': delta},
            {'type': 'content_block_stop', 'index': 0},
            {'type': 'message_delta', 'delta': {'stop_reason': 'tool_use' if tool else 'end_turn',
                                               'stop_sequence': None}, 'usage': {'output_tokens': 12}},
            {'type': 'message_stop'}]
        raw = ''.join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        return httpx.Response(200, content=raw, headers={'content-type': 'text/event-stream'})

    sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw: SimpleNamespace(input_tokens=100)))
    ledger = Ledger(root / 'ledger.json', manifest_sha256='offline-permissions-only')
    proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt='offline', evidence=root / 'requests',
        model='claude-opus-5', prices={'input': .000005, 'output': .000025,
                                    'cache_read': .0000005, 'cache_write': .00000625},
        verify=lambda: None, provider_key='offline-synthetic-key', base_url='https://api.cborg.lbl.gov',
        upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM'}}
    config = root / 'config'
    config.mkdir()
    env.update(CLAUDE_CONFIG_DIR=str(config), DISABLE_NON_ESSENTIAL_MODEL_CALLS='1', DISABLE_TELEMETRY='1',
               CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS='1', ANTHROPIC_API_KEY=proxy.token,
               PYTHONPATH=str(work))
    prompt = root / 'probe_instruction.txt'
    prompt.write_text('Perform the synthetic offline permission probe.\n')
    argv = [cli, '--print', '--safe-mode', '--restricted', '--strict-mcp-config', '--no-session-persistence',
        '--model', 'claude-opus-5', '--name', 'd4d-offline-permissions', '--disable-slash-commands',
        '--max-budget-usd', '5', '--prompt-suggestions', 'false', '--output-format', 'stream-json', '--verbose',
        '--permission-mode', 'dontAsk', '--tools', 'Read,Write,Bash', *permission_arguments(policy),
        '--system-prompt', 'Synthetic offline capability probe. Do not access other files or networks.' + command_guidance(policy)]
    with proxy.running() as url:
        env['ANTHROPIC_BASE_URL'] = url
        code = execute_child(argv, proxy=proxy, instruction=prompt, attempt=root, cwd=work, env=env,
                             deadline_seconds=120, verify_launch=lambda: verified_executable(pin))
    with (root / 'transcript.jsonl').open(encoding='utf-8') as stream:
        events = [json.loads(line) for line in stream if line.strip()]
    terminals = [e for e in events if e.get('type') == 'result']
    if len(terminals) != 1:
        raise RuntimeError('probe did not reach one terminal result')
    denied = {d['tool_use_id'] for d in terminals[0].get('permission_denials', [])}
    results = {c['tool_use_id']: c for e in events if isinstance(e.get('message'), dict)
               for c in e['message'].get('content', []) if isinstance(c, dict) and c.get('type') == 'tool_result'}
    checked = [{**case, 'denied': case['id'] in denied,
                'tool_result_error': results.get(case['id'], {}).get('is_error'),
                'passed': case['id'] in results and ((case['id'] not in denied) == case['allow'])
                          and (not case['allow'] or results[case['id']].get('is_error') is False)} for case in cases]
    conformance = command_history(events, policy, terminals[0].get('permission_denials', []))
    summary = {'exit_code': code, 'passed': code == 0 and all(c['passed'] for c in checked)
               and not conformance['problems'], 'command_history': conformance,
        'cases': checked, 'scripted_requests': len(calls), 'real_provider_requests': 0,
        'proxy_failure': proxy.failure, 'unfinished_handlers': proxy.unfinished_handlers,
        'runtime': pin, 'project_settings_contamination_probe': args.project_settings_mode == 'broad',
        'policy_sha256': sha(root / 'policy.json'),
        'transcript_sha256': sha(root / 'transcript.jsonl')}
    (root / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({**{k: v for k, v in summary.items() if k != 'cases'},
                      'cases': [{k: c[k] for k in ('id', 'allow', 'denied', 'passed')} for c in checked]}, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
