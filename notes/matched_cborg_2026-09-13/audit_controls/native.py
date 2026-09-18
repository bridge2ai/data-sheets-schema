"""One registered native Phase 3 audit; inherited generation stays read-only.

A successful local run is pending independent review, not scientific acceptance.
The selected validator runs once, freezes the audit, and cannot be repaired here.
"""
import argparse
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / 'native_controls'))
from budgeted_cborg import (BudgetStop, attempt_identity, now,
    provider_context_headers, write_new)
from native_command_policy import _simple_command, _literal_rule, permission_arguments
from native_control import CONTRACT, check_control_history, load_native_events
from native_file_policy import FileAccess
from native_proxy import NativeProxy
from run_native_canary import execute_child
from .registration import native_api_timeout, sha, strict_json
from .transport import provider_clients

CLI_FLAGS = ['--print', '--safe-mode', '--restricted', '--strict-mcp-config',
    '--disable-slash-commands', '--no-session-persistence', '--prompt-suggestions', 'false',
    '--output-format', 'stream-json', '--verbose', '--permission-mode', 'dontAsk',
    '--tools', 'Read,Write,Bash']
VALIDATOR_RESULT_WAIT_SECONDS = 2
ENVIRONMENT = {'DISABLE_NON_ESSENTIAL_MODEL_CALLS': '1', 'DISABLE_TELEMETRY': '1',
               'CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS': '1'}


def classify_command(command, python, programs, command_policy=None):
    if not isinstance(command, str):
        return 'unclassifiable', 'missing audit validator command'
    tokens, problem = _simple_command(command)
    if tokens is None:
        return 'not_prescribed', problem
    expected = (command_policy or {}).get('validator_argv')
    if expected and tokens == expected and tokens[0] == python:
        return 'prescribed', 'the exact registered audit validator and arguments'
    return 'not_prescribed', 'outside the exact registered audit validator'


def build_policy(manifest, registration_path):
    job = manifest['job']
    expected = [manifest['python'], '-m', 'audit_controls.contract',
                '--registration', str(registration_path)]
    if job['validator_argv'] != expected:
        raise BudgetStop('audit validator argv differs from the selected registration')
    reads = job['readable_inputs']
    for value in [*reads, job['instruction'], job['system_prompt']]:
        if manifest['pinned_files'].get(value) != sha(value):
            raise BudgetStop('audit registered read changed or is not pinned')
    output = Path(job['output_dir'])
    if Path(job['audit_path']).parent != output or output.parent != Path(job['attempt_dir']):
        raise BudgetStop('audit output must be isolated below its attempt')
    return {'version': 1, 'pretool_control': CONTRACT, 'python': manifest['python'],
        'programs': [], 'manifest_paths': [], 'validator_argv': expected,
        'allowed_tools': ['Read', 'Write', _literal_rule(shlex.join(expected))],
        'readonly_lookups': {'repository': manifest['repository'],
            'inputs': sorted(set([*reads, job['instruction'], job['system_prompt']])),
            'output_directories': [str(output)]}}


def additional_directories(manifest):
    root = Path(manifest['repository'])
    job = manifest['job']
    directories = {Path(p).parent for p in [*job['readable_inputs'], job['instruction'], job['system_prompt']]}
    directories.add(Path(job['output_dir']))
    return sorted(str(p) for p in directories if p != root and root not in p.parents)


def _blocks(event):
    message = event.get('message') if isinstance(event, dict) else None
    return message['content'] if isinstance(message, dict) and isinstance(message.get('content'), list) else []


def _write_success(call, block, event, target):
    metadata = event.get('tool_use_result')
    return ((block.get('is_error') is None or block.get('is_error') is False) and
        isinstance(metadata, dict) and metadata.get('type') in ('create', 'update') and
        metadata.get('filePath') == str(target) and isinstance(metadata.get('content'), str) and
        metadata['content'] == call['input'].get('content') and
        all(key not in metadata or (type(metadata[key]) is int and metadata[key] == 0)
            for key in ('exitCode', 'exit_code')))


