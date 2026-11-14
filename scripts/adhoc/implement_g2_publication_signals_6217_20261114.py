#!/usr/bin/env python3
# Prepare issue 6217 candidate sources/tests and review provenance, 2026-11-14.
# Inputs: current assigned worktree and retained proposal. Outputs: external
# scratch candidate snapshots, unapplied unified patch and review ledger.
# Never applies the patch, imports project code, runs tests or changes Git.
from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUTPUT = SCRATCH / 'proposal-6217-implementation'
LEGACY = 'src/data_sheets_schema/native_execution.py'
ENGINE = 'src/data_sheets_schema/native_execution_orchestration.py'
TEST = 'tests/test_native_publication_signals.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def replace_one(body, before, after):
    if body.count(before) != 1:
        raise ValueError('candidate source anchor is not unique: ' + before[:100])
    return body.replace(before, after, 1)


def candidate_legacy(body):
    body = replace_one(body,
        "    def interrupt(signum, _frame):\n        observed.append(signum)\n        if len(observed) == 1:\n",
        "    interruptible = True\n"
        "    def record_only():\n"
        "        nonlocal interruptible\n"
        "        interruptible = False\n"
        "    def interrupt(signum, _frame):\n"
        "        observed.append(signum)\n"
        "        if interruptible and len(observed) == 1:\n")
    return replace_one(body,
        "            signal.signal(sig, interrupt)\n        yield\n",
        "            signal.signal(sig, interrupt)\n        yield record_only\n")


def candidate_engine(body):
    body = replace_one(body, '    with _signals(signals):\n',
                       '    with _signals(signals) as record_only_signals:\n')
    first = body.index('            try:\n                for directory in outputs:\n')
    end = body.index('            except BaseException as exc:\n', first)
    preparation = body[first + len('            try:\n'):end]
    body = (body[:first] + '            try:\n                try:\n'
            + ''.join('    ' + line if line.strip() else line
                      for line in preparation.splitlines(keepends=True))
            + '                finally:\n'
            + '                    # Transport/preparation has ended. Even its failure-evidence\n'
            + '                    # writes and all later cleanup must survive a first signal.\n'
            + '                    record_only_signals()\n' + body[end:])
    body = replace_one(body,
        "                    if guard.active:\n"
        "                        guard.close()\n"
        "                        awake.update(state='released_after_failure', passed=False)\n"
        "                    awake.update(releases=guard.releases, released_at=guard.released_at,\n"
        "                                 signals_received=list(signals))\n"
        "                    try:\n"
        "                        if not (attempt/'keep-awake.json').exists():\n"
        "                            durable_new(attempt/'keep-awake.json', draft._encoded(awake))\n",
        "                    if guard.active:\n"
        "                        guard.close()\n"
        "                        if not (attempt/'keep-awake.json').exists():\n"
        "                            awake.update(state='released_after_failure', passed=False)\n"
        "                    try:\n"
        "                        if not (attempt/'keep-awake.json').exists():\n"
        "                            # This object must still equal its consumed file. Later\n"
        "                            # signals belong to final first_stop, not a rewrite.\n"
        "                            awake.update(releases=guard.releases, released_at=guard.released_at,\n"
        "                                         signals_received=list(signals))\n"
        "                            durable_new(attempt/'keep-awake.json', draft._encoded(awake))\n")
    body = replace_one(body,
        "            guard_snapshot, subscription_observation_verification, validation_failure = _publication_subscription(\n"
        "                launch_guard, registration_raw, value['runtime'], authorization, transcript_raw,\n"
        "                completed=completed)\n"
        "            if validation_failure is not None:\n"
        "                stopped('publication validation failed at ' + validation_failure['stage'] + ': '\n"
        "                        + validation_failure['reason'])\n"
        "                results['first_stop'] = {'checked': True, 'passed': False, 'reason': first_stop}\n"
        "                completed = False\n",
        "            (guard_snapshot, subscription_observation_verification, validation_failure,\n"
        "             publication_signals, publication_stop) = _publication_signal_cutoff(\n"
        "                launch_guard, registration_raw, value['runtime'], authorization, transcript_raw,\n"
        "                completed=completed, signals=signals, first_stop=first_stop)\n"
        "            if publication_stop is not None:\n"
        "                stopped(publication_stop)\n"
        "            if first_stop is not None:\n"
        "                results['first_stop'] = {'checked': True, 'passed': False, 'reason': first_stop}\n"
        "                completed = False\n")
    helper = '''def _publication_signal_cutoff(guard, registration_raw, runtime, authorization,
                               transcript_raw, *, completed, signals, first_stop):
    """Freeze signal disposition after validation, before final construction.

    Signals after this one tuple snapshot remain record-only while the immutable
    final/publication pair is assembled and saved; they do not revise its decision.
    A late stop needs actual failed-mode verification, because read_final derives
    that mode from runtime_gates_passed and compares the complete saved result.
    """
    snapshot, verification, failure = _publication_subscription(
        guard, registration_raw, runtime, authorization, transcript_raw,
        completed=completed)
    received = tuple(signals)
    if received and first_stop is None:
        first_stop = 'launcher interrupted by signal ' + str(received[0])
    if received and completed and failure is None:
        snapshot, verification, failure = _publication_subscription(
            guard, registration_raw, runtime, authorization, transcript_raw,
            completed=False)
    if failure is not None and first_stop is None:
        first_stop = ('publication validation failed at ' + failure['stage'] + ': '
                      + failure['reason'])
    return snapshot, verification, failure, received, first_stop


'''
    return replace_one(body, 'def _publication_subscription(', helper + 'def _publication_subscription(')


