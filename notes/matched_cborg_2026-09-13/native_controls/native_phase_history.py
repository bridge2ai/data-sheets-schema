"""Review the native receipt boundary and terminal source/evidence failures.

This is an execution-history check, not schema validation or semantic review.
Callers must supply the frozen RunSpec and the original ordered native events,
with its registered repository. Permission/control evidence, ordered initial
source reads and receipt writes, original-freeze hashes, complete Phase 3/4
artifacts and scientific acceptance are checked separately. Partial observations do not
fail merely because a Phase 1 correction or tool result is still pending.
"""
from pathlib import Path
from types import SimpleNamespace

from native_command_policy import classify_program_command, _simple_command

HELPER_ARGUMENTS = 1


def _options(tokens, flags=()):
    result = {}
    while tokens:
        key, *tokens = tokens
        if not key.startswith('--') or key in result:
            raise ValueError('unexpected or duplicate helper argument')
        if key in flags:
            result[key] = True
        elif tokens and not tokens[0].startswith('--'):
            result[key], *tokens = tokens
        else:
            raise ValueError('missing helper argument')
    return result


def _path(value, repository=None):
    # Match relative spellings from the registered cwd without following links
    # into different file identities. The file-control audit verifies links.
    import os
    return os.path.abspath(os.path.join(str(repository or Path.cwd()), str(value)))


def _require(condition):
    if not condition:
        raise ValueError("helper arguments differ from the selected run")


def _classify(command, spec, repository, command_policy):
    """Recognize selected commands; a different run can never satisfy a gate."""
    if not isinstance(command, str):
        return None, None
    path = lambda value: _path(value, repository)
    python = spec._agentic_toolchain['python']
    tokens, _ = _simple_command(command)
    if tokens is None:
        return None, None
    if tokens[:2] != [python, '-m'] or len(tokens) < 3:
        return None, None
    if classify_program_command(command, python, set(), command_policy)[0] != 'prescribed':
        # These commands will be denied by the permission controller. They
        # cannot satisfy or violate a phase gate through a helper they never
        # execute. Keep their call/result bookkeeping for the separate audit.
        # Under a policy that records the helper arguments, that includes a
        # helper called with other arguments (#2444).
        return None, None
    return _helper_arguments(tokens, spec, path)


def _helper_arguments(tokens, spec, path):
    """The helper a `python -m` command runs and whether its arguments are the selected run's."""
    paths = spec._agentic_artifact_paths
    module, args = tokens[2], tokens[3:]
    if module == 'data_sheets_schema.cli':
        root = {}
        if args[:1] == ['--manifest'] and len(args) >= 2:
            root, args = {'--manifest': args[1]}, args[2:]
        head, args = args[:2], args[2:]
        if head not in (['receipts', 'check'], ['derive', 'core']):
            return None, None
        kind = 'receipts' if head[0] == 'receipts' else 'derive'
        try:
            options = _options(args, {'--strict', '--write', '--validate', '--phase4-complete'})
            if root:
                expected = 'none' if spec.manifest is None else str(spec.manifest)
                _require(root['--manifest'] == expected or (
                    expected != 'none' and path(root['--manifest']) == path(expected)))
            if kind == 'receipts':
                _require(root and options.get('--strict') is True)
                _require(options.get('--method') == spec.method)
                _require(options.get('--label') == spec.label)
                _require(options.get('--project') == spec.project)
                _require(path(options['--bundle']) == path(spec.bundle))
                _require(path(options['--chunk-manifest']) == path(spec.chunk_manifest))
                _require(set(options) <= {'--strict', '--write', '--method', '--label', '--project',
                                        '--bundle', '--chunk-manifest'})
            else:
                _require(path(options['--full']) == path(paths['full']))
                _require(path(options['--out']) == path(paths['core']))
                _require(set(options) <= {'--full', '--out', '--validate', '--phase4-complete'})
            return kind, None
        except (ValueError, KeyError):
            return kind, 'helper arguments differ from the selected run'
    if module not in {'data_sheets_schema.evidence_assertions', 'data_sheets_schema.source_review'}:
        return None, None
    kind = 'evidence' if module.endswith('evidence_assertions') else 'source_inventory'
    try:
        options = _options(args)
        directory = Path(paths['core']).parent / 'evidence'
        if kind == 'source_inventory':
            artifact = options['--artifact']
            _require(artifact in {'original_full', 'final_full'})
            record = directory / 'original_full.yaml' if artifact == 'original_full' else paths['full']
            _require(path(options['--record']) == path(record))
            _require(set(options) == {'--record', '--artifact'})
        else:
            from data_sheets_schema.evidence_assertions import protocol_for_renderer
            required = {'--audit': directory / 'audit.json', '--bundle': spec.bundle,
                        '--manifest': spec.chunk_manifest, '--original-full': directory / 'original_full.yaml',
                        '--original-core': directory / 'original_core.yaml'}
            final = {'--final-full': paths['full'], '--final-core': paths['core'], '--report': paths['report']}
            if any(key in options for key in final):
                required.update(final)
            if spec.render_version >= 16 and spec.manifest_used:
                required['--source-manifest'] = spec.manifest
            _require(all(path(options[key]) == path(value) for key, value in required.items()))
            if spec.render_version >= 16 and spec.manifest_used:
                required['--project'] = spec.project
                _require(options.get('--project') == spec.project)
            if spec.render_version >= 11:
                # A policy view carries the version recorded when it was built (#2490).
                recorded = getattr(spec, 'protocol_version', None)
                required['--protocol-version'] = str(recorded if recorded is not None
                                                     else protocol_for_renderer(spec.render_version))
                _require(options.get('--protocol-version') == required['--protocol-version'])
            _require(set(options) == set(required))
        return kind, None
    except (ValueError, KeyError):
        return kind, 'helper arguments differ from the selected run'