class AuditHistory:
    """Incremental audit-only state; shared by live admission and replay.

    NativeControl independently establishes call/callback/result identities.
    No inherited generation or source-reading events are fabricated here.
    """
    def __init__(self, manifest, registration_sha256, policy):
        self.manifest, self.job = manifest, manifest['job']
        self.registration_sha256, self.policy = registration_sha256, policy
        self.files = FileAccess(policy)
        self.audit = Path(self.job['audit_path'])
        self.marker = Path(self.job['attempt_dir']) / 'validation.json'
        self.failure = Path(self.job['attempt_dir']) / 'validation_failure.json'
        self.lock = threading.Condition(threading.RLock())
        self.problem = None
        self.calls, self.results, self.pending = {}, set(), set()
        self.last_write, self.validator, self.validation = None, None, None
        self.line = 0

    def _marker(self):
        if self.failure.exists():
            raise BudgetStop('audit validator recorded a terminal failure')
        if not self.marker.exists():
            raise BudgetStop('audit validator did not record a complete validation receipt')
        try:
            report = strict_json(self.marker.read_text())
        except (ValueError, OSError, UnicodeError) as error:
            raise BudgetStop('audit validation receipt is unreadable or incomplete') from error
        if (not isinstance(report, dict) or report.get('passed') is not True or report.get('checked') is not True or
            report.get('findings') != [] or report.get('errors') != [] or
            report.get('job_id') != self.job['id'] or
            report.get('registration_sha256') != self.registration_sha256 or
            not self.last_write or report.get('audit_sha256') != self.last_write['sha256'] or
            report.get('audit_sha256') != sha(self.audit)):
            raise BudgetStop('audit validation receipt failed or its identity changed')
        return report

    def verify_admission(self):
        """Wait briefly for stdout observation; never spend on a marker alone.

        A genuine native host may flush its successful tool result and start
        HTTP before the controller reads stdout. The result, not elapsed time,
        releases this bounded wait (#2104).
        """
        with self.lock:
            deadline = time.monotonic() + VALIDATOR_RESULT_WAIT_SECONDS
            while True:
                if self.problem:
                    raise BudgetStop(self.problem)
                if self.failure.exists():
                    raise BudgetStop('audit validator recorded a terminal failure')
                if self.validator is None:
                    if self.marker.exists():
                        raise BudgetStop('audit validation receipt has no observed validator invocation')
                    return
                if self.validation is not None:
                    self._marker()
                    return
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BudgetStop('audit validator has no observed successful typed result; no further request admitted')
                self.lock.wait(min(remaining, 0.05))

    def observe(self, event):
        with self.lock:
            try:
                self._observe(event)
            except BaseException as error:
                self.problem = (str(error) if isinstance(error, BudgetStop) else
                                'audit observer failed: ' + type(error).__name__)
                raise
            finally:
                self.lock.notify_all()

    def _observe(self, event):
        with self.lock:
            self.line += 1
            if not isinstance(event, dict):
                raise BudgetStop('audit transcript contains a non-object event')
            for block in _blocks(event):
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use':
                    identity, tool, payload = block.get('id'), block.get('name'), block.get('input')
                    if not isinstance(identity, str) or not identity or identity in self.calls or not isinstance(payload, dict):
                        raise BudgetStop('audit tool identity or input is malformed')
                    if self.validator is not None:
                        raise BudgetStop('audit tools cannot continue after the single terminal validator')
                    self.calls[identity] = (self.line, block)
                    if tool == 'Write':
                        target = self.files.target(payload.get('file_path'))
                        if target != self.audit:
                            raise BudgetStop('audit-only continuation can write only its new audit file')
                        if not isinstance(payload.get('content'), str):
                            raise BudgetStop('audit Write must contain exact text')
                        self.last_write = None
                    if tool == 'Bash' and classify_command(payload.get('command'), self.policy['python'], [], self.policy)[0] == 'prescribed':
                        if (set(payload) - {'command', 'description', 'timeout'} or
                            ('description' in payload and not isinstance(payload['description'], str)) or
                            ('timeout' in payload and (type(payload['timeout']) is not int or payload['timeout'] <= 0))):
                            raise BudgetStop('audit validator must use the foreground Bash invocation without extra options')
                        if self.pending or not self.last_write or sha(self.audit) != self.last_write['sha256']:
                            raise BudgetStop('audit validator requires a completed current native Write and no pending tools')
                        self.validator = {'id': identity, 'line': self.line, 'audit_sha256': self.last_write['sha256']}
                    self.pending.add(identity)
                elif block.get('type') == 'tool_result':
                    identity = block.get('tool_use_id')
                    if identity not in self.calls or identity in self.results:
                        raise BudgetStop('audit result lacks a unique preceding call')
                    self.results.add(identity)
                    self.pending.discard(identity)
                    start, call = self.calls[identity]
                    if call['name'] == 'Write':
                        if not _write_success(call, block, event, self.audit):
                            raise BudgetStop('audit Write lacks its exact successful typed result')
                        content = call['input']['content']
                        self.last_write = {'call_line': start, 'result_line': self.line,
                            'sha256': hashlib.sha256(content.encode()).hexdigest()}
                    if self.validator and identity == self.validator['id']:
                        metadata = event.get('tool_use_result')
                        if (block.get('is_error') is not False or not isinstance(metadata, dict) or
                            metadata.get('interrupted') is not False or
                            not isinstance(metadata.get('stdout'), str) or not isinstance(metadata.get('stderr'), str) or
                            any(key in metadata and (type(metadata[key]) is not int or metadata[key] != 0)
                                for key in ('exitCode', 'exit_code'))):
                            raise BudgetStop('audit validator failed or lacks typed successful result evidence')
                        try:
                            report = strict_json(metadata['stdout'])
                        except (ValueError, TypeError) as error:
                            raise BudgetStop('audit validator did not return its exact JSON receipt') from error
                        if json.dumps(report, sort_keys=True, allow_nan=False) != json.dumps(self._marker(), sort_keys=True, allow_nan=False):
                            raise BudgetStop('audit validator result differs from its current receipt')
                        self.validation = report
            if event.get('type') == 'result':
                self.finish()

    def finish(self):
        if self.pending or not self.last_write or not self.validator or not self.validation:
            raise BudgetStop('audit completion lacks a final Write and single successful terminal validator')
        if self.validation != self._marker():
            raise BudgetStop('audit validation changed after its result')
        return {'audit_write': self.last_write, 'validator': self.validator, 'validation': self.validation}



