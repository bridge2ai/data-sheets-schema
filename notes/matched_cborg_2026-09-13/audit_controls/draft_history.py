"""Typed history for the separately registered, bounded audit drafting stage."""
import os
from pathlib import Path
import time

from budgeted_cborg import BudgetStop
from native_command_policy import _simple_command
from . import draft_output as output
from .native import AuditHistory, VALIDATOR_RESULT_WAIT_SECONDS, _blocks, _write_success
from .registration import strict_json
from .output_parts import read_regular, describe, same_json


class DraftAuditHistory(AuditHistory):
    def __init__(self, manifest, registration_sha256, policy, *, replay=False):
        super().__init__(manifest, registration_sha256, policy)
        self.output = output.configuration(manifest)
        self.round = 1
        self.part_writes = []
        self.drafts = []
        self.checker = None
        self.sealer = self.seal = self.seal_stdout = None
        self.replay = replay

    def _artifact_hash(self):
        return self.seal and self.seal['audit']['sha256']

    def _parts(self):
        return [row['part'] for row in self.part_writes]

    def _current(self):
        raw, parts = output.read_round(self.manifest, self.round, allow_empty=not self.part_writes)
        if parts != self._parts():
            raise BudgetStop('draft parts differ from completed native Writes')
        return raw, parts

    def _check_prior(self):
        for draft in self.drafts:
            parts = [row['part'] for row in draft['part_writes']]
            receipt = output.verify_check(self.manifest, self.registration_sha256, draft['round'], parts)
            summary = output.check_summary(self.manifest, receipt)
            if (not same_json(receipt, draft['receipt']) or
                    summary['receipt_sha256'] != draft['receipt_sha256']):
                raise BudgetStop('checked draft or grammar receipt changed after its typed result')

    def _sealed(self):
        if not self.drafts or self.drafts[-1]['receipt']['grammar']['passed'] is not True:
            raise BudgetStop('audit seal requires a passed observed grammar result')
        self._check_prior()
        last = self.drafts[-1]
        report = output.verify_seal(self.manifest, self.registration_sha256, last['round'],
                                    [row['part'] for row in last['part_writes']])
        if self.seal is not None and not same_json(report, self.seal):
            raise BudgetStop('audit seal changed after its typed result')
        if self.seal_stdout is not None and not same_json(output.seal_summary(self.manifest, report), self.seal_stdout):
            raise BudgetStop('audit seal receipt bytes changed')
        return report

    def verify_admission(self):
        with self.lock:
            deadline = time.monotonic() + VALIDATOR_RESULT_WAIT_SECONDS
            while not self.problem and (self.checker is not None or
                    (self.sealer is not None and self.seal is None) or
                    any(self.calls[key][1]['name'] == 'Write' for key in self.pending)):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BudgetStop('draft tool has no observed typed result; no further request admitted')
                self.lock.wait(min(.05, remaining))
            if self.problem:
                raise BudgetStop(self.problem)
            output.verify_open(self.manifest)
            self._check_prior()
            # A receipt without its observed command/result never admits spending.
            for number in range(1, self.output['max_rounds'] + 1):
                if number > len(self.drafts) and any(os.path.lexists(p) for p in output.check_paths(self.manifest, number)):
                    raise BudgetStop('draft receipt has no observed typed checker result')
            if self.sealer is None and any(os.path.lexists(p) for p in
                    (*output.seal_paths(self.manifest), self.audit)):
                raise BudgetStop('audit seal has no observed invocation')
            if self.seal is not None:
                self._sealed()
            else:
                self._current()
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
                if self.checker is not None or (self.sealer is not None and self.seal is None) or any(
                        self.calls[key][1]['name'] == 'Write' for key in self.pending):
                    raise BudgetStop('draft Write or helper result is still pending')
                tokens, _ = _simple_command(payload.get('command')) if tool == 'Bash' and isinstance(payload.get('command'), str) else (None, None)
                check = tool == 'Bash' and tokens == self.output['rounds'][self.round-1]['check_argv']
                any_check = tool == 'Bash' and any(tokens == row['check_argv'] for row in self.output['rounds'])
                seal = tool == 'Bash' and tokens == self.output['seal_argv']
                validator = tool == 'Bash' and tokens == self.policy['validator_argv']
                if any_check and not check:
                    raise BudgetStop('draft grammar check must use the current registered round')
                if self.sealer is not None and not validator:
                    raise BudgetStop('only the terminal validator may follow audit sealing')
                passed = self.drafts and self.drafts[-1]['receipt']['grammar']['passed'] is True
                if passed and self.sealer is None and not seal:
                    raise BudgetStop('a grammar-passing draft must be sealed without further drafting')
                if check or seal or validator:
                    if (set(payload) - {'command', 'description', 'timeout'} or
                            ('description' in payload and not isinstance(payload['description'], str)) or
                            ('timeout' in payload and (type(payload['timeout']) is not int or payload['timeout'] <= 0)) or self.pending):
                        raise BudgetStop('audit helper requires a foreground invocation and no pending tools')
                if tool == 'Write':
                    if self.pending or len(self.part_writes) >= self.output['max_parts']:
                        raise BudgetStop('draft Write requires no pending tools and an unused slot')
                    target = self.files.target(payload.get('file_path'))
                    expected = self.output['rounds'][self.round-1]['parts'][len(self.part_writes)]
                    if str(target) != expected or self.files.classify(tool, payload)[0] != 'prescribed':
                        raise BudgetStop('draft Write must use its next registered part')
                    if not self.replay and os.path.lexists(target):
                        raise BudgetStop('draft part already exists before native Write')
                    if self.part_writes and not self.replay:
                        self._current()
                if check:
                    if not self.part_writes or len(self.drafts) >= self.round:
                        raise BudgetStop('draft check requires completed parts and an unchecked round')
                    self._current()
                    if not self.replay and any(os.path.lexists(p) for p in output.check_paths(self.manifest, self.round)):
                        raise BudgetStop('draft check has stale receipts')
                    self.checker = {'id': identity, 'call_line': self.line}
                if seal:
                    if not passed or self.sealer is not None:
                        raise BudgetStop('audit seal is once-only after passed grammar')
                    self._check_prior()
                    if not self.replay and any(os.path.lexists(p) for p in (*output.seal_paths(self.manifest), self.audit)):
                        raise BudgetStop('audit seal has stale output or receipts')
                    self.sealer = {'id': identity, 'call_line': self.line}
                if validator:
                    if self.seal is None:
                        raise BudgetStop('audit validator requires completed typed sealing')
                    self._sealed()
                    self.validator = {'id': identity, 'line': self.line, 'audit_sha256': self._artifact_hash()}
                self.calls[identity] = (self.line, block)
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
                    recovered = read_result(self.manifest, self.files, call, event, block)
                    if recovered is not None:
                        self.recovery_reads.append({'call_line': start, 'result_line': self.line, **recovered})
                if call['name'] == 'Write':
                    target = Path(self.output['rounds'][self.round-1]['parts'][len(self.part_writes)])
                    if not _write_success(call, block, event, target):
                        raise BudgetStop('draft Write lacks its exact successful typed result')
                    raw = call['input']['content'].encode('utf-8')
                    if read_regular(target, self.output['max_part_bytes']) != raw:
                        raise BudgetStop('draft part differs from its native Write result')
                    self.part_writes.append({'call_line': start, 'result_line': self.line, 'part': describe(target, raw)})
                checker = self.checker and identity == self.checker['id']
                sealer = self.sealer and identity == self.sealer['id']
                validator = self.validator and identity == self.validator['id']
                if checker or sealer or validator:
                    metadata = event.get('tool_use_result')
                    if (block.get('is_error') is not False or not isinstance(metadata, dict) or
                            metadata.get('interrupted') is not False or not isinstance(metadata.get('stdout'), str) or
                            not isinstance(metadata.get('stderr'), str) or any(k in metadata and
                            (type(metadata[k]) is not int or metadata[k] != 0) for k in ('exitCode', 'exit_code'))):
                        raise BudgetStop('draft helper lacks an exact successful typed result')
                    report = strict_json(metadata['stdout'])
                    if checker:
                        receipt = output.verify_check(self.manifest, self.registration_sha256, self.round, self._parts())
                        expected = output.check_summary(self.manifest, receipt)
                        if not same_json(report, expected):
                            raise BudgetStop('draft grammar stdout differs from its receipt')
                        self.checker['result_line'] = self.line
                        self.drafts.append({'round': self.round, 'part_writes': self.part_writes,
                            'checker': self.checker, 'receipt': receipt, 'receipt_sha256': expected['receipt_sha256']})
                        self.checker = None
                        if receipt['grammar']['passed'] is not True:
                            if self.round == self.output['max_rounds']:
                                raise BudgetStop('final registered grammar draft failed; no further request admitted')
                            self.round += 1
                            self.part_writes = []
                    elif sealer:
                        receipt = self._sealed()
                        if not same_json(report, output.seal_summary(self.manifest, receipt)):
                            raise BudgetStop('draft seal stdout differs from its receipt')
                        self.seal, self.seal_stdout = receipt, report
                        self.sealer['result_line'] = self.line
                    else:
                        if not same_json(report, self._marker()):
                            raise BudgetStop('audit validator result differs from its receipt')
                        self.validation = report
        if event.get('type') == 'result':
            self.finish()

    def finish(self):
        if self.pending or not self.seal or not self.validator or not self.validation:
            raise BudgetStop('audit completion lacks typed drafts, sealing and a successful terminal validator')
        self._sealed()
        if self.validation != self._marker():
            raise BudgetStop('audit validation changed after its result')
        return {'audit_drafts': self.drafts, 'audit_seal': {**self.sealer, 'receipt': self.seal,
                    'receipt_sha256': self.seal_stdout['receipt_sha256']},
                'validator': self.validator, 'validation': self.validation,
                **({'context_recovery_reads': self.recovery_reads} if 'context_recovery' in self.manifest else {})}
