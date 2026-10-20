"""Recorder lifetime protocol controls, not selected-owner/process acceptance.

Successful lower-writer cases use an explicit guard double to isolate ordering,
readback, error precedence and context propagation. They do not fabricate a live
owner proof or claim the actual registered helper fits its original deadline.
"""
from contextlib import contextmanager
from copy import deepcopy
import importlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import backfill_checks as bc
from data_sheets_schema import provenance as pv
from data_sheets_schema import native_shared_capture as capture

cli = importlib.import_module('data_sheets_schema.cli.provenance')


class Stopped(RuntimeError):
    pass


class Protocol:
    """Explicit test-only recorder guard; never an actual owner context."""
    def __init__(self, path):
        self.path = path
        self.context = object()
        self.stopped = False
        self.active = False
        self.events = []

    def refuse(self, owner_context):
        if owner_context is None and self.active:
            raise Stopped('missing explicit context')

    def guard(self, path, *, owner_context=None, record):
        self.refuse(owner_context)
        if owner_context is None:
            return
        assert owner_context is self.context
        self.events.append(('guard', Path(path), deepcopy(record)))
        if self.stopped:
            raise Stopped('original owner stopped')
        if Path(path) != self.path:
            raise ValueError('wrong fixed recorder destination')
        if record.get('native_shared_generation') != {'test_identity': 'same-run'}:
            raise ValueError('wrong current record identity')


@pytest.fixture
def recorder(tmp_path, monkeypatch):
    path = tmp_path / 'method_core' / 'label' / 'P_provenance.yaml'
    protocol = Protocol(path)
    monkeypatch.setattr(capture, '_refuse_implicit_owner_context', protocol.refuse)
    monkeypatch.setattr(capture, 'require_recorder_write', protocol.guard)
    monkeypatch.setattr(pv, 'preservable_validation', lambda path, data: None)

    def conformance(data):
        protocol.events.append(('conformance', deepcopy(data)))
        return [], None

    monkeypatch.setattr(pv, 'check_record', conformance)
    data = {'project': 'P', 'native_shared_generation': {'test_identity': 'same-run'}}
    return protocol, pv.ProvenanceRecord(data)


def test_one_original_scope_cleanup_and_primary_error_identity(monkeypatch):
    context = object()
    events = []
    primary = RuntimeError('original body failure')
    cleanup = RuntimeError('later cleanup failure')

    @contextmanager
    def scope(selection):
        assert selection == 'exact-S'
        events.append('enter')
        try:
            yield context
        finally:
            events.append('cleanup')
            raise cleanup

    monkeypatch.setattr(capture, '_helper_owner_scope', scope)
    acknowledgements = []
    with pytest.raises(RuntimeError) as failed:
        with cli._recorder_owner_lifetime('exact-S') as actual:
            assert actual is context
            events.append('body')
            raise primary
        acknowledgements.append('success')
    assert failed.value is primary
    assert events == ['enter', 'body', 'cleanup'] and acknowledgements == []
    events.clear()
    with pytest.raises(RuntimeError) as failed:
        with cli._recorder_owner_lifetime('exact-S') as actual:
            assert actual is context
            events.append('body')
        acknowledgements.append('success')
    assert failed.value is cleanup
    assert events == ['enter', 'body', 'cleanup'] and acknowledgements == []

    @contextmanager
    def succeeds(selection):
        events.append(('enter', selection))
        yield context
        events.append('cleanup-ok')

    events.clear()
    monkeypatch.setattr(capture, '_helper_owner_scope', succeeds)
    with cli._recorder_owner_lifetime('exact-S') as actual:
        assert actual is context
        events.append('body')
    events.append('acknowledged')
    assert events == [('enter', 'exact-S'), 'body', 'cleanup-ok', 'acknowledged']
    with cli._recorder_owner_lifetime(None) as actual:
        assert actual is None


