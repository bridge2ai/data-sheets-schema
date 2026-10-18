"""Real completion transactions and all three publishers' late-failure boundaries."""
import json
import os
from pathlib import Path

import pytest

from data_sheets_schema import figure_publication as publication

RAW = b'{"state":"complete","artifacts":{}}\n'


@pytest.fixture
def directory(tmp_path):
    root = tmp_path / 'output'
    root.mkdir()
    close = os.close
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield root, fd
    finally:
        close(fd)


def test_ordinary_transaction_and_exclusive_reentry(directory):
    root, fd = directory
    checks = []
    publication.complete(fd, 'manifest.json', RAW, lambda: checks.append(True))
    assert checks == [True, True]
    assert (root / 'manifest.json').read_bytes() == RAW
    assert (root / publication.PENDING).samefile(root / 'manifest.json')
    with pytest.raises(FileExistsError):
        publication.complete(fd, 'manifest.json', RAW, lambda: None)
    assert (root / 'manifest.json').read_bytes() == RAW


@pytest.mark.parametrize('when', ['write', 'close', 'write-and-close'])
def test_actual_data_stream_failure_precedes_commit(directory, monkeypatch, when):
    root, fd = directory
    original = publication.os.fdopen
    error = OSError('injected data ' + when)
    later = OSError('subsequent buffered close failure')
    events = []

    class Stream:
        def __init__(self, actual): self.actual = actual
        def __enter__(self): return self
        def write(self, raw):
            self.actual.write(raw)
            events.append('write')
            if when in ('write', 'write-and-close'): raise error
        def __exit__(self, *args):
            self.actual.__exit__(*args)
            events.append('close')
            if when == 'close': raise error
            if when == 'write-and-close': raise later

    monkeypatch.setattr(publication.os, 'fdopen', lambda *a, **kw: Stream(original(*a, **kw)))
    with pytest.raises(OSError) as caught:
        publication.complete(fd, 'manifest.json', RAW, lambda: None)
    assert caught.value is error and events == ['write', 'close']
    if when == 'write-and-close': assert caught.value.__cause__ is later
    assert not (root / 'manifest.json').exists()
    assert (root / publication.PENDING).read_bytes() == b''


@pytest.mark.parametrize('after', [False, True])
def test_link_failure_before_or_after_effect_revokes_only_owned_inode(directory, monkeypatch, after):
    root, fd = directory
    link = publication.os.link
    error = OSError('exclusive link failure')
    def broken(*args, **kwargs):
        if after: link(*args, **kwargs)
        raise error
    monkeypatch.setattr(publication.os, 'link', broken)
    with pytest.raises(OSError) as caught:
        publication.complete(fd, 'manifest.json', RAW, lambda: None)
    assert caught.value is error
    assert (root / publication.PENDING).read_bytes() == b''
    assert (root / 'manifest.json').read_bytes() == b'' if after else not (root / 'manifest.json').exists()


def test_postlink_check_failure_preserves_original_and_invalidates_extra_hardlink(directory):
    root, fd = directory
    error = ValueError('source changed')
    def check():
        if (root / 'manifest.json').exists():
            os.link(root / 'manifest.json', root / 'extra')
            raise error
    with pytest.raises(ValueError) as caught:
        publication.complete(fd, 'manifest.json', RAW, check)
    assert caught.value is error
    assert all((root / name).read_bytes() == b'' for name in ('manifest.json', publication.PENDING, 'extra'))


@pytest.mark.parametrize('point', ['pending', 'final'])
def test_replaced_name_is_never_unlinked_or_written(directory, monkeypatch, point):
    root, fd = directory
    link = publication.os.link
    original = publication._write_pending
    winner = b'foreign winner'
    name = publication.PENDING if point == 'pending' else 'manifest.json'
    def replace():
        (root / name).rename(root / 'owned')
        (root / name).write_bytes(winner)
    if point == 'pending':
        def write(*args):
            original(*args)
            replace()
        monkeypatch.setattr(publication, '_write_pending', write)
    else:
        def publish(*args, **kwargs):
            link(*args, **kwargs)
            replace()
        monkeypatch.setattr(publication.os, 'link', publish)
    with pytest.raises(ValueError, match='identity changed'):
        publication.complete(fd, 'manifest.json', RAW, lambda: None)
    assert (root / name).read_bytes() == winner
    assert (root / 'owned').read_bytes() == b''


