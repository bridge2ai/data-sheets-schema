"""Exercise the launch identity and deadline using local synthetic processes."""
import contextlib
import errno
import os
import json
from contextlib import contextmanager
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop
import run_native_canary as runner
from run_native_canary import execute_child, sha, terminate_group, verified_executable

#: The controller refuses to launch without os.waitid (macOS Python before 3.13), and
#: most tests here launch or clean up a child through it (#2714, #2956).
pytestmark = pytest.mark.skipif(not hasattr(os, 'waitid'),
                                reason='native control requires os.waitid (macOS Python 3.13+)')


def executable(path, marker):
    path.write_text(f'#!/bin/sh\nif [ "$1" = "--version" ]; then echo same-version; else echo {marker}; fi\n')
    path.chmod(0o700)


def test_same_version_alias_retarget_cannot_change_launched_bytes(tmp_path):
    one=tmp_path/'one';two=tmp_path/'two';alias=tmp_path/'cli'
    executable(one,'one');executable(two,'two');alias.symlink_to(one)
    target=alias.resolve()
    overlay={'claude_executable':str(target),'pinned_files':{str(target):sha(target)}}
    alias.unlink();alias.symlink_to(two)
    assert subprocess.check_output([str(one),'--version'])==subprocess.check_output([str(alias),'--version'])
    assert subprocess.check_output([verified_executable(overlay)],text=True).strip()=='one'
    executable(one,'changed')
    with pytest.raises(BudgetStop,match='bytes differ'):
        verified_executable(overlay)


def test_unresolved_launch_alias_is_refused(tmp_path):
    target=tmp_path/'target';alias=tmp_path/'alias'
    executable(target,'one');alias.symlink_to(target)
    with pytest.raises(BudgetStop,match='resolved path'):
        verified_executable({'claude_executable':str(alias),'pinned_files':{str(target):sha(target)}})


def test_deadline_closes_admission_and_kills_child_before_proxy_cleanup(tmp_path):
    instruction=tmp_path/'input.txt';instruction.write_text('offline')
    pidfile=tmp_path/'pid'
    closed=[]
    proxy=SimpleNamespace(failed=threading.Event(),failure=None,close_admission=lambda:closed.append(time.monotonic()))
    code='import os,time,pathlib,signal;pathlib.Path("pid").write_text(str(os.getpid()));signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)'
    start=time.monotonic()
    with pytest.raises(BudgetStop,match='deadline elapsed'):
        execute_child([sys.executable,'-c',code],proxy=proxy,instruction=instruction,attempt=tmp_path,
            cwd=tmp_path,env=dict(os.environ),deadline_seconds=0.2,verify_launch=lambda:None)
    assert closed and time.monotonic()-start < 4
    with pytest.raises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)


def process_state(pid):
    """pid's state letters (Z for exited, unreaped), '' once it is reaped: from /proc where
    there is one, else `ps`. Reading it never reaps, and it stays independent of the
    os.waitid(WNOWAIT) check the controller under test uses (#2600, #2714)."""
    try:
        return Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()[0]
    except (FileNotFoundError, ProcessLookupError, IndexError):
        if Path('/proc/self/stat').exists():
            return ''
    return subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()


