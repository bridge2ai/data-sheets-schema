"""Lane-wide hygiene for the tests/ collection: no test writes under notes/.

Two parts, both scoped to this directory's collection. A repository-root
conftest would also reach the ``pytest notes/matched_cborg_2026-09-13/...``
jobs CI runs separately, and that environment is left as it is.

* Bytecode goes outside the checkout (#3771). Tests import and
  ``exec_module`` the dated execution tools under ``notes/``, which wrote
  ``__pycache__`` beside them, into pinned directories. ``sys.pycache_prefix``
  moves every ``.pyc`` this process writes, and ``PYTHONPYCACHEPREFIX`` does
  the same for the subprocesses that inherit the environment. A prefix
  already chosen by the caller (``-X pycache_prefix`` or the variable) is
  kept. pytest compiles this file, and any ``-p`` plugin such as
  ``utils.pytest_shard``, before it can run, so their bytecode still lands
  in ``tests/__pycache__`` and ``utils/__pycache__`` unless the prefix is
  already set: CI sets ``PYTHONPYCACHEPREFIX`` for the suite (#3866), and a
  developer who wants a clean tree exports it too.
* No test may add a path under ``notes/`` (#3772). The tree is listed once
  when the session is configured and again when it finishes, in the process
  that runs the session: under pytest-xdist that is the controller, before
  any worker starts and after every worker has stopped, so a sibling
  worker's in-flight file is never read as a leak (#3778). Paths the tree
  already had are not reported, so a stale checkout does not fail. A note
  written by hand into the same checkout during the run is reported too;
  the listing cannot tell who wrote it.
"""
import os
from pathlib import Path
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "notes"


@pytest.fixture(autouse=True)
def prelock_refusal_diagnostics(request, monkeypatch):
    """Apply one hash assertion to every #5212 round-3–7 pre-lock refusal.

    Observe diagnostics without replacing any existing expected exception or
    tree/call assertion. A successful prior launch's printed head is outside
    the next call's capture. Post-lock failures may print their retained head.
    """
    names = {'test_d68_legacy_readonly.py', 'test_d69_fail_closed.py',
             'test_d69_artifact_completeness.py', 'test_d69_round4_ownership.py',
             'test_d69_round5_boundaries.py', 'test_d69_round5_launch.py',
             'test_d70_record_age.py'}
    if not (request.node.path.name in names or request.node.path.name.startswith('test_pr5212_')):
        return
    from contextlib import redirect_stderr
    from functools import wraps
    from data_sheets_schema import api_runner as api, latch_journal as journal
    from tests.test_pr5212_round7_journal import assert_no_unverified_hashes
    calls = []

    class Tee:
        def __init__(self, original):
            self.original, self.chunks = original, []
        def write(self, value):
            self.chunks.append(value)
            return self.original.write(value)
        def __getattr__(self, key):
            return getattr(self.original, key)

    def observe(function, *, execution=False):
        @wraps(function)
        def checked(*args, **kwargs):
            state = {'locked': False}
            if execution:
                calls.append(state)
            captured = Tee(sys.stderr)
            try:
                with redirect_stderr(captured):
                    return function(*args, **kwargs)
            except Exception as exc:
                if not execution or not state['locked']:
                    assert_no_unverified_hashes(exc, ''.join(captured.chunks))
                raise
            finally:
                if execution:
                    calls.pop()
        return checked

    acquire = journal.guarded_launch
    @wraps(acquire)
    def lock_boundary(*args, **kwargs):
        if calls:
            calls[-1]['locked'] = True
        return acquire(*args, **kwargs)
    monkeypatch.setattr(journal, 'guarded_launch', lock_boundary)
    monkeypatch.setattr(api, 'execute', observe(api.execute, execution=True))
    monkeypatch.setattr(api, '_prelock_checks', observe(api._prelock_checks))
    for name in ('_events', '_read_events', 'require_launch_head', 'refuse_legacy_execution'):
        monkeypatch.setattr(journal, name, observe(getattr(journal, name)))


