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
from budgeted_cborg import (BudgetStop, STALL_DEBIT_BASIS, attempt_identity, now,
    provider_context_headers, write_new)
from native_command_policy import _simple_command, _literal_rule, permission_arguments
from native_control import CONTRACT, HISTORY_CONTRACT, check_control_history, load_native_events
from native_file_policy import FileAccess
from native_proxy import NativeProxy
from run_native_canary import execute_child
from .registration import (native_api_force_idle_timeout, native_api_timeout, native_stall_policy, native_response_buffer, native_history_control,
                           native_upstream_read_timeout, sha, strict_json)
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
    assembly = (command_policy or {}).get('assemble_argv')
    if assembly and tokens == assembly and tokens[0] == python:
        return 'prescribed', 'the exact registered audit part assembly and arguments'
    for expected_draft in (command_policy or {}).get('draft_argv', []):
        if tokens == expected_draft and tokens[0] == python:
            return 'prescribed', 'the exact registered draft grammar or seal command'
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
    recovery = {}
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths
        recovery = {'bounded_reads': recovery_paths(manifest)}
    staged = {}
    helpers = [_literal_rule(shlex.join(expected))]
    if 'audit_output' in manifest:
        from .output_parts import configuration
        block = configuration(manifest, registration_path)
        staged = {'assemble_argv': block['assemble_argv']}
        recovery['write_paths'] = {path: block['max_part_bytes'] for path in block['parts']}
        helpers.append(_literal_rule(shlex.join(block['assemble_argv'])))
    if 'audit_drafting' in manifest:
        from .draft_output import configuration
        block = configuration(manifest, registration_path)
        commands = [row['check_argv'] for row in block['rounds']] + [block['seal_argv']]
        staged = {'draft_argv': commands}
        recovery['write_paths'] = {path: block['max_part_bytes']
                                  for row in block['rounds'] for path in row['parts']}
        helpers.extend(_literal_rule(shlex.join(argv)) for argv in commands)
    return {'version': 1, 'pretool_control': CONTRACT, 'python': manifest['python'],
        'programs': [], 'manifest_paths': [], 'validator_argv': expected, **staged,
        'allowed_tools': ['Read', 'Write', *helpers],
        'readonly_lookups': {'repository': manifest['repository'],
            'inputs': sorted(set([*reads, job['instruction'], job['system_prompt']])),
            'output_directories': [str(output)], **recovery}}


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
        self.recovery_reads = []
        self.responsive_control = policy.get('pretool_control') == HISTORY_CONTRACT
        self.admission_cancelled = None

    @property
    def result_wait_seconds(self):
        return (HISTORY_CONTRACT['runtime_callback_timeout_seconds']
                if self.responsive_control else VALIDATOR_RESULT_WAIT_SECONDS)

    def _check_admission_cancelled(self):
        if self.admission_cancelled is not None and self.admission_cancelled.is_set():
            raise BudgetStop('native admission is closed')

    @contextmanager
    def admission_lock(self):
        """Selected verification never waits unboundedly to acquire history.

        File verification itself can still block. Its caller must not hold
        the proxy lifecycle lock; cancellation is rechecked before mutation.
        """
        if not self.responsive_control:
            with self.lock:
                yield
            return
        deadline = time.monotonic() + self.result_wait_seconds
        while True:
            self._check_admission_cancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BudgetStop('native history admission lock timed out')
            if self.lock.acquire(timeout=min(.05, remaining)):
                break
        try:
            self._check_admission_cancelled()
            yield
            self._check_admission_cancelled()
        finally:
            self.lock.release()

    def _artifact_hash(self):
        return self.last_write and self.last_write['sha256']

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
            not self._artifact_hash() or report.get('audit_sha256') != self._artifact_hash() or
            report.get('audit_sha256') != sha(self.audit)):
            raise BudgetStop('audit validation receipt failed or its identity changed')
        return report

    def verify_admission(self):
        """Wait briefly for stdout observation; never spend on a marker alone.

        A genuine native host may flush its successful tool result and start
        HTTP before the controller reads stdout. The result, not elapsed time,
        releases this bounded wait (#2104).
        """
        with self.admission_lock():
            deadline = time.monotonic() + self.result_wait_seconds
            while True:
                self._check_admission_cancelled()
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
                    if 'context_recovery' in self.manifest:
                        from native_context_control import read_result
                        observed = read_result(self.manifest, self.files, call, event, block)
                        if observed is not None:
                            self.recovery_reads.append({'call_line': start, 'result_line': self.line, **observed})
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
        return {'audit_write': self.last_write, 'validator': self.validator, 'validation': self.validation,
            **({'context_recovery_reads': self.recovery_reads} if 'context_recovery' in self.manifest else {})}