def parent_of(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()[1])
    except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
        if Path('/proc/self/stat').exists():
            return None
    owner = subprocess.run(['ps', '-o', 'ppid=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
    return int(owner) if owner.isdigit() else None


def wait_until_exited_unreaped(pid, timeout=30):
    """Bounded (#2602): an exited, unreaped child is a zombie, state Z."""
    deadline = time.monotonic() + timeout
    while not process_state(pid).startswith('Z'):
        if time.monotonic() >= deadline:
            raise AssertionError(f'process {pid} did not exit within {timeout} s')
        time.sleep(0.01)


#: Darwin answers killpg on a group whose only member is an unreaped zombie with
#: EPERM; Linux delivers the signal. `simulated` gives any platform Darwin's answer,
#: so CI (Linux) exercises the same path the kernel takes on the Mac (#2601).
REFUSALS = [pytest.param('kernel', marks=pytest.mark.skipif(
                sys.platform != 'darwin', reason="only Darwin's kernel refuses a zombie-led group")),
            'simulated']


@pytest.fixture
def darwin_refusal(request, monkeypatch):
    if request.param == 'simulated':
        signal_group = os.killpg
        def killpg(pgid, sig):
            if process_state(pgid).startswith('Z'):
                raise PermissionError(errno.EPERM, 'Operation not permitted')
            return signal_group(pgid, sig)
        monkeypatch.setattr(os, 'killpg', killpg)
    return request.param


#: How a leader ends: cleanly, with a failure status, or killed by a signal (#2615).
EXITS = [pytest.param('pass', 0, id='exit_0'), pytest.param('raise SystemExit(3)', 3, id='exit_3'),
         pytest.param('import os,signal;os.kill(os.getpid(),signal.SIGKILL)', -signal.SIGKILL, id='killed')]


@pytest.mark.parametrize('code, returncode', EXITS)
@pytest.mark.parametrize('darwin_refusal', REFUSALS, indirect=True)
def test_terminating_an_exited_unreaped_child_is_not_a_cleanup_error(darwin_refusal, code, returncode):
    """#2571: the group whose only member is the exited, unreaped leader refuses the
    signal with EPERM; terminate_group reaps the leader instead of raising, however the
    leader ended."""
    process = subprocess.Popen([sys.executable, '-c', code], start_new_session=True)
    try:
        wait_until_exited_unreaped(process.pid)
        assert process.returncode is None
        with pytest.raises(PermissionError):
            os.killpg(process.pid, 0)                                 # the state the fix must handle
        terminate_group(process)
        assert process.returncode == returncode
    finally:
        if process.returncode is None:
            process.kill(); process.wait()


def test_a_refusal_before_the_reported_exit_is_excused_by_the_exit(monkeypatch):
    """#2571: the refusal can precede waitpid's report of the exit; the exit decides."""
    process = subprocess.Popen([sys.executable, '-c', 'import sys;print("ready",flush=True);sys.stdin.read()'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, start_new_session=True)
    assert process.stdout.readline().strip() == 'ready'
    calls = []
    def refuse_while_exiting(pid, sig):
        calls.append(sig)
        if process.returncode is not None:
            # Reaped: Darwin's zombie-only group is gone, as the kernel then answers (#2614).
            raise ProcessLookupError(errno.ESRCH, 'No such process')
        if len(calls) == 1:
            # Still blocked on stdin: not exited, so the refusal comes before the exit.
            assert not process_state(pid).startswith('Z')
            process.stdin.close()
        raise PermissionError(errno.EPERM, 'Operation not permitted')
    monkeypatch.setattr(os, 'killpg', refuse_while_exiting)
    try:
        terminate_group(process)
    finally:
        monkeypatch.undo()
        if process.returncode is None:
            process.kill(); process.wait()
    assert calls and process.returncode == 0


def test_a_refused_signal_to_a_running_leader_is_raised_and_keeps_the_stop(monkeypatch):
    """A live leader's refusal is real; the exception being unwound stays in its chain.
    Whatever the cleanup raises is caught here (#2603), so a regression that lets the
    interrupt through fails this test instead of ending the pytest session."""
    process = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'], start_new_session=True)
    sends = []
    def refuse(pid, sig):
        sends.append(sig)
        raise PermissionError(errno.EPERM, 'Operation not permitted')
    monkeypatch.setattr(os, 'killpg', refuse)
    try:
        for unwinding in (BudgetStop('recorded stop'), KeyboardInterrupt()):
            raised, sends[:] = None, []
            start = time.monotonic()
            try:
                try:
                    raise unwinding
                finally:
                    terminate_group(process)
            except BaseException as error:   # noqa: B036 - the interrupt must not escape the test
                raised = error
            elapsed = time.monotonic() - start
            assert isinstance(raised, PermissionError), raised
            # Raised at once after the first wait: one send, no re-sends, no longer wait (#2700).
            assert sends == [signal.SIGTERM] and elapsed < 6, (sends, elapsed)
            chain, node = [], raised
            while node is not None:
                chain.append(node); node = node.__context__
            assert unwinding in chain, chain
    finally:
        monkeypatch.undo(); process.kill(); process.wait()


def test_a_live_leader_refusing_the_kill_step_is_raised(monkeypatch):
    """#2616: a leader that outlives SIGTERM and then refuses SIGKILL is a real refusal,
    raised as the PermissionError, not a timeout from the final wait."""
    process = subprocess.Popen([sys.executable, '-c', 'import signal,sys,time;signal.signal(signal.SIGTERM,'
                                'signal.SIG_IGN);print("ready",flush=True);time.sleep(30)'],
                               stdout=subprocess.PIPE, text=True, start_new_session=True)
    assert process.stdout.readline().strip() == 'ready'
    signal_group, kills = os.killpg, []
    def refuse_the_kill(pgid, sig):
        if sig == signal.SIGKILL:
            kills.append(sig)
            raise PermissionError(errno.EPERM, 'Operation not permitted')
        return signal_group(pgid, sig)
    monkeypatch.setattr(os, 'killpg', refuse_the_kill)
    try:
        start = time.monotonic()
        with pytest.raises(PermissionError):
            terminate_group(process)
        elapsed = time.monotonic() - start
        assert process.returncode is None
        assert kills == [signal.SIGKILL] and elapsed < 8, (kills, elapsed)       # raised at once (#2700)
    finally:
        monkeypatch.undo(); process.kill(); process.wait()


def run_bounded(cleanup, timeout=20):
    """Run `cleanup` in a thread joined with a timeout, so a missing second bound fails the
    test rather than hanging the session (#2653, #2675). Returns (error, elapsed)."""
    outcome = {}
    def body():
        start = time.monotonic()
        try:
            cleanup()
        except BaseException as error:    # noqa: B036 - reported to the test thread
            outcome['error'] = error
        outcome['elapsed'] = time.monotonic() - start
    worker = threading.Thread(target=body, daemon=True)
    worker.start()
    worker.join(timeout=timeout)
    assert not worker.is_alive(), "terminate_group's second bound did not end the re-sends"
    return outcome.get('error'), outcome['elapsed']


@pytest.mark.parametrize('after_reap', ['refuses', 'empties', 'accepts'],
                         ids=['member_lives_on', 'group_empties', 'an_unverified_member_answers'])
def test_after_the_leader_exits_a_standing_refusal_is_raised_and_a_cleared_one_is_not(monkeypatch, after_reap):
    """#2614: the leader's exit does not show the group is empty. A member that still
    refuses once the leader is reaped (one that changed its credentials, say) is raised
    once the second bound has passed, not before it (#2675), with the stop being unwound
    still in its chain (#2652). A group that empties (ESRCH) is done. After the reap the
    group is only probed, never signalled (#2708, #2713): a probe that suddenly succeeds
    finds a member whose identity cannot be verified (the group id may have been reused),
    and it is raised as the refusal rather than signalled."""
    process = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
    wait_until_exited_unreaped(process.pid)            # exited before cleanup, bounded (#2653)
    calls = []
    def member_refuses(pgid, sig):
        calls.append((sig, process.returncode))
        if process.returncode is not None and after_reap == 'empties' and len(calls) > 6:   # 5 re-sends (#2699)
            raise ProcessLookupError(errno.ESRCH, 'No such process')
        if process.returncode is not None and after_reap == 'accepts':
            return None
        raise PermissionError(errno.EPERM, 'Operation not permitted')
    monkeypatch.setattr(os, 'killpg', member_refuses)
    def cleanup():
        try:
            raise BudgetStop('recorded stop')
        finally:
            terminate_group(process)
    try:
        error, elapsed = run_bounded(cleanup)
        assert process.returncode == 0 and (0, 0) in calls                     # probed after the reap
        if after_reap == 'refuses':
            assert isinstance(error, PermissionError), error
            assert isinstance(error.__context__, BudgetStop), error.__context__   # the stop stays in the chain
            assert 2 <= elapsed < 4.5, elapsed                                    # the second bound is 2 s
            # Paced, not a busy spin: about one probe per 20 ms over the 2 s bound (#2699),
            # and no real signal to a group id that may have been recycled after the reap (#2708).
            assert calls.count((0, 0)) <= 150 and (signal.SIGTERM, 0) not in calls, calls[-3:]
        elif after_reap == 'empties':
            assert isinstance(error, BudgetStop)                                  # only the stop being unwound
        if after_reap == 'empties':
            assert elapsed < 1.5, elapsed                     # a refusal that clears is excused promptly (#2699)
        if after_reap == 'accepts':
            # Reported at once, never signalled (#2713).
            assert isinstance(error, PermissionError) and isinstance(error.__context__, BudgetStop), error
            assert (signal.SIGTERM, 0) not in calls and calls.count((0, 0)) == 1 and elapsed < 1.5, (calls, elapsed)
    finally:
        monkeypatch.undo()
        if process.returncode is None:
            process.kill(); process.wait()


@pytest.mark.parametrize('standing', [False, True], ids=['clears', 'stands'])
@pytest.mark.parametrize('shape', ['completed_run', 'kill_step'])
def test_a_refusal_to_the_unreaped_leader_is_excused_only_once_the_group_is_gone(monkeypatch, shape, standing):
    """#2674, #2714: cleanup now reaches the group with the leader exited but unreaped, on
    normal completion (`completed_run`: the run loop watches the exit without reaping it)
    or when the leader exits on SIGTERM (`kill_step`: terminate_group waits for the exit
    without reaping). Darwin can refuse the signal while other members are exiting; the
    refusal path reaps the leader and from then on only probes, excusing the refusal once
    the group is gone and raising one that stands. The kernel's window here is a few
    milliseconds and cannot be timed by a test, so the refusal is simulated everywhere."""
    if shape == 'completed_run':
        process = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
        wait_until_exited_unreaped(process.pid)          # exited; the run loop no longer reaps it
        refused_signal = signal.SIGTERM
    else:
        process = subprocess.Popen([sys.executable, '-c', 'import sys,time;print("ready",flush=True);'
                                    'time.sleep(30)'], stdout=subprocess.PIPE, text=True, start_new_session=True)
        assert process.stdout.readline().strip() == 'ready'
        refused_signal = signal.SIGKILL
    signal_group, refusals, calls = os.killpg, [], []
    def killpg(pgid, sig):
        calls.append((sig, process.returncode))        # every call, forwarded ones included (#2955)
        if sig not in (refused_signal, 0):
            return signal_group(pgid, sig)             # SIGTERM ends the leader, which stays unreaped
        refusals.append((sig, process.returncode))
        if standing or len(refusals) < 6:          # cleared after 5 re-sends, so pacing adds up (#2699)
            raise PermissionError(errno.EPERM, 'Operation not permitted')   # a member still exiting / refusing
        raise ProcessLookupError(errno.ESRCH, 'No such process')             # the group is gone
    monkeypatch.setattr(os, 'killpg', killpg)
    try:
        error, elapsed = run_bounded(lambda: terminate_group(process))
        # The one real signal went to the group while the leader still held its id; every
        # later call is a probe after the refusal path's reap (#2708, #2714).
        assert refusals[0] == (refused_signal, None), refusals
        assert all(sig == 0 and code is not None for sig, code in refusals[1:]), refusals
        assert all(sig == 0 for sig, code in calls if code is not None), calls    # none forwarded after the reap
        if standing:
            assert isinstance(error, PermissionError), error
            assert elapsed >= 2, elapsed
        else:
            assert error is None, error
            assert len(refusals) == 6 and elapsed < 1.5, (refusals, elapsed)   # excused promptly (#2699)
    finally:
        monkeypatch.undo()
        if process.stdout:
            process.stdout.close()
        if process.returncode is None:
            process.kill(); process.wait()


def test_a_leader_reaped_before_cleanup_is_sent_nothing(monkeypatch):
    """#2714: a leader reaped before terminate_group (only by someone else, now that the run
    loop does not reap) may have released its group id to another group, so nothing is sent."""
    process = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
    process.wait()
    sends = []
    monkeypatch.setattr(os, 'killpg', lambda pgid, sig: sends.append(sig))
    terminate_group(process)
    assert sends == [] and process.returncode == 0


def test_a_reap_by_someone_else_during_the_grace_wait_stops_the_sigkill(monkeypatch):
    """#2953: a leader reaped behind its Popen after the SIGTERM (here by a thread blocked in
    a raw waitpid) has released its group id; the exit check in the grace wait records it,
    and the group SIGKILL is not sent."""
    process = subprocess.Popen([sys.executable, '-c', 'import time;print("ready",flush=True);time.sleep(30)'],
                               stdout=subprocess.PIPE, text=True, start_new_session=True)
    assert process.stdout.readline().strip() == 'ready'
    reaper = threading.Thread(target=os.waitpid, args=(process.pid, 0), daemon=True)
    reaper.start()                                         # reaps the moment SIGTERM ends the leader
    signal_group, calls = os.killpg, []
    def killpg(pgid, sig):
        calls.append((sig, process.returncode))
        return signal_group(pgid, sig)
    monkeypatch.setattr(os, 'killpg', killpg)
    try:
        error, _ = run_bounded(lambda: terminate_group(process))
        reaper.join(5)
        assert error is None, error
        assert calls == [(signal.SIGTERM, None)], calls
        assert process.returncode is not None and not reaper.is_alive()
    finally:
        monkeypatch.undo()
        process.stdout.close()
        if process.returncode is None and process_state(process.pid):
            process.kill(); process.wait()


@pytest.mark.parametrize('entry', ['exit_check', 'terminate_group'])
def test_a_leader_reaped_behind_popen_is_recorded_and_sent_nothing(monkeypatch, entry):
    """#2943: a leader reaped by a raw waitpid, not by its Popen, leaves returncode unset. The
    exit check's ECHILD branch must record a status so terminate_group sends nothing: the id
    is no longer held and may name another group."""
    process = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
    os.waitpid(process.pid, 0)                             # reaped behind Popen's back
    assert process.returncode is None
    sends = []
    monkeypatch.setattr(os, 'killpg', lambda pgid, sig: sends.append(sig))
    if entry == 'exit_check':
        assert runner.leader_exited(process)
    else:
        terminate_group(process)
    assert sends == [] and process.returncode is not None


def test_the_exit_check_sees_an_exited_leader_without_reaping_it():
    """#2714: the check the run loop uses reports a running leader as running and an exited
    one as exited, and leaves the exited one a zombie that still holds its pid and group id."""
    process = subprocess.Popen([sys.executable, '-c', 'import sys;sys.stdin.read()'], stdin=subprocess.PIPE,
                               start_new_session=True)
    try:
        assert not runner.leader_exited(process)
        process.stdin.close()
        wait_until_exited_unreaped(process.pid)
        assert runner.leader_exited(process) and runner.leader_exited(process)
        assert process.returncode is None and process_state(process.pid).startswith('Z')
        assert runner.await_leader_exit(process, 1)
    finally:
        if process.returncode is None:
            process.kill(); process.wait()
    assert process.returncode == 0


def test_the_leader_gets_its_sigterm_grace_before_the_group_sigkill(monkeypatch):
    """#2945: terminate_group waits (without reaping) for the leader to act on SIGTERM before
    the group SIGKILL, so a leader that takes a moment to exit cleanly ends by its own exit,
    not by the kill that follows."""
    process = subprocess.Popen([sys.executable, '-c', 'import signal,sys,time\n'
                                'def stop(*_):\n    time.sleep(0.3); sys.exit(0)\n'
                                'signal.signal(signal.SIGTERM, stop)\nprint("ready", flush=True)\ntime.sleep(30)\n'],
                               stdout=subprocess.PIPE, text=True, start_new_session=True)
    try:
        assert process.stdout.readline().strip() == 'ready'
        terminate_group(process)
        assert process.returncode == 0, process.returncode
    finally:
        process.stdout.close()
        if process.returncode is None:
            process.kill(); process.wait()


def run_recorded(tmp_path, monkeypatch, code, deadline):
    """Run `code` through execute_child, recording every killpg with the leader's reap state.
    Returns (status or the BudgetStop raised, the leader, the non-zero sends)."""
    instruction = tmp_path / 'input.txt'; instruction.write_text('offline')
    created, calls, real_popen, signal_group = [], [], subprocess.Popen, os.killpg
    class Recorded(real_popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if kwargs.get('start_new_session'):           # the leader, not the test's own `ps`
                created.append(self)
    def killpg(pgid, sig):
        calls.append((sig, created[0].returncode, process_state(pgid) if sig else None))
        return signal_group(pgid, sig)
    monkeypatch.setattr(runner.subprocess, 'Popen', Recorded)
    monkeypatch.setattr(os, 'killpg', killpg)
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: None)
    try:
        outcome = execute_child([sys.executable, '-c', code], proxy=proxy, instruction=instruction, attempt=tmp_path,
                                cwd=tmp_path, env=dict(os.environ), deadline_seconds=deadline, verify_launch=lambda: None)
    except BudgetStop as stop:
        outcome = stop
    finally:
        monkeypatch.undo()
    leader, = created
    sent = [(sig, code, state) for sig, code, state in calls if sig]
    # Not vacuous: the group was signalled, and every real signal went while the leader was
    # unreaped (running, or a zombie holding the id); the leader is reaped by the end.
    assert sent, calls
    assert all(code is None and state for sig, code, state in sent), sent
    assert leader.returncode is not None and process_state(leader.pid) == ''
    return outcome, leader, sent


#: The kernel's own answer on every platform (Linux delivers to a zombie-led group, Darwin
#: refuses it), and Darwin's answer simulated anywhere, so Linux CI runs both (#2946).
KERNEL_OR_SIMULATED = ['kernel', 'simulated']


@pytest.mark.parametrize('shape', ['completed', 'stopped'])
@pytest.mark.parametrize('darwin_refusal', KERNEL_OR_SIMULATED, indirect=True)
def test_no_signal_reaches_the_group_after_the_leader_is_reaped(tmp_path, monkeypatch, darwin_refusal, shape):
    """#2714 end to end through execute_child: every non-zero signal to the child's group is
    sent while the leader is unreaped, whether the run completes or is stopped at its
    deadline, on the platform's own kernel and with Darwin's refusal of a zombie-led group
    simulated. A completed run still returns the child's own exit status, read after the
    cleanup that reaps it."""
    if shape == 'completed':
        outcome, leader, _ = run_recorded(tmp_path, monkeypatch, 'raise SystemExit(3)', 60)
        assert outcome == 3 and leader.returncode == 3
    else:
        outcome, leader, sent = run_recorded(tmp_path, monkeypatch, 'import time;time.sleep(30)', 0.3)
        assert isinstance(outcome, BudgetStop) and 'deadline elapsed' in str(outcome)
        assert sent[0][0] == signal.SIGTERM and leader.returncode == -signal.SIGTERM


#: A leader that leaves a SIGTERM-ignoring member in its group and exits.
DESCENDANT = ('import os,pathlib,subprocess,sys\n'
              'child = subprocess.Popen([sys.executable, "-c", "import os,pathlib,signal,time;'
              'signal.signal(signal.SIGTERM, signal.SIG_IGN);'
              'pathlib.Path(\'member.tmp\').write_text(str(os.getpid()));'
              'os.replace(\'member.tmp\', \'member\');time.sleep(60)"])\n'
              'while not pathlib.Path("member").exists(): pass\n')


def test_a_member_left_behind_is_removed_by_the_group_sigkill(tmp_path, monkeypatch):
    """#2714: a SIGTERM-ignoring member the leader leaves behind is removed by the group
    SIGKILL, which run_recorded shows was sent while the exited leader was unreaped. The
    real kernel on each platform: with a live member Darwin delivers rather than refuses,
    which `simulated` does not model."""
    gone = False
    try:
        outcome, leader, sent = run_recorded(tmp_path, monkeypatch, DESCENDANT, 60)
        assert outcome == 0 and signal.SIGKILL in [sig for sig, _, _ in sent], sent
        # Reparented on the leader's exit and reaped by its new parent: bounded wait.
        pid, end = int((tmp_path / 'member').read_text()), time.monotonic() + 10
        while time.monotonic() < end and process_state(pid) and not process_state(pid).startswith('Z'):
            time.sleep(0.02)
        gone = process_state(pid) == '' or process_state(pid).startswith('Z')
        assert gone, process_state(pid)
    finally:
        # Only a member still seen alive is killed: once it is gone its pid is released and
        # may name another process (#2944).
        member = tmp_path / 'member'
        if not gone and member.exists():
            pid = int(member.read_text())
            state = process_state(pid)
            if state and not state.startswith('Z'):
                with contextlib.suppress(OSError):
                    os.kill(pid, signal.SIGKILL)


def test_without_a_non_reaping_exit_check_nothing_is_launched(tmp_path, monkeypatch):
    """#2714, #2942: a Python without os.waitid (macOS before 3.13) cannot keep the leader
    unreaped while it signals the group, so the controller refuses before launching anything."""
    instruction = tmp_path / 'input.txt'; instruction.write_text('offline')
    monkeypatch.delattr(os, 'waitid', raising=False)
    assert not runner.exit_check_available()
    launched = []
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: None)
    with pytest.raises(BudgetStop, match='non-reaping exit check'):
        execute_child([sys.executable, '-c', 'open("should-not-exist","w").close()'], proxy=proxy,
                      instruction=instruction, attempt=tmp_path, cwd=tmp_path, env=dict(os.environ),
                      deadline_seconds=5, verify_launch=lambda: launched.append(True))
    assert launched == [] and not (tmp_path / 'should-not-exist').exists()


@pytest.mark.parametrize('standing', [False, True], ids=['group_gone', 'refusal_stands'])
@pytest.mark.parametrize('darwin_refusal', REFUSALS, indirect=True)
def test_the_kill_step_excuses_a_refusal_only_once_the_group_is_gone(darwin_refusal, monkeypatch, standing):
    """#2651: the leader outlives SIGTERM and exits a moment before the SIGKILL killpg,
    which the kernel (or `simulated`) then refuses. The kill step, like the SIGTERM step,
    excuses it once the group is gone; a refusal still standing after the reap is raised,
    within the bound (a thread joined with a timeout, so a missing bound fails, #2675)."""
    process = subprocess.Popen([sys.executable, '-c', 'import signal,time;signal.signal(signal.SIGTERM,'
                                'signal.SIG_IGN);print("ready",flush=True);time.sleep(30)'],
                               stdout=subprocess.PIPE, text=True, start_new_session=True)
    assert process.stdout.readline().strip() == 'ready'
    signal_group, refused = os.killpg, []
    def killpg(pgid, sig):
        if sig == signal.SIGKILL and not refused:
            os.kill(pgid, signal.SIGKILL)               # the leader exits just before the killpg
            wait_until_exited_unreaped(pgid)
            try:
                signal_group(pgid, 0)                   # the refusal the fix must handle
            except PermissionError:
                refused.append(sig)
            else:
                refused.append('delivered')
        if standing and refused and process.returncode is not None:
            raise PermissionError(errno.EPERM, 'Operation not permitted')
        return signal_group(pgid, sig)
    monkeypatch.setattr(os, 'killpg', killpg)
    try:
        error, _ = run_bounded(lambda: terminate_group(process))
        if standing:
            assert isinstance(error, PermissionError), error
        else:
            assert error is None, error
        assert refused == [signal.SIGKILL] and process.returncode == -signal.SIGKILL
    finally:
        monkeypatch.undo()
        process.stdout.close()
        if process.returncode is None:
            process.kill(); process.wait()


@pytest.mark.parametrize('darwin_refusal', REFUSALS, indirect=True)
def test_a_stop_after_the_child_exited_is_not_replaced_by_group_cleanup(tmp_path, darwin_refusal):
    """#2571 end to end: the child exits before the controller's cleanup, as a fast child
    does under load, and its group refuses the signal (the Darwin kernel, or `simulated`
    anywhere). The stop raised is the recorded one and the child is reaped: this is what
    fails when execute_child's cleanup does not excuse the refusal by the exit."""
    instruction = tmp_path / 'input.txt'; instruction.write_text('offline')
    pidfile = tmp_path / 'pid'
    code = ('import os,pathlib,time\npathlib.Path("pid.tmp").write_text(str(os.getpid()))\n'
            'os.replace("pid.tmp","pid")\nwhile not pathlib.Path("go").exists():time.sleep(0.01)\n')
    def stop_once_the_child_has_exited():
        deadline = time.monotonic() + 30                              # bounded (#2602)
        while not pidfile.exists():
            if time.monotonic() >= deadline:
                raise AssertionError('the child never wrote its pid')
            time.sleep(0.01)
        (tmp_path / 'go').touch()
        wait_until_exited_unreaped(int(pidfile.read_text()))
        return True
    proxy = SimpleNamespace(failed=SimpleNamespace(is_set=stop_once_the_child_has_exited),
                            failure='synthetic stop raised after the child exited', close_admission=lambda: None)
    reaped = False
    try:
        with pytest.raises(BudgetStop, match='synthetic stop raised after the child exited'):
            execute_child([sys.executable, '-c', code], proxy=proxy, instruction=instruction, attempt=tmp_path,
                          cwd=tmp_path, env=dict(os.environ), deadline_seconds=60, verify_launch=lambda: None)
        assert process_state(int(pidfile.read_text())) == ''
        reaped = True
    finally:
        # Nothing orphaned when the test fails: a child of this process that was not
        # reaped still holds its pid, so that pid names no one else's process.
        (tmp_path / 'go').touch()
        if not reaped and pidfile.exists():
            pid = int(pidfile.read_text())
            if process_state(pid) and parent_of(pid) == os.getpid():
                with contextlib.suppress(OSError):
                    os.kill(pid, signal.SIGKILL)
                with contextlib.suppress(ChildProcessError):
                    os.waitpid(pid, 0)


def test_launch_verification_failure_never_starts_process(tmp_path):
    instruction=tmp_path/'input.txt';instruction.write_text('offline')
    proxy=SimpleNamespace(close_admission=lambda:None)
    def changed():raise BudgetStop('changed pin')
    with pytest.raises(BudgetStop,match='changed pin'):
        execute_child([sys.executable,'-c','open("should-not-exist","w").close()'],proxy=proxy,
            instruction=instruction,attempt=tmp_path,cwd=tmp_path,env=dict(os.environ),
            deadline_seconds=1,verify_launch=changed)
    assert not (tmp_path/'should-not-exist').exists()


@pytest.mark.parametrize('override, expected', [(None, '5'), (15, '15')])
@pytest.mark.parametrize('bypass', [False, True])
@pytest.mark.parametrize('render_version, binding', [(7, 'omitted'), (9, 'matched'),
                                                   (9, 'omitted'), (9, 'different'), (9, 'unkeyed')])
def test_native_cli_receives_the_same_attempt_cap_as_its_proxy(tmp_path, monkeypatch, override, expected,
                                                            render_version, binding, bypass):
    import anthropic
    import run_native_canary as runner

    job = {'id': 'external_native', 'canary': True, 'execution_arm': 'agentic',
           'render_spec': {}, 'input_identity': {}, 'output_directories': [], 'outputs': {}}
    instruction = tmp_path / 'instruction.md'
    instruction.write_text('Synthetic offline instruction')
    job['instruction'] = str(instruction)
    base = {'repository': str(tmp_path), 'claude_version': 'test-version',
            'provider_base_url': 'https://unused.invalid', 'model': {'model': 'test-model'},
            'budget': {'additional_usd': 200, 'per_attempt_usd': 5,
                       'ledger_path': str(tmp_path / 'billing.json'), 'prices_per_token': {}},
            'generation': {'jobs': [job], 'canary_order': [job['id']],
                           'agentic_attempt_deadline_seconds': 1}}
    if override is not None:
        base['budget']['per_job_attempt_usd'] = {job['id']: override}
    if bypass:
        base['provider_context_policy'] = 'headroom_bypass_v1'
    registration = tmp_path / 'registration.json'
    registration.write_text(json.dumps(base))
    overlay = tmp_path / 'overlay.json'
    environment = ({} if binding == 'omitted' else {'D4D_LAUNCH_INSTRUCTION':
                   str(instruction) if binding in ('matched', 'unkeyed') else str(tmp_path / 'another.md')})
    overlay.write_text(json.dumps({'registration': str(registration),
        'registration_sha256': sha(registration), 'allowed_jobs': [job['id']],
        'pinned_files': {}, 'environment': {}, 'per_job_environment': {job['id']: environment},
        'cli_flags': [], 'allowed_tools': ['Read'], 'system_prompt': str(instruction)}))
    review = tmp_path / 'review.json'
    review.write_text(json.dumps({'verdict': 'approve', 'ci_conclusion': 'success',
        'overlay_sha256': sha(overlay), 'allowed_jobs': [job['id']]}))
    observed = {}

    class OfflineProxy:
        token = 'synthetic-local-token'
        unfinished_handlers = 0
        failed = threading.Event()

        def __init__(self, **kwargs):
            observed['proxy_cap'] = str(kwargs['ledger'].limit_for_attempt(kwargs['attempt']))
            assert kwargs['request_headers'] == ({'x-headroom-bypass': 'true'} if bypass else {})

        @contextmanager
        def running(self):
            yield 'http://127.0.0.1:1'

    def capture(argv, **kwargs):
        observed['cli_cap'] = argv[argv.index('--max-budget-usd') + 1]
        if render_version >= 9:
            assert kwargs['env']['D4D_LAUNCH_INSTRUCTION'] == str(instruction)
        raise BudgetStop('synthetic probe stops before process or provider execution')

    monkeypatch.setattr(runner, 'verify', lambda *args: None)
    monkeypatch.setattr(runner, 'verify_history', lambda *args: None)
    # This fixture isolates budget propagation from source/policy preparation.
    monkeypatch.setattr(runner, 'validated_command_policy', lambda *args: {
        'allowed_tools': ['Read'], 'command_examples': [], 'programs': [], 'manifest_paths': [],
        'readonly_lookups': {'repository': str(tmp_path), 'inputs': [], 'output_directories': []}})
    monkeypatch.setattr(runner, 'verified_executable', lambda *args: sys.executable)
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *args, **kwargs: 'test-version')
    monkeypatch.setattr(runner, 'spec_for', lambda *args: SimpleNamespace(
        render_spec=lambda: {}, input_identity=lambda: {}, render_version=render_version,
        prompt_text_env=render_version >= 9 and binding != 'unkeyed'))
    def sdk(**kwargs):
        assert kwargs['default_headers'] == ({'x-headroom-bypass': 'true'} if bypass else {})
        return object()
    monkeypatch.setattr(anthropic, 'Anthropic', sdk)
    monkeypatch.setattr(runner, 'NativeProxy', OfflineProxy)
    monkeypatch.setattr(runner, 'execute_child', capture)
    monkeypatch.setenv('CBORG_API_KEY', 'synthetic-never-sent')
    monkeypatch.setattr(sys, 'argv', ['run_native_canary', '--overlay', str(overlay),
                                    '--review', str(review), '--job', job['id']])
    if binding == 'unkeyed':
        # A renderer-9+ job whose recorder line carries the refused expansion
        # stops before credentials, ledger, attempt directory or runtime
        # (#2341): with no key in the environment and each later step failing
        # if reached, only the guard's own refusal can come out.
        monkeypatch.delenv('CBORG_API_KEY', raising=False)
        monkeypatch.setattr(runner, 'verified_executable', lambda *a: pytest.fail('runtime check reached'))
        monkeypatch.setattr(runner.subprocess, 'check_output', lambda *a, **k: pytest.fail('runtime version reached'))
        monkeypatch.setattr(runner, 'open_ledger', lambda *a: pytest.fail('ledger reached'))
        with pytest.raises(BudgetStop, match='renders a shell expansion Claude Code refuses'):
            runner.main()
        assert observed == {}
        assert not (tmp_path / 'attempts').exists()
        return
    if render_version >= 9 and binding != 'matched':
        with pytest.raises(BudgetStop, match='exact registered launch instruction'):
            runner.main()
        assert observed == {}
        assert not (tmp_path / 'billing.json').exists()
        return
    assert runner.main() == 1
    assert observed == {'proxy_cap': expected, 'cli_cap': expected}
    receipt = json.loads((tmp_path/'attempts'/job['id']/'started.json').read_bytes())
    assert receipt['provider_context']['requested_headers'] == ({'x-headroom-bypass': 'true'} if bypass else {})
    assert receipt['provider_context']['provider_behavior_independently_observed'] is False


def test_stop_explanation_prefers_the_ledger_then_the_controller_then_the_proxy(tmp_path):
    """#1914: the v10q receipt said PermissionError and nothing else while the
    ledger held the cause. The ledger's stop entry for this attempt wins;
    a BudgetStop the controller raised is next; the proxy's recorded failure
    is last. A BudgetStop carrying the proxy's recorded failure is the
    proxy's, and a bare exception with none of them is named by its type
    (#2038)."""
    from run_native_canary import stop_explanation
    ledger = tmp_path / 'billing.json'
    ledger.write_text(json.dumps({'requests': [], 'stopped_attempts': {'reg:job': {'reason': 'request reserve $2.30 exceeds remaining budget', 'paid_request': False}}}))
    out = stop_explanation(PermissionError('x'), ledger, 'reg:job', 'PermissionError')
    assert out['reason'].startswith('request reserve') and out['reason_source'] == 'ledger' and out['ledger_stop']['paid_request'] is False
    assert out['proxy_failure'] == 'PermissionError'
    out = stop_explanation(BudgetStop('deadline elapsed'), ledger, 'reg:other', None)
    assert out == {'reason': 'deadline elapsed', 'reason_source': 'controller'}
    out = stop_explanation(RuntimeError('boom'), ledger, 'reg:other', 'OSError')
    assert out == {'reason': 'OSError', 'reason_source': 'proxy', 'proxy_failure': 'OSError'}
    out = stop_explanation(RuntimeError('boom'), tmp_path / 'missing.json', 'reg:other', None)
    assert out == {'reason': 'unexpected RuntimeError', 'reason_source': 'controller'}
    out = stop_explanation(BudgetStop('unregistered upstream response format'), tmp_path / 'missing.json', 'reg:other',
                           'unregistered upstream response format')
    assert out['reason_source'] == 'proxy' and out['reason'] == 'unregistered upstream response format'
    out = stop_explanation(BudgetStop('native attempt deadline elapsed'), tmp_path / 'missing.json', 'reg:other', 'OSError')
    assert out['reason_source'] == 'controller' and out['proxy_failure'] == 'OSError'


def prescribed_playbook_commands(text):
    """Every `d4d <group> <command>[ <subcommand>]` the playbook text names —
    fenced or inline, with or without `poetry run` — as the roster spells
    them (`api prompts check` keeps its third token)."""
    import re
    found = set()
    for m in re.finditer(r'(?<![\w/.-])d4d\s+([a-z][a-z-]*)\s+([a-z][a-z-]*)(?:\s+([a-z][a-z-]*))?', text):
        group, command, sub = m.group(1), m.group(2), m.group(3)
        if command.startswith('-'):
            continue
        found.add(f'{group} {command} {sub}' if group == 'api' and command == 'prompts' and sub else f'{group} {command}')
    return found


def test_every_command_the_playbook_prescribes_is_allowed():
    """#1916/#1927: the v10q run lacked `prompt render`, which the playbook
    prescribes; the roster must cover every command the whole playbook names
    (inline text too, since the receipts-check gate is inline), except the
    ones the playbook mentions only to forbid."""
    from prepare_overlay_roster import PLAYBOOK_COMMANDS, MENTIONED_NOT_PRESCRIBED
    playbook = Path(__file__).resolve().parents[3] / '.claude/commands/d4d-full-core.md'
    prescribed = prescribed_playbook_commands(playbook.read_text(encoding='utf-8'))
    for expected in ('receipts check', 'bundle chunk', 'runs validate', 'download list-projects',
                     'api prompts check', 'prompt render', 'provenance record', 'derive core'):
        assert expected in prescribed, f'extraction lost {expected}'
    missing = sorted(p for p in prescribed - set(MENTIONED_NOT_PRESCRIBED) if p not in PLAYBOOK_COMMANDS)
    assert missing == [], f'playbook commands the overlay does not allow: {missing}'
    assert 'provenance backfill' not in PLAYBOOK_COMMANDS


def test_the_extractor_reads_inline_fenced_and_nested_forms():
    text = ("Run `poetry run d4d receipts check --label X --strict` first.\n```bash\nd4d bundle chunk --check\n"
            "d4d api prompts check --strict\n```\nNever `d4d provenance backfill` here. See d4d-agent.md and /d4d-full-core.")
    assert prescribed_playbook_commands(text) == {'receipts check', 'bundle chunk', 'api prompts check', 'provenance backfill'}


def test_the_instruction_module_entry_points_are_allowed():
    """#1923: renderer 12 prescribes source_review before audit and report."""
    from prepare_overlay_roster import MODULE_ENTRY_POINTS
    assert {'source_review', 'evidence_assertions', 'agentic_observed', 'd4d_pair_consistency'} <= set(MODULE_ENTRY_POINTS)


def test_stop_explanation_never_raises_on_a_malformed_ledger(tmp_path):
    """#1925: a diagnostic that fails must not displace the stop it explains."""
    from run_native_canary import stop_explanation
    ledger = tmp_path / 'billing.json'
    ledger.write_text(json.dumps({'requests': [], 'stopped_attempts': ['bad']}))
    out = stop_explanation(PermissionError('x'), ledger, 'reg:job', 'PermissionError')
    assert out['reason'] == 'PermissionError' and out['reason_source'] == 'proxy' and 'ledger_stop_note' in out
    ledger.write_bytes(b'{not json')
    out = stop_explanation(BudgetStop('deadline'), ledger, 'reg:job', None)
    assert out['reason'] == 'deadline' and out['ledger_stop_note'].startswith('ledger unreadable')


def test_a_malformed_observation_refuses_completion():
    """#1930: the observer's malformed-event count must reach the completion
    decision, not only the receipt's observation block."""
    from run_native_canary import observation_problems
    assert observation_problems({'output_tokens': 5, 'usage_from_terminal_result': 1}) == []
    assert observation_problems({'malformed_message_events': 2, 'usage_from_terminal_result': 1}) == ['transcript carries 2 malformed measurement events']
    assert observation_problems({'overlapping_evidence': 1, 'usage_from_terminal_result': 1}) == ['transcript carries 1 overlapping evidence events (#1972)']
    assert observation_problems({'output_tokens': 3}) == ['transcript carries no terminal result with complete usage']
    assert observation_problems({'output_tokens': 3, 'usage_from_terminal_result': 1}) == []
    assert observation_problems(None) == ['transcript observation unavailable']


def test_a_stopped_attempt_records_whether_the_transcript_reached_its_result(tmp_path):
    """#2014: a deadline stop leaves no runtime result line; the receipt says so."""
    from run_native_canary import transcript_terminal_state
    t = tmp_path / 'transcript.jsonl'
    t.write_text('{"type":"system","subtype":"init"}\n{"type":"assistant","message":{"id":"m1"}}\n')
    state = transcript_terminal_state(t)
    assert state['transcript_terminal_result'] == 'absent' and 'ledger' in state['transcript_accounting_note']
    t.write_text(t.read_text() + '{"type":"result","usage":{"input_tokens":1,"output_tokens":1}}\n')
    assert transcript_terminal_state(t) == {'transcript_terminal_result': 'present'}
    assert transcript_terminal_state(tmp_path / 'missing.jsonl')['transcript_terminal_result'] == 'missing'


def test_the_attempt_deadline_is_a_registration_parameter():
    """#2010/#2020/#2021: the deadline is parsed as a positive whole number,
    defaults to what v10q and v10r registered, and is what the generation
    block records."""
    import pytest
    from types import SimpleNamespace
    import prepare_registration as prep
    parser = prep.build_parser()
    assert parser.parse_args([]).agentic_deadline_seconds == 1800
    explicit = parser.parse_args(['--agentic-deadline-seconds', '10800'])
    assert explicit.agentic_deadline_seconds == 10800 and isinstance(explicit.agentic_deadline_seconds, int)
    for bad in ('0', '-1', '1.5', 'soon'):
        with pytest.raises(SystemExit):
            parser.parse_args(['--agentic-deadline-seconds', bad])
    assert prep.generation_deadline(SimpleNamespace(agentic_deadline_seconds=10800)) == 10800
    import inspect
    assert '"agentic_attempt_deadline_seconds": generation_deadline(args)' in inspect.getsource(prep.main)


def test_the_transcript_diagnostic_never_raises(tmp_path):
    """#2019: undecodable bytes and a missing file are reported, not raised."""
    from run_native_canary import transcript_terminal_state
    t = tmp_path / 'transcript.jsonl'
    t.write_bytes(b'{"type":"system"}\n\xff\xfe\x80 cut mid-write')
    assert transcript_terminal_state(t)['transcript_terminal_result'] == 'absent'
    t.write_bytes(b'\xff\n{"type":"result","usage":{"input_tokens":1,"output_tokens":1}}\n')
    assert transcript_terminal_state(t) == {'transcript_terminal_result': 'present'}
    assert transcript_terminal_state(tmp_path / 'none.jsonl')['transcript_terminal_result'] == 'missing'
    assert transcript_terminal_state(tmp_path)['transcript_terminal_result'] == 'unreadable'


def test_a_controller_stop_is_recorded_in_the_ledger(tmp_path):
    """#2018/#2023: a deadline stop marks the attempt stopped in the ledger; a
    ledger stop is left as the ledger recorded it; an entry the ledger already
    holds is reported, not overwritten."""
    from run_native_canary import record_controller_stop
    from budgeted_cborg import Ledger
    ledger = Ledger(tmp_path / 'billing.json', manifest_sha256='m', total_cap=200, attempt_cap=5)
    out = record_controller_stop(ledger, 'm:job', {'reason': 'native attempt deadline elapsed', 'reason_source': 'controller'})
    state = json.loads((tmp_path / 'billing.json').read_bytes())
    assert state['stopped_attempts']['m:job']['reason'] == 'controller: native attempt deadline elapsed'
    assert out == {'ledger_stop_recorded': 'controller: native attempt deadline elapsed'}
    # recording again (the except path after a pre-close record) is idempotent
    assert record_controller_stop(ledger, 'm:job', {'reason': 'native attempt deadline elapsed'}) == out
    assert record_controller_stop(ledger, 'm:job', {'reason': 'x', 'reason_source': 'ledger'}) == {}
    ledger.stop_attempt('m:other', 'attempt cap reached')
    note = record_controller_stop(ledger, 'm:other', {'reason': 'native attempt deadline elapsed'})
    assert note == {'ledger_stop_record_note': 'the ledger already held a stop entry: attempt cap reached'}
    class Broken:
        path = tmp_path / 'none.json'
        def stop_attempt(self, *a): raise OSError('disk')
    assert 'could not record' in record_controller_stop(Broken(), 'm:x', {'reason': 'x'})['ledger_stop_record_note']


#: The controller's registered deadline in a test that orders its stop by an event.
#: A hang guard, not a measurement: the real clock would reach it only if the event
#: never came, and the tests assert that it did not (#2617).
HANG_SECONDS = 600


class EventClock:
    """`run_native_canary`'s clock (#2617, #2763). It is the real monotonic clock
    until `event` is set. At its first reading after the event it moves ahead so
    that a deadline of `offset` from its first reading lies UNDER_SECONDS away, and
    from then on it runs at the real rate. A controller that enforces its registered
    deadline of `offset` therefore stops about UNDER_SECONDS after the event, at a
    reading at or past that deadline. One whose deadline is more than UNDER_SECONDS
    short of it stops at its first check after the event, at a reading before it.

    execute_child takes its deadline from its first reading, so `first` is that
    deadline's base; an earlier reading would only put `deadline` before the
    controller's. `jumped` is the real instant of the first reading after the
    event, and `last` the value most recently returned. Durations the controller
    measures after the event, such as terminate_group's, are unchanged.

    The assertions name how a run failed (#2736): the clock was never read after
    the event, so no deadline check could have ended the run; the real clock had
    nearly reached the deadline before the event, so the hang guard could have;
    or the controller stopped before its registered deadline, or LATE_SECONDS or
    more after it."""
    UNDER_SECONDS = 1.0
    #: How long past its registered deadline the controller may stop. It checks its
    #: deadline once per 0.05 s poll, and the clock runs at the real rate after the
    #: jump, so this is scheduling inside the test process, never start-up. A
    #: deadline enforced LATE_SECONDS or more late fails (#2818).
    LATE_SECONDS = 2.0

    def __init__(self, event, offset, sleep=time.sleep):
        self.event, self.offset, self.sleep = event, offset, sleep
        self.first = self.jumped = self.last = None
        self._shift = 0.0

    def monotonic(self):
        now = time.monotonic()
        if self.first is None:
            self.first = now
        if self.jumped is None and self.event.is_set():
            self.jumped = now
            self._shift = max(0.0, self.first + self.offset - self.UNDER_SECONDS - now)
        self.last = now + self._shift
        return self.last

    @property
    def deadline(self):
        return self.first + self.offset

    def now(self):
        """The clock's value now, read by the test rather than the controller: it
        neither sets `first` nor counts as a reading after the event (#2823)."""
        return time.monotonic() + self._shift

    def assert_read_after_the_event(self):
        assert self.jumped is not None, \
            "the controller never read its clock after the event: its deadline was not checked"
        assert self.jumped - self.first < self.offset - self.UNDER_SECONDS, \
            "the real clock had nearly reached the registered deadline before the event: the hang guard could have ended the run"

    def assert_stopped_at_the_deadline(self, last_at_stop, closed_at):
        """`last_at_stop`: the value the controller had last read when it stopped, which
        decides whether it stopped early. `closed_at`: the clock's value when admission
        actually closed, read then by the test, which decides whether it stopped late:
        a delay between the expiry check and the close is late too (#2823)."""
        self.assert_read_after_the_event()
        assert last_at_stop is not None and last_at_stop >= self.deadline, \
            f"the controller stopped {self.deadline - last_at_stop:.2f} s before its registered deadline"
        assert closed_at is not None and closed_at - self.deadline < self.LATE_SECONDS, \
            f"admission closed {closed_at - self.deadline:.2f} s after the registered deadline"


def closing_observed(clock, close, before=lambda: None):
    """Wrap `close`, a proxy's close_admission. At its first call it records the
    controller's last clock reading and what `before` returns, both as they stood
    when the controller began to close, and, once `close` has returned, the
    clock's value then: the instant admission is closed. Timing the entry instead
    accepts a close delayed inside it by any amount (#2725 Codex review)."""
    seen = {}
    def closing():
        first = not seen
        if first:
            seen.update(clock=clock.last, before=before())
        close()
        if first:
            seen['closed'] = clock.now()
    return closing, seen


def _deadline_while_counting(tmp_path, *, record_first, interrupt=None, close_delay=None):
    """The real NativeProxy.running() and execute_child: the deadline fires
    while a /v1/messages handler is still counting tokens, so the handler
    meets the admission the controller has just closed (#2023/#2024).

    The deadline elapses UNDER_SECONDS after the count begins, by EventClock,
    not after one real second that also paid for the child's interpreter
    start-up and its request (#2617), and never before it is due (#2763). An
    interrupt arm raises its interrupt at the controller's first sleep after it
    has checked its deadline since the count began, so a deadline enforced more
    than UNDER_SECONDS early would be recorded instead of the interrupt; one less
    early is caught by the deadline tests' own check. A shortfall under one
    controller poll (0.05 s) is caught only when a deadline check happens to fall
    inside it, which depends on the poll's overhead: 30 ms was caught in most runs,
    10 ms in few (#2778, #2793, #2807). `close_delay` holds admission open that
    long inside close_admission, the lateness a negative control injects."""
    import threading, time
    from types import SimpleNamespace
    from test_native_proxy import fixture_proxy, REQUEST
    import run_native_canary as rnc
    proxy, ledger, calls = fixture_proxy(tmp_path)
    counting = threading.Event()
    def count(**kw):
        counting.set()
        while not proxy.closed:
            time.sleep(0.01)
        time.sleep(0.2)   # returns inside running()'s cleanup window
        return SimpleNamespace(input_tokens=100)
    proxy.messages.client.messages.count_tokens = count
    def interrupted_sleep(seconds):
        if clock.jumped is not None:
            raise interrupt('private exception detail')
        time.sleep(seconds)
    clock = EventClock(counting, HANG_SECONDS, sleep=time.sleep if interrupt is None else interrupted_sleep)
    if close_delay is not None:
        prompt_close = proxy.close_admission
        def late_close():
            time.sleep(close_delay)
            prompt_close()
        proxy.close_admission = late_close
    # What the ledger holds as admission first closes (#2029), the controller's
    # last clock reading then, and when admission was closed.
    proxy.close_admission, at_close = closing_observed(
        clock, proxy.close_admission,
        before=lambda: json.loads(ledger.path.read_bytes()).get('stopped_attempts') if ledger.path.exists() else None)
    attempt = tmp_path / 'attempt'; attempt.mkdir()
    instruction = tmp_path / 'instruction.txt'; instruction.write_text('offline')
    child = ("import json,os,time,urllib.request\n"
             "req=urllib.request.Request(os.environ['URL']+'/v1/messages?beta=true',data=json.dumps(%r).encode(),"
             "headers={'x-api-key':os.environ['TOKEN'],'content-type':'application/json'})\n"
             "print(json.dumps({'type':'system','subtype':'init'}),flush=True)\n"
             "try:\n urllib.request.urlopen(req,timeout=30)\nexcept Exception: pass\n"
             "time.sleep(30)\n") % (REQUEST,)
    record = (lambda reason: rnc.record_controller_stop(ledger, 'native-offline', {'reason': reason})) if record_first else None
    receipt = {}
    real_time, rnc.time = rnc.time, clock
    try:
        with proxy.running() as url:
            env = dict(os.environ, URL=url, TOKEN=proxy.token)
            rnc.execute_child([sys.executable, '-c', child], proxy=proxy, instruction=instruction, attempt=attempt,
                              cwd=tmp_path, env=env, deadline_seconds=HANG_SECONDS, verify_launch=lambda: None,
                              record_stop=record)
    except BaseException as exc:
        receipt.update(status='stopped', error_type=type(exc).__name__)
        receipt.update(rnc.stop_explanation(exc, ledger.path, 'native-offline', getattr(proxy, 'failure', None)))
        receipt.update(rnc.transcript_terminal_state(attempt / 'transcript.jsonl'))
        receipt.update(rnc.record_controller_stop(ledger, 'native-offline', receipt))
    finally:
        rnc.time = real_time
    assert counting.is_set() and calls == []
    if interrupt is None:
        clock.assert_stopped_at_the_deadline(at_close.get('clock'), at_close.get('closed'))   # due, after the count began
    else:
        clock.assert_read_after_the_event()
    receipt['stops_at_close'] = at_close.get('before')
    return receipt, json.loads(ledger.path.read_bytes()).get('stopped_attempts')


@pytest.mark.parametrize('interrupt', [KeyboardInterrupt, RuntimeError])
def test_controller_interrupt_is_recorded_before_in_flight_admission_closes(tmp_path, interrupt):
    receipt, stops = _deadline_while_counting(tmp_path, record_first=True, interrupt=interrupt)
    reason = f'unexpected {interrupt.__name__}'
    assert receipt['reason_source'] == 'controller' and receipt['reason'] == reason
    assert stops['native-offline']['reason'] == 'controller: ' + reason
    assert receipt['stops_at_close']['native-offline']['reason'] == 'controller: ' + reason
    assert 'private exception detail' not in json.dumps(receipt)


def test_proxy_failure_is_not_recorded_as_a_controller_failure(tmp_path):
    instruction = tmp_path / 'instruction.txt'
    instruction.write_text('offline')
    failed = threading.Event()
    failed.set()
    proxy = SimpleNamespace(failed=failed, failure='upstream stream interrupted', close_admission=lambda: None)
    recorded = []
    with pytest.raises(BudgetStop, match='upstream stream interrupted'):
        execute_child([sys.executable, '-c', 'import time; time.sleep(30)'], proxy=proxy,
                      instruction=instruction, attempt=tmp_path, cwd=tmp_path, env=dict(os.environ),
                      deadline_seconds=5, verify_launch=lambda: None, record_stop=recorded.append)
    assert recorded == []


def test_a_deadline_during_an_in_flight_request_is_recorded_as_the_deadline(tmp_path):
    receipt, stops = _deadline_while_counting(tmp_path, record_first=True)
    assert receipt['status'] == 'stopped' and receipt['reason_source'] == 'controller'
    assert receipt['reason'].startswith('native attempt deadline elapsed')
    assert stops['native-offline']['reason'].startswith('controller: native attempt deadline elapsed')
    assert receipt['ledger_stop_recorded'] == stops['native-offline']['reason']
    # the deadline was already in the ledger when admission closed (#2029)
    assert receipt['stops_at_close']['native-offline']['reason'].startswith('controller: native attempt deadline elapsed')


def test_admission_closed_late_inside_its_close_fails_the_deadline_check(tmp_path):
    """Negative control (#2725 Codex review): the controller checks its deadline on
    time but admission closes LATE_SECONDS later, inside close_admission. That is a
    late stop, and the check must say so."""
    with pytest.raises(AssertionError, match=r'admission closed \d+\.\d+ s after the registered deadline'):
        _deadline_while_counting(tmp_path, record_first=True, close_delay=EventClock.LATE_SECONDS + 0.5)


def test_the_admission_closed_consequence_never_masks_a_controller_stop(tmp_path):
    """Even when the pre-close record did not happen, the entry the refused
    handler wrote is reported as a consequence, not as the cause."""
    receipt, stops = _deadline_while_counting(tmp_path, record_first=False)
    assert stops['native-offline']['reason'] == 'native admission is closed'
    assert receipt['reason_source'] == 'controller' and receipt['reason'].startswith('native attempt deadline elapsed')
    assert 'consequence' not in receipt['reason'] and 'refused after the controller closed admission' in receipt['ledger_stop_note']
    assert receipt['ledger_stop_record_note'] == 'the ledger already held a stop entry: native admission is closed'


PY = '/opt/env/bin/python'
SNAPSHOT = ("from pathlib import Path\nimport hashlib, json\npairs = [('out/full.yaml', 'out/evidence/original_full.yaml')]\n"
            "pins = {}\nfor src, dst in pairs:\n    raw = Path(src).read_bytes()\n    pins[dst] = hashlib.sha256(raw).hexdigest()\n"
            "print(json.dumps({'original_sha256': pins}, sort_keys=True))\n")
VALIDATE = 'from linkml.validator.cli import cli; cli()'


def _instruction():
    import shlex
    return (f"VALIDATE both files:\n\n    {PY} -c '{VALIDATE}' -s /repo/schema_all.yaml -C Dataset <full>\n\n"
            f"Freeze the originals:\n\n{PY} -c {shlex.quote(SNAPSHOT)}\n\nThen run {PY} -m data_sheets_schema.cli derive core --full x\n")


def _classify(*denials):
    from run_native_canary import classify_denials
    return classify_denials(list(denials), instruction_text=_instruction(), python=PY, repository='/repo',
                            output_directories=['out', 'out_core'], readable_inputs=['data/bundle.txt', 'data/chunks.yaml'])


def _bash(command):
    return {'tool_name': 'Bash', 'tool_use_id': 't', 'tool_input': {'command': command, 'description': 'x'}}


def test_the_instruction_programs_are_read_verbatim_including_the_multi_line_one():
    from run_native_canary import prescribed_programs
    assert prescribed_programs(_instruction(), PY) == {VALIDATE, SNAPSHOT.strip()}


def test_denials_of_forbidden_commands_are_listed_and_not_disqualifying():
    """#2026: the shapes the v10q and v10r runs were denied, all forbidden by the system prompt."""
    import shlex
    from run_native_canary import denial_problems
    forbidden = [
        _bash(f'{PY} -m data_sheets_schema.cli --help 2>&1 | head -60'),
        _bash(f'{PY} -m data_sheets_schema.cli --help'),
        _bash(f'{PY} -m data_sheets_schema.cli schema --help'),
        _bash(f'{PY} -m data_sheets_schema.cli agents digest 2>&1 | head -30'),
        _bash(f"{PY} - <<'PY' > /tmp/digest.txt\nprint(1)\nPY"),
        _bash(f'{PY} -c {shlex.quote("import sys; print(sys.argv)")}'),
        _bash("cat >> out/receipt.yaml <<'EOF'\n- id: c002\nEOF"),
        _bash('grep -o "python -c" /repo/cli_config/projects/session.jsonl'),
        _bash('grep -n "Leadership" data/bundle.txt | head -20; grep -n "Cohort" data/bundle.txt'),
        {'tool_name': 'Write', 'tool_use_id': 'w', 'tool_input': {'file_path': '/tmp/scratch/digest.py', 'content': 'x'}},
        {'tool_name': 'WebFetch', 'tool_use_id': 'f', 'tool_input': {'url': 'https://example.org'}},
    ]
    classified = _classify(*forbidden)
    assert [d['classification'] for d in classified] == ['not_prescribed'] * len(forbidden)
    assert all(d['basis'] for d in classified) and denial_problems(classified) == []


def test_a_denied_prescribed_command_disqualifies():
    import shlex
    from run_native_canary import denial_problems
    prescribed = [
        _bash(f'{PY} -m data_sheets_schema.cli receipts check --label L --project P --strict'),
        _bash(f'{PY} -m data_sheets_schema.cli --manifest /repo/manifest.yaml download priority --project P'),
        _bash(f'{PY} -m data_sheets_schema.agentic_observed --bundle data/bundle.txt t.jsonl'),
        _bash(f"{PY} -c '{VALIDATE}' -s /repo/schema_all.yaml -C Dataset out/full.yaml"),
        _bash(f'{PY} -c {shlex.quote(SNAPSHOT)}'),
        {'tool_name': 'Write', 'tool_use_id': 'w', 'tool_input': {'file_path': '/repo/out/full.yaml', 'content': 'x'}},
        {'tool_name': 'Read', 'tool_use_id': 'r', 'tool_input': {'file_path': 'data/bundle.txt'}},
    ]
    classified = _classify(*prescribed)
    assert [d['classification'] for d in classified] == ['prescribed'] * len(prescribed), classified
    assert len(denial_problems(classified)) == len(prescribed)
    # a roster command whose form the system prompt forbids is not the prescribed command
    assert _classify(_bash(f'{PY} -m data_sheets_schema.cli receipts check --label L; ls'))[0]['classification'] == 'not_prescribed'
    # a command outside the roster, and the mentioned-not-prescribed backfill, are not prescribed
    assert _classify(_bash(f'{PY} -m data_sheets_schema.cli provenance backfill --label L'))[0]['classification'] == 'not_prescribed'


def test_an_unreadable_denial_record_disqualifies():
    from run_native_canary import classify_denials, denial_problems
    kw = dict(instruction_text='', python=PY, repository='/repo', output_directories=[], readable_inputs=[])
    assert classify_denials(None, **kw) == [] and classify_denials([], **kw) == []
    odd = classify_denials({'tool_name': 'Bash'}, **kw)
    assert odd[0]['classification'] == 'unclassifiable' and denial_problems(odd)
    assert classify_denials(['Bash'], **kw)[0]['classification'] == 'unclassifiable'


ROSTER = f'{PY} -m data_sheets_schema.cli'


def test_commands_bash_would_split_or_redirect_are_not_the_prescribed_command():
    """#2031: shlex reads a newline as whitespace, merges operator runs into
    one token and treats a `#` inside a word as a comment. Bash reads each of
    these as a second command, a redirection or a substitution."""
    from run_native_canary import FORBIDDEN_SHELL, denial_problems
    shapes = [
        f'{ROSTER} runs list\nrm -rf data/d4d_concatenated',
        f'{ROSTER} derive core --full a --out b\ncp a /tmp/b',
        f'{ROSTER} runs list >| /tmp/x.txt',
        f'{ROSTER} runs list &>> /tmp/x.txt',
        f'{ROSTER} runs list <> /tmp/x.txt',
        f'{ROSTER} runs check <(cat /etc/hosts)|tee /tmp/y',
        f"{PY} -c '{VALIDATE}' -s x -C Dataset out/full.yaml\ncurl http://example.org",
        f'{ROSTER} runs list #x\nls /',
        f"{ROSTER} runs list # don't\nrm -rf x",
        f'{ROSTER} runs list --label a#b; rm x',
        f'{ROSTER} runs list --label "$(cat /etc/hosts)"',
        f'{ROSTER} runs list --label "`id`"',
        f'{ROSTER} runs list\r\nls',
        f'{ROSTER} runs list \\\n\nls',
    ]
    classified = _classify(*[_bash(c) for c in shapes])
    assert [(d['classification'], d['basis']) for d in classified] == [('not_prescribed', FORBIDDEN_SHELL)] * len(shapes)
    assert denial_problems(classified) == []


def test_forms_bash_reads_as_one_prescribed_command_stay_prescribed():
    """A continuation line, a comment, surrounding newlines and quoted
    operator characters leave one simple command (#2031); a three-word roster
    command is matched word by word."""
    shapes = {
        f'{ROSTER} receipts check \\\n  --label L --project P': 'receipts check',
        f'{ROSTER} runs list  # just the list': 'runs list',
        f'{ROSTER} runs list\n# a note\n': 'runs list',
        f'\n{ROSTER} runs list\n': 'runs list',
        f"{ROSTER} runs list --label 'a;b|c>d'": 'runs list',
        f'{ROSTER} runs list --label "x(y)"': 'runs list',
        f'{ROSTER} api prompts check --strict': 'api prompts check',
        f'{ROSTER} api prompts check': 'api prompts check',
        f'{ROSTER} --manifest /repo/m.yaml api prompts check': 'api prompts check',
        f"{PY} -c '{VALIDATE}' -s x -C Dataset out/full.yaml  # validate": None,
    }
    classified = _classify(*[_bash(c) for c in shapes])
    assert [d['classification'] for d in classified] == ['prescribed'] * len(shapes), classified
    for d, roster in zip(classified, shapes.values()):
        assert roster is None or d['basis'] == f"the roster command '{roster}'"
    others = _classify(*[_bash(c) for c in (f'{ROSTER} api prompts pin --file x', f'{ROSTER} api prompts',
                                              f'{ROSTER} runs\rlist', f'{ROSTER} runs lister')])
    assert [d['classification'] for d in others] == ['not_prescribed'] * 4


def test_malformed_denial_records_are_unclassifiable(tmp_path):
    from run_native_canary import classify_denials, denial_problems
    odd = [
        {'tool_name': None, 'tool_use_id': 'a', 'tool_input': {'command': 'ls'}},
        {'tool_use_id': 'b', 'tool_input': {'command': 'ls'}},
        {'tool_name': 'Bash', 'tool_use_id': 'c', 'tool_input': {}},
        {'tool_name': 'Bash', 'tool_use_id': 'd', 'tool_input': {'command': ['ls']}},
        {'tool_name': 'Write', 'tool_use_id': 'e', 'tool_input': {'path': 'out/x.yaml'}},
        {'tool_name': 'Read', 'tool_use_id': 'f', 'tool_input': {'file_path': ''}},
        {'tool_name': 'Write', 'tool_use_id': 'g', 'tool_input': {'file_path': 'out/x\x00y'}},
    ]
    classified = _classify(*odd)
    assert [d['classification'] for d in classified] == ['unclassifiable'] * len(odd), classified
    assert len(denial_problems(classified)) == len(odd)
    # a path the filesystem cannot encode, under a directory that exists
    (tmp_path / 'out').mkdir()
    surrogate = classify_denials([{'tool_name': 'Write', 'tool_use_id': 'h', 'tool_input': {'file_path': 'out/x\ud800y'}}],
                                 instruction_text='', python=PY, repository=str(tmp_path),
                                 output_directories=['out'], readable_inputs=[])
    assert surrogate[0]['classification'] == 'unclassifiable', surrogate


def test_reads_of_the_registered_instruction_schemas_and_playbooks_are_prescribed():
    """#2033/#2039: the manifest, the instruction, the two schemas and the
    playbook closure are registered reads; the other agent definitions the
    toolchain inventories (evaluation rubrics among them) are not."""
    from run_native_canary import classify_denials, registered_reads
    resources = {
        'src/data_sheets_schema/schema/data_sheets_schema_all.yaml': '/repo/src/schema_all.yaml',
        'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml': '/repo/src/schema_core_all.yaml',
        '.claude/commands/d4d-full-core.md': '/repo/.claude/commands/d4d-full-core.md',
        '.claude/commands/d4d-uniform-rules.md': '/repo/.claude/commands/d4d-uniform-rules.md',
        '.claude/commands/d4d-agent.md': '/repo/.claude/commands/d4d-agent.md',
        '.claude/agents/d4d-provenance-guard.md': '/repo/.claude/agents/d4d-provenance-guard.md',
        '.claude/agents/d4d-rubric10.md': '/repo/.claude/agents/d4d-rubric10.md',
        '.claude/commands/d4d-webfetch.md': '/repo/.claude/commands/d4d-webfetch.md',
    }
    job = {'bundle': 'data/b.txt', 'chunks': 'data/c.yaml', 'manifest': '/repo/m.yaml',
           'instruction': '/repo/prompts/job.md',
           'input_identity': {'source_manifest': {'path': '/repo/m2.yaml'},
                              'instruction': {'spec': {'agentic_toolchain': {'resources': resources}}}}}
    reads = registered_reads(job)
    def read(path):
        return {'tool_name': 'Read', 'tool_use_id': 'r', 'tool_input': {'file_path': path}}
    registered = ['/repo/m.yaml', '/repo/m2.yaml', '/repo/prompts/job.md', 'data/c.yaml',
                  *[v for k, v in resources.items() if 'rubric' not in k and 'webfetch' not in k]]
    other = ['/repo/.claude/agents/d4d-rubric10.md', '/repo/.claude/commands/d4d-webfetch.md',
             '/repo/data/prior_record.yaml']
    classified = classify_denials([read(p) for p in registered + other], instruction_text='', python=PY,
                                  repository='/repo', output_directories=[], readable_inputs=reads)
    assert [d['classification'] for d in classified] == ['prescribed'] * len(registered) + ['not_prescribed'] * len(other)
    assert registered_reads({}) == []


def test_a_blank_command_is_listed_and_not_disqualifying():
    """#2036: the runtime accepts an empty or whitespace command and would
    deny it; it is harmless and prescribed by nothing."""
    from run_native_canary import denial_problems
    classified = _classify(*[_bash(c) for c in ('', ' ', '\n', '\t')])
    assert [(d['classification'], d['basis']) for d in classified] == [('not_prescribed', 'an empty command')] * 4
    assert denial_problems(classified) == []


def test_each_bash_reading_rule_decides_a_classification():
    """#2040: each rule of the scan changes a classification when removed."""
    from run_native_canary import FORBIDDEN_SHELL
    cases = [
        # an unquoted parenthesis is an operator on its own
        (f'{ROSTER} runs list (x)', 'not_prescribed', FORBIDDEN_SHELL),
        (f'{ROSTER} runs list x)', 'not_prescribed', FORBIDDEN_SHELL),
        # a # inside a word is part of the word, never a comment
        (f'{ROSTER} agents playbook#x', 'not_prescribed', 'a CLI command outside the prescribed roster'),
        (f"{PY} -c '{VALIDATE}'#x -s s -C Dataset out/full.yaml", 'not_prescribed',
         'an ad-hoc -c script the system prompt forbids'),
        # an escaped character ends the start of a word, so a following # is not a comment
        (f'{ROSTER} agents playbook \\x#; rm -rf data', 'not_prescribed', FORBIDDEN_SHELL),
        # a backslash-newline joins lines anywhere, before the roster words included
        (f'{ROSTER} \\\nreceipts check --label L', 'prescribed', "the roster command 'receipts check'"),
        (f'{PY} \\\n-m data_sheets_schema.cli runs list', 'prescribed', "the roster command 'runs list'"),
        (f'{ROSTER} run\\\ns list', 'prescribed', "the roster command 'runs list'"),
    ]
    classified = _classify(*[_bash(c) for c, _, _ in cases])
    assert [(d['classification'], d['basis']) for d in classified] == [(c, b) for _, c, b in cases]


def test_a_stopped_attempt_classifies_its_single_result_line(tmp_path):
    """#2037: a stopped attempt that holds one result line is classified from
    it; with none, or with two, the receipt says it classified nothing."""
    from run_native_canary import stopped_denials, STOPPED_DENIALS_NOTE, classify_denials
    def classify(denials):
        return classify_denials(denials, instruction_text=_instruction(), python=PY, repository='/repo',
                                output_directories=['out'], readable_inputs=[])
    prescribed = _bash(f'{ROSTER} receipts check --label L')
    forbidden = _bash(f'{ROSTER} --help')
    path = tmp_path / 'transcript.jsonl'
    init = json.dumps({'type': 'system', 'subtype': 'init'}) + '\n'
    result = json.dumps({'type': 'result', 'is_error': True, 'permission_denials': [prescribed, forbidden]}) + '\n'
    path.write_bytes(init.encode() + b'\xff\xfe not json\n' + result.encode())
    out = stopped_denials(path, classify)
    assert [d['classification'] for d in out['permission_denials']] == ['prescribed', 'not_prescribed']
    assert len(out['disqualifying_denials']) == 1 and 'permission_denials_note' not in out
    path.write_text(init)
    assert stopped_denials(path, classify) == {'permission_denials_note': STOPPED_DENIALS_NOTE}
    path.write_text(init + result + result)
    assert '2 runtime result lines' in stopped_denials(path, classify)['permission_denials_note']
    assert 'FileNotFoundError' in stopped_denials(tmp_path / 'missing.jsonl', classify)['permission_denials_note']
    path.write_text(init + result)
    assert 'ZeroDivisionError' in stopped_denials(path, lambda denials: 1 / 0)['permission_denials_note']


def test_the_pre_close_record_waits_for_a_handler_holding_the_proxy_state(tmp_path):
    """#2029: the controller's record takes proxy.state, so a handler writing
    the ledger under it is not interrupted by a lock Timeout, and the
    controller's entry still lands before admission closes."""
    import threading, time
    from test_native_proxy import fixture_proxy
    from run_native_canary import record_then_close, record_controller_stop
    proxy, ledger, calls = fixture_proxy(tmp_path)
    ready, outcome = threading.Event(), {}
    def handler():
        with proxy.state:
            with ledger.transaction() as state:
                ready.set(); time.sleep(0.3)
                state.setdefault('handler_note', 'written')
        outcome['handler'] = 'ok'
    thread = threading.Thread(target=handler); thread.start(); ready.wait(5)
    seen = {}
    record_then_close(proxy, lambda reason: seen.update(r=record_controller_stop(ledger, 'native-offline', {'reason': reason})),
                      'native attempt deadline elapsed')
    thread.join(5)
    state = json.loads(ledger.path.read_bytes())
    assert outcome == {'handler': 'ok'} and state['handler_note'] == 'written'
    assert seen['r'] == {'ledger_stop_recorded': 'controller: native attempt deadline elapsed'}
    assert state['stopped_attempts']['native-offline']['reason'] == 'controller: native attempt deadline elapsed'
    assert proxy.closed
    # a record that raises never prevents admission from closing
    proxy2, _, _ = fixture_proxy(tmp_path / 'second')
    record_then_close(proxy2, lambda reason: 1 / 0, 'x')
    assert proxy2.closed


def test_the_second_bound_starts_when_the_leader_exits(monkeypatch):
    """#2709: the leader exits about 1 s into the first wait and the group keeps refusing
    for 1.5 s more; the refusal is excused, since the second 2 s bound runs from the
    leader's exit, not from the first refusal."""
    process = subprocess.Popen([sys.executable, '-c', 'import time;print("ready",flush=True);time.sleep(1.0)'],
                               stdout=subprocess.PIPE, text=True, start_new_session=True)
    assert process.stdout.readline().strip() == 'ready'
    reaped_at = []
    def refuse_until_after_the_exit(pgid, sig):
        if process.returncode is None:
            raise PermissionError(errno.EPERM, 'Operation not permitted')     # the leader is still running
        if not reaped_at:
            reaped_at.append(time.monotonic())
        if time.monotonic() < reaped_at[0] + 1.5:
            raise PermissionError(errno.EPERM, 'Operation not permitted')     # members still exiting
        raise ProcessLookupError(errno.ESRCH, 'No such process')
    monkeypatch.setattr(os, 'killpg', refuse_until_after_the_exit)
    try:
        error, elapsed = run_bounded(lambda: terminate_group(process))
        assert error is None and process.returncode == 0, (error, elapsed)
    finally:
        monkeypatch.undo()
        process.stdout.close()
        if process.returncode is None:
            process.kill(); process.wait()
