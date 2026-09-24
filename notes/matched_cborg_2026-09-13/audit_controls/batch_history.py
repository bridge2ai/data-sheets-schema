"""Typed per-child history; workers cannot source-check, integrator checks once."""
import hashlib
import os
from pathlib import Path
import time

from budgeted_cborg import BudgetStop
from native_command_policy import _simple_command
from . import batch_output as output
from .native import AuditHistory, VALIDATOR_RESULT_WAIT_SECONDS, _blocks, _write_success
from .registration import strict_json
from .output_parts import read_regular, describe, same_json


# Fixed result enums from the pinned native 2.1.272 runtime (#2230). Unknown
# values remain unavailable; never copy arbitrary error or model-authored text.
_TERMINAL_ENUMS = {
    'subtype': frozenset({'success', 'error_during_execution', 'error_max_turns',
        'error_max_budget_usd', 'error_max_structured_output_retries'}),
    'terminal_reason': frozenset({'blocking_limit', 'rapid_refill_breaker', 'prompt_too_long',
        'image_error', 'model_error', 'api_error', 'malformed_tool_use_exhausted',
        'aborted_streaming', 'aborted_tools', 'stop_hook_prevented', 'hook_stopped',
        'tool_deferred', 'max_turns', 'background_requested', 'completed',
        'budget_exhausted', 'structured_output_retry_exhausted',
        'tool_deferred_unavailable', 'turn_setup_failed'}),
    'stop_reason': frozenset({'end_turn', 'max_tokens', 'stop_sequence', 'tool_use',
        'pause_turn', 'compaction', 'refusal', 'model_context_window_exceeded'}),
}


def _terminal_diagnostic(event):
    """Detached, individually validated scalars; never completion or cause proof.

    Missing, malformed and unknown fields are explicit. The limits below bound
    diagnostic values only and cannot change request admission or accounting.
    total_cost_usd is the CLI's estimate, not authoritative provider accounting.
    """
    fields, unavailable = {}, {}
    for key in (*_TERMINAL_ENUMS, 'is_error', 'num_turns', 'total_cost_usd', 'api_error_status'):
        if key not in event:
            unavailable[key] = 'absent'
            continue
        value = event[key]
        if key in _TERMINAL_ENUMS:
            valid = type(value) is str or (key == 'stop_reason' and value is None)
            if valid and value is not None and value not in _TERMINAL_ENUMS[key]:
                unavailable[key] = 'unrecognized'
                continue
        elif key == 'is_error':
            valid = type(value) is bool
        elif key == 'num_turns':
            valid = type(value) is int and 0 <= value <= 1_000_000
        elif key == 'total_cost_usd':
            valid = type(value) in (int, float) and 0 <= value <= 1_000_000
        else:
            valid = value is None or (type(value) is int and 100 <= value <= 599)
        if valid:
            fields[key] = value
        else:
            unavailable[key] = 'malformed'
    denials = event.get('permission_denials')
    if 'permission_denials' not in event:
        unavailable['permission_denial_count'] = 'absent'
    elif type(denials) is list and len(denials) <= 1_000_000 and all(type(d) is dict for d in denials):
        fields['permission_denial_count'] = len(denials)
    else:
        unavailable['permission_denial_count'] = 'malformed'
    return {'state': 'observed', 'fields': fields, 'unavailable': unavailable}