def test_first_write_exact_readback_and_post_serialization_refusal(recorder, monkeypatch):
    protocol, record = recorder
    wrong = protocol.path.parent / 'other_provenance.yaml'
    with pytest.raises(ValueError, match='wrong fixed'):
        record.write(wrong, owner_context=protocol.context)
    assert not wrong.parent.exists()  # refusal precedes even mkdir
    protocol.events.clear()
    assert record.write(protocol.path, owner_context=protocol.context) == protocol.path
    first = protocol.path.read_bytes()
    assert yaml.safe_load(first)['native_shared_generation'] == record.data['native_shared_generation']
    assert any(row[0] == 'conformance' for row in protocol.events)
    assert protocol.events[-1][0] == 'guard'  # conformance cannot end the lifetime check

    original_dump = pv.dump_yaml

    def stop_while_serializing(data):
        result = original_dump(data)
        protocol.stopped = True
        return result

    monkeypatch.setattr(pv, 'dump_yaml', stop_while_serializing)
    with pytest.raises(Stopped, match='original owner stopped'):
        record.write(protocol.path, owner_context=protocol.context)
    assert protocol.path.read_bytes() == first
    protocol.stopped = False
    monkeypatch.setattr(pv, 'dump_yaml', original_dump)
    original_write = Path.write_text

    def corrupt_readback(path, text, *args, **kwargs):
        if path == protocol.path:
            text += '\n# changed after selected serialization\n'
        return original_write(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, 'write_text', corrupt_readback)
    with pytest.raises(ValueError, match='exact readback'):
        record.write(protocol.path, owner_context=protocol.context)
    assert protocol.path.read_bytes().endswith(b'# changed after selected serialization\n')
    # Failure preserves the evidence on disk; the writer does not roll it back.


def test_conformance_stop_and_inline_failure_keep_first_record(recorder, monkeypatch, capsys):
    protocol, record = recorder

    def conformance_then_stop(data):
        protocol.stopped = True
        return [], None

    monkeypatch.setattr(pv, 'check_record', conformance_then_stop)
    with pytest.raises(Stopped):
        record.write(protocol.path, owner_context=protocol.context)
    first = protocol.path.read_bytes()
    assert yaml.safe_load(first)['project'] == 'P'
    protocol.stopped = False
    failure = RuntimeError('inline computation refused')
    calls = []

    def compute(path, *, origin_prior=None, owner_context=None):
        calls.append(('compute', path, owner_context, origin_prior))
        raise failure

    monkeypatch.setattr(bc, 'compute', compute)
    monkeypatch.setattr(bc, 'apply', lambda *args, **kwargs: pytest.fail('second write after failed compute'))
    with pytest.raises(RuntimeError) as failed:
        cli._inline_checks(protocol.path, origin_prior={'prior': True}, owner_context=protocol.context)
    assert failed.value is failure
    assert calls == [('compute', protocol.path, protocol.context, {'prior': True})]
    assert protocol.path.read_bytes() == first
    assert capsys.readouterr().out == ''
    # The historical maintenance path still warns and leaves its record intact.
    assert cli._inline_checks(protocol.path) is None
    assert 'deterministic checks not computed' in capsys.readouterr().out
    assert protocol.path.read_bytes() == first


def test_inline_context_and_summary_wait_for_successful_owner_cleanup(recorder, monkeypatch, capsys):
    protocol, record = recorder
    record.write(protocol.path, owner_context=protocol.context)
    calls = []
    blocks = {'form': {'checked': True, 'test': 'computed'}}

    def compute(path, *, origin_prior=None, owner_context=None):
        calls.append(('compute', owner_context))
        return deepcopy(blocks)

    def apply(path, actual_blocks, overwrite=False, *, owner_context=None):
        calls.append(('apply', owner_context))
        assert overwrite is True
        assert actual_blocks['form']['recorded_by'] == 'd4d provenance record'
        return True

    monkeypatch.setattr(bc, 'compute', compute)
    monkeypatch.setattr(bc, 'apply', apply)
    monkeypatch.setattr(bc, 'summarise', lambda actual: 'protocol checks complete')
    result = cli._inline_checks(protocol.path, owner_context=protocol.context)
    assert result == '  protocol checks complete'
    assert calls == [('compute', protocol.context), ('apply', protocol.context)]
    assert capsys.readouterr().out == ''
    # The default path retains its existing immediate summary output.
    assert cli._inline_checks(protocol.path) is None
    assert capsys.readouterr().out == '  protocol checks complete\n'