def helper_expectations(spec, repository):
    """What `_helper_arguments` reads from a run specification, as plain values a
    command policy can carry, so the controller can refuse a helper call with
    other arguments before it runs instead of stopping on it afterwards (#2444)."""
    return {'version': HELPER_ARGUMENTS, 'repository': _path(repository),
            'python': spec._agentic_toolchain['python'], 'method': spec.method, 'label': spec.label,
            'project': spec.project, 'bundle': str(spec.bundle), 'chunk_manifest': str(spec.chunk_manifest),
            'manifest': None if spec.manifest is None else str(spec.manifest),
            'manifest_used': bool(spec.manifest_used), 'render_version': spec.render_version,
            'artifact_paths': {key: str(value) for key, value in spec._agentic_artifact_paths.items()},
            'protocol_version': _protocol_version(spec.render_version)}


def _protocol_version(render_version):
    if render_version < 11:
        return None
    from data_sheets_schema.evidence_assertions import protocol_for_renderer
    return protocol_for_renderer(render_version)


def helper_argument_problem(command, policy):
    """(kind, problem) for a registered helper called with other arguments, else (kind, None)."""
    view = policy['helper_arguments']
    if not isinstance(view, dict) or view.get('version') != HELPER_ARGUMENTS:
        raise ValueError('unsupported registered helper arguments')
    tokens, _ = _simple_command(command) if isinstance(command, str) else (None, None)
    if tokens is None or tokens[:2] != [view['python'], '-m'] or len(tokens) < 3:
        return None, None
    spec = SimpleNamespace(_agentic_artifact_paths=view['artifact_paths'], method=view['method'],
                           label=view['label'], project=view['project'], bundle=view['bundle'],
                           chunk_manifest=view['chunk_manifest'], manifest=view['manifest'],
                           manifest_used=view['manifest_used'], render_version=view['render_version'],
                           protocol_version=view.get('protocol_version'))
    return _helper_arguments(tokens, spec, lambda value: _path(value, view['repository']))