class AuditProxy(NativeProxy):
    """Recheck terminal markers after token counting, before reservation/send."""
    def __init__(self, *, audit_history, **kwargs):
        self.audit_history = audit_history
        super().__init__(**kwargs)

    def require_open(self):
        super().require_open()
        self.audit_history.verify_admission()

    @contextmanager
    def mutation_guard(self, phase):
        with super().mutation_guard(phase):
            if phase == 'admit':
                self.audit_history.verify_admission()
            yield

def inspect_transcript(events, policy, manifest, registration_sha256, control_path, config_root):
    check = check_control_history(events, control_path, policy, classify_command, config_root)
    if not check.get('checked') or check.get('problems'):
        raise BudgetStop('native audit control history is incomplete or invalid')
    inits = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    finals = [e for e in events if e.get('type') == 'result']
    runtime = manifest['native_runtime']
    if len(inits) != 1 or len(finals) != 1:
        raise BudgetStop('native audit initialization or terminal evidence is ambiguous')
    init, terminal = inits[0], finals[0]
    if (init.get('model') != manifest['model']['model'] or init.get('apiKeySource') != 'ANTHROPIC_API_KEY' or
        init.get('claude_code_version') != runtime['version'].split()[0] or
        set(init.get('tools', [])) != {'Read', 'Write', 'Bash'}):
        raise BudgetStop('native audit runtime differs from registration')
    if (terminal.get('is_error') is not False or terminal.get('terminal_reason') != 'completed' or
        terminal.get('stop_reason') != 'end_turn' or set(terminal.get('modelUsage', {})) != {manifest['model']['model']}):
        raise BudgetStop('native audit did not complete under the registered model')
    usage = terminal['modelUsage'][manifest['model']['model']]
    if usage.get('contextWindow') != runtime['context_window'] or usage.get('maxOutputTokens') != runtime['max_output_tokens']:
        raise BudgetStop('native audit context or output limits changed')
    denials = terminal.get('permission_denials')
    if not isinstance(denials, list):
        raise BudgetStop('native audit lacks permission denial evidence')
    file_policy = FileAccess(policy, config_root)
    classified = []
    for denial in denials:
        if not isinstance(denial, dict) or not isinstance(denial.get('tool_input'), dict):
            raise BudgetStop('native audit permission denial is malformed')
        tool, payload = denial.get('tool_name'), denial['tool_input']
        if tool == 'Bash':
            classification, basis = classify_command(payload.get('command'), policy['python'], [], policy)
        elif tool in ('Read', 'Write'):
            classification, basis = file_policy.classify(tool, payload)
        else:
            classification, basis = 'not_prescribed', 'tool not granted'
        classified.append({**denial, 'classification': classification, 'basis': basis})
    if any(d['classification'] != 'not_prescribed' for d in classified):
        raise BudgetStop('a prescribed or unclassifiable audit operation was denied')
    history = AuditHistory(manifest, registration_sha256, policy)
    for event in events:
        history.observe(event)
    return {'control': check, 'denials': classified, 'phase3': history.finish(), 'terminal': terminal,
            'phase1_phase2_performed_here': False}