TEST_BODY = r'''"""Issue 6217: publication signals retain readable immutable final evidence.

The public witnesses stop before any peer dispatch. Host readings are invented
by isolated_modules; unit cases have no child, network or host probe.
"""
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution as legacy
from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_subscription_admission as subscription
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401

pytestmark = pytest.mark.usefixtures('isolated_modules')


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize('unexpected_error', [False, True])
def test_record_only_survives_first_and_repeated_signals_and_restores_handlers(signum, unexpected_error):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    observed = []
    sentinel = RuntimeError('declared publication failure')
    try:
        with legacy._signals(observed) as record_only:
            record_only()
            signal.raise_signal(signum)
            signal.raise_signal(signum)
            assert observed == [signum, signum]
            if unexpected_error:
                raise sentinel
    except RuntimeError as exc:
        assert unexpected_error and exc is sentinel
    else:
        assert not unexpected_error
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
def test_preparation_first_signal_still_interrupts_then_cleanup_records(signum):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    observed = []
    with legacy._signals(observed) as record_only:
        with pytest.raises(KeyboardInterrupt, match='native attempt received signal'):
            try:
                signal.raise_signal(signum)
            finally:
                record_only()
        signal.raise_signal(signum)
    assert observed == [signum, signum]
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())


@pytest.mark.parametrize('initial_completed,earlier_stop', [(False, 'earlier failure'), (True, None)])
def test_late_signal_revalidates_exact_failed_mode_once(monkeypatch, initial_completed, earlier_stop):
    observed, calls = [], []
    failed = {'checked': False, 'complete': False, 'passed': False,
              'transcript_diagnostic': {'declared': 'failed-mode replay'}}
    successful = {'checked': True, 'complete': True, 'passed': True}
    def observations(*args, complete, **kwargs):
        calls.append(complete)
        observed.append(signal.SIGINT if len(calls) == 1 else signal.SIGTERM)
        return successful if complete else failed
    monkeypatch.setattr(subscription, 'context', lambda *a, **k: (
        SimpleNamespace(validate_saved_observations=observations), {}))
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': True})
    snapshot, verdict, failure, received, first_stop = engine._publication_signal_cutoff(
        guard, b'registration', {}, {'raw': {'launch_word': b'word', 'review': b'review'}},
        b'transcript', completed=initial_completed, signals=observed, first_stop=earlier_stop)
    assert snapshot == {'dispatched': True} and failure is None
    assert verdict is failed
    assert calls == ([True, False] if initial_completed else [False])
    assert received == (signal.SIGINT,)
    assert first_stop == (earlier_stop or 'launcher interrupted by signal ' + str(signal.SIGINT))
    # A signal during failed-mode revalidation cannot reopen the fixed decision.
    assert observed == ([signal.SIGINT, signal.SIGTERM] if initial_completed else [signal.SIGINT])


def test_signal_cutoff_does_not_turn_validation_refusal_into_success(monkeypatch):
    calls, observed = [], []
    def refuse(*args, **kwargs):
        calls.append(True)
        observed.append(signal.SIGTERM)
        raise ValueError('declared validation refusal')
    monkeypatch.setattr(subscription, 'context', refuse)
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': False})
    _, verdict, failure, received, first_stop = engine._publication_signal_cutoff(
        guard, b'registration', {}, {'raw': {'launch_word': b'word', 'review': b'review'}},
        None, completed=True, signals=observed, first_stop=None)
    assert calls == [True] and received == (signal.SIGTERM,)
    assert verdict['passed'] is verdict['complete'] is False
    assert failure['reason'] == 'declared validation refusal'
    assert first_stop == 'launcher interrupted by signal ' + str(signal.SIGTERM)


def test_signal_after_cutoff_keeps_the_original_successful_decision(monkeypatch):
    observed = []
    verdict = {'checked': True, 'complete': True, 'passed': True}
    monkeypatch.setattr(subscription, 'context', lambda *a, **k: (
        SimpleNamespace(validate_saved_observations=lambda *a, **k: verdict), {}))
    guard = SimpleNamespace(raw=b'guard', snapshot=lambda: {'dispatched': True})
    with legacy._signals(observed) as record_only:
        record_only()
        _, saved, failure, received, first_stop = engine._publication_signal_cutoff(
            guard, b'registration', {}, {'raw': {'launch_word': b'word', 'review': b'review'}},
            b'transcript', completed=True, signals=observed, first_stop=None)
        signal.raise_signal(signal.SIGINT)
        signal.raise_signal(signal.SIGTERM)
    assert failure is None and received == () and first_stop is None and saved is verdict
    assert observed == [signal.SIGINT, signal.SIGTERM]


@pytest.mark.parametrize('signum', [signal.SIGINT, signal.SIGTERM])
def test_public_first_signal_during_publication_keeps_exact_readback(tmp_path, monkeypatch, signum):
    from tests.test_native_shared_execution import make_case
    from data_sheets_schema import native_shared_execution_orchestration as execute
    from data_sheets_schema import native_execution_authority_v2 as authority
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'publication-signals')
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    def fail_before_dispatch(value):
        raise RuntimeError('declared offline failure before any peer dispatch')
    monkeypatch.setattr(execute, '_synthetic_runtime_observation', fail_before_dispatch)
    def forbidden_transport(*args, **kwargs):
        pytest.fail('publication signal witness dispatched a child')
    monkeypatch.setattr(engine, '_execute_child', forbidden_transport)
    original_publication = engine._publication_subscription
    consumed, boundaries = {}, []
    def interrupted_publication(*args, **kwargs):
        cleanup = Path(case['value']['attempt_directory']) / 'keep-awake.json'
        consumed['cleanup'] = cleanup.read_bytes()
        boundaries.append('subscription')
        signal.raise_signal(signum)
        return original_publication(*args, **kwargs)
    monkeypatch.setattr(engine, '_publication_subscription', interrupted_publication)
    original_write = execute.durable_new
    def interrupted_write(path, raw):
        if Path(path).name in ('final.json', 'published.json'):
            boundaries.append(Path(path).name)
            signal.raise_signal(signum)
        return original_write(path, raw)
    monkeypatch.setattr(execute, 'durable_new', interrupted_write)
    result = execute.synthetic_launch(case['raw'], **case['kwargs'])
    assert boundaries == ['subscription', 'final.json', 'published.json']
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert result['first_stop'] == 'launch or runtime failed: RuntimeError'
    assert result['gates']['first_stop'] == {
        'checked': True, 'passed': False, 'reason': result['first_stop']}
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())
    attempt = Path(case['value']['attempt_directory'])
    evidence = Path(case['value']['evidence_directory'])
    assert (attempt / 'keep-awake.json').read_bytes() == consumed['cleanup']
    assert result['keep_awake'] == c.strict_json(consumed['cleanup'])
    assert (evidence / 'final.json').read_bytes() == c.canonical(result)
    marker = c.strict_json((evidence / 'published.json').read_bytes())
    assert marker['final_sha256'] == c.sha((evidence / 'final.json').read_bytes())
    assert execute.read_final(case['raw']) == result
'''