@pytest.fixture
def subprocess_checkpoint(tmp_path):
    """#5212: bound a missing checkpoint, while draining both child pipes.

    The 120-second deadline accommodates loaded four-worker CI. Successful
    checkpoints return immediately. Keep consumed stderr for later assertions
    and persist timings so READY latency is measured rather than guessed.
    """
    import json
    import selectors
    import time
    measurements = []

    def wait(child, line='READY', *, timeout=120):
        started = time.monotonic()
        output = {'stdout': bytearray(), 'stderr': bytearray()}
        with selectors.DefaultSelector() as selector:
            for name in output:
                pipe = getattr(child, name)
                assert pipe is not None, f'checkpoint requires piped {name}'
                selector.register(pipe, selectors.EVENT_READ, name)
            while True:
                remaining = timeout - (time.monotonic() - started)
                for key, _ in selector.select(max(0, min(remaining, 0.1))):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if chunk:
                        output[key.data].extend(chunk)
                    else:
                        selector.unregister(key.fileobj)
                elapsed = time.monotonic() - started
                decoded = {name: bytes(raw).decode('utf-8', errors='replace')
                           for name, raw in output.items()}
                ready = line + '\n' in decoded['stdout'].splitlines(keepends=True)
                status = child.poll()
                if ready or status is not None or elapsed >= timeout:
                    result = dict(decoded, elapsed_seconds=elapsed, checkpoint=line,
                                  reached=ready, exit_status=status, deadline_seconds=timeout)
                    measurements.append(result)
                    (tmp_path / 'subprocess-checkpoints.json').write_text(json.dumps(measurements, indent=2))
                    assert ready, (f'checkpoint {line!r} not reached after {elapsed:.3f}s '
                                   f'(deadline={timeout}s); exit_status={status}; '
                                   f'stderr={decoded["stderr"]!r}; stdout={decoded["stdout"]!r}')
                    return result
    return wait


@pytest.fixture
def journal_launch_monitor(monkeypatch):
    """Explicit opt-in launch record for pre-D57 runner regression fixtures.

    Capture heads at durable appends, independently of mutable ledger reads.
    A raw journal rewrite/deletion cannot change this monitor's expected head.
    Tests of missing/wrong CLI or runner expectations do not use this fixture.
    """
    from functools import wraps
    from data_sheets_schema import api_runner, latch_journal
    heads = {}
    append = latch_journal._append
    execute = api_runner.execute

    def observed_append(spec, events, event):
        append(spec, events, event)
        heads[str(latch_journal.journal_path(spec))] = event['sha256']

    @wraps(execute)
    def monitored_execute(spec, **kwargs):
        kwargs.setdefault('expect_journal_head_sha256', heads.get(str(latch_journal.journal_path(spec))))
        return execute(spec, **kwargs)

    monkeypatch.setattr(latch_journal, '_append', observed_append)
    monkeypatch.setattr(api_runner, 'execute', monitored_execute)
    return heads

if sys.pycache_prefix is None:
    sys.pycache_prefix = str(Path(tempfile.gettempdir()) / "d4d-tests-pycache")
os.environ.setdefault("PYTHONPYCACHEPREFIX", sys.pycache_prefix)


def notes_listing(root):
    """Every file, directory and link under *root*, relative to it."""
    found = set()
    for directory, dirnames, filenames in os.walk(root):
        relative = os.path.relpath(directory, root)
        if relative in (os.curdir, os.fsencode(os.curdir)):
            relative = relative[:0]
        for name in dirnames + filenames:
            found.add(os.path.join(relative, name))
    return frozenset(found)


def _runs_the_session(config):
    """False in a pytest-xdist worker, which sees only its share of tests."""
    return not hasattr(config, "workerinput")


def pytest_configure(config):
    if _runs_the_session(config):
        config._d4d_notes_before = notes_listing(NOTES)


def pytest_sessionfinish(session, exitstatus):
    before = getattr(session.config, "_d4d_notes_before", None)
    if before is None:
        return
    added = sorted(notes_listing(NOTES) - before)
    session.config._d4d_notes_added = added
    if added and session.exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    added = getattr(config, "_d4d_notes_added", None)
    if not added:
        return
    terminalreporter.section("paths added under notes/ during the run (#3772)", red=True)
    for path in added[:50]:
        terminalreporter.write_line(f"notes/{path}")
    if len(added) > 50:
        terminalreporter.write_line(f"... and {len(added) - 50} more")
    terminalreporter.write_line(
        "A test must write under tmp_path, never into the checkout's notes/.")