class PhaseHistory:
    """Incremental boundary reviewer; no result or current-file repair erases history."""

    def __init__(self, spec, repository=None, command_policy=None):
        self.spec = spec
        self.repository = _path(repository or Path.cwd())
        self.command_policy = command_policy if command_policy is not None else {
            'programs': [], 'manifest_paths': [str(spec.manifest) if spec.manifest is not None else 'none']}
        self._pending, self._seen = {}, set()
        self._epoch, self._passed_epoch, self._index = 0, None, 0
        self._latest_receipt = None
        self._result = {'checked': True, 'phase1_receipt_checks': [], 'phase2_started': False,
                        'phase2_completed': False, 'receipt_gate_current': False,
                        'terminal_failures': [], 'continuation_after_terminal': [],
                        'pending_tool_ids': [], 'problems': []}

    def observe(self, event):
        """Observe one original native event before any callback is admitted."""
        self._index += 1
        index, spec, result = self._index, self.spec, self._result
        pending, seen = self._pending, self._seen
        epoch, passed_epoch = self._epoch, self._passed_epoch
        paths = spec._agentic_artifact_paths
        problem = result['problems'].append
        if not isinstance(event, dict):
            return
        message = event.get('message')
        if not isinstance(message, dict):
            return
        content = message.get('content') or []
        if not isinstance(content, list):
            return
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'tool_use' and event.get('type') == 'assistant':
                identity = item.get('id')
                if not isinstance(identity, str) or identity in seen:
                    problem(f'event {index}: missing or duplicate tool identity')
                    continue
                seen.add(identity)
                name, inputs = item.get('name'), item.get('input')
                if not isinstance(inputs, dict):
                    problem(f'event {index}: tool call has nonmapping inputs')
                    continue
                kind, mismatch = _classify(inputs.get('command', ''), spec, self.repository, self.command_policy) if name == 'Bash' else (None, None)
                row = {'tool_use_id': identity, 'call_event': index, 'kind': kind, 'epoch': epoch}
                if result['terminal_failures']:
                    result['continuation_after_terminal'].append({'tool_use_id': identity, 'call_event': index})
                    problem(f'event {index}: tool continuation after terminal evidence/source failure')
                if mismatch:
                    problem(f'event {index}: {kind} {mismatch}')
                    row['mismatch'] = True
                if kind and inputs.get('run_in_background') not in (None, False):
                    problem(f'event {index}: selected phase helper requested background execution')
                    row['mismatch'] = True
                if kind == 'receipts' and not result['phase2_completed']:
                    # A new observation supersedes an older pass immediately,
                    # before its callback can execute or its result can arrive.
                    self._latest_receipt = identity
                    passed_epoch = None
                if name == 'Write' and 'file_path' in inputs:
                    target = _path(inputs['file_path'], self.repository)
                    if target in {_path(paths['full'], self.repository), _path(paths['receipt'], self.repository)}:
                        epoch += 1
                        passed_epoch = None
                        row['mutation'] = True
                    if target == _path(paths['core'], self.repository) and not result['phase2_completed']:
                        problem(f'event {index}: core written before successful deterministic derivation')
                if kind == 'derive':
                    result['phase2_started'] = True
                    if not result['phase2_completed'] and (passed_epoch != epoch or any(
                            call.get('mutation') or call['kind'] == 'receipts'
                            for call in pending.values())):
                        problem(f'event {index}: core derivation precedes a passing receipt check for current files')
                pending[identity] = row
            elif item.get('type') == 'tool_result' and event.get('type') == 'user':
                identity = item.get('tool_use_id')
                row = pending.pop(identity, None)
                if row is None:
                    problem(f'event {index}: tool result has no unique pending call')
                    continue
                success = item.get('is_error') is False
                kind = row['kind']
                metadata = event.get('tool_use_result')
                if kind and isinstance(metadata, dict) and (
                        metadata.get('interrupted') or metadata.get('backgroundTaskId')
                        or metadata.get('background_task_id')):
                    success = False
                    problem(f'event {index}: helper result is interrupted or pending')
                if kind and isinstance(metadata, dict) and (
                        metadata.get('exitCode') not in (None, 0)
                        or metadata.get('exit_code') not in (None, 0)):
                    # Ordinary Phase 1 receipt failures permit correction;
                    # exit metadata must not make them globally terminal.
                    success = False
                if kind and not isinstance(item.get('is_error'), bool):
                    problem(f'event {index}: tool result lacks boolean success evidence')
                if kind == 'receipts' and not result['phase2_completed']:
                    observation = {**row, 'result_event': index, 'success': success}
                    result['phase1_receipt_checks'].append(observation)
                    # Keep the newest successful observation while older read-only
                    # checks settle. Admission/reporting still requires no pending
                    # check; older results cannot overwrite the newest verdict.
                    if identity == self._latest_receipt:
                        if (success and not row.get('mismatch') and row['epoch'] == epoch
                                and not any(call.get('mutation') for call in pending.values())):
                            passed_epoch = epoch
                        else:
                            passed_epoch = None
                if kind == 'derive' and success and not row.get('mismatch'):
                    result['phase2_completed'] = True
                if kind in {'evidence', 'source_inventory'} and (not success or row.get('mismatch')):
                    result['terminal_failures'].append({**row, 'result_event': index})
                    problem(f'event {index}: terminal {kind} check failed')
        self._epoch, self._passed_epoch = epoch, passed_epoch

    def report(self, complete=False):
        """Return detached evidence; partial observations need no completed pair."""
        from copy import deepcopy
        result = deepcopy(self._result)
        result['receipt_gate_current'] = self._passed_epoch == self._epoch and not any(
            call.get('mutation') or call['kind'] == 'receipts' for call in self._pending.values())
        result['pending_tool_ids'] = sorted(self._pending)
        if complete:
            if self._pending:
                result['problems'].append('completed attempt has tool calls without results')
            if not result['phase2_completed']:
                result['problems'].append('completed attempt has no successful core derivation')
        return result


def phase_history(events, spec, complete=False, repository=None, command_policy=None):
    """Review ordered events with the same state machine used during execution.

    Receipt summaries contain nongating diagnostics. Only actual helper result
    metadata establishes pass/fail; scientific acceptance is still separate.
    """
    reviewer = PhaseHistory(spec, repository=repository, command_policy=command_policy)
    for event in events:
        reviewer.observe(event)
    return reviewer.report(complete=complete)
