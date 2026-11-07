"""Validate live and saved schema graphs once, with no cached admission."""
from contextlib import contextmanager
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_selection as selected
from tests.test_native_shared_selection import artifact, declaration, pin


def _pool(saved, *, replacements=None, extras=()):
    replacements = replacements or {}
    artifacts = (saved.registration, saved.receipt_policy, *saved.authority,
                 *(a for schema in saved.schemas for a in schema.sources), *extras)
    artifacts = tuple(replacements.get(a.pin.role, a) for a in artifacts)
    members = tuple(evidence.PoolMember(a, c.canonical({
        'exists': True, 'regular': True, 'symlink': False, 'links': 1,
        'device': 0, 'inode': index + 1, 'size': len(a.raw), 'mtime_ns': 0}))
        for index, a in enumerate(artifacts))
    registration = replacements.get('selection', saved.registration)
    value = {'composition_raw_json': c.canonical({
        'selection_raw_json': registration.raw.decode('utf-8')}).decode('utf-8')}
    return evidence.CapturePool(members, ()), value


def _no_io(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('saved selection attempted ambient filesystem access')

    for name in ('read_bytes', 'read_text', 'resolve', 'open', 'stat', 'lstat'):
        monkeypatch.setattr(Path, name, deny)
    monkeypatch.setattr(selected, 'resource_path', deny)


def test_live_and_saved_capture_each_build_two_real_views(declaration, monkeypatch):
    views = []
    actual_view = selected.captured_view

    @contextmanager
    def observe(snapshot):
        views.append(str(snapshot.sources[0][1]))
        with actual_view(snapshot) as view:
            yield view

    monkeypatch.setattr(selected, 'captured_view', observe)
    saved = selected.capture(declaration['registration_path'])
    expected = [declaration['inputs'][kind + '_schema']['root']
                for kind in ('full', 'core')]
    assert views == expected
    pool, value = _pool(saved)
    views.clear()
    with monkeypatch.context() as trapped:
        _no_io(trapped)
        assert results._captured_selection(pool, value) == saved
        assert views == expected
        # Every independent public rebuild still derives both actual graphs.
        for _ in range(2):
            views.clear()
            assert selected.rebuild(saved.registration, saved.authority,
                                    saved.schemas, saved.receipt_policy) == saved
            assert views == expected


@pytest.mark.parametrize('mutation,diagnostic', [
    ('missing_class', 'lacks Dataset'),
    ('missing_import', 'outside the complete captured closure'),
    ('wrong_name', 'names, order or import closure differ'),
    ('unused_source', 'names, order or import closure differ'),
])
def test_declared_saved_carriers_still_require_actual_graph_validation(
        declaration, monkeypatch, mutation, diagnostic):
    saved = selected.capture(declaration['registration_path'])
    doc = saved.document()
    source = saved.schemas[0].sources[0]
    replacements, extras = {}, ()
    if mutation in ('missing_class', 'missing_import'):
        raw = (source.raw.replace(b'Dataset:', b'Different:')
               if mutation == 'missing_class'
               else source.raw + b'imports:\n  - missing\n')
        replacements[source.pin.role] = artifact(source.pin.role, source.pin.path, raw)
        doc['inputs']['full_schema']['sources'][0].update(pin(source.pin.path, raw))
    elif mutation == 'wrong_name':
        doc['inputs']['full_schema']['sources'][0]['name'] = 'foreign_name'
    else:
        path = str(Path(source.pin.path).with_name('unused.yaml'))
        raw = b'id: https://example.org/unused\nname: unused\nclasses:\n  Unused: {}\n'
        extras = (artifact('full_schema:1', path, raw),)
        doc['inputs']['full_schema']['sources'].append({'name': 'unused', **pin(path, raw)})
    replacements['selection'] = artifact('selection', saved.registration.pin.path, c.canonical(doc))
    pool, value = _pool(saved, replacements=replacements, extras=extras)
    rebuilds = []
    actual_rebuild = selected.rebuild

    def observe(*args):
        rebuilds.append(args)
        return actual_rebuild(*args)

    monkeypatch.setattr(selected, 'rebuild', observe)
    with monkeypatch.context() as trapped:
        _no_io(trapped)
        with pytest.raises(ValueError, match=diagnostic):
            results._captured_selection(pool, value)
    assert len(rebuilds) == 1


def test_live_capture_still_rereads_authority_after_a_success(declaration, tmp_path):
    saved = selected.capture(declaration['registration_path'])
    path = Path(declaration['inputs']['full_schema']['root'])
    original = path.read_bytes()
    (tmp_path / 'retained-original-full-schema.bin').write_bytes(original)
    changed = original.replace(b'Dataset:', b'Awayset:')
    assert changed != original and len(changed) == len(original)
    path.write_bytes(changed)
    with pytest.raises(ValueError, match='bytes differ from their registration'):
        selected.capture(declaration['registration_path'])
    assert saved.schemas[0].sources[0].raw == original
    assert path.read_bytes() == changed
