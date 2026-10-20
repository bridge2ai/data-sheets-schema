"""Selected helper fault controls with actual admitted protocol prerequisites.

The shared fixture owns real C/E/proof, owner/adapter and stream appends. Earlier
helper settlements are explicit protocol fixtures. These tests use an independent
in-process consuming thread (pytest main), not additional child-helper evidence.
No source verifier, phase replay, proposal, context or publisher is replaced.
"""
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
from pathlib import Path
import sys
import threading

import pytest

from data_sheets_schema import native_clock_domain_v1 as clocks
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_publication as publication
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_stream_coordination_v1 as coordination
from tests.test_native_owner_stage_helper import stage_helper_factory


@contextmanager
def pending(factory):
    session = factory(mode='hold_before_stage')
    try:
        session.start()
        session.wait_pending()
        assert profile._ACTIVE.get() is None
        assert coordination.current_reader_budget() is None
        yield session
    finally:
        session.stop()


def forbid_helper_clock(patch, message):
    caller = threading.current_thread()
    real = clocks.capture_domain
    def acquire():
        if threading.current_thread() is caller:
            pytest.fail(message)
        return real()
    patch.setattr(clocks, 'capture_domain', acquire)


def registration_path(session):
    return session.case['selection'].registration.pin.path


def current_invocation(session, context):
    # Match stage.main's one-invocation derivation context. Every capture,
    # replay and publication still runs under the original owner deadline.
    catalogs = stage.nr._catalog_context()
    invocation = capture.capture_stage(registration_path(session), owner_context=context,
                                       _catalogs=catalogs)
    selected = (invocation.selection, invocation.execution, invocation.phase1, invocation.history)
    replay = stage._Replay(*selected, _catalogs=catalogs).run()
    assert replay.pending is not None and replay.pending[0] == 'receipt_zero_work'
    assert replay.pending[-1] is None, 'first zero-work advance has no consumed response'
    proposal = stage._prepare_next(*selected, catalogs)
    assert proposal.state == 'receipt_zero_work'
    assert tuple(invocation.current_advance.argv) == tuple(session.case['helper_argv'])
    assert invocation.current_advance.command == session.case['helper_command']
    assert proposal.publications
    return invocation, proposal, catalogs


def proposed_journal(invocation, proposal, route):
    if route == 'publish':
        journal = [item.artifact for item in proposal.publications
                   if item.action == 'replace_journal_from_exact_predecessor']
        assert len(journal) == 1
        return journal[0], None
    # This explicitly tests capture's record/CAS plumbing, not a successful
    # stage decision or a second admission. The terminal diagnostic is closed.
    payload = stage._failure_payload(None, None, None, ValueError('fixture terminal diagnostic'))
    _, journal = stage.append_records(invocation.selection, invocation.execution,
        invocation.history, (('failed', c.canonical(payload)),))
    return journal, payload


def apply_route(invocation, proposal, context, route, payload, catalogs):
    if route == 'publish':
        return publication.publish_derived(invocation, proposal, owner_context=context,
                                           _catalogs=catalogs)
    return capture._append(invocation.selection, invocation.execution, invocation.history,
                           'failed', payload, owner_context=context)


