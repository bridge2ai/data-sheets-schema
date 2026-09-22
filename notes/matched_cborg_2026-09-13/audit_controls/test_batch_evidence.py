"""One terminal source check also binds model-authored integration decisions."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE/'native_controls')]
from audit_controls import contract, registration, batch_output
from audit_controls.test_contract import audit_fixture
from audit_controls.test_source_metadata_upgrade import install_metadata_authority
from data_sheets_schema import evidence_assertions


def inputs(tmp_path):
    manifest, _ = audit_fixture(tmp_path)
    manifest.update(protocol_version=7, render_version=20,
        scientific_contract_transition={'kind': registration.BATCH_TRANSITION_KIND})
    install_metadata_authority(manifest, tmp_path)
    paths = {key: Path(value) for key, value in manifest['inputs'].items()}
    kwargs = dict(audit=Path(manifest['job']['audit_path']), bundle=paths['bundle'],
        manifest=paths['chunk_manifest'], artifacts={k: paths[k] for k in ('original_full','original_core')},
        protocol_version=7, source_manifest=paths['source_manifest'], project='EXAMPLE')
    return manifest, kwargs


def source(quote='The service is planned.'):
    return {'source': 'protocol.txt', 'chunk': 'c001', 'quote': quote}


@pytest.mark.parametrize('assertions,kind', [([], None), ([source()], None),
    ([source('A nonexistent claim.')], 'source_quote_not_found'),
    ([{'artifact':'original_full','path':'/description','op':'contains','quote':'not present'}],
     'artifact_assertion_contradicted'),
    ([{'artifact':'final_full','path':'/description','op':'contains','quote':'planned'}], 'evidence_contract'),
    ([{'source':'different.txt','chunk':'c001','quote':'The service is planned.'}], 'evidence_contract')])
def test_real_terminal_checker_checks_every_integration_assertion(tmp_path, assertions, kind):
    _, kwargs = inputs(tmp_path)
    baseline = evidence_assertions.check_files(**kwargs)
    assert baseline['checked'] is True and baseline['findings'] == []
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = evidence_assertions.check_files(**kwargs, integration_assertions=assertions)
    assert result['integration_assertions_checked'] == len(assertions)
    assert result['assertions_checked'] == baseline['assertions_checked'] + len(assertions)
    if kind:
        assert any(f['kind'] == kind and f['integration_decision'] is True for f in result['findings'])
    else:
        assert result['findings'] == []
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize('protocol', [1,2,3,4,5,6])
def test_legacy_protocols_cannot_silently_gain_integration_checks(tmp_path, protocol):
    _, kwargs = inputs(tmp_path)
    kwargs.update(protocol_version=protocol)
    if protocol < 5:
        kwargs.pop('source_manifest'); kwargs.pop('project')
    with pytest.raises(ValueError, match='integration assertions require protocol 7'):
        evidence_assertions.check_files(**kwargs, integration_assertions=[])


@pytest.mark.parametrize('value', [{}, 'assertion', 0, False])
def test_integration_assertions_require_explicit_list(tmp_path, value):
    _, kwargs = inputs(tmp_path)
    with pytest.raises(ValueError, match='explicit array'):
        evidence_assertions.check_files(**kwargs, integration_assertions=value)


@pytest.mark.parametrize('damage', [None, 'false_quote', 'lineage_changed_before', 'lineage_changed_during'])
def test_audit_contract_consumes_assembly_bound_decisions_once(tmp_path, monkeypatch, damage):
    # Assembly's pure grammar/closure has separate tests; this test stubs only
    # its returned descriptor to isolate actual terminal checker wiring and races.
    manifest, _ = inputs(tmp_path)
    manifest['audit_batches'] = {'synthetic': 'assembly checked separately'}
    lineage = tmp_path/'lineage.json'
    from audit_controls.test_context_preparation import save
    save(lineage, {'decision_assertions': [source('not in source') if damage == 'false_quote' else source()]})
    descriptor = {'path': str(lineage), 'sha256': registration.sha(lineage)}
    monkeypatch.setattr(batch_output, 'validate_output', lambda m: {'lineage': deepcopy(descriptor)})
    original = evidence_assertions.check_files
    calls = []
    def counted(**kwargs):
        calls.append(kwargs)
        report = original(**kwargs)
        if damage == 'lineage_changed_during': lineage.write_text('{}')
        return report
    monkeypatch.setattr(evidence_assertions, 'check_files', counted)
    if damage == 'lineage_changed_before': lineage.write_text('{}')
    result = contract.validate_audit(manifest)
    assert result['passed'] is (damage is None)
    assert len(calls) == (0 if damage == 'lineage_changed_before' else 1)
    if calls: assert calls[0]['integration_assertions']
    if damage and damage.startswith('lineage_changed'):
        assert any('integration lineage changed' in message for message in result['errors'])
