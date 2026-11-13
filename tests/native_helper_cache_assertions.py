"""Issue 6030: assert cache exclusion without treating its declared path as content."""
from pathlib import Path
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_results as results


def assert_cache_excluded(cache, snapshot, pool):
    # rglob includes dotfiles; the focused capture test supplies a hidden member.
    members = {str(p) for p in cache.rglob('*')}
    assert members
    for catalog in (snapshot.identity(), snapshot.metadata, snapshot.aliases,
                    snapshot.alias_metadata):
        assert not members.intersection(catalog)
    assert not members.intersection(snapshot.aliases.values())
    assert not members.intersection(m.captured.pin.path for m in pool.members)
    assert pool == evidence.decode(pool.encode())


def assert_public_cache_excluded(value, result):
    cache = Path(value['environment']['PYSTOW_HOME'])
    assert (cache / 'README.md').stat().st_size > 0
    assert (cache / 'oaklib').is_dir()
    assert list(Path(value['environment']['HOME']).iterdir()) == []
    directory = Path(value['evidence_directory'])
    pool = evidence.decode((directory / results.POOL_NAME).read_bytes())
    snapshot = results.Snapshot(value['working_directory'], pool.members)
    assert_cache_excluded(cache, snapshot, pool)
    for key, actual in (('captured_files', snapshot.identity()),
                        ('captured_metadata', snapshot.metadata),
                        ('captured_aliases', snapshot.aliases),
                        ('captured_alias_metadata', snapshot.alias_metadata)):
        assert result[key] == actual
    expected = set()
    for index, (original, raw) in enumerate(sorted(snapshot.raw.items())):
        projected = directory / 'captured' / str(index) / Path(original).name
        expected.add(projected)
        assert projected.read_bytes() == raw
    assert {p for p in (directory / 'captured').rglob('*') if p.is_file()} == expected
