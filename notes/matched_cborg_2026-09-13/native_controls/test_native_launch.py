"""Exercise the launch identity and deadline using local synthetic processes."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop
from run_native_canary import execute_child, sha, verified_executable


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


def test_launch_verification_failure_never_starts_process(tmp_path):
    instruction=tmp_path/'input.txt';instruction.write_text('offline')
    proxy=SimpleNamespace(close_admission=lambda:None)
    def changed():raise BudgetStop('changed pin')
    with pytest.raises(BudgetStop,match='changed pin'):
        execute_child([sys.executable,'-c','open("should-not-exist","w").close()'],proxy=proxy,
            instruction=instruction,attempt=tmp_path,cwd=tmp_path,env=dict(os.environ),
            deadline_seconds=1,verify_launch=changed)
    assert not (tmp_path/'should-not-exist').exists()
