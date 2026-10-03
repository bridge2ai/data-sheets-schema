"""Removal report identities are disclosures, never substituted measurements."""
import copy
import importlib.util
from pathlib import Path

from data_sheets_schema import removals


def module():
    path = Path(__file__).parents[1] / 'scripts/arm_comparison.py'
    spec = importlib.util.spec_from_file_location('arm_removal_basis', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_report_carries_actual_identifier_person_enum_bases_without_changing_counts(monkeypatch):
    m = module()
    block = removals.classify(None, {})
    identity = {'instrument': 'receipt-identity-rules-v1', 'schema_basis': {
        'source': "today's schema", 'sha256': 'a' * 64, 'reason': 'history unavailable',
        'requested_schema': {'sha256': 'b' * 64}}, 'bases': [['https://resolver.test/', 'x']],
        'bases_sha256': 'c' * 64, 'boundary_rule': 'ordered first match'}
    block['artifacts'] = {'identifier_rules': identity,
                         'person_slot_rules': {'source': 'independent-person-selection'},
                         'enum_alias_tables': {'source': 'independent-enum-selection'}}
    original = copy.deepcopy(block)
    monkeypatch.setattr(removals, 'for_record', lambda *a, **kw: block)
    ordinary = m.removal_metrics(Path('unused'), {})
    reported = m.removal_metrics(Path('unused'), {}, include_basis=True)
    assert {k:v for k,v in reported.items() if k != 'removal_schema_basis'} == ordinary
    assert all(value is None for value in ordinary.values())
    basis = reported['removal_schema_basis']
    assert basis['checked'] is False and basis['reason']
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    data['v4']['AI_READI'] = [{'label': 'run|label\n<x>`', **reported}]
    text = '\n'.join(m.removal_schema_section(data))
    for value in ('a' * 64, 'b' * 64, 'c' * 64, 'history unavailable',
                  'independent-person-selection', 'independent-enum-selection'):
        assert value in text
    assert 'run&#124;label<br>&lt;x&gt;&#96;' in text
    assert 'https://resolver.test/' not in text
    assert block == original and basis['identifier_rules'] == identity


def test_missing_authority_is_reported_as_missing_not_a_current_or_recorded_claim():
    m = module()
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    data['v4']['CHORUS'] = [{'label': 'missing'}]
    text = '\n'.join(m.removal_schema_section(data))
    assert '| missing | unrecorded — no removal basis supplied |' in text
    assert 'unmeasured, not zero' in text