def test_independent_scope_direct_publisher_and_terminal_context_boundaries(stage_helper_factory, monkeypatch):
    """Grouped boundaries share one real pending call; no write is proposed twice."""
    with pending(stage_helper_factory) as session:
        owner = c.strict_json((session.case['attempt'] / 'stream-owner.json').read_bytes())
        manager = capture._helper_owner_scope(registration_path(session))
        with manager as context:
            active = profile._ACTIVE.get()
            budget = coordination.current_reader_budget()
            assert active is not session.case['parent_scope']
            assert active._creator is threading.current_thread()
            assert active._parent is None
            assert budget is context.budget
            assert budget.deadline_ns == owner['deadline_ns']
            assert budget.clock_domain() == owner['clock_domain']
            assert len(budget.stop_events) == 1
            invocation, proposal, catalogs = current_invocation(session, context)
            old = Path(invocation.history.journal.pin.path).read_bytes()
            with monkeypatch.context() as patch:
                forbid_helper_clock(patch, 'nested helper acquired a lease')
                with pytest.raises(ValueError, match='cannot borrow or nest'):
                    with capture._helper_owner_scope(registration_path(session)):
                        pytest.fail('nested helper yielded')
            context.require_current()
            with monkeypatch.context() as patch:
                patch.setattr(publication, '_physical_destination',
                              lambda *a: pytest.fail('refused publisher reached physical preflight'))
                for supplied in (None, object()):
                    with pytest.raises(ValueError, match='exact owner reader context'):
                        publication.publish_derived(invocation, proposal, owner_context=supplied,
                                                    _catalogs=catalogs)
                # Mutate a valid immutable captured call, then let the real fresh
                # capture prove it is not the currently admitted invocation.
                call = replace(invocation.current_advance.call, tool_use_id='different-admitted-id')
                changed = replace(invocation, current_advance=replace(invocation.current_advance, call=call))
                with pytest.raises(ValueError, match='changed before stage publication'):
                    publication.publish_derived(changed, proposal, owner_context=context,
                                                _catalogs=catalogs)
            assert Path(invocation.history.journal.pin.path).read_bytes() == old
        assert profile._ACTIVE.get() is None
        assert coordination.current_reader_budget() is None
        with monkeypatch.context() as patch:
            patch.setattr(publication, '_physical_destination',
                          lambda *a: pytest.fail('escaped publisher reached physical preflight'))
            with pytest.raises(ValueError):
                publication.publish_derived(invocation, proposal, owner_context=context,
                                            _catalogs=catalogs)
        # The generator context is terminal; a new scope would be a different
        # independently verified entry with the unchanged owner deadline.
        with pytest.raises((AttributeError, RuntimeError, ValueError)):
            manager.__enter__()
        assert Path(invocation.history.journal.pin.path).read_bytes() == old


def test_helper_refuses_ambient_budget_and_malformed_selected_discriminators(stage_helper_factory, monkeypatch):
    with pending(stage_helper_factory) as session:
        selection = session.case['selection']
        path = Path(selection.role('execution_capture'))
        original = path.read_bytes()
        owner = c.strict_json((session.case['attempt'] / 'stream-owner.json').read_bytes())
        budget = coordination.ReaderBudget(owner['deadline_ns'], (threading.Event(),))
        with coordination.reader_budget(budget):
            with monkeypatch.context() as patch:
                forbid_helper_clock(patch, 'ambient budget acquired helper lease')
                with pytest.raises(ValueError, match='cannot borrow or nest'):
                    with capture._helper_owner_scope(registration_path(session)):
                        pytest.fail('ambient budget was borrowed')
        # These writes affect only fixture-owned E capture, restored byte-for-byte.
        # They do not assert inode/mtime preservation or represent genuine E.
        value = c.strict_json(original)
        mutants = []
        for version in (True, 2.0, None):
            item = deepcopy(value); item['dependencies']['version'] = version; mutants.append(item)
        for selected in (None, True, {}, {'version': 1}):
            item = deepcopy(value); comp = c.strict_json(item['composition_raw_json'].encode())
            comp['stream_snapshot_profile'] = selected
            raw = c.canonical(comp); item['composition_raw_json'] = raw.decode()
            item['composition_sha256'] = c.sha(raw); mutants.append(item)
        real_read = evidence.read_regular
        def before_owner(*args, **kwargs):
            if threading.current_thread() is threading.main_thread() and args[1] == 'owner':
                pytest.fail('malformed discriminator progressed to owner bootstrap')
            return real_read(*args, **kwargs)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(evidence, 'read_regular', before_owner)
                forbid_helper_clock(patch, 'malformed selector acquired lease')
                for item in mutants:
                    path.write_bytes(c.canonical(item))
                    with pytest.raises(ValueError):
                        with capture._helper_owner_scope(registration_path(session)):
                            pytest.fail('malformed selected profile fell back')
        finally:
            path.write_bytes(original)
        assert path.read_bytes() == original