def verify_initial_context(context, rows):
    """The first retained request must contain the entire registered task bytes."""
    if not rows:
        raise BudgetStop('native audit has no recorded model request')
    request = strict_json((context.attempt / 'requests' / rows[0]['id'] / 'native_request.json').read_text())
    messages = request.get('messages')
    if not isinstance(messages, list):
        raise BudgetStop('native initial request lacks its registered inline context')
    def texts(content):
        if isinstance(content, str):
            return [content]
        if isinstance(content, list):
            return [b['text'] for b in content if isinstance(b, dict) and b.get('type') == 'text' and isinstance(b.get('text'), str)]
        return []
    instruction = Path(context.job['instruction']).read_text()
    system_prompt = Path(context.job['system_prompt']).read_text()
    user_text = [t for m in messages if isinstance(m, dict) and m.get('role') == 'user' for t in texts(m.get('content'))]
    if not any(instruction in t for t in user_text) or not any(system_prompt in t for t in texts(request.get('system'))):
        raise BudgetStop('native initial request omitted registered inline instruction or system prompt')
    return {'first_request_id': rows[0]['id'], 'instruction_sha256': sha(context.job['instruction']),
            'system_prompt_sha256': sha(context.job['system_prompt']), 'complete_inline_context_observed': True}


def verify_runtime(manifest):
    native_api_timeout(manifest)
    runtime = manifest['native_runtime']
    executable = Path(runtime['executable'])
    if manifest['pinned_files'].get(str(executable)) != sha(executable):
        raise BudgetStop('native audit executable is unpinned or changed')
    if subprocess.check_output([str(executable), '--version'], text=True).strip() != runtime['version']:
        raise BudgetStop('native audit executable version changed')
    if runtime.get('effort', 'native_default') != 'native_default':
        raise BudgetStop('native audit retains native default effort')
    if runtime['context_window'] != 200000 or runtime['max_output_tokens'] != 64000:
        raise BudgetStop('native audit registered runtime limits changed')
    return executable


