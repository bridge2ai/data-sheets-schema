"""Native evaluation through the existing capped proxy and parent controls.

Only the exact registered validation command is executable. File admission
uses the shared controller; this remains a tool policy, not an OS sandbox.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from registration import BudgetStop, canonical_path, pinned, sha, strict_json
from validation import validate_native, validator_argv
from budgeted_cborg import attempt_identity, provider_context_headers
from audit_controls.transport import provider_clients
from native_command_policy import _simple_command, _literal_rule, permission_arguments
from native_control import CONTRACT, check_control_history, load_native_events
from native_file_policy import FileAccess
from native_proxy import NativeProxy
from run_native_canary import execute_child

CLI_FLAGS = ['--print', '--safe-mode', '--restricted', '--strict-mcp-config',
    '--disable-slash-commands', '--no-session-persistence', '--prompt-suggestions', 'false',
    '--output-format', 'stream-json', '--verbose', '--permission-mode', 'dontAsk',
    '--tools', 'Read,Write,Bash']
ENVIRONMENT = {'DISABLE_NON_ESSENTIAL_MODEL_CALLS': '1', 'DISABLE_TELEMETRY': '1',
               'CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS': '1'}


def classify_command(command, python, programs, command_policy=None):
    if not isinstance(command, str):
        return 'unclassifiable', 'missing native evaluation command'
    tokens, problem = _simple_command(command)
    if tokens is None:
        return 'not_prescribed', problem
    expected = (command_policy or {}).get('validator_argv')
    if expected and tokens == expected and tokens[0] == python:
        return 'prescribed', 'the exact registered evaluation validator and arguments'
    return 'not_prescribed', 'outside the exact registered evaluation validator'


def build_policy(manifest, job):
    expected = validator_argv(manifest, job)
    if job.get('validator_argv') != expected:
        raise BudgetStop('native validator argv differs from the selected evaluation job')
    reads = [job[key] for key in ('input', 'context_path', 'agent_definition', 'rubric_file', 'instruction')]
    for value in reads:
        pinned(manifest, value)
    candidate = canonical_path(job['candidate'])
    return {'version': 1, 'pretool_control': CONTRACT, 'python': manifest['python'],
        'programs': [], 'manifest_paths': [], 'validator_argv': expected,
        'allowed_tools': ['Read', 'Write', _literal_rule(shlex.join(expected))],
        'readonly_lookups': {'repository': manifest['repository'], 'inputs': reads,
                            'output_directories': [str(candidate.parent)]}}


def additional_directories(manifest, job):
    """Reachability for --restricted; FileAccess still admits exact files only."""
    repository = canonical_path(manifest['repository'])
    directories = {Path(job[key]).parent for key in
                   ('input', 'context_path', 'agent_definition', 'rubric_file', 'instruction', 'candidate')}
    return sorted(str(path) for path in directories if path != repository and repository not in path.parents)


def _blocks(event):
    message = event.get('message')
    return message['content'] if isinstance(message, dict) and isinstance(message.get('content'), list) else []


def _success(call, block, event, write_target=None):
    if block.get('is_error') is not None and block.get('is_error') is not False:
        return False
    metadata = event.get('tool_use_result')
    if not isinstance(metadata, dict):
        return False
    for key in ('exitCode', 'exit_code'):
        if key in metadata and (type(metadata[key]) is not int or metadata[key] != 0):
            return False
    if call['name'] == 'Write':
        # The native Write success has no is_error flag. Its structured result
        # carries the actual target and complete written bytes instead.
        return (metadata.get('type') in ('create', 'update') and
            metadata.get('filePath') == str(write_target) and
            isinstance(metadata.get('content'), str) and metadata['content'] == call['input'].get('content'))
    return (block.get('is_error') is False and metadata.get('interrupted') is False and
            isinstance(metadata.get('stdout'), str) and isinstance(metadata.get('stderr'), str))


def inspect_transcript(events, policy, job, manifest, control_path, config_root):
    """Require callback evidence, definition echo, own writes and own validation.

    This is procedural acceptance only; independent review still decides
    whether the canary's judgments correctly apply its instrument.
    """
    check = check_control_history(events, control_path, policy, classify_command, config_root)
    if not check.get('checked') or check.get('problems'):
        raise BudgetStop('native evaluation control history is incomplete or invalid')
    inits = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    finals = [e for e in events if e.get('type') == 'result']
    runtime = job['native_runtime']
    if len(inits) != 1 or len(finals) != 1:
        raise BudgetStop('native evaluation initialization or terminal evidence is ambiguous')
    init, terminal = inits[0], finals[0]
    if (init.get('model') != manifest['model']['model'] or init.get('apiKeySource') != 'ANTHROPIC_API_KEY' or
        init.get('claude_code_version') != runtime['version'].split()[0] or
        set(init.get('tools', [])) != {'Read', 'Write', 'Bash'}):
        raise BudgetStop('native evaluation runtime differs from its registered instrument')
    if (terminal.get('is_error') or terminal.get('terminal_reason') != 'completed' or
        terminal.get('stop_reason') != 'end_turn' or set(terminal.get('modelUsage', {})) != {manifest['model']['model']}):
        raise BudgetStop('native evaluation did not complete under the selected model')
    usage = terminal['modelUsage'][manifest['model']['model']]
    if usage.get('contextWindow') != runtime['context_window'] or usage.get('maxOutputTokens') != runtime['max_output_tokens']:
        raise BudgetStop('native evaluation runtime limits differ from registration')
    file_policy = FileAccess(policy, config_root)
    denials = []
    raw_denials = terminal.get('permission_denials', [])
    if not isinstance(raw_denials, list):
        raise BudgetStop('native permission denial evidence is malformed')
    for denial in raw_denials:
        if not isinstance(denial, dict) or not isinstance(denial.get('tool_input'), dict):
            raise BudgetStop('native permission denial cannot be classified')
        tool, payload = denial.get('tool_name'), denial['tool_input']
        if tool == 'Bash':
            classification, basis = classify_command(payload.get('command'), policy['python'], [], policy)
        elif tool in ('Read', 'Write'):
            classification, basis = file_policy.classify(tool, payload)
        elif isinstance(tool, str) and tool:
            classification, basis = 'not_prescribed', 'tool not granted by this registration'
        else:
            raise BudgetStop('native permission denial lacks its tool identity')
        denials.append({**denial, 'classification': classification, 'basis': basis})
    if any(row['classification'] != 'not_prescribed' for row in denials):
        raise BudgetStop('a prescribed or unclassifiable evaluation operation was denied')
    denied = {row.get('tool_use_id') for row in denials}
    calls, results, opening_text = {}, {}, []
    first_tool = False
    for line, event in enumerate(events, 1):
        for block in _blocks(event):
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'text' and event.get('type') == 'assistant' and not first_tool:
                opening_text.append(block.get('text', ''))
            if block.get('type') == 'tool_use':
                first_tool = True
                calls[block['id']] = (line, block)
            elif block.get('type') == 'tool_result':
                results[block['tool_use_id']] = (line, block, event)
    from data_sheets_schema.agent_pin import verify_echo, StaleAgentDefinition, NoDiscriminatingChallenge
    try:
        verify_echo(Path(job['agent_definition']).stem, '\n'.join(opening_text))
    except (StaleAgentDefinition, NoDiscriminatingChallenge) as error:
        raise BudgetStop('native evaluator did not verify its definition before starting the task') from error
    writes, validations = [], []
    for identity, (line, call) in calls.items():
        payload = call['input']
        if call['name'] == 'Bash':
            classification, _ = classify_command(payload.get('command'), policy['python'], [], policy)
            if identity not in denied and classification != 'prescribed':
                raise BudgetStop('unregistered evaluation command executed')
            if classification == 'prescribed' and identity in results and _success(call, results[identity][1], results[identity][2]):
                try:
                    # The fixed validator prints exactly one JSON report. No
                    # substring marker or successful shell exit establishes it.
                    stdout = results[identity][2]['tool_use_result']['stdout']
                    report = strict_json(stdout)
                except (ValueError, TypeError):
                    report = None
                if (isinstance(report, dict) and report.get('passed') is True and
                    report.get('candidate_sha256') == sha(job['candidate'])):
                    validations.append((line, results[identity][0]))
        elif call['name'] == 'Write' and file_policy.target(payload.get('file_path')) == Path(job['candidate']):
            if identity in denied:
                continue
            if identity not in results or not _success(call, results[identity][1], results[identity][2],
                                                       file_policy.target(payload.get('file_path'))):
                raise BudgetStop('candidate write lacks a successful native result')
            content = payload.get('content')
            if not isinstance(content, str):
                raise BudgetStop('candidate write did not carry exact text')
            writes.append((line, results[identity][0], hashlib.sha256(content.encode()).hexdigest()))
    if not writes or writes[-1][2] != sha(job['candidate']):
        raise BudgetStop('candidate differs from the native evaluator last successful Write')
    if not any(start > writes[-1][1] for start, _ in validations):
        raise BudgetStop('native evaluator did not validate its latest candidate after writing it')
    return {'control': check, 'denials': denials, 'definition_echo_verified': True,
            'candidate_write_sha256': writes[-1][2], 'terminal': terminal}


def execute_job(context, *, client=None):
    manifest, job, attempt = context.manifest, context.job, context.attempt
    policy = build_policy(manifest, job)
    from instructions import verify_instruction
    verify_instruction(manifest, job)
    runtime = job['native_runtime']
    if runtime.get('effort', 'native_default') != 'native_default':
        raise BudgetStop('native evaluation uses the native default effort; no effort override is registered')
    if runtime.get('cli_flags') != CLI_FLAGS or runtime.get('environment') != ENVIRONMENT:
        raise BudgetStop('native evaluation requires isolated tools and environment flags')
    if runtime.get('additional_directories') != additional_directories(manifest, job):
        raise BudgetStop('native restricted directories differ from the registered inputs and output')
    executable = pinned(manifest, runtime['executable'])
    if subprocess.check_output([str(executable), '--version'], text=True).strip() != runtime['version']:
        raise BudgetStop('native evaluation executable version changed')
    from data_sheets_schema.agent_pin import spawn_preamble
    instruction = pinned(manifest, job['instruction'])
    if not instruction.read_text().startswith(spawn_preamble(Path(job['agent_definition']).stem)):
        raise BudgetStop('native evaluation instruction lacks its current check-echo preamble')
    key = os.environ.get('CBORG_API_KEY')
    if not key and client is None:
        raise BudgetStop('CBORG_API_KEY is required')
    context.verify()
    config = attempt / 'cli_config'
    config.mkdir(mode=0o700)
    billing_attempt = attempt_identity(context.manifest_sha256, job['id'])
    owned_client = client is None
    upstream = None
    if owned_client:
        client, upstream = provider_clients(manifest, key)
    try:
        proxy = NativeProxy(sdk=client,
            ledger=context.ledger, attempt=billing_attempt, evidence=attempt / 'requests',
            model=manifest['model']['model'], prices=manifest['budget']['prices_per_token'],
            verify=context.verify, provider_key=key or 'offline-test-key', base_url=manifest['provider_base_url'],
            request_headers=provider_context_headers(manifest), upstream=upstream)
    except BaseException:
        # running() owns both clients after construction; before that boundary,
        # close only clients created here, preserving the original setup error.
        if owned_client:
            for resource in (client, upstream):
                close = getattr(resource, 'close', None)
                if close is not None:
                    try:
                        close()
                    except BaseException:
                        pass
        raise
    environment = {key: value for key, value in os.environ.items()
                   if key in {'PATH', 'HOME', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM'}}
    environment.update(ENVIRONMENT)
    environment.update(CLAUDE_CONFIG_DIR=str(config), ANTHROPIC_API_KEY=proxy.token,
        PYTHONPATH=str(Path(manifest['repository']) / 'src'), VIRTUAL_ENV=str(Path(manifest['python']).parent.parent))
    directory_flags = [part for directory in runtime['additional_directories'] for part in ('--add-dir', directory)]
    argv = [str(executable), *CLI_FLAGS, *directory_flags, '--model', manifest['model']['model'], '--name', job['id'],
        '--max-budget-usd', '5', *permission_arguments(policy),
        '--system-prompt', Path(job['agent_definition']).read_text()]
    with proxy.running() as url:
        environment['ANTHROPIC_BASE_URL'] = url
        exit_code = execute_child(argv, proxy=proxy, instruction=instruction, attempt=attempt,
            cwd=manifest['repository'], env=environment, deadline_seconds=job['deadline_seconds'],
            verify_launch=context.verify, command_policy=policy, command_classifier=classify_command,
            record_stop=lambda reason: context.ledger.stop_attempt(billing_attempt, reason))
    if proxy.failed.is_set() or proxy.unfinished_handlers or exit_code:
        raise BudgetStop('native evaluator stopped or has unfinished request handlers')
    events = load_native_events(attempt / 'transcript.jsonl')
    evidence = inspect_transcript(events, policy, job, manifest, attempt / 'control.jsonl', config)
    validation = validate_native(Path(job['candidate']), job, manifest)
    return {'candidate_path': Path(job['candidate']), 'validation': validation,
        'runtime': {'native_version': runtime['version'], 'model': manifest['model']['model'],
                    'effort': 'native_default', 'exit_code': exit_code},
        'evidence': evidence}
