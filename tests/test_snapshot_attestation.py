"""Opt-in snapshot metadata uses the existing selected byte authority (#4356)."""
from copy import deepcopy

import pytest
import yaml

from data_sheets_schema import api_runner as api, snapshot_store as store, usage_ledger as ledger
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


def captured(spec):
    ledger.prepare_usage(spec, resume=True)
    store.activate(spec, fresh=True, completed=False, prior_record={})
    name = spec.project + '_audit.json'
    path = api._snapshot(spec, name, '{"findings":[]}', usage_id='index-attribution')
    record = {'run': {**ledger.run_identity(spec), 'generation_id': ledger.generation_id(spec)},
              'intermediates': store.entries(spec)}
    spec.provenance_path.write_text(yaml.safe_dump(record))
    return name, path, record


@pytest.mark.parametrize('authority', ['index', 'supplied_record', 'missing_index'])
def test_selected_attestation_preserves_default_tuple_and_copies_authority(external, authority):
    name, path, record = captured(external)
    kw = {'spec': external}
    expected = 'index-attribution'
    if authority == 'supplied_record':
        # The explicit record outranks the live index, including its metadata.
        record['intermediates'][0].update(usage_id='portable-attribution', annotation={'nested': [1]})
        kw['record'] = record
        expected = 'portable-attribution'
    elif authority == 'missing_index':
        store.index_path(external.metadata_dir, external.project).unlink()
    before = deepcopy(record)
    args = (external.metadata_dir, external.project, name)
    legacy = store.read_latest(*args, **kw)
    enriched = store.read_latest(*args, include_attestation=True, **kw)
    assert legacy == (True, (path, b'{"findings":[]}'))
    assert enriched[0] == legacy[0] and enriched[1][:2] == legacy[1]
    assert enriched[1][2]['usage_id'] == expected
    enriched[1][2]['usage_id'] = 'caller-mutation'
    if authority == 'supplied_record': enriched[1][2]['annotation']['nested'].append(2)
    assert record == before
    assert store.read_latest(*args, include_attestation=True, **kw)[1][2]['usage_id'] == expected


@pytest.mark.parametrize('metadata', [False, True])
def test_byte_refusal_remains_required_with_optional_metadata(external, metadata):
    name, path, _ = captured(external)
    path.write_bytes(b'changed')
    with pytest.raises(ledger.UsageLedgerError, match='bytes changed'):
        store.read_latest(external.metadata_dir, external.project, name, spec=external,
                          include_attestation=metadata)