def test_existing_marker_winner_is_preserved(directory):
    root, fd = directory
    (root / 'manifest.json').write_bytes(b'existing winner')
    with pytest.raises(FileExistsError):
        publication.complete(fd, 'manifest.json', RAW, lambda: None)
    assert (root / 'manifest.json').read_bytes() == b'existing winner'
    assert (root / publication.PENDING).read_bytes() == b''


def test_rollback_failure_is_explicit_and_chains_original(directory, monkeypatch):
    root, fd = directory
    error = OSError('post-link failure')
    def verify():
        if (root / 'manifest.json').exists(): raise error
    def fail(*_): raise OSError('invalidation refused')
    monkeypatch.setattr(publication.os, 'ftruncate', fail)
    with pytest.raises(RuntimeError, match='invalidation could not be certified') as caught:
        publication.complete(fd, 'manifest.json', RAW, verify)
    assert caught.value.__cause__ is error
    # Explicitly uncertain cleanup: the test must not pretend this is revoked.
    assert (root / 'manifest.json').read_bytes() == RAW


def test_postcommit_bookkeeping_close_is_nonfatal_even_with_warning_errors(directory, monkeypatch, capfd):
    root, fd = directory
    close = publication.os.close
    calls = []
    def broken(target):
        owned = os.fstat(target).st_ino == (root / publication.PENDING).stat().st_ino
        close(target)
        if owned:
            calls.append(target)
            raise OSError('bookkeeping close failure')
    monkeypatch.setattr(publication.os, 'close', broken)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        publication.complete(fd, 'manifest.json', RAW, lambda: None)
    monkeypatch.setattr(publication.os, 'close', close)
    assert len(calls) == 1 and (root / 'manifest.json').read_bytes() == RAW
    assert 'committed' in capfd.readouterr().err


def test_precommit_close_failure_does_not_hide_original_cause(directory, monkeypatch):
    root, fd = directory
    close = publication.os.close
    original = ValueError('original check failure')
    def broken(target):
        owned = os.fstat(target).st_ino == (root / publication.PENDING).stat().st_ino
        close(target)
        if owned: raise OSError('bookkeeping close failure')
    def verify(): raise original
    monkeypatch.setattr(publication.os, 'close', broken)
    with pytest.raises(RuntimeError, match='descriptor cleanup could not be certified') as caught:
        publication.complete(fd, 'manifest.json', RAW, verify)
    monkeypatch.setattr(publication.os, 'close', close)
    assert caught.value.__cause__ is original
    assert (root / publication.PENDING).read_bytes() == b''


@pytest.mark.parametrize('marker,raw', [('other.json', RAW), ('manifest.json', bytearray(RAW))])
def test_invalid_private_transaction_arguments_do_not_reserve(directory, marker, raw):
    root, fd = directory
    with pytest.raises(ValueError): publication.complete(fd, marker, raw, lambda: None)
    assert list(root.iterdir()) == []


def real_prepared(kind, inputs):
    inputs.mkdir()
    if kind == 'attainability':
        from data_sheets_schema import attainability_figure as figure
        from tests.test_attainability_figure import prepared_fixture
        prepared, _, _ = prepared_fixture(inputs)
    elif kind == 'typed':
        from data_sheets_schema import typed_audit_figure as figure
        from tests.test_typed_audit import supplied, packet
        from tests.test_typed_audit_figure import assembly
        args = supplied.__wrapped__(inputs)
        actual = packet.__wrapped__(args)
        selected = inputs / 'assembly.json'
        selected.write_bytes(assembly(actual, 'merged'))
        prepared = figure.prepare([selected])
    else:
        from data_sheets_schema import semantic_taxonomy_figure as figure
        from tests.test_semantic_taxonomy_figure import fixture, selection, entry
        _, rating, inp, context = fixture(inputs)
        prepared = figure.prepare(selection(inputs, [entry(rating, inp, context)]))
    return figure, prepared


