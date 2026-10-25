"""Actual phase/history replay on new offline registered tiny-schema captures.

Native/tool events and initial full/core bytes are synthetic fixture data; no
helper executable or transport runs. Actual loader, seals, zero-work receipt
publication, phase validation and typed packet derivation are not substituted.
The unchanged pre-optimization phase function is the explicit parity oracle.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
from types import SimpleNamespace
import socket
import subprocess

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_shared_attempt_catalog import (
    basic_declaration, declaration, started, execution, bound, native_spec as basic_native_spec)
from tests.test_native_shared_live_capture import native_init, stream_capture
from tests.test_native_shared_observations import events

# Exact function at 147959, SHA256 43a85c2851a699c81255ce3c541b8f0cf00991c3ff29d4939042a40797238496.
_BASELINE_PHASE = 'def phase_replay(run, *, complete=False):\n    """Freshly run the actual phase machine over observed journal visibility."""\n    from .native_shared_phase import PhaseState\n    from .native_shared_render import commands\n    paths = run.spec._agentic_artifact_paths\n    phase = PhaseState(commands(run.spec), full_path=paths[\'full\'], core_path=paths[\'core\'],\n        report_path=paths[\'report\'], receipt_path=paths[\'receipt\'], working_directory=run.binding.working_directory)\n    catalog, advance_before, advance_after, visible, seal_observations = _chronology(run)\n    actions = {}\n    for line, _, frame in observed.rows(run.transcript):\n        count = 0\n        for item in run.history.records:\n            if item.pin.sha256 not in visible or visible[item.pin.sha256] >= line:\n                break\n            count += 1\n        decision = None\n        if count >= 3:\n            raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,\n                execution_sha256=run.binding.execution.pin.sha256, attempt_id=run.binding.attempt_id,\n                records=tuple(item.pin for item in run.history.records[:count]))\n            decision = _decision_at(run, c.sha(raw))\n        blocks = frame.get(\'message\', {}).get(\'content\', [])\n        for block in blocks if type(blocks) is list else ():\n            if type(block) is not dict:\n                continue\n            identity = block.get(\'id\') if block.get(\'type\') == \'tool_use\' else block.get(\'tool_use_id\')\n            if block.get(\'type\') == \'tool_use\' and identity in advance_before:\n                decision = _decision_at(run, advance_before[identity])\n            if block.get(\'type\') == \'tool_result\' and identity in advance_after:\n                decision = _decision_at(run, advance_after[identity])\n        emitted = phase.observe(frame, stage_decision=decision)\n        if emitted:\n            actions[line] = (emitted, phase.report())\n        if line in seal_observations:\n            kind, payload = seal_observations[line]\n            needed = \'seal_phase1\' if kind == \'phase1_sealed\' else \'seal_core\'\n            if needed not in emitted:\n                raise ValueError(\'sealed originals lack the actual settled phase boundary\')\n            expected = [row[\'tool_use_id\'] for row in phase.report()[\'checks\']\n                        if row[\'helper\'] in ({\'chunk_check\', \'source_scope\', \'full_schema\', \'full_terms\', \'phase1_receipts\'}\n                                            if needed == \'seal_phase1\' else {\'derive_core\', \'core_schema\', \'pair\'})]\n            if payload[\'helper_calls\'] != expected:\n                raise ValueError(\'seal helper identities differ from actual phase observations\')\n    if complete and set(visible) != {item.pin.sha256 for item in run.history.records}:\n        raise ValueError(\'completed history has unpublished or unobserved stage records\')\n    return phase.report(complete=complete), actions'


def baseline_phase():
    assert hashlib.sha256(_BASELINE_PHASE.encode()).hexdigest() == '43a85c2851a699c81255ce3c541b8f0cf00991c3ff29d4939042a40797238496'
    namespace = dict(capture.__dict__)
    exec(compile(_BASELINE_PHASE, '<phase_replay at 147959>', 'exec'), namespace)
    return namespace['phase_replay']


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('offline replay test attempted network or native/helper process')
    original = subprocess.Popen
    def only_git(argv, *args, **kwargs):
        assert isinstance(argv, (list, tuple)) and Path(str(argv[0])).name == 'git', argv
        return original(argv, *args, **kwargs)
    monkeypatch.setattr(subprocess, 'Popen', only_git)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def native_spec(basic_native_spec):
    spec = basic_native_spec
    doc = c.strict_json(spec.native_shared_generation_registration.encode())
    raw = c.canonical({'profile': 'neutral', 'projects': {doc['run']['project']: {'sources': [{'id': 'synthetic-source', 'processed_file': '<unsegmented>', 'source_type': 'documentation'}]}}})
    path = Path(doc['inputs']['source_manifest']['path'])
    path.write_bytes(raw)
    doc['inputs']['source_manifest'].update(bytes=len(raw), sha256=c.sha(raw))
    Path(doc['registration_path']).write_bytes(c.canonical(doc))
    spec.native_shared_generation_registration = c.canonical(doc).decode()
    from data_sheets_schema.native_shared_selection import capture as capture_selection
    spec._native_shared_generation_capture = capture_selection(doc['registration_path'])
    return spec


class PhaseFixture:
    def __init__(self, started):
        self.selection, self.value, self.composition, _, _ = started
        self.path = self.selection.registration.pin.path
        native, parent = native_init(self.selection, self.value, self.composition)
        self.native = [c.strict_json(row) for row in native.splitlines()]
        self.parent = [c.strict_json(row) for row in parent.splitlines()]
        self.session = self.native[1]['session_id']
        self.number = 0
        self.paths = self.composition['render_spec']['agentic_artifact_paths']
        capture.initialize(self.path, transcript_bytes=len(native), control_bytes=len(parent),
                           **stream_capture(self.value))
        self.helper('chunk_check'); self.helper('source_scope')
        full = b'name: Complete synthetic source.\n'
        manifest = c.strict_json(self.selection.raw('chunk_manifest'))
        receipt = c.canonical({'bundle_md5': hashlib.md5(self.selection.raw('bundle')).hexdigest(),
            'chunks': [{'id': row['id'], 'status': 'extracted', 'extracted': [
                {'slot': 'name', 'snippet': 'Complete synthetic source.'}]} for row in manifest['chunks']]})
        self.write('full', full); self.write('receipt', receipt)
        self.helper('full_schema'); self.helper('full_terms'); self.helper('phase1_receipts')
        capture.seal_originals(self.load(), 'seal_phase1')
        before = self.load().decision()
        assert before.state == 'receipt_zero_work'
        identity, result = self.begin('Bash', {'command': self.commands['advance']})
        invocation = capture.capture_stage(self.path)
        proposal = stage.prepare_next(invocation.selection, invocation.execution, invocation.phase1, invocation.history)
        published = capture.publish_stage(invocation, proposal)
        assert published['state'] == 'await_core'
        self.settle(result, published)
        capture.observe_advance_settled(self.load(), identity)
        # The fixture provides core bytes; the synthetic derive success is not
        # presented as a real CLI/helper run. Actual seal validation stays real.
        core = Path(self.paths['core']); core.parent.mkdir(parents=True, exist_ok=True); core.write_bytes(full)
        self.helper('derive_core'); self.helper('core_schema'); self.helper('pair')
        capture.seal_originals(self.load(), 'seal_core')
        self.helper('original_source_inventory', {'artifact': 'original_full',
            'sha256': c.sha(full), 'values': []})
        self.begin('Bash', {'command': self.commands['advance']})
        self.run = self.load()
        assert self.run.phase1.core is not None

    @property
    def commands(self):
        return self.composition['policy']['native_shared_helpers']

    def streams(self):
        root = Path(self.value['attempt_directory'])
        for role, rows in (('transcript', self.native), ('control', self.parent)):
            (root / (role + '.jsonl')).write_bytes(b''.join(c.canonical(row) + b'\n' for row in rows))

    def begin(self, tool, inputs):
        self.number += 1; identity = 'fixture-' + str(self.number)
        native, parent, _ = events('Write', b'neutral')
        call, callback, result = native
        call['session_id'] = result['session_id'] = self.session
        call['message']['content'][0].update(id=identity, name=tool, input=deepcopy(inputs))
        callback['request_id'] = 'callback-' + identity
        callback['request']['callback_id'] = self.composition['policy']['pretool_control']['callback_id']
        callback['request']['input'].update(tool_use_id=identity, tool_name=tool,
            cwd=self.value['working_directory'], tool_input=deepcopy(inputs))
        result['message']['content'][0].update(tool_use_id=identity, is_error=False)
        if tool == 'Bash':
            result['tool_use_result'] = {'stdout': 'checked', 'stderr': '', 'exitCode': 0}
        else:
            result['tool_use_result']['filePath'] = inputs['file_path']
        parent[0]['request'] = deepcopy(callback)
        parent[0]['response']['response']['request_id'] = callback['request_id']
        self.native.extend((call, callback)); self.parent.extend(parent); self.streams()
        return identity, result

    def settle(self, result, value=None):
        text = 'checked' if value is None else c.canonical(value).decode()
        result['message']['content'][0]['content'] = text
        if 'stdout' in result.get('tool_use_result', {}):
            result['tool_use_result']['stdout'] = text
        self.native.append(result); self.streams()

    def helper(self, name, value=None):
        _, result = self.begin('Bash', {'command': self.commands[name]})
        self.settle(result, value)

    def write(self, role, raw):
        path = Path(self.paths[role]); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        _, result = self.begin('Write', {'file_path': str(path), 'content': raw.decode()})
        self.settle(result)

    def load(self):
        return capture._load_live(self.path)


@pytest.fixture
def captured(started):
    return PhaseFixture(started)


def test_actual_phase_matches_original_with_fewer_real_reconstructions(captured, monkeypatch, tmp_path):
    run = captured.run
    calls = []; packets = []
    owner = ['baseline']
    original = capture._decision_at
    packet = stage._Replay._packet
    def counted(*args, **kwargs):
        value = original(*args, **kwargs)
        calls.append((owner[0], args[1], value))
        return value
    def actual_packet(*args, **kwargs):
        value = packet(*args, **kwargs); packets.append(owner[0]); return value
    monkeypatch.setattr(capture, '_decision_at', counted)
    monkeypatch.setattr(stage._Replay, '_packet', actual_packet)
    expected = baseline_phase()(run)
    owner[0] = 'candidate'
    actual = capture.phase_replay(run)
    assert actual == expected
    report, actions = actual
    assert report['passed'] and report['phase1_sealed'] and report['core_sealed']
    assert not report['complete'] and report['pending_tool_ids'] == ['fixture-13']
    assert actions and packets.count('candidate') >= 1
    baseline = [row for row in calls if row[0] == 'baseline']
    candidate = [row for row in calls if row[0] == 'candidate']
    distinct = []
    for _, digest, value in baseline:
        if not distinct or distinct[-1][0] != digest:
            distinct.append((digest, value))
    (tmp_path / 'actual-parity.json').write_bytes(c.canonical({'baseline_count': len(baseline),
        'candidate_count': len(candidate), 'distinct_consecutive': len(distinct),
        'packet_counts': dict(Counter(packets)), 'report': report,
        'histories': [d for d, _ in distinct], 'request_hashes': [v.request.pin.sha256 if v.request else None for _, v in distinct]}))
    assert [(d, v) for _, d, v in candidate] == distinct
    assert len(candidate) < len(baseline)
    assert packets.count('candidate') < packets.count('baseline')
    with pytest.raises(FrozenInstanceError):
        candidate[-1][2].state = 'failed'

    # A second invocation, including complete=True, must reconstruct afresh.
    before_calls = len(calls)
    complete = capture.phase_replay(replace(run), complete=True)
    assert complete == baseline_phase()(replace(run), complete=True)
    assert not complete[0]['passed'] and complete[0]['complete']
    assert 'unsettled native tool calls' in complete[0]['problems']
    assert len(calls) > before_calls
    # A foreign override at the final pending tool must still reach the real
    # prefix resolver, even after this invocation has had repeated cache hits.
    chronology = capture._chronology
    def foreign_override(value):
        catalog, before, after, visible, seals = chronology(value)
        return catalog, {**before, 'fixture-13': 'f' * 64}, after, visible, seals
    monkeypatch.setattr(capture, '_chronology', foreign_override)
    with pytest.raises(ValueError, match='one exact actual journal prefix'):
        capture.phase_replay(run)


def routing_case(monkeypatch, *, override=False):
    """Small routing-only seam: phase machine real, stage decisions supplied."""
    from tests.test_native_shared_phase import Trace, artifact
    from data_sheets_schema import native_shared_render as render
    trace = Trace()
    records = tuple(artifact('record-' + str(i)) for i in range(3))
    run = SimpleNamespace(spec=SimpleNamespace(_agentic_artifact_paths={
        'full': '/neutral/full', 'core': '/neutral/core', 'report': '/neutral/report', 'receipt': '/neutral/receipt'}),
        selection=SimpleNamespace(registration=artifact('selection')),
        binding=SimpleNamespace(execution=artifact('execution'), attempt_id='attempt', working_directory='/neutral'),
        history=SimpleNamespace(records=records), transcript=object())
    raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,
        execution_sha256=run.binding.execution.pin.sha256, attempt_id='attempt', records=tuple(x.pin for x in records))
    digest = c.sha(raw)
    frames = [{'type': 'system', 'subtype': 'init', 'session_id': 'session'},
        {'type': 'assistant', 'session_id': 'session', 'message': {'content': []}},
        {'type': 'assistant', 'session_id': 'session', 'message': {'content': []}}]
    if override:
        frames[1]['message']['content'] = [{'type': 'tool_use', 'id': 'override', 'name': 'Read', 'input': {'file_path': '/neutral/source'}}]
        frames[2] = {'type': 'user', 'session_id': 'session', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'override', 'is_error': False, 'content': 'neutral'}]}}
    monkeypatch.setattr(render, 'commands', lambda spec: trace.commands)
    monkeypatch.setattr(capture.observed, 'rows', lambda stream: ((n, 0, frame) for n, frame in enumerate(frames, 1)))
    monkeypatch.setattr(capture, '_chronology', lambda value: ({}, {'override': 'b' * 64} if override else {}, {},
        {x.pin.sha256: 0 for x in records}, {}))
    return run, digest


def test_one_entry_transitions_and_fresh_invocations(monkeypatch):
    from tests.test_native_shared_phase import decision
    run, digest = routing_case(monkeypatch, override=True)
    calls = []
    def derive(value, identity):
        calls.append(identity)
        return replace(decision(), history_sha256=identity)
    monkeypatch.setattr(capture, '_decision_at', derive)
    first = capture.phase_replay(run)
    # Original general computation still happens before its B override; the
    # subsequent A must be recomputed rather than read from an all-history map.
    assert calls == [digest, 'b' * 64, digest]
    assert first[0]['passed']
    calls.clear()
    assert capture.phase_replay(run) == first
    assert calls == [digest, 'b' * 64, digest]


def test_failed_decisions_are_not_retained(monkeypatch):
    from tests.test_native_shared_phase import decision
    run, digest = routing_case(monkeypatch)
    calls = []
    def derive(value, identity):
        calls.append(identity)
        return replace(decision(), state='failed', history_sha256=identity, failure_json=b'{"fixture":"failed"}')
    monkeypatch.setattr(capture, '_decision_at', derive)
    capture.phase_replay(run)
    assert calls == [digest] * 3


def test_error_propagates_without_cross_call_state(monkeypatch):
    from tests.test_native_shared_phase import decision
    run, digest = routing_case(monkeypatch, override=True)
    calls = []
    def derive(value, identity):
        calls.append(identity)
        if identity != digest:
            raise ValueError('actual resolver refusal sentinel')
        return replace(decision(), history_sha256=identity)
    monkeypatch.setattr(capture, '_decision_at', derive)
    for _ in range(2):
        with pytest.raises(ValueError, match='actual resolver refusal sentinel'):
            capture.phase_replay(run)
    assert calls == [digest, 'b' * 64, digest, 'b' * 64]