class StagedAuditHistory(AuditHistory):
    """Opt-in exact part Writes → typed assembly → existing once-only validator."""
    def __init__(self, manifest, registration_sha256, policy, *, replay=False):
        super().__init__(manifest, registration_sha256, policy)
        from . import output_parts
        self.parts_module = output_parts
        self.output = output_parts.configuration(manifest)
        self.part_writes = []
        self.assembler = self.assembly = None
        self.assembly_summary = None
        self.replay = replay

    def _artifact_hash(self):
        return self.assembly and self.assembly['audit']['sha256']

    def _part_descriptions(self):
        return [entry['part'] for entry in self.part_writes]

    def _current_parts(self, *, allow_empty=False):
        # Admission also verifies the initial empty roster. Assembly retains
        # read_parts' nonempty requirement, including during transcript replay.
        if allow_empty and not self.part_writes:
            block = self.parts_module.configuration(self.manifest)
            directory = self.parts_module.canonical(Path(block['parts'][0]).parent)
            if any(directory.iterdir()):  # Includes hidden/ignored entries.
                raise BudgetStop('audit parts differ from completed native Writes')
            return b'', []
        raw, parts = self.parts_module.read_parts(self.manifest)
        if parts != self._part_descriptions():
            raise BudgetStop('audit parts differ from completed native Writes')
        return raw, parts

    def _assembled(self):
        report = self.parts_module.verify_assembly(self.manifest, self.registration_sha256, self._part_descriptions())
        if self.assembly is not None and not self.parts_module.same_json(report, self.assembly):
            raise BudgetStop('audit assembly changed after its typed result')
        if (self.assembly_summary is not None and
                not self.parts_module.same_json(self.parts_module.summary(self.manifest, report), self.assembly_summary)):
            raise BudgetStop('audit assembly receipt bytes changed after its typed result')
        return report

    def verify_admission(self):
        with self.lock:
            deadline = time.monotonic() + VALIDATOR_RESULT_WAIT_SECONDS
            while not self.problem and ((self.assembler is not None and self.assembly is None) or
                    any(self.calls[key][1]['name'] == 'Write' for key in self.pending)):
                if time.monotonic() >= deadline:
                    raise BudgetStop('audit part or assembly has no observed successful typed result; no further request admitted')
                self.lock.wait(min(.05, max(0, deadline - time.monotonic())))
            if self.problem:
                raise BudgetStop(self.problem)
            receipt, failure = self.parts_module.receipt_paths(self.manifest)
            if os.path.lexists(failure) or (self.assembler is None and
                    any(os.path.lexists(p) for p in (self.audit, receipt, self.parts_module.ready_path(self.manifest)))):
                raise BudgetStop('audit output or assembly receipt has no successful observed assembly')
            if self.assembly is not None:
                self._assembled()
            else:
                self._current_parts(allow_empty=True)
            super().verify_admission()

    def _observe(self, event):
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
                pending_write = any(self.calls[key][1]['name'] == 'Write' for key in self.pending)
                if pending_write or (self.assembler is not None and self.assembly is None):
                    raise BudgetStop('audit part or assembly tool result is still pending')
                tokens, _ = _simple_command(payload.get('command')) if tool == 'Bash' and isinstance(payload.get('command'), str) else (None, None)
                assembly = tool == 'Bash' and tokens == self.policy['assemble_argv']
                validator = tool == 'Bash' and tokens == self.policy['validator_argv']
                if self.assembler is not None and not validator:
                    raise BudgetStop('only the terminal validator may follow audit assembly')
                if assembly or validator:
                    if (set(payload) - {'command', 'description', 'timeout'} or
                        ('description' in payload and not isinstance(payload['description'], str)) or
                        ('timeout' in payload and (type(payload['timeout']) is not int or payload['timeout'] <= 0)) or self.pending):
                        raise BudgetStop('audit helper requires foreground invocation and no pending tools')
                if tool == 'Write':
                    if self.pending or len(self.part_writes) >= len(self.output['parts']):
                        raise BudgetStop('audit part Write requires no pending tools and an unused registered slot')
                    target = self.files.target(payload.get('file_path'))
                    if (str(target) != self.output['parts'][len(self.part_writes)] or
                            self.files.classify(tool, payload)[0] != 'prescribed'):
                        raise BudgetStop('audit Write must use the next bounded registered part')
                    if not self.replay and os.path.lexists(target):
                        raise BudgetStop('audit part already exists before its native Write')
                    if self.part_writes and not self.replay:
                        self._current_parts()
                if assembly:
                    self._current_parts()
                    if self.assembler is not None:
                        raise BudgetStop('audit assembly is once-only')
                    if not self.replay and any(os.path.lexists(p) for p in (*self.parts_module.receipt_paths(self.manifest),
                            self.parts_module.ready_path(self.manifest), self.audit)):
                        raise BudgetStop('audit assembly has stale output or receipts')
                    self.assembler = {'id': identity, 'call_line': self.line}
                if validator:
                    if self.assembly is None:
                        raise BudgetStop('audit validator requires a completed typed assembly')
                    self._assembled()
                    self.validator = {'id': identity, 'line': self.line, 'audit_sha256': self._artifact_hash()}
                self.calls[identity] = (self.line, block)
                self.pending.add(identity)
            elif block.get('type') == 'tool_result':
                identity = block.get('tool_use_id')
                if identity not in self.calls or identity in self.results:
                    raise BudgetStop('audit result lacks a unique preceding call')
                self.results.add(identity); self.pending.discard(identity)
                start, call = self.calls[identity]
                if 'context_recovery' in self.manifest:
                    from native_context_control import read_result
                    recovered = read_result(self.manifest, self.files, call, event, block)
                    if recovered is not None:
                        self.recovery_reads.append({'call_line': start, 'result_line': self.line, **recovered})
                if call['name'] == 'Write':
                    target = Path(self.output['parts'][len(self.part_writes)])
                    if not _write_success(call, block, event, target):
                        raise BudgetStop('audit part Write lacks its exact successful typed result')
                    raw = call['input']['content'].encode('utf-8')
                    if self.parts_module.read_regular(target, self.output['max_part_bytes']) != raw:
                        raise BudgetStop('audit part differs from its native Write result')
                    self.part_writes.append({'call_line': start, 'result_line': self.line,
                                            'part': self.parts_module.describe(target, raw)})
                if ((self.assembler and identity == self.assembler['id']) or
                        (self.validator and identity == self.validator['id'])):
                    metadata = event.get('tool_use_result')
                    if (block.get('is_error') is not False or not isinstance(metadata, dict) or
                        metadata.get('interrupted') is not False or not isinstance(metadata.get('stdout'), str) or
                        not isinstance(metadata.get('stderr'), str) or
                        any(k in metadata and (type(metadata[k]) is not int or metadata[k] != 0) for k in ('exitCode', 'exit_code'))):
                        raise BudgetStop('audit helper lacks an exact successful typed result')
                    report = strict_json(metadata['stdout'])
                    if self.assembler and identity == self.assembler['id']:
                        expected = self._assembled()
                        if not self.parts_module.same_json(report, self.parts_module.summary(self.manifest, expected)):
                            raise BudgetStop('audit assembly stdout differs from its receipt')
                        self.assembly = expected
                        self.assembly_summary = report
                        self.assembler['result_line'] = self.line
                    else:
                        if not self.parts_module.same_json(report, self._marker()):
                            raise BudgetStop('audit validator result differs from its current receipt')
                        self.validation = report
        if event.get('type') == 'result':
            self.finish()

    def finish(self):
        if self.pending or not self.assembly or not self.validator or not self.validation:
            raise BudgetStop('audit completion lacks typed part assembly and a single successful terminal validator')
        self._assembled()
        if self.validation != self._marker():
            raise BudgetStop('audit validation changed after its result')
        return {'audit_parts': self.part_writes, 'audit_assembly': {**self.assembler, 'receipt': self.assembly,
                    'receipt_sha256': self.assembly_summary['receipt_sha256']},
                'validator': self.validator, 'validation': self.validation,
                **({'context_recovery_reads': self.recovery_reads} if 'context_recovery' in self.manifest else {})}


