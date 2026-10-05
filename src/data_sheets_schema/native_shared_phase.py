"""Pure ordered-helper checks for the explicitly selected native26 contract.

The caller supplies the fixed renderer's commands and freshly reconstructed
stage decisions. This module does not read files, publish seals, authenticate
callbacks, validate scientific support, or replace the other native gates.
The same observer is used live and when replaying captured native events.
"""
from __future__ import annotations

from copy import deepcopy
import os
import re
import shlex

from . import native_shared_contract as c


COMMAND_NAMES = frozenset((
    'chunk_check', 'source_scope', 'full_schema', 'full_terms', 'phase1_receipts',
    'advance', 'derive_core', 'core_schema', 'pair', 'original_source_inventory',
    'final_source_inventory', 'draft', 'audit_evidence', 'final_evidence',
    'derive_final_core', 'final_scope', 'recorder'))
_TERMINAL_HELPERS = frozenset((
    'original_source_inventory', 'final_source_inventory', 'audit_evidence', 'final_evidence'))
_JSON_HELPERS = _TERMINAL_HELPERS | {'draft', 'advance'}
_ADVANCE_KEYS = frozenset((
    'kind', 'version', 'selection_sha256', 'execution_sha256', 'attempt_id', 'session_id',
    'advance_tool_use_id', 'before_history_sha256', 'after_history_sha256', 'state', 'publications'))


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _digest(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


class PhaseState:
    """Track actual settled helpers and mutation epochs, never proposed success.

    ``before`` has no side effects. ``observe`` records calls/results and returns
    seal actions only after their prerequisites settle. A capture-layer caller
    must publish and independently verify those seals. The lexical path helper
    recognizes attempted mutations; it grants no alias or filesystem access.
    """

    def __init__(self, commands, *, full_path, core_path, report_path, receipt_path,
                 working_directory):
        _require(type(commands) is dict and set(commands) == COMMAND_NAMES,
                 'native phase requires the exact seventeen helper names')
        self.commands = {}
        for name, argv in commands.items():
            _require(type(argv) is tuple and argv and all(type(x) is str and x for x in argv),
                     'native phase helper argv must be a nonempty tuple of text')
            self.commands[shlex.join(argv)] = name
        _require(len(self.commands) == len(COMMAND_NAMES), 'native helper commands must be distinct')
        c.canonical_path(working_directory, 'phase working directory')
        self.working_directory = working_directory
        self.paths = {'full': full_path, 'core': core_path, 'report': report_path, 'receipt': receipt_path}
        for value in self.paths.values():
            c.canonical_path(value, 'phase artifact path')
        _require(len(set(self.paths.values())) == 4, 'phase artifact paths must be distinct')
        self._epoch = dict.fromkeys(self.paths, 0)
        self._written = set()
        self._passed = {}
        self._latest = {}
        self._pending = {}
        self._seen = set()
        self._problems = []
        self._checks = []
        self._terminal_failures = []
        self._session = None
        self._native_terminal = False
        self._phase1_sealed = self._core_sealed = self._assembly_complete = False
        self._binding = None
        self._report_inventory = None
        self._stage_state = None
        self._index = 0

    def _path(self, value):
        _require(type(value) is str and value and '\x00' not in value, 'file effect lacks a path')
        return os.path.normpath(os.path.join(self.working_directory, value))

    def _stamp(self, name):
        roles = {
            'full_schema': ('full',), 'full_terms': ('full',),
            'phase1_receipts': ('full', 'receipt'), 'derive_core': ('full', 'core'),
            'derive_final_core': ('full', 'core'), 'core_schema': ('core',),
            'pair': ('full', 'core'), 'final_scope': ('full', 'core'),
            'final_source_inventory': ('full',), 'draft': ('full', 'report'),
            'final_evidence': ('full', 'core', 'receipt', 'report'),
            'recorder': ('full', 'core', 'receipt', 'report'),
        }.get(name, ())
        return tuple((role, self._epoch[role]) for role in roles)

    def _has(self, name):
        return name in self._passed and self._passed[name] == self._stamp(name)

    def _all(self, *names):
        return all(self._has(name) for name in names)

    def _decision(self, decision):
        _require(type(decision) is c.StageDecision, 'phase requires a freshly reconstructed stage decision')
        _require(decision.state != 'failed', 'stage reconstruction is failed')
        return decision

    def _final_checks(self):
        return self._all('derive_final_core', 'full_schema', 'full_terms', 'core_schema',
                         'pair', 'phase1_receipts', 'final_scope')

    def _kind(self, name, inputs):
        _require(type(inputs) is dict, 'native tool inputs must be an object')
        if name == 'Bash':
            command = inputs.get('command')
            _require(type(command) is str and command, 'Bash command must retain explicit text')
            _require(inputs.get('run_in_background') is None or inputs['run_in_background'] is False,
                     'phase helper cannot run in background')
            # Ordinary read-only shell lookups retain their actual command
            # policy's admission. Phase observation never grants a command:
            # only these exact spellings can earn a helper milestone.
            return self.commands.get(command)
        _require(name in ('Read', 'Write', 'Edit', 'MultiEdit'), 'unsupported phase tool')
        return None

    def before(self, tool_name, tool_input, *, stage_decision=None):
        """Refuse an out-of-order attempted effect before its callback executes."""
        _require(self._session is not None and not self._native_terminal,
                 'tool admission is outside the initialized native session')
        _require(not self._problems and not self._terminal_failures, 'phase history already failed')
        _require(not self._has('recorder'), 'tool continuation after the final recorder')
        kind = self._kind(tool_name, tool_input)
        own_pending = any(row['name'] == tool_name and row['inputs'] == c.canonical(tool_input)
                          for row in self._pending.values())
        if self._phase1_sealed:
            self._decision(stage_decision)
            _require(not self._assembly_complete or stage_decision.state == 'assembly_complete',
                     'fresh stage decision regressed after observed assembly completion')
        if tool_name in ('Write', 'Edit', 'MultiEdit'):
            target = self._path(tool_input.get('file_path'))
            role = next((r for r, path in self.paths.items() if path == target), None)
            if role in ('full', 'receipt'):
                _require(self._all('chunk_check', 'source_scope'), 'generation precedes chunk/source checks')
                _require(not self._phase1_sealed or self._assembly_complete,
                         'sealed original cannot be mutated before checked assembly completion')
                if self._assembly_complete:
                    _require(self._has('audit_evidence'), 'reconciliation precedes checked audit evidence')
            elif role == 'core':
                raise ValueError('core requires the genuine deterministic derive helper')
            elif role == 'report':
                _require(self._assembly_complete and self._has('audit_evidence'),
                         'report precedes checked audit and assembly')
                _require(self._final_checks() and self._has('final_source_inventory'),
                         'report rewrite requires current final checks and source inventory')
                _require(own_pending or self._latest.get('final_source_inventory') != self._report_inventory,
                         'each report rewrite requires a new settled final source inventory')
            return
        if kind is None:
            return
        if kind in ('chunk_check', 'source_scope'):
            _require(not self._phase1_sealed, 'initial source helper follows phase1 seal')
        elif kind in ('full_schema', 'full_terms', 'phase1_receipts'):
            _require('full' in self._written and self._all('chunk_check', 'source_scope'),
                     'full validation precedes initial generation')
            if kind == 'phase1_receipts':
                _require('receipt' in self._written and self._all('full_schema', 'full_terms'),
                         'receipt check requires current full validation and an original receipt')
            if self._phase1_sealed:
                _require(self._assembly_complete and self._has('audit_evidence'),
                         'original validation cannot substitute for active typed stages')
        elif kind == 'advance':
            decision = self._decision(stage_decision)
            _require(self._phase1_sealed, 'advance precedes settled phase1 checks')
            if decision.cursor is not None and decision.cursor.kind != 'receipt':
                _require(self._core_sealed and self._has('original_source_inventory'),
                         'typed advance precedes core seal and original source inventory')
        elif kind in ('derive_core', 'core_schema', 'pair') and not self._assembly_complete:
            decision = self._decision(stage_decision)
            _require(self._phase1_sealed and not self._core_sealed and decision.state == 'await_core'
                     and self._stage_state == 'await_core',
                     'initial core helper requires the actual await_core stage')
            if kind != 'derive_core':
                _require(self._has('derive_core'), 'core validation precedes deterministic derivation')
        elif kind == 'original_source_inventory':
            _require(self._core_sealed and not self._assembly_complete,
                     'original inventory requires the actual sealed original pair')
        elif kind == 'audit_evidence':
            _require(self._assembly_complete, 'audit evidence precedes observed assembly completion')
        elif kind in ('derive_final_core', 'core_schema', 'pair', 'final_scope', 'final_source_inventory'):
            _require(self._assembly_complete and self._has('audit_evidence'),
                     'final helper precedes checked audit and assembly')
            if kind in ('core_schema', 'pair', 'final_scope'):
                _require(self._has('derive_final_core'), 'final core check requires current final derivation')
            if kind == 'final_source_inventory':
                _require(self._final_checks(), 'final source inventory precedes current final checks')
        elif kind == 'derive_core':
            raise ValueError('final reconciliation requires derive_final_core')
        elif kind == 'draft':
            _require(self._final_checks() and self._has('final_source_inventory') and 'report' in self._written,
                     'draft requires the current checked final record and rewritten report')
        elif kind == 'final_evidence':
            _require(self._final_checks() and self._has('draft'), 'final evidence precedes a current passing draft')
        elif kind == 'recorder':
            _require(self._final_checks() and self._all('draft', 'final_evidence'),
                     'recorder precedes all current final checks')

    def _call(self, item, decision):
        identity = item.get('id')
        _require(type(identity) is str and identity and identity not in self._seen,
                 'tool call lacks a unique identity')
        name, inputs = item.get('name'), item.get('input')
        self.before(name, inputs, stage_decision=decision)
        kind = self._kind(name, inputs)
        # Helpers may read many files and some mutate them. Serial helper/write
        # admission prevents a prior result from certifying newer file bytes.
        _require(not self._pending or (name == 'Read' and all(r['name'] == 'Read' for r in self._pending.values())),
                 'helper or mutation overlaps an unsettled tool call')
        self._seen.add(identity)
        role = None
        if name in ('Write', 'Edit', 'MultiEdit'):
            path = self._path(inputs.get('file_path'))
            role = next((r for r, target in self.paths.items() if path == target), None)
        elif kind in ('derive_core', 'derive_final_core'):
            role = 'core'
        if role is not None:
            self._epoch[role] += 1
            if role == 'report':
                self._report_inventory = self._latest.get('final_source_inventory')
        if kind:
            self._latest[kind] = identity
            self._passed.pop(kind, None)
        self._pending[identity] = {'name': name, 'kind': kind, 'role': role,
            'inputs': c.canonical(inputs),
            'stamp': self._stamp(kind), 'event': self._index,
            'history': decision.history_sha256 if kind == 'advance' else None}

    def _json_success(self, kind, raw, success, row, identity, decision):
        value = c.strict_json(raw.encode('utf-8'), 'settled ' + kind, c.HARD_LIMITS['request_bytes'])
        _require(type(value) is dict, 'helper JSON result must be an object')
        if kind == 'advance':
            c.exact(value, _ADVANCE_KEYS, 'advance result')
            _require(value['kind'] == c.KINDS['advance_result'] and type(value['version']) is int
                     and value['version'] == 1, 'advance result has another protocol')
            for key in ('selection_sha256', 'execution_sha256', 'before_history_sha256', 'after_history_sha256'):
                _require(_digest(value[key]), 'advance result has an invalid identity')
            _require(type(value['attempt_id']) is str and value['attempt_id'], 'advance result lacks attempt identity')
            _require(value['session_id'] == self._session and value['advance_tool_use_id'] == identity,
                     'advance result belongs to another observed call/session')
            _require(value['before_history_sha256'] == row['history'], 'advance predecessor differs from admitted history')
            _require(type(value['publications']) is list, 'advance publications must be explicit')
            for pin in value['publications']:
                c.exact(pin, {'role', 'path', 'bytes', 'sha256'}, 'advance publication')
                c.ArtifactPin(**pin)
            _require(type(decision) is c.StageDecision and value['state'] == decision.state
                     and value['after_history_sha256'] == decision.history_sha256,
                     'advance result differs from freshly reconstructed post-publication state')
            binding = tuple(value[k] for k in ('selection_sha256', 'execution_sha256', 'attempt_id', 'session_id'))
            _require(self._binding is None or self._binding == binding, 'advance execution identity changed')
            self._binding = binding
            _require(success and decision.state != 'failed', 'advance settled with failed stage state')
            self._stage_state = decision.state
            if decision.state == 'assembly_complete':
                complete = decision.completion
                _require(self._core_sealed and self._has('original_source_inventory'),
                         'assembly completion precedes checked original pair and inventory')
                _require(tuple(getattr(complete, k) for k in ('selection_sha256', 'execution_sha256', 'attempt_id', 'session_id')) == binding
                         and complete.history_sha256 == decision.history_sha256,
                         'assembly completion belongs to another execution/history')
                self._assembly_complete = True
                # Final validation is a new actual boundary even if the model
                # retains every full-record value unchanged.
                for name in ('full_schema', 'full_terms', 'phase1_receipts'):
                    self._passed.pop(name, None)
        elif kind.endswith('source_inventory'):
            expected = 'original_full' if kind.startswith('original') else 'final_full'
            c.exact(value, {'artifact', 'sha256', 'values'}, 'source inventory')
            _require(value['artifact'] == expected and _digest(value['sha256']) and type(value['values']) is list,
                     'source inventory result belongs to another artifact or has no inventory')
        elif kind in ('audit_evidence', 'final_evidence'):
            _require(value.get('checked') is True and type(value.get('findings')) is list
                     and (not value['findings']) is success, 'evidence result disagrees with its exit status')
        elif kind == 'draft':
            _require(value.get('checked') is True and type(value.get('passed')) is bool
                     and value['passed'] is success and type(value.get('protocol_version')) is int
                     and value['protocol_version'] == 7, 'draft result is unusable or disagrees with its exit status')

    def _result(self, event, item, decision):
        identity = item.get('tool_use_id')
        _require(type(identity) is str and identity in self._pending, 'tool result has no unique pending call')
        row = self._pending.pop(identity)
        _require(type(item.get('is_error')) is bool, 'tool result lacks explicit boolean outcome')
        success = not item['is_error']
        kind = row['kind']
        if row['name'] == 'Bash':
            meta = event.get('tool_use_result')
            _require(type(meta) is dict, 'Bash result lacks explicit exit metadata')
            codes = [meta[k] for k in ('exitCode', 'exit_code') if k in meta]
            _require(codes and all(type(x) is int and x == codes[0] for x in codes),
                     'Bash exit aliases are missing, untyped or contradictory')
            _require(item['is_error'] is bool(codes[0]) and not any(meta.get(k) for k in (
                'interrupted', 'backgroundTaskId', 'background_task_id')),
                'Bash result is contradictory, interrupted or pending')
            _require(type(item.get('content')) is str and type(meta.get('stdout')) is str,
                     'Bash result must retain explicit stdout and tool content')
            if kind in _JSON_HELPERS:
                left = c.strict_json(item['content'].encode('utf-8'), 'tool content', c.HARD_LIMITS['request_bytes'])
                right = c.strict_json(meta['stdout'].encode('utf-8'), 'helper stdout', c.HARD_LIMITS['request_bytes'])
                _require(c.canonical(left) == c.canonical(right), 'helper stdout and tool content disagree')
                self._json_success(kind, meta['stdout'], success, row, identity, decision)
            else:
                _require(item['content'] == meta['stdout'], 'helper stdout and tool content disagree')
            if kind == 'draft':
                _require(codes[0] in (0, 1), 'draft checker returned an unusable exit')
            self._checks.append({'tool_use_id': identity, 'helper': kind, 'exit_code': codes[0],
                                 'call_event': row['event'], 'result_event': self._index})
        if kind in _TERMINAL_HELPERS and not success:
            self._terminal_failures.append({'tool_use_id': identity, 'helper': kind, 'event': self._index})
            raise ValueError('terminal source inventory or evidence helper failed')
        if row['role'] is not None and success:
            self._written.add(row['role'])
        if kind and success and self._latest.get(kind) == identity and row['stamp'] == self._stamp(kind):
            self._passed[kind] = row['stamp']
        actions = []
        if (kind == 'phase1_receipts' and success and not self._phase1_sealed
                and self._all('full_schema', 'full_terms', 'phase1_receipts')):
            self._phase1_sealed = True
            actions.append('seal_phase1')
        if (kind in ('core_schema', 'pair') and success and not self._core_sealed
                and self._all('derive_core', 'core_schema', 'pair')):
            self._core_sealed = True
            actions.append('seal_core')
        return tuple(actions)

    def observe(self, event, *, stage_decision=None):
        """Consume one original native event; errors remain sticky in reports."""
        self._index += 1
        actions = []
        try:
            _require(type(event) is dict, 'native event must be an object')
            if event.get('type') == 'system' and event.get('subtype') == 'init':
                session = event.get('session_id')
                _require(self._session is None and not self._seen and type(session) is str and session,
                         'native initialization lacks a unique session')
                self._session = session
                return ()
            if 'session_id' in event:
                _require(event['session_id'] == self._session, 'native event belongs to another session')
            if event.get('type') == 'result':
                _require(not self._native_terminal and self._session is not None and not self._pending,
                         'native terminal precedes settled history or repeats')
                _require(self._has('recorder') and not self._problems, 'native terminal precedes all final obligations')
                self._native_terminal = True
                return ()
            message = event.get('message', {})
            _require(type(message) is dict, 'native message must be an object')
            content = message.get('content', [])
            if not isinstance(content, list):
                return ()
            results = [x for x in content if type(x) is dict and x.get('type') == 'tool_result']
            _require(len(results) <= 1 or not any(self._pending.get(x.get('tool_use_id'), {}).get('name') == 'Bash'
                                                 for x in results), 'one metadata object cannot settle multiple Bash helpers')
            for item in content:
                if type(item) is not dict or item.get('type') not in ('tool_use', 'tool_result'):
                    continue
                _require(self._session is not None and not self._native_terminal,
                         'tool history lies outside the initialized native session')
                if item['type'] == 'tool_use':
                    _require(event.get('type') == 'assistant', 'tool call is not an assistant event')
                    self._call(item, stage_decision)
                else:
                    _require(event.get('type') == 'user', 'tool result is not a user event')
                    actions.extend(self._result(event, item, stage_decision))
        except (ValueError, TypeError, KeyError) as error:
            self._problems.append('event {}: {}'.format(self._index, error))
            raise ValueError(self._problems[-1]) from error
        return tuple(actions)

    def report(self, complete=False):
        """Detached ordered evidence; actual hashes and all other gates are external."""
        _require(type(complete) is bool, 'complete must be a boolean')
        problems = list(self._problems)
        if complete:
            for ok, message in ((self._session is not None, 'missing native initialization'),
                (not self._pending, 'unsettled native tool calls'),
                (self._phase1_sealed, 'no settled phase1 receipt boundary'),
                (self._core_sealed, 'no checked deterministic original core'),
                (self._assembly_complete, 'no observed checked stage assembly'),
                (self._final_checks() and self._all('draft', 'final_evidence', 'recorder'), 'missing current final obligations'),
                (self._native_terminal, 'missing native terminal')):
                if not ok:
                    problems.append(message)
        return deepcopy({'checked': True, 'passed': not problems, 'complete': complete,
            'phase1_sealed': self._phase1_sealed, 'core_sealed': self._core_sealed,
            'assembly_complete': self._assembly_complete, 'native_terminal': self._native_terminal,
            'current_checks': sorted(name for name in self._passed if self._has(name)),
            'pending_tool_ids': sorted(self._pending), 'checks': self._checks,
            'terminal_failures': self._terminal_failures, 'problems': problems,
            'scope': 'Ordered settled helper obligations; capture, callback authority, file bytes and scientific support are separate checks.'})