def write_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)


def main():
    if OUTPUT.exists():
        raise ValueError('candidate evidence already exists; retain it and use a new reviewed revision')
    if (ROOT / TEST).exists():
        raise ValueError('new regression test path already exists')
    originals = {name: (ROOT / name).read_text() for name in (LEGACY, ENGINE)}
    candidates = {LEGACY: candidate_legacy(originals[LEGACY]),
                  ENGINE: candidate_engine(originals[ENGINE]), TEST: TEST_BODY}
    for name, source in candidates.items():
        ast.parse(source, filename=name)
    proposal = SCRATCH / 'issue-6217-proposal.json'
    proposal_raw = proposal.read_bytes()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    patch = ''.join(''.join(difflib.unified_diff(
        originals.get(name, '').splitlines(keepends=True), source.splitlines(keepends=True),
        fromfile='a/' + name if name in originals else '/dev/null', tofile='b/' + name))
        for name, source in candidates.items())
    for name, source in originals.items():
        write_new(OUTPUT / 'original' / name, source.encode())
    for name, source in candidates.items():
        write_new(OUTPUT / 'candidate' / name, source.encode())
    write_new(OUTPUT / 'proposal-before.json', proposal_raw)
    write_new(OUTPUT / 'implementation.patch', patch.encode())
    record = {
        'issue': 6217, 'finding_id': 'G2-REVIEW-6217-F2',
        'status': 'candidate prepared; unapplied and untested',
        'finding': 'The prior proposal unnecessarily deferred an authorized implementation choice to the owner.',
        'supersedes_recommendation_only': pin(OUTPUT / 'proposal-before.json'),
        'original_proposal_preserved': pin(proposal),
        'rationale': 'Only controller-pinned, protected, prompt-pinned or model-facing changes require a proposal. '
                     'This change uses unpinned execution modules and the existing first_stop/gate schema.',
        'cutoff': 'after primary subscription publication validation, before immutable final construction; '
                  'one failed-mode revalidation follows only when a captured signal downgrades completion',
        'head': head, 'producer': pin(Path(__file__).resolve()),
        'originals': [pin(OUTPUT / 'original' / name) for name in originals],
        'candidates': [pin(OUTPUT / 'candidate' / name) for name in candidates],
        'patch': pin(OUTPUT / 'implementation.patch'),
        'syntax': {'method': 'stdlib ast.parse', 'files': list(candidates), 'passed': True},
        'tests_run': [], 'applied': False,
        'test_plan': {'whole_file': TEST,
                      'public_witnesses': 'first SIGINT and SIGTERM during subscription publication, repeated at both final writes; no peer dispatch',
                      'unit_coverage': 'interrupt-before-return, record-only first/repeated signals, restoration, successful-to-failed revalidation, immutable cutoff and validation refusal'},
        'limits': 'The cutoff does not make publication atomic against power loss or non-signal I/O failures; '
                  'actual source application, independent review and tests remain required.'}
    write_new(OUTPUT / 'review-6217-superseding.json',
              (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'output': str(OUTPUT), 'patch': record['patch'],
                      'candidate_files': list(candidates), 'applied': False, 'tests_run': []}, sort_keys=True))


if __name__ == '__main__':
    main()