def make_history(manifest, registration_sha256, policy, *, replay=False):
    if 'audit_drafting' in manifest:
        from .draft_history import DraftAuditHistory
        return DraftAuditHistory(manifest, registration_sha256, policy, replay=replay)
    if 'audit_output' in manifest:
        return StagedAuditHistory(manifest, registration_sha256, policy, replay=replay)
    return AuditHistory(manifest, registration_sha256, policy)


class AuditProxy(NativeProxy):
    """Recheck terminal markers after token counting, before reservation/send."""
    def __init__(self, *, audit_history, **kwargs):
        self.audit_history = audit_history
        super().__init__(**kwargs)
        self.history_preflight = getattr(self.audit_history, 'responsive_control', False)
        if getattr(self.audit_history, 'responsive_control', False):
            self.audit_history.admission_cancelled = self.admission_closed
            self.control_shutdown = {'control_initialized': False,
                'control_shutdown_complete': True, 'unfinished_control_workers': 0}

    def preflight_open(self):
        if getattr(self.audit_history, 'responsive_control', False):
            self.audit_history.verify_admission()

    def require_open(self):
        super().require_open()
        if not getattr(self.audit_history, 'responsive_control', False):
            self.audit_history.verify_admission()

    @contextmanager
    def mutation_guard(self, phase):
        if phase == 'admit' and getattr(self.audit_history, 'responsive_control', False):
            # Always history -> proxy, never proxy -> expensive history. Keep
            # the verified history stable through the reservation operation.
            with self.audit_history.admission_lock():
                self.audit_history.verify_admission()
                with super().mutation_guard(phase):
                    yield
            return
        with super().mutation_guard(phase):
            if phase == 'admit':
                self.audit_history.verify_admission()
            yield