def test_helper_domain_precedes_deadline_and_expiry_precedes_loader(stage_helper_factory, monkeypatch):
    with pending(stage_helper_factory) as session:
        owner = c.strict_json((session.case['attempt'] / 'stream-owner.json').read_bytes())
        caller = threading.current_thread()
        real_capture, real_now = clocks._capture, coordination.time.monotonic_ns
        wrong = deepcopy(owner['clock_domain'])
        wrong['boot_uuid'] = ('11111111-2222-4333-8444-555555555555'
                              if wrong['boot_uuid'] != '11111111-2222-4333-8444-555555555555'
                              else 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee')
        def domain():
            return (wrong, None) if threading.current_thread() is caller else real_capture()
        def forbidden_time():
            if threading.current_thread() is caller:
                pytest.fail('owner deadline interpreted before domain equality')
            return real_now()
        with monkeypatch.context() as patch:
            patch.setattr(clocks, '_capture', domain)
            patch.setattr(coordination.time, 'monotonic_ns', forbidden_time)
            with pytest.raises(clocks.ClockDomainError, match='owner and local clock domains differ'):
                with capture._helper_owner_scope(registration_path(session)):
                    pytest.fail('foreign domain entered')
        real_loader = authority.loaded_dependencies
        def loader(*args, **kwargs):
            if threading.current_thread() is caller:
                pytest.fail('expired helper entered a loader')
            return real_loader(*args, **kwargs)
        def expired():
            return owner['deadline_ns'] + 1 if threading.current_thread() is caller else real_now()
        with monkeypatch.context() as patch:
            patch.setattr(coordination.time, 'monotonic_ns', expired)
            patch.setattr(authority, 'loaded_dependencies', loader)
            with pytest.raises(ValueError, match='deadline elapsed'):
                with capture._helper_owner_scope(registration_path(session)):
                    pytest.fail('expired owner deadline was reset')
        assert profile._ACTIVE.get() is None
        assert coordination.current_reader_budget() is None


def test_equal_owner_bytes_on_another_inode_refuse_bootstrap(stage_helper_factory, monkeypatch):
    with pending(stage_helper_factory) as session:
        path = session.case['attempt'] / 'stream-owner.json'
        backup = path.with_name('fixture-original-owner')
        original, info = path.read_bytes(), path.stat()
        real_read = evidence.read_regular
        swapped = []
        caller = threading.current_thread()
        def substitute(*args, **kwargs):
            result = real_read(*args, **kwargs)
            if threading.current_thread() is caller and args[:2] == (str(path), 'owner') and not swapped:
                path.rename(backup); path.write_bytes(original)
                assert path.stat().st_ino != info.st_ino
                swapped.append(result)
            return result
        try:
            with monkeypatch.context() as patch:
                patch.setattr(evidence, 'read_regular', substitute)
                with pytest.raises(ValueError, match='owner identity changed during bootstrap'):
                    with capture._helper_owner_scope(registration_path(session)):
                        pytest.fail('replacement owner was admitted by byte equality')
            assert len(swapped) == 1 and path.read_bytes() == original
        finally:
            if backup.exists():
                path.unlink(); backup.rename(path)
        assert path.stat().st_ino == info.st_ino and path.read_bytes() == original


@pytest.mark.parametrize('route', ['publish', 'append'])
def test_both_actual_cas_callers_accept_proposed_successor_only(stage_helper_factory, monkeypatch, route):
    with pending(stage_helper_factory) as session:
        with capture._helper_owner_scope(registration_path(session)) as context:
            invocation, proposal, catalogs = current_invocation(session, context)
            after, payload = proposed_journal(invocation, proposal, route)
            assert type(after) is c.ProposedArtifact  # #4739: real producer contract.
            before = invocation.history.journal
            assert type(before) is c.CapturedArtifact
            wrong = c.CapturedArtifact(after.pin, after.raw)
            with monkeypatch.context() as patch:
                patch.setattr(publication.tempfile, 'mkstemp',
                              lambda *a, **kw: pytest.fail('wrong successor staged bytes'))
                with pytest.raises(ValueError, match='differs from its owner selection'):
                    publication._replace_journal(Path(before.pin.path), before, wrong, owner_context=context)
            calls = []
            real_cas = publication._replace_journal
            def witness(path, actual_before, actual_after, *, owner_context=None):
                assert owner_context is context
                assert type(actual_before) is c.CapturedArtifact
                assert type(actual_after) is c.ProposedArtifact
                calls.append((actual_before, actual_after))
                return real_cas(path, actual_before, actual_after, owner_context=owner_context)
            with monkeypatch.context() as patch:
                patch.setattr(publication, '_replace_journal', witness)
                result = apply_route(invocation, proposal, context, route, payload, catalogs)
            assert calls == [(before, after)]
            assert Path(before.pin.path).read_bytes() == after.raw
            if route == 'publish':
                assert result[0]['state'] == 'await_core'
                assert result[1][-1].captured.raw == after.raw


@pytest.mark.parametrize(('route', 'boundary'), [('publish', 'persisted'), ('append', 'predecessor')])
def test_both_cas_callpaths_stop_inside_staging_before_replace(stage_helper_factory, monkeypatch, route, boundary):
    with pending(stage_helper_factory) as session:
        staging, attempts, injected = [], [], []
        with pytest.raises(ValueError, match='coordination stopped'):
            with capture._helper_owner_scope(registration_path(session)) as context:
                invocation, proposal, catalogs = current_invocation(session, context)
                after, payload = proposed_journal(invocation, proposal, route)
                assert type(after) is c.ProposedArtifact
                path = Path(invocation.history.journal.pin.path)
                before = path.read_bytes()
                real_temp, real_fsync = publication.tempfile.mkstemp, publication.os.fsync
                real_read, real_replace = publication.read_regular, publication.os.replace
                def temporary(*args, **kwargs):
                    fd, name = real_temp(*args, **kwargs)
                    if kwargs.get('prefix') == 'journal.partial-' and Path(kwargs['dir']) == path.parent:
                        staging.append((fd, Path(name)))
                    return fd, name
                def synced(fd):
                    result = real_fsync(fd)
                    if boundary == 'persisted' and staging and fd == staging[-1][0]:
                        assert staging[-1][1].read_bytes() == after.raw
                        context.budget.stop_events[0].set(); injected.append(boundary)
                    return result
                def reread(*args, **kwargs):
                    result = real_read(*args, **kwargs)
                    if boundary == 'predecessor' and args[:2] == (str(path), 'journal') and staging:
                        assert result.captured.raw == before
                        context.budget.stop_events[0].set(); injected.append(boundary)
                    return result
                def replacing(source, destination, *args, **kwargs):
                    if Path(destination) == path:
                        attempts.append((source, destination))
                    return real_replace(source, destination, *args, **kwargs)
                with monkeypatch.context() as patch:
                    patch.setattr(publication.tempfile, 'mkstemp', temporary)
                    patch.setattr(publication.os, 'fsync', synced)
                    patch.setattr(publication, 'read_regular', reread)
                    patch.setattr(publication.os, 'replace', replacing)
                    apply_route(invocation, proposal, context, route, payload, catalogs)
        assert injected == [boundary]
        assert attempts == []
        assert len(staging) == 1 and staging[0][1].read_bytes() == after.raw
        assert path.read_bytes() == before


def test_selected_cas_partial_write_keeps_first_error_over_close(stage_helper_factory, monkeypatch):
    with pending(stage_helper_factory) as session:
        primary, secondary = OSError('fixture staging write failed'), OSError('fixture staging close failed')
        staged, closed = [], []
        with pytest.raises(OSError) as caught:
            with capture._helper_owner_scope(registration_path(session)) as context:
                invocation, proposal, catalogs = current_invocation(session, context)
                after, payload = proposed_journal(invocation, proposal, 'publish')
                path = Path(invocation.history.journal.pin.path); before = path.read_bytes()
                real_temp, real_open = publication.tempfile.mkstemp, publication.os.fdopen
                def temporary(*args, **kwargs):
                    fd, name = real_temp(*args, **kwargs)
                    if kwargs.get('prefix') == 'journal.partial-' and Path(kwargs['dir']) == path.parent:
                        staged.append((fd, Path(name)))
                    return fd, name
                class BrokenStream:
                    def __init__(self, stream): self.stream = stream
                    def write(self, raw):
                        assert self.stream.write(raw[:7]) == 7
                        raise primary
                    def close(self):
                        self.stream.close(); closed.append(True); raise secondary
                    def flush(self): pytest.fail('failed write continued to flush')
                    def fileno(self): return self.stream.fileno()
                def opened(fd, *args, **kwargs):
                    stream = real_open(fd, *args, **kwargs)
                    if staged and fd == staged[-1][0]:
                        assert kwargs.get('buffering') == 0
                        return BrokenStream(stream)
                    return stream
                with monkeypatch.context() as patch:
                    patch.setattr(publication.tempfile, 'mkstemp', temporary)
                    patch.setattr(publication.os, 'fdopen', opened)
                    publication.publish_derived(invocation, proposal, owner_context=context,
                                                _catalogs=catalogs)
        assert caught.value is primary
        assert closed == [True]
        assert len(staged) == 1 and staged[0][1].read_bytes() == after.raw[:7]
        assert path.read_bytes() == before


@pytest.mark.parametrize('fault', ['none', 'cleanup_only', 'body_and_cleanup'])
def test_main_acknowledges_only_after_cleanup_and_preserves_body_error(stage_helper_factory, monkeypatch, fault):
    with pending(stage_helper_factory) as session:
        caller = threading.current_thread()
        cleanup_error = OSError('fixture retained helper lease close')
        body_error = OSError('fixture stage output write')
        held, closed, printed = [], [], []
        real_capture, real_close = clocks.capture_domain, clocks._DomainLease.close
        real_print, real_write = print, publication.durable_new
        path = Path(session.case['selection'].role('journal')); before = path.read_bytes()
        def acquire():
            lease = real_capture()
            if threading.current_thread() is caller and not held:
                held.append(lease)
            return lease
        def close(lease):
            result = real_close(lease)
            if held and lease is held[0]:
                closed.append(True)
                if fault != 'none': raise cleanup_error
            return result
        def write(destination, raw):
            if fault == 'body_and_cleanup' and threading.current_thread() is caller:
                raise body_error
            return real_write(destination, raw)
        def acknowledged(*args, **kwargs):
            if threading.current_thread() is caller:
                assert profile._ACTIVE.get() is None
                assert coordination.current_reader_budget() is None
                assert coordination._OWNER_READER.get() is None
                assert held and held[0]._closed and closed == [True]
                printed.append(args)
            return real_print(*args, **kwargs)
        output = io.StringIO()
        with monkeypatch.context() as patch:
            patch.setattr(clocks, 'capture_domain', acquire)
            patch.setattr(clocks._DomainLease, 'close', close)
            patch.setattr(publication, 'durable_new', write)
            patch.setattr('builtins.print', acknowledged)
            patch.setattr(sys, 'argv', ['stage-helper'] + list(session.case['helper_argv'][3:]))
            with redirect_stdout(output):
                if fault == 'none':
                    stage.main()
                else:
                    with pytest.raises(OSError) as caught:
                        stage.main()
                    assert caught.value is (body_error if fault == 'body_and_cleanup' else cleanup_error)
        assert closed == [True]
        assert profile._ACTIVE.get() is None and coordination.current_reader_budget() is None
        if fault == 'none':
            document = c.strict_json(output.getvalue().encode())
            assert document['state'] == 'await_core' and len(printed) == 1
        else:
            assert printed == [] and output.getvalue() == ''
        if fault == 'body_and_cleanup':
            assert path.read_bytes() == before
        else:
            assert path.read_bytes() != before  # persisted output is not acknowledgement.
