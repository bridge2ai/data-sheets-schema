#!/usr/bin/env python3
"""Bound an owned POSIX test subprocess group.

Inputs: argv/cwd/environment, fresh evidence path, output stream, deadline.
Outputs: child return code, deadline flag and retained ownership/signal proof.
Stdlib only, usable by ordinary pytest without Git or review tooling. The
process-group retirement algorithm retains its independently reviewed behavior.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import time


@dataclass(frozen=True)
class Result:
    returncode: int
    expired: bool


class ParentTerminated(BaseException):
    """A waiting supervisor received TERM and must retire its owned child."""


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def owned_group_state(group):
    observed = None
    try:
        observed = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid=,state='],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        members = []
        for line in observed.stdout.splitlines():
            pid, pgid, state = line.split()
            if int(pgid) == group:
                members.append({'pid': int(pid), 'group': int(pgid), 'state': state})
        retired = (observed.returncode == 0 and any(row['pid'] == group for row in members)
                   and all(row['state'].startswith('Z') for row in members))
        return {'observed': observed.returncode == 0, 'members': members, 'all_retired': retired,
                'returncode': observed.returncode, 'stdout': observed.stdout, 'stderr': observed.stderr}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'observed': False, 'all_retired': False, 'error': repr(exc),
                'stdout': observed.stdout if observed is not None else None,
                'stderr': observed.stderr if observed is not None else None,
                'returncode': observed.returncode if observed is not None else None}


def run(command, *, cwd, env, evidence, stream, seconds):
    """Reap only after the owned group is killed or independently non-running."""
    evidence = Path(evidence)
    evidence.mkdir(exist_ok=False)
    if not 0 < seconds <= 7200:
        raise ValueError('deadline must be positive and bounded at 7200 seconds')
    started = time.monotonic()
    child = None
    expired, signals, retirement = False, [], None
    pending_term, cleanup_ready = False, False

    def parent_term(_signum, _frame):
        nonlocal pending_term
        pending_term = True
        if cleanup_ready:
            # Popen.wait specially handles KeyboardInterrupt by briefly waiting
            # and potentially reaping. A distinct BaseException preserves our
            # unreaped ownership until group cleanup.
            raise ParentTerminated('waiting parent received SIGTERM')

    previous_term = signal.signal(signal.SIGTERM, parent_term)
    try:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        cleanup_ready = True
        if pending_term:
            raise ParentTerminated('SIGTERM received while establishing child ownership')
        save(evidence / 'controller.json', {'pid': child.pid, 'group': child.pid,
             'deadline_seconds': seconds, 'command': command, 'cwd': str(cwd)})
        try:
            code = child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            expired = True
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(child.pid, sig)
                    signals.append({'signal': sig.name, 'sent': True})
                except ProcessLookupError:
                    signals.append({'signal': sig.name, 'sent': False, 'error': 'ProcessLookupError'})
                except PermissionError as exc:
                    retirement = owned_group_state(child.pid)
                    signals.append({'signal': sig.name, 'sent': False, 'error': repr(exc),
                                    'group_state_before_reap': retirement})
                    if sig != signal.SIGKILL or not retirement['all_retired']:
                        save(evidence / 'deadline.json', {'expired': True, 'seconds': seconds,
                            'signals': signals, 'termination_verified': False, 'controller_pid': child.pid})
                        raise RuntimeError('deadline group retirement unverified; evidence: ' + str(evidence)) from exc
                if sig == signal.SIGTERM:
                    # Holding the unreaped leader reserves its PID/group identity.
                    time.sleep(5)
            try:
                code = child.wait(timeout=10)
            except subprocess.TimeoutExpired as exc:
                save(evidence / 'deadline.json', {'expired': True, 'seconds': seconds,
                    'signals': signals, 'termination_verified': False, 'controller_pid': child.pid,
                    'error': 'controller did not reap after group SIGKILL'})
                raise RuntimeError('deadline controller did not reap; evidence: ' + str(evidence)) from exc
    except BaseException as interruption:
        # The enclosing review runner TERM->5s->KILL must cascade to this
        # separately sessioned child before it kills the waiting pytest worker.
        # No grace here: immediate group KILL, before any possible owner reap.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        proof = {'reason': repr(interruption), 'controller_pid': child.pid if child is not None else None,
                 'termination_verified': False,
                 'scope': 'owned waiting-parent SIGTERM; SIGKILL-only or already-reaped SIGINT paths are not proved'}
        if child is not None and child.returncode is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
                proof['group_kill_sent'] = True
                proof['returncode'] = child.wait(timeout=2)
                proof['termination_verified'] = True
            except PermissionError as exc:
                proof['signal_error'] = repr(exc)
                proof['group_state_before_reap'] = owned_group_state(child.pid)
                if proof['group_state_before_reap']['all_retired']:
                    proof['returncode'] = child.wait(timeout=2)
                    proof['termination_verified'] = True
            except (ProcessLookupError, subprocess.TimeoutExpired) as exc:
                proof['retirement_error'] = repr(exc)
        elif child is not None:
            proof['retirement_error'] = 'owner already reaped; descendant retirement is unverified'
        else:
            proof['retirement_error'] = 'child ownership was not established'
        save(evidence / 'interruption.json', proof)
        raise
    finally:
        signal.signal(signal.SIGTERM, previous_term)
    save(evidence / 'deadline.json', {'expired': expired, 'seconds': seconds,
        'signals': signals, 'returncode': code, 'termination_verified': True,
        'group_state_before_reap': retirement, 'wall_seconds': time.monotonic() - started,
        'scope': 'owned process group; separately sessioned descendants are not claimed'})
    return Result(code, expired)