def inspect_transcript(events, policy, manifest, registration_sha256, control_path, config_root,
                       *, history_factory=None, command_classifier=classify_command, phase_key="phase3"):
    check = check_control_history(events, control_path, policy, command_classifier, config_root)
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
            classification, basis = command_classifier(payload.get('command'), policy['python'], [], policy)
        elif tool in ('Read', 'Write'):
            classification, basis = file_policy.classify(tool, payload)
        else:
            classification, basis = 'not_prescribed', 'tool not granted'
        classified.append({**denial, 'classification': classification, 'basis': basis})
    if any(d['classification'] != 'not_prescribed' for d in classified):
        raise BudgetStop('a prescribed or unclassifiable audit operation was denied')
    history = (history_factory(manifest, registration_sha256, policy) if history_factory else
               make_history(manifest, registration_sha256, policy, replay=True))
    for event in events:
        history.observe(event)
    return {'control': check, 'denials': classified, phase_key: history.finish(), 'terminal': terminal,
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
    native_api_force_idle_timeout(manifest)
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
    result = {'proxy_initialized': proxy is not None,
              'proxy_shutdown_complete': finalized, 'unfinished_handlers': count}
    control = getattr(proxy, 'control_shutdown', None)
    if control is not None:
        initialized = control.get('control_initialized')
        complete, workers = control.get('control_shutdown_complete'), control.get('unfinished_control_workers')
        valid = (type(initialized) is bool and type(complete) is bool
                 and type(workers) is int and workers >= 0 and complete == (workers == 0)
                 and (initialized or complete))
        result.update(control_initialized=initialized if type(initialized) is bool else None,
                      control_shutdown_complete=complete if valid else False,
                      unfinished_control_workers=workers if valid else None)
    return result


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


def execute_job(context, *, client=None, upstream=None, protocol=None):
    native_history_control(context.manifest)
    if 'audit_batches' in context.manifest:
        if protocol is not None:
            raise BudgetStop('audit batches are restricted to the native audit controller')
        from .batch_native import execute_job as execute_batches
        return execute_batches(context, client=client, upstream=upstream)
    state = {'stop_source': 'native_preflight', 'proxy': None}
    try:
        return _execute_job(context, state, client=client, upstream=upstream, protocol=protocol)
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


def _execute_job(context, state, *, client=None, upstream=None, protocol=None):
    manifest, job, attempt = context.manifest, context.job, context.attempt
    if 'audit_drafting' in manifest:
        if protocol is not None:
            raise BudgetStop('audit drafting is restricted to the native audit controller')
        from .draft_output import configuration
        configuration(manifest, context.registration_path)
    if 'audit_contract_context' in manifest:
        if protocol is not None:
            raise BudgetStop('audit_contract_context is restricted to the native audit controller')
        from .contract_context import enabled
        enabled(manifest)
    upstream_timeout = native_upstream_read_timeout(manifest)
    if upstream_timeout is not None and protocol is not None:
        raise BudgetStop('upstream read timeout is restricted to the native audit controller')
    stall_policy = native_stall_policy(manifest)
    if stall_policy is not None and protocol is not None:
        raise BudgetStop('stall policy is restricted to the native audit controller')
    response_buffer = native_response_buffer(manifest)
    if response_buffer is not None and protocol is not None:
        raise BudgetStop('response buffering is restricted to the native audit controller')
    selected = protocol or sys.modules[__name__]
    policy = selected.build_policy(manifest, context.registration_path)
    executable = verify_runtime(manifest)
    key = os.environ.get('CBORG_API_KEY')
    if not key and client is None:
        raise BudgetStop('CBORG_API_KEY is required')
    context.verify()
    state['stop_source'] = 'native_setup'
    config = attempt / 'cli_config'; config.mkdir(mode=0o700)
    billing_attempt = attempt_identity(context.manifest_sha256, job['id'])
    history = getattr(selected, 'make_history', selected.AuditHistory)(manifest, context.manifest_sha256, policy)
    if selected is sys.modules[__name__] and 'audit_output' in manifest:
        from .output_parts import configuration
        Path(configuration(manifest)['parts'][0]).parent.mkdir()
    if selected is sys.modules[__name__] and 'audit_drafting' in manifest:
        from .draft_output import configuration
        block = configuration(manifest)
        directory = Path(block['rounds'][0]['parts'][0]).parent.parent
        directory.mkdir()
        for row in block['rounds']:
            Path(row['parts'][0]).parent.mkdir()
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
            base_url=manifest['provider_base_url'], request_headers=provider_context_headers(manifest), upstream=upstream,
            **({'upstream_read_timeout_seconds': upstream_timeout} if upstream_timeout is not None else {}),
            **({'stall_policy': stall_policy} if stall_policy is not None else {}),
            **({'response_buffer': response_buffer} if response_buffer is not None else {}))
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
    idle_timeout = native_api_force_idle_timeout(manifest)
    if idle_timeout is not None:
        environment['API_FORCE_IDLE_TIMEOUT'] = 'false'
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
                verify_launch=admission, command_policy=policy, command_classifier=selected.classify_command,
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
    evidence = selected.inspect_transcript(load_native_events(attempt/'transcript.jsonl'), policy, manifest,
        context.manifest_sha256, attempt/'control.jsonl', config)
    evidence['initial_context'] = verify_initial_context(context, rows)
    if protocol is not None:
        return protocol.complete(context, evidence, {
            'exit_code': exit_code, 'native_version': manifest['native_runtime']['version'],
            'model': manifest['model']['model'], 'effort': 'native_default', **shutdown_evidence(proxy)})
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
        if 'audit_batches' in manifest:
            context._batch_clock = time.monotonic
            context._batch_deadline = time.monotonic() + job['deadline_seconds']
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
            if 'native_stall_policy' in manifest:
                # Requests the registered policy counted at their whole
                # reservation; their provider fee is unknown (#2150).
                receipt['stall_debited_requests'] = [r['id'] for r in rows
                                                     if r.get('settlement_basis') == STALL_DEBIT_BASIS]
            if 'audit_batches' in manifest and error is None:
                from .batch_native import finish_deadline
                try:
                    finish_deadline(context, result)
                except BaseException as late:
                    error = late
                    reason = str(late) if isinstance(late, BudgetStop) else type(late).__name__
                    receipt.update(status='stopped', error_type=type(late).__name__, reason=reason,
                        **getattr(late, 'native_stop', {'stop_source': 'batch_deadline',
                            'runtime': shutdown_evidence(None)}))
                    ledger.stop_attempt(billing_attempt, reason)
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