def shutdown_evidence(proxy):
    """Snapshot only the completed bounded shutdown, never an initial zero.

    A finalized proxy may still retain live handlers. Their count is frozen at
    that boundary; those handlers cannot later mutate evidence or accounting.
    Before that boundary the retained count is unknown, including prelaunch.
    """
    finalized = proxy is not None and proxy.frozen is True
    count = proxy.unfinished_handlers if finalized else None
    if type(count) is not int or count < 0:
        count = None
    return {'proxy_initialized': proxy is not None,
            'proxy_shutdown_complete': finalized, 'unfinished_handlers': count}


def cleanup_error(source, error):
    # Arbitrary transport/OS exception text may contain sensitive details.
    return {'source': source, 'error_type': type(error).__name__,
            'reason': str(error) if isinstance(error, BudgetStop) else type(error).__name__}


def controller_primary(state, error):
    """Recover the callback-recorded failure if execute_child cleanup hid it."""
    reason = state.get('first_stop_reason')
    if reason is None:
        return error
    current, seen = error, set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        recorded = str(current) if isinstance(current, BudgetStop) else f'unexpected {type(current).__name__}'
        if recorded == reason:
            return current
        current = current.__context__
    # A cleanup implementation can discard the original exception object. The
    # callback still proves the first reason; do not invent its exception type.
    state['primary_error_recovered_from_stop_record'] = True
    return BudgetStop(reason)


def execute_job(context, *, client=None, upstream=None):
    state = {'stop_source': 'native_preflight', 'proxy': None}
    try:
        return _execute_job(context, state, client=client, upstream=upstream)
    except BaseException as error:
        proxy = state['proxy']
        source = state['stop_source']
        primary = state.get('primary_error', error)
        if 'escaped_child_error' in state and error is not state['escaped_child_error']:
            state.setdefault('cleanup_errors', []).append(cleanup_error('native_proxy_shutdown', error))
        # Snapshot only after proxy cleanup. A raising cleanup must neither
        # replace the first failure nor turn an unfinished shutdown into zero.
        primary.native_stop = {'stop_source': source, 'runtime': shutdown_evidence(proxy)}
        for key in ('cleanup_errors', 'primary_error_recovered_from_stop_record'):
            if key in state:
                primary.native_stop[key] = state[key]
        if 'first_stop_reason' in state:
            primary.native_stop_reason = state['first_stop_reason']
        if primary is error:
            raise
        raise primary.with_traceback(state.get('primary_traceback')) from None