def test_second_write_preserves_header_attestations_and_prior_measurements(recorder, monkeypatch):
    protocol, record = recorder
    record.data.update({
        'pair_consistency': {'checked': True, 'artifacts': {'full': 'a'},
                             'semantic_review': {'reviewer': 'human'}},
        'receipts': {'checked': True, 'expected': True, 'measurement': 'keep'},
    })
    record.write(protocol.path, owner_context=protocol.context)
    first = protocol.path.read_bytes()
    assert bc.apply(protocol.path, {
        'pair_consistency': {'checked': True, 'artifacts': {'full': 'a'}},
        'receipts': {'checked': False, 'expected': True},
    }, overwrite=True, owner_context=protocol.context) is True
    updated = protocol.path.read_bytes()
    assert bc._split_header(updated.decode())[0] == bc._split_header(first.decode())[0]
    assert updated.startswith(b'# D4D generation provenance record\n# record_version ')
    data = yaml.safe_load(updated)
    assert data['pair_consistency']['semantic_review'] == {'reviewer': 'human'}
    assert data['receipts']['measurement'] == 'keep'
    original_dump = bc.yaml.safe_dump

    def stop_while_serializing(*args, **kwargs):
        result = original_dump(*args, **kwargs)
        protocol.stopped = True
        return result

    monkeypatch.setattr(bc.yaml, 'safe_dump', stop_while_serializing)
    with pytest.raises(Stopped):
        bc.apply(protocol.path, {'form': {'checked': True}}, overwrite=True,
                 owner_context=protocol.context)
    assert protocol.path.read_bytes() == updated
    protocol.stopped = False
    monkeypatch.setattr(bc.yaml, 'safe_dump', original_dump)
    original_write = Path.write_text

    def corrupt(path, text, *args, **kwargs):
        if path == protocol.path:
            text += '\n# changed second-write bytes\n'
        return original_write(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, 'write_text', corrupt)
    with pytest.raises(ValueError, match='exact readback'):
        bc.apply(protocol.path, {'form': {'checked': True}}, overwrite=True,
                 owner_context=protocol.context)
    assert protocol.path.read_bytes().endswith(b'# changed second-write bytes\n')


def test_compute_receipt_route_same_context_and_no_write_exit_guard(recorder, monkeypatch):
    protocol, record = recorder
    record.write(protocol.path, owner_context=protocol.context)
    receipts = importlib.import_module('data_sheets_schema.receipts')
    origin = importlib.import_module('data_sheets_schema.receipt_origin_record')
    seen = []

    def assessment(*args, **kwargs):
        seen.append(kwargs)
        return {'checked': True, 'expected': True}

    monkeypatch.setattr(receipts, 'block_for', assessment)
    monkeypatch.setattr(origin, 'for_assessment', lambda *args, **kwargs: {'test': 'no transcript'})
    result = bc.compute(protocol.path, only={'receipts'}, owner_context=protocol.context)
    assert len(seen) == 1 and seen[0]['owner_context'] is protocol.context
    assert seen[0]['snapshot_record']['native_shared_generation'] == record.data['native_shared_generation']
    assert result['receipts']['checked'] is True
    before = protocol.path.read_bytes()
    guard = protocol.guard
    admitted = []

    def stop_after_initial_guard(path, *, owner_context=None, record):
        guard(path, owner_context=owner_context, record=record)
        if owner_context is not None and not admitted:
            admitted.append(True)
            protocol.stopped = True

    monkeypatch.setattr(capture, 'require_recorder_write', stop_after_initial_guard)
    with pytest.raises(Stopped):
        bc.apply(protocol.path, {}, owner_context=protocol.context)
    assert protocol.path.read_bytes() == before


def test_omitted_context_refuses_active_owner_before_effects(recorder, monkeypatch):
    protocol, record = recorder
    protocol.active = True
    with pytest.raises(Stopped, match='missing explicit context'):
        record.write(protocol.path)
    assert not protocol.path.parent.exists()
    for operation in (lambda: bc.compute(protocol.path),
                      lambda: bc.apply(protocol.path, {}),
                      lambda: cli._inline_checks(protocol.path)):
        with pytest.raises(Stopped, match='missing explicit context'):
            operation()
    assert not protocol.path.exists()