@pytest.mark.parametrize('kind', ['attainability', 'typed', 'semantic'])
@pytest.mark.parametrize('failure', ['late-data-close', 'moved-at-link', 'source-after-link', 'artifact-after-link', 'caller-close'])
def test_real_publishers_complete_or_invalidate_at_original_boundaries(tmp_path, monkeypatch, capfd, kind, failure):
    inputs = tmp_path / 'inputs'
    figure, prepared = real_prepared(kind, inputs)
    before = {str(p): p.read_bytes() for p in inputs.rglob('*') if p.is_file()}
    report = prepared.report()
    good = tmp_path / 'good'
    manifest = figure.publish(prepared, good)
    marker = 'report.json' if kind == 'semantic' else 'manifest.json'
    assert json.loads((good / marker).read_bytes()) == manifest
    assert manifest['state'] == 'complete'
    sources = manifest['consumer_sources']
    assert str(Path(publication.__file__).resolve()) in {p['path'] for p in sources}
    artifacts = {name: (good / name).read_bytes() for name in manifest['artifacts']}
    assert any(name.endswith('.svg') for name in artifacts)
    assert prepared.report() == report
    output, displaced = tmp_path / 'bad', tmp_path / 'displaced'
    error = OSError('late buffered completion close')
    calls = []
    original_write, original_link = publication._write_pending, publication.os.link
    close = publication.os.close
    original_input = (prepared.selected.absolute if kind == 'attainability' else
                      prepared.selected[0].absolute if kind == 'typed' else
                      next(cap.path for cap in prepared.captures if cap.path in before))
    if failure == 'late-data-close':
        def write(*args):
            original_write(*args)
            calls.append('closed')
            raise error
        monkeypatch.setattr(publication, '_write_pending', write)
    elif failure == 'caller-close':
        armed = []
        def commit_link(*args, **kwargs):
            original_link(*args, **kwargs)
            armed.append(True)
        def broken(fd):
            info = os.fstat(fd)
            owned = armed and any(os.path.samestat(info, path.stat()) for path in
                                  (output, output.parent, output / publication.PENDING))
            close(fd)
            if owned:
                calls.append('close')
                raise OSError('bookkeeping cleanup')
        monkeypatch.setattr(publication.os, 'link', commit_link)
        monkeypatch.setattr(publication.os, 'close', broken)
    else:
        def link(*args, **kwargs):
            original_link(*args, **kwargs)
            calls.append('linked')
            if failure == 'moved-at-link':
                output.rename(displaced)
                output.mkdir()
                (output / 'winner').write_bytes(b'preserve winner')
            elif failure == 'source-after-link':
                Path(original_input).write_bytes(before[original_input] + b'\n')
            else:
                (output / next(iter(artifacts))).write_bytes(b'changed artifact')
        monkeypatch.setattr(publication.os, 'link', link)
    if failure == 'caller-close':
        actual_manifest = figure.publish(prepared, output)
        monkeypatch.setattr(publication.os, 'close', close)
        assert actual_manifest == manifest
        assert json.loads((output / marker).read_bytes()) == manifest
        assert len(calls) == (3 if kind == 'attainability' else 2)
        assert capfd.readouterr().err.count('cleanup is not certified') == len(calls)
    else:
        with pytest.raises((OSError, ValueError)) as caught:
            figure.publish(prepared, output)
        if failure == 'late-data-close': assert caught.value is error
        assert len(calls) == 1
        actual = displaced if failure == 'moved-at-link' else output
        assert not (actual / marker).exists() or (actual / marker).read_bytes() == b''
        assert (actual / publication.PENDING).read_bytes() == b''
        if failure == 'moved-at-link':
            assert {p.name:p.read_bytes() for p in output.iterdir()} == {'winner': b'preserve winner'}
        if failure not in ('artifact-after-link',):
            assert {name: (actual / name).read_bytes() for name in artifacts} == artifacts
        if failure == 'source-after-link':
            Path(original_input).write_bytes(before[original_input])
    assert {str(p):p.read_bytes() for p in inputs.rglob('*') if p.is_file()} == before