def _execute_job(context, state, *, client=None, upstream=None):
    manifest, job, attempt = context.manifest, context.job, context.attempt
    policy = build_policy(manifest, context.registration_path)
    executable = verify_runtime(manifest)
    key = os.environ.get('CBORG_API_KEY')
    if not key and client is None:
        raise BudgetStop('CBORG_API_KEY is required')
    context.verify()
    state['stop_source'] = 'native_setup'
    config = attempt / 'cli_config'; config.mkdir(mode=0o700)
    billing_attempt = attempt_identity(context.manifest_sha256, job['id'])
    history = AuditHistory(manifest, context.manifest_sha256, policy)
    def admission():
        context.verify()
        history.verify_admission()
    owned_client = client is None
    registered_upstream = None
    if owned_client:
        client, registered_upstream = provider_clients(manifest, key)
        if upstream is None:
            upstream = registered_upstream
    try:
        proxy = AuditProxy(audit_history=history, sdk=client, ledger=context.ledger,
            attempt=billing_attempt, evidence=attempt / 'requests', model=manifest['model']['model'],
            prices=manifest['budget']['prices_per_token'], verify=admission, provider_key=key or 'offline-test-key',
            base_url=manifest['provider_base_url'], request_headers=provider_context_headers(manifest), upstream=upstream)
    except BaseException:
        # Before running() owns cleanup, close only resources created here.
        if owned_client:
            for resource in (client, registered_upstream):
                close = getattr(resource, 'close', None)
                if close is not None:
                    try:
                        close()
                    except BaseException as cleanup:
                        state.setdefault('cleanup_errors', []).append(cleanup_error('native_setup_cleanup', cleanup))
        raise
    state['proxy'] = proxy
    environment = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM'}}
    environment.update(ENVIRONMENT)
    timeout = native_api_timeout(manifest)
    if timeout is not None:
        environment['API_TIMEOUT_MS'] = str(timeout)
    environment.update(CLAUDE_CONFIG_DIR=str(config), ANTHROPIC_API_KEY=proxy.token,
        PYTHONPATH=os.pathsep.join([str(Path(manifest['repository'])/'src'), str(BASE), str(BASE/'native_controls')]),
        VIRTUAL_ENV=str(Path(manifest['python']).parent.parent))
    directory_flags = [p for d in additional_directories(manifest) for p in ('--add-dir', d)]
    argv = [str(executable), *CLI_FLAGS, *directory_flags, '--model', manifest['model']['model'], '--name', job['id'],
        '--max-budget-usd', str(context.ledger.limit_for_attempt(billing_attempt)), *permission_arguments(policy),
        '--system-prompt', Path(job['system_prompt']).read_text()]
    def controller_stop(reason):
        # execute_child records controller failures before its own cleanup.
        state.setdefault('first_stop_source', 'native_controller')
        state.setdefault('first_stop_reason', reason)
        context.ledger.stop_attempt(billing_attempt, reason)
    with proxy.running() as url:
        state['stop_source'] = 'native_controller'
        environment['ANTHROPIC_BASE_URL'] = url
        child_failed = False
        try:
            exit_code = execute_child(argv, proxy=proxy, instruction=Path(job['instruction']), attempt=attempt,
                cwd=manifest['repository'], env=environment, deadline_seconds=job['deadline_seconds'],
                verify_launch=admission, command_policy=policy, command_classifier=classify_command,
                event_observer=history.observe,
                record_stop=controller_stop)
        except BaseException as error:
            child_failed = True
            # Capture the first observed cause before shutdown can make an
            # in-flight handler fail merely because admission was closed.
            state['stop_source'] = state.get('first_stop_source') or ('native_proxy' if proxy.failed.is_set() else 'native_controller')
            primary = controller_primary(state, error)
            state.update(primary_error=primary, primary_traceback=primary.__traceback__, escaped_child_error=error)
            if primary is not error:
                state.setdefault('cleanup_errors', []).append(cleanup_error('native_controller_cleanup', error))
            raise
        finally:
            if not child_failed:
                state['stop_source'] = 'native_shutdown'
    state['stop_source'] = 'native_exit'
    if proxy.failed.is_set() or proxy.unfinished_handlers or exit_code:
        if proxy.failed.is_set():
            state['stop_source'] = 'native_proxy'
        raise BudgetStop('native audit stopped or has unfinished request handlers')
    state['stop_source'] = 'native_postcheck'
    context.verify()
    context.ledger.require_resolved(billing_attempt)
    ledger_state = strict_json(context.ledger.path.read_text())
    rows = [r for r in ledger_state['requests'] if r['attempt'] == billing_attempt]
    if not rows or any(r['status'] != 'settled' for r in rows):
        raise BudgetStop('native audit lacks fully settled model requests')
    evidence = inspect_transcript(load_native_events(attempt/'transcript.jsonl'), policy, manifest,
        context.manifest_sha256, attempt/'control.jsonl', config)
    evidence['initial_context'] = verify_initial_context(context, rows)
    from .contract import validate_audit
    validation = validate_audit(manifest)
    if validation.get('passed') is not True or validation.get('audit_sha256') != sha(job['audit_path']):
        raise BudgetStop('native audit failed terminal independent mechanical recheck')
    return {'audit_path': Path(job['audit_path']), 'validation': validation, 'evidence': evidence,
        'runtime': {'exit_code': exit_code, 'native_version': manifest['native_runtime']['version'],
                    'model': manifest['model']['model'], 'effort': 'native_default', **shutdown_evidence(proxy)}}


