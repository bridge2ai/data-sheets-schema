"""Actual selected schema and pair validation without ambient schema reads."""
from dataclasses import replace
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import native_shared_contract as contract
from data_sheets_schema import native_shared_schema_gates as gates
from data_sheets_schema import native_shared_selection as selected
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_native_shared_selection import declaration, pin, save


@pytest.fixture
def captured(declaration):
    root = Path(declaration['inputs']['full_schema']['root']).parent
    (root / 'common.yaml').write_text('''id: https://example.org/common
name: common
prefixes:
  xsd: http://www.w3.org/2001/XMLSchema#
  ex: https://example.org/
  d4d: https://example.org/d4d/
default_prefix: ex
types:
  string: {base: str, uri: xsd:string}
classes:
  Base:
    attributes:
      id: {range: string, identifier: true}
      title: {range: string, required: true}
      conforms_to_class:
        range: string
        annotations: {d4d:perRecord: true}
''')
    for kind, cls in (('full', 'Dataset'), ('core', 'CoreDataset')):
        path = root / (kind + '.yaml')
        path.write_text(f'''id: https://example.org/{kind}
name: {kind}
imports: [common]
prefixes:
  ex: https://example.org/
default_prefix: ex
classes:
  {cls}:
    is_a: Base
''')
        snapshot = capture_schema(path, strict=True)
        declaration['inputs'][kind + '_schema']['sources'] = [
            {'name': str(name), **pin(source, raw)} for name, source, raw in snapshot.sources]
    save(declaration)
    return selected.capture(declaration['registration_path'])


def raw(kind, **changes):
    return yaml.safe_dump({'id': 'example:1', 'title': 'Example',
                          'conforms_to_class': kind, **changes}).encode()


def test_real_schema_and_pair_use_captured_imports_after_live_files_change(captured, monkeypatch):
    for schema in captured.schemas:
        for source in schema.sources:
            Path(source.pin.path).write_text('invalid live schema after capture\n')
    from data_sheets_schema import schema_view, api_runner
    def refuse(*args, **kwargs):
        pytest.fail('ambient schema or record read')
    for name in ('read_bytes', 'read_text', 'open', 'resolve'):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(schema_view, 'shared_view', refuse)
    monkeypatch.setattr(api_runner, '_validator_lines', refuse)
    monkeypatch.setattr(gates.pair, 'load_pair_schema', refuse)
    full, core = raw('Dataset'), raw('CoreDataset')
    assert gates.check_schemas(captured, full, core) == {'passed': True, 'problems': []}
    paired = gates.check_pair(captured, full, core)
    assert paired['passed'] is True and paired['schema_moved'] is False


@pytest.mark.parametrize('kind', ['full', 'core'])
@pytest.mark.parametrize('mutation', ['missing_required', 'unknown_slot', 'wrong_type'])
def test_actual_closed_validator_reports_selected_conformance_failures(captured, kind, mutation):
    docs = {'full': yaml.safe_load(raw('Dataset')), 'core': yaml.safe_load(raw('CoreDataset'))}
    if mutation == 'missing_required':
        del docs[kind]['title']
    elif mutation == 'unknown_slot':
        docs[kind]['foreign_slot'] = 'no'
    else:
        docs[kind]['title'] = ['wrong shape']
    result = gates.check_schemas(captured, *(yaml.safe_dump(docs[k]).encode() for k in ('full', 'core')))
    assert result['passed'] is False
    assert result['problems'] and all(p.startswith(kind + ':') for p in result['problems'])


def test_pair_gate_uses_selected_shared_slots_and_per_record_annotation(captured):
    # Each record conforms independently, but differing dataset titles fail
    # pair identity. Their per-record class labels legitimately differ.
    full, core = raw('Dataset'), raw('CoreDataset', title='Another dataset')
    assert gates.check_schemas(captured, full, core)['passed'] is True
    result = gates.check_pair(captured, full, core)
    assert result['passed'] is False and 'title' in result['diagnostic']
    assert gates.check_pair(captured, full, raw('CoreDataset'))['passed'] is True


@pytest.mark.parametrize('reader', [gates.check_schemas, gates.check_pair])
@pytest.mark.parametrize('bad', [b'id: one\nid: two\n', b'- sequence\n', b'title: [', 'not bytes', b''])
def test_unusable_records_raise_instead_of_reporting_a_pass(captured, reader, bad):
    with pytest.raises(ValueError):
        reader(captured, bad, raw('CoreDataset'))


@pytest.mark.parametrize('reader', [gates.check_schemas, gates.check_pair])
def test_incomplete_captured_import_cannot_fall_back_to_live_file(captured, reader):
    def omit_import(schema):
        sources = schema.sources[:1]
        roles = tuple(pair for pair in schema.import_roles if pair[1] == sources[0].pin.role)
        return replace(schema, sources=sources, import_roles=roles,
                       closure_sha256=contract.schema_closure_sha(sources, roles))
    schemas = tuple(omit_import(s) if s.kind == 'full' else s for s in captured.schemas)
    incomplete = replace(captured, schemas=schemas)
    with pytest.raises(ValueError, match='outside the captured closure'):
        reader(incomplete, raw('Dataset'), raw('CoreDataset'))


@pytest.mark.parametrize('reader', [gates.check_schemas, gates.check_pair])
def test_supplied_record_bound_is_enforced_before_parsing(declaration, reader):
    declaration['bounds']['max_input_bytes'] = 16384
    save(declaration)
    captured = selected.capture(declaration['registration_path'])
    with pytest.raises(ValueError, match='16384-byte bound'):
        reader(captured, b'#' + b'x' * 16384, raw('CoreDataset'))


@pytest.mark.parametrize('reader', [gates.check_schemas, gates.check_pair])
def test_expanded_final_records_use_selected_input_bound(captured, reader):
    # Final reconciliation may legitimately add supported values beyond the
    # smaller original seal limit. A real shared value must still conform
    # to both selected schemas and their pair rules.
    title = 'x' * 4_000_001
    records = tuple(json.dumps({'id': 'example:1', 'title': title,
                               'conforms_to_class': cls}).encode()
                    for cls in ('Dataset', 'CoreDataset'))
    assert all(4_000_000 < len(record) < 8_000_000 for record in records)
    assert reader(captured, *records)['passed'] is True


@pytest.mark.parametrize('reader', [gates.check_schemas, gates.check_pair])
@pytest.mark.parametrize('kind', ['full', 'core'])
def test_final_input_ceiling_refuses_before_parsing(captured, reader, kind):
    records = {'full': raw('Dataset'), 'core': raw('CoreDataset')}
    records[kind] = b'x' * 8_000_001
    with pytest.raises(ValueError, match='native final ' + kind + '.*8000000-byte bound'):
        reader(captured, records['full'], records['core'])