class BatchHistory(AuditHistory):
    def __init__(self, manifest, identity, policy, child_id, *, replay=False):
        super().__init__(manifest, identity, policy)
        self.child_id = child_id
        self.output = output.child(manifest, child_id)
        self.integration = child_id == 'integration'
        self.round = 1
        self.part_writes, self.drafts, self.row_reads = [], [], []
        self.checker = self.sealer = self.seal = self.seal_stdout = None
        self.assembler = self.assembly = self.assembly_stdout = None
        self.replay = replay
        self.native_terminal = {'state': 'absent'}

    def _parts(self):
        return [r['part'] for r in self.part_writes]

    def _current(self):
        raw, parts = output.read_round(self.manifest, self.child_id, self.round, allow_empty=not self.part_writes)
        if not same_json(parts, self._parts()):
            raise BudgetStop('batch parts differ from completed native Writes')
        return raw, parts

    def _prior(self):
        for draft in self.drafts:
            receipt = output.verify_check(self.manifest, self.registration_sha256, self.child_id,
                draft['round'], [r['part'] for r in draft['part_writes']])
            if (not same_json(receipt, draft['receipt']) or
                    output.check_summary(self.manifest, receipt)['receipt_sha256'] != draft['receipt_sha256']):
                raise BudgetStop('batch grammar receipt changed after typed success')

    def _sealed(self):
        self._prior()
        if not self.drafts or not self.drafts[-1]['receipt']['grammar']['passed']:
            raise BudgetStop('batch sealing requires an observed passing grammar result')
        last = self.drafts[-1]
        receipt = output.verify_seal(self.manifest, self.registration_sha256, self.child_id,
            last['round'], [r['part'] for r in last['part_writes']])
        if self.seal is not None and not same_json(self.seal, receipt):
            raise BudgetStop('batch seal changed after successful typed result')
        return receipt

    def _assembled(self):
        self._sealed()
        self._required_row_reads()
        receipt = output.validate_output(self.manifest)
        if self.assembly is not None and not same_json(self.assembly, receipt):
            raise BudgetStop('batch assembly changed after successful typed result')
        return receipt

    def _artifact_hash(self):
        return self.assembly and self.assembly['audit']['sha256']

    def _read_row(self, call, event, block, start):
        payload = call['input']
        if call['name'] != 'Read' or not self.integration:
            return
        path = str(self.files.target(payload.get('file_path')))
        descriptor = self.policy.get('batch_row_views', {}).get(path)
        if descriptor is None or self.files.classify('Read', payload)[0] != 'prescribed':
            return
        raw = read_regular(path, output.MAX_BYTES)
        if hashlib.sha256(raw).hexdigest() != descriptor['sha256']:
            raise BudgetStop('integration row view changed during native Read')
        lines = raw.decode('utf-8').split('\n')
        offset, limit = payload.get('offset', 1), payload.get('limit', len(lines))
        if (type(offset) is not int or type(limit) is not int or offset < 1
                or limit <= 0 or offset > len(lines)):
            raise BudgetStop('integration row Read has invalid bounds')
        selected = lines[offset - 1:offset - 1 + limit]
        metadata = event.get('tool_use_result')
        file = metadata.get('file') if type(metadata) is dict else None
        numbered = '\n'.join(f'{i}\t{line}' for i, line in enumerate(selected, offset))
        if ((block.get('is_error') is not None and block.get('is_error') is not False)
                or type(file) is not dict or metadata.get('type') != 'text' or file.get('filePath') != path
                or type(file.get('startLine')) is not int or file['startLine'] != offset
                or type(file.get('numLines')) is not int or file['numLines'] != len(selected)
                or type(file.get('totalLines')) is not int or file['totalLines'] != len(lines)
                or file.get('content') != '\n'.join(selected) or block.get('content') != numbered):
            raise BudgetStop('integration row Read lacks exact complete typed range evidence')
        self.row_reads.append({'path': path, 'sha256': descriptor['sha256'],
            'row_sha256': descriptor['row_sha256'], 'call_line': start, 'result_line': self.line,
            'offset': offset, 'limit': len(selected), 'total_lines': len(lines)})

    def _required_row_reads(self):
        for path, descriptor in self.policy.get('batch_row_views', {}).items():
            count = len(read_regular(path, output.MAX_BYTES).decode('utf-8').split('\n'))
            covered = set()
            for read in self.row_reads:
                if read['path'] == path and read['sha256'] == descriptor['sha256']:
                    covered.update(range(read['offset'], read['offset'] + read['limit']))
            if covered != set(range(1, count + 1)):
                raise BudgetStop('integration requires complete successful Reads of every prior worker row')

    def verify_admission(self):
        with self.admission_lock():
            deadline = time.monotonic() + self.result_wait_seconds
            while not self.problem and (self.checker is not None or
                    (self.sealer is not None and self.seal is None) or
                    (self.assembler is not None and self.assembly is None) or
                    (self.validator is not None and self.validation is None) or
                    any(self.calls[k][1]['name'] == 'Write' for k in self.pending)):
                self._check_admission_cancelled()
                left = deadline - time.monotonic()
                if left <= 0:
                    raise BudgetStop('batch tool has no observed successful result; no request admitted')
                self.lock.wait(min(.05, left))
            if self.problem:
                raise BudgetStop(self.problem)
            self._prior()
            for number in (1, 2):
                if number > len(self.drafts) and any(os.path.lexists(p) for p in output.check_paths(self.manifest, self.child_id, number)):
                    raise BudgetStop('batch receipt has no observed grammar invocation')
            if self.sealer is None and any(os.path.lexists(p) for p in (*output.seal_paths(self.manifest, self.child_id), self.output['proposal_path'])):
                raise BudgetStop('batch seal lacks an observed invocation')
            if self.seal is None:
                self._current()
            else:
                self._sealed()
            if self.integration:
                if self.assembler is None and any(os.path.lexists(p) for p in (*output.assembly_paths(self.manifest), self.audit)):
                    raise BudgetStop('batch assembly lacks an observed invocation')
                if self.assembly is not None:
                    self._assembled()
                super().verify_admission()

    def _observe(self, event):
        self.line += 1
        if type(event) is not dict:
            raise BudgetStop('batch transcript contains a non-object event')
        if event.get('type') == 'result':
            # Save safe metadata before finish() can reject an unsealed proposal.
            # A later result cannot replace the first observed diagnostic.
            if self.native_terminal['state'] == 'absent':
                self.native_terminal = _terminal_diagnostic(event)
            else:
                self.native_terminal = {**self.native_terminal, 'state': 'ambiguous'}
        for block in _blocks(event):
            if type(block) is not dict:
                continue
            if block.get('type') == 'tool_use':
                identity, tool, payload = block.get('id'), block.get('name'), block.get('input')
                if type(identity) is not str or not identity or identity in self.calls or type(payload) is not dict:
                    raise BudgetStop('batch tool identity/input is malformed')
                if self.validator is not None:
                    raise BudgetStop('no tools may follow the terminal batch validator')
                if (self.checker is not None or (self.sealer is not None and self.seal is None)
                        or (self.assembler is not None and self.assembly is None)
                        or any(self.calls[k][1]['name'] == 'Write' for k in self.pending)):
                    raise BudgetStop('batch helper has a pending result')
                tokens, _ = _simple_command(payload.get('command')) if tool == 'Bash' and isinstance(payload.get('command'), str) else (None, None)
                check = tool == 'Bash' and tokens == self.output['rounds'][self.round - 1]['check_argv']
                any_check = tool == 'Bash' and any(tokens == r['check_argv'] for r in self.output['rounds'])
                seal = tool == 'Bash' and tokens == self.output['seal_argv']
                assemble = self.integration and tool == 'Bash' and tokens == self.manifest['audit_batches']['assemble_argv']
                validator = self.integration and tool == 'Bash' and tokens == self.manifest['job']['validator_argv']
                if any_check and not check:
                    raise BudgetStop('batch grammar must use its current registered round')
                if self.sealer is not None and not (assemble or validator):
                    raise BudgetStop('only integration assembly and final validation may follow sealing')
                if self.assembler is not None and not validator:
                    raise BudgetStop('only terminal validation may follow assembly')
                passed = bool(self.drafts and self.drafts[-1]['receipt']['grammar']['passed'])
                row_read = self.integration and tool == 'Read' and str(self.files.target(payload.get('file_path'))) in self.policy.get('batch_row_views', {})
                if passed and self.sealer is None and not (seal or row_read):
                    raise BudgetStop('a passing batch draft must be sealed immediately')
                if check or seal or assemble or validator:
                    if (self.pending or set(payload) - {'command', 'description', 'timeout'}
                            or ('description' in payload and type(payload['description']) is not str)
                            or ('timeout' in payload and (type(payload['timeout']) is not int or payload['timeout'] <= 0))):
                        raise BudgetStop('batch helper requires a foreground invocation without pending tools')
                if tool == 'Write':
                    if self.pending or len(self.part_writes) >= output.MAX_PARTS:
                        raise BudgetStop('batch Write requires an unused slot and no pending tools')
                    target = self.files.target(payload.get('file_path'))
                    expected = self.output['rounds'][self.round - 1]['parts'][len(self.part_writes)]
                    if str(target) != expected or self.files.classify(tool, payload)[0] != 'prescribed':
                        raise BudgetStop('batch Write must use its next registered part')
                    if not self.replay and os.path.lexists(target):
                        raise BudgetStop('batch native part already exists')
                    if self.part_writes and not self.replay:
                        self._current()
                if check:
                    if not self.part_writes or len(self.drafts) >= self.round:
                        raise BudgetStop('batch grammar requires completed parts and an unused round')
                    self._current()
                    if not self.replay and any(os.path.lexists(p) for p in output.check_paths(self.manifest, self.child_id, self.round)):
                        raise BudgetStop('batch grammar has stale receipts')
                    self.checker = {'id': identity, 'call_line': self.line}
                if seal:
                    if not passed or self.sealer is not None:
                        raise BudgetStop('batch sealing requires its passing typed grammar')
                    self._prior()
                    if self.integration:
                        self._required_row_reads()
                    self.sealer = {'id': identity, 'call_line': self.line}
                if assemble:
                    if self.seal is None or self.assembler is not None:
                        raise BudgetStop('batch assembly requires typed integration sealing exactly once')
                    self._sealed(); self._required_row_reads()
                    self.assembler = {'id': identity, 'call_line': self.line}
                if validator:
                    if self.assembly is None:
                        raise BudgetStop('batch validator requires typed full assembly')
                    self._assembled()
                    self.validator = {'id': identity, 'line': self.line, 'audit_sha256': self._artifact_hash()}
                self.calls[identity] = (self.line, block); self.pending.add(identity)
            elif block.get('type') == 'tool_result':
                identity = block.get('tool_use_id')
                if identity not in self.calls or identity in self.results:
                    raise BudgetStop('batch result lacks one preceding tool call')
                self.results.add(identity); self.pending.discard(identity)
                start, call = self.calls[identity]
                self._read_row(call, event, block, start)
                if call['name'] == 'Write':
                    target = Path(self.output['rounds'][self.round - 1]['parts'][len(self.part_writes)])
                    if not _write_success(call, block, event, target):
                        raise BudgetStop('batch Write lacks its exact successful typed result')
                    raw = call['input']['content'].encode('utf-8')
                    if read_regular(target, output.MAX_PART_BYTES) != raw:
                        raise BudgetStop('batch part differs from exact native Write')
                    self.part_writes.append({'call_line': start, 'result_line': self.line, 'part': describe(target, raw)})
                checker = self.checker and identity == self.checker['id']
                sealer = self.sealer and identity == self.sealer['id']
                assembler = self.assembler and identity == self.assembler['id']
                validator = self.validator and identity == self.validator['id']
                if checker or sealer or assembler or validator:
                    metadata = event.get('tool_use_result')
                    if (block.get('is_error') is not False or type(metadata) is not dict
                            or metadata.get('interrupted') is not False or type(metadata.get('stdout')) is not str
                            or type(metadata.get('stderr')) is not str or any(k in metadata and
                            (type(metadata[k]) is not int or metadata[k] != 0) for k in ('exitCode', 'exit_code'))):
                        raise BudgetStop('batch helper lacks an exact successful typed result')
                    report = strict_json(metadata['stdout'])
                    if checker:
                        receipt = output.verify_check(self.manifest, self.registration_sha256, self.child_id, self.round, self._parts())
                        summary = output.check_summary(self.manifest, receipt)
                        if not same_json(report, summary):
                            raise BudgetStop('batch grammar stdout differs from its receipt')
                        self.checker['result_line'] = self.line
                        self.drafts.append({'round': self.round, 'part_writes': self.part_writes,
                            'checker': self.checker, 'receipt': receipt, 'receipt_sha256': summary['receipt_sha256']})
                        self.checker = None
                        if not receipt['grammar']['passed']:
                            if self.round == output.MAX_ROUNDS:
                                raise BudgetStop('batch exhausted its grammar drafts')
                            self.round += 1; self.part_writes = []
                    elif sealer:
                        receipt = self._sealed()
                        if not same_json(report, output.seal_summary(self.manifest, receipt)):
                            raise BudgetStop('batch seal stdout differs from its receipt')
                        self.seal, self.seal_stdout = receipt, report
                        self.sealer['result_line'] = self.line
                    elif assembler:
                        receipt = self._assembled()
                        if not same_json(report, output.assembly_summary(self.manifest, receipt)):
                            raise BudgetStop('batch assembly stdout differs from its receipt')
                        self.assembly, self.assembly_stdout = receipt, report
                        self.assembler['result_line'] = self.line
                    else:
                        if not same_json(report, self._marker()):
                            raise BudgetStop('batch validator stdout differs from its receipt')
                        self.validation = report
        if event.get('type') == 'result':
            self.finish()

    def finish(self):
        if self.pending or self.seal is None:
            raise BudgetStop('batch child lacks complete typed proposal sealing')
        self._sealed()
        result = {'child_id': self.child_id, 'drafts': self.drafts,
            'seal': {**self.sealer, 'receipt': self.seal, 'receipt_sha256': self.seal_stdout['receipt_sha256']},
            'row_reads': self.row_reads}
        if self.integration:
            if self.assembly is None or self.validator is None or self.validation is None:
                raise BudgetStop('integration lacks complete typed assembly and terminal validation')
            self._assembled()
            if not same_json(self.validation, self._marker()):
                raise BudgetStop('batch validation changed after successful result')
            result.update(assembly={**self.assembler, 'receipt': self.assembly,
                'receipt_sha256': self.assembly_stdout['receipt_sha256']},
                validator=self.validator, validation=self.validation)
        return result