def run_job(registration_path, review_path, *, adapter=None):
    from .registration import validate_registration, verify, sequence_guard, open_audit_ledger
    registration_path, review_path = Path(registration_path).resolve(), Path(review_path).resolve()
    manifest = validate_registration(registration_path)
    manifest_sha256, review_sha256 = sha(registration_path), sha(review_path)
    job = manifest['job']
    def verify_all():
        verify(manifest, registration_path, manifest_sha256)
        if sha(review_path) != review_sha256:
            raise BudgetStop('audit independent launch review changed')
        review = strict_json(review_path.read_text())
        if (review.get('verdict') != 'approve' or review.get('registration_sha256') != manifest_sha256 or
            review.get('ci_conclusion') != 'success' or review.get('repository_commit') != manifest['repository_commit'] or
            review.get('allowed_jobs') != [job['id']]):
            raise BudgetStop('audit registration needs independent review and passing CI for its single job')
    verify_all(); build_policy(manifest, registration_path); verify_runtime(manifest)
    attempt = Path(job['attempt_dir'])
    with sequence_guard(manifest, manifest_sha256):
        if attempt.exists() or Path(job['output_dir']).exists():
            raise BudgetStop('audit attempt already exists; never overwrite or resume')
        ledger = open_audit_ledger(manifest, registration_path, manifest_sha256)
        billing_attempt = attempt_identity(manifest_sha256, job['id'])
        ledger.require_resolved(billing_attempt)
        verify_all()
        attempt.mkdir(parents=True, exist_ok=False); Path(job['output_dir']).mkdir()
        receipt = {'schema_version': 1, 'job_id': job['id'], 'registration_sha256': manifest_sha256,
            'review_sha256': review_sha256, 'status': 'incomplete', 'started_at': now(),
            'billing_attempt': billing_attempt, 'scope': 'phase3_audit_only', 'phase1_phase2_performed_here': False}
        write_new(attempt/'started.json', receipt)
        context = SimpleNamespace(manifest=manifest, job=job, attempt=attempt, manifest_sha256=manifest_sha256,
            registration_path=registration_path, ledger=ledger, verify=verify_all)
        error, result = None, None
        try:
            result = (adapter or execute_job)(context)
            verify_all(); ledger.require_resolved(billing_attempt)
            if result.get('validation', {}).get('passed') is not True:
                raise BudgetStop('audit adapter did not pass its mechanical validator')
            receipt.update(status='completed_pending_independent_review', audit_path=job['audit_path'],
                audit_sha256=sha(job['audit_path']), validation=result['validation'], runtime=result['runtime'], evidence=result['evidence'])
        except BaseException as exc:
            error = exc
            reason = getattr(exc, 'native_stop_reason', str(exc) if isinstance(exc, BudgetStop) else type(exc).__name__)
            observation = getattr(exc, 'native_stop', None)
            if observation is None:
                observation = {'stop_source': 'audit_orchestrator',
                    'runtime': result.get('runtime', shutdown_evidence(None)) if isinstance(result, dict) else shutdown_evidence(None)}
            receipt.update(status='stopped', error_type=type(exc).__name__, reason=reason, **observation)
            ledger.stop_attempt(billing_attempt, reason)
        finally:
            state = strict_json(ledger.path.read_text())
            rows = [r for r in state['requests'] if r['attempt'] == billing_attempt]
            receipt.update(finished_at=now(), requests_admitted=len(rows),
                settled_cost_usd=str(sum((Decimal(r['cost_usd']) for r in rows if r['status']=='settled'), Decimal(0))),
                unresolved_requests=[r['id'] for r in rows if r['status']!='settled'])
            write_new(attempt/'result.json', receipt)
        if error is not None:
            raise error
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    args = parser.parse_args()
    run_job(args.registration, args.review)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
