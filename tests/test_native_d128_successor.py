"""PR6302 D128 successor controls, 2026-11-22; invented objects are not approval.

Historical bytes and decision stay unchanged. These pure controls require exact
types, order and duplicate occurrences; no scanner, Git or native process runs.
"""

from copy import deepcopy
import socket
import subprocess

import pytest

from scripts.adhoc import compare_pr6302_d128_successor_20261122 as successor
from tests import test_native_d128_scanner_comparison as gate


def prohibit_effects(monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail('pure successor control attempted a process or transport')
    monkeypatch.setattr(subprocess, 'run', refused)
    monkeypatch.setattr(subprocess, 'Popen', refused)
    monkeypatch.setattr(subprocess, 'check_output', refused)
    monkeypatch.setattr(socket.socket, 'connect', refused)


prohibit_effects = pytest.fixture(autouse=True)(prohibit_effects)


def parent_approval():
    return gate.approval()


parent_approval = pytest.fixture(scope='module')(parent_approval)


def toy():
    a = dict(path='one.py', line=1, snippet='neutral', role='old')
    b = dict(path='two.py', line=8, snippet='neutral', role='old')
    before = [a, deepcopy(a), b, dict(path='gone.py', line=2)]
    after = [deepcopy(a), dict(a, line=2), dict(b, role='new'), dict(path='added.py', line=3)]
    return before, after


def test_full_occurrence_mapping_retains_duplicates_types_order_and_positions():
    before, after = toy()
    ledger = successor.diff_array(before, after)
    assert ledger['exact_matches'] == [[0, 0]]
    assert all(len(ledger[kind]) == 1 for kind in successor.KINDS)
    assert ledger['relocations'][0]['differing_fields'] == ['line']
    assert ledger['changed_fields'][0]['differing_fields'] == ['role']
    assert len(ledger['positional_differences']) == 3
    successor.validate_array(before, after, ledger)
    reordered = successor.diff_array([before[0], before[2], before[1]], [before[0], before[1], before[2]])
    assert not reordered['exact_arrays_equal']
    assert reordered['exact_matches'] == [[0, 0], [1, 2], [2, 1]]
    assert all(reordered[kind] == [] for kind in successor.KINDS)
    assert len(reordered['positional_differences']) == 2


def test_comparator_does_not_collapse_json_type_or_presence_changes(change):
    before = [dict(path='one.py', line=1, detail=[1])]
    after = deepcopy(before)
    if change == 'bool_line': after[0]['line'] = True
    elif change == 'float_line': after[0]['line'] = 1.0
    elif change == 'nested_bool': after[0]['detail'] = [True]
    else: after[0]['extra'] = None
    ledger = successor.diff_array(before, after)
    assert not ledger['exact_arrays_equal'] and ledger['exact_matches'] == []
    assert ledger['before_sha256'] != ledger['after_sha256']
    successor.validate_array(before, after, ledger)


test_comparator_does_not_collapse_json_type_or_presence_changes = pytest.mark.parametrize(
    'change', ['bool_line', 'float_line', 'nested_bool', 'missing_null'])(
        test_comparator_does_not_collapse_json_type_or_presence_changes)


def test_full_ledger_refuses_missing_extra_duplicate_or_changed_occurrences(change):
    before, after = toy()
    ledger = successor.diff_array(before, after)
    if change == 'duplicate': ledger['exact_matches'].append([0, 0])
    elif change == 'missing': ledger['added'] = []
    elif change == 'bool_index': ledger['exact_matches'][0][0] = False
    elif change == 'bool_count': ledger['before_count'] = True
    elif change == 'wrong_object': ledger['changed_fields'][0]['after']['role'] = 'changed again'
    elif change == 'wrong_fields': ledger['relocations'][0]['differing_fields'] = []
    elif change == 'reorder': after.reverse()
    elif change == 'extra': after.append(deepcopy(after[0]))
    elif change == 'bool_nested': after[0]['line'] = True
    elif change == 'position_missing': ledger['positional_differences'].pop()
    elif change == 'position_bool': ledger['positional_differences'][0]['index'] = True
    elif change == 'equality_bool': ledger['exact_arrays_equal'] = 0
    else: ledger['before_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        successor.validate_array(before, after, ledger)


test_full_ledger_refuses_missing_extra_duplicate_or_changed_occurrences = pytest.mark.parametrize(
    'change', ['duplicate', 'missing', 'bool_index', 'bool_count', 'wrong_object',
               'wrong_fields', 'reorder', 'extra', 'bool_nested', 'wrong_hash',
               'position_missing', 'position_bool', 'equality_bool'])(
        test_full_ledger_refuses_missing_extra_duplicate_or_changed_occurrences)


def invented_review(parent):
    """Synthetic loader control only; never selected by the live pinned gate."""
    value = dict(kind='pr6302_d128_reviewed_successor', version=1,
        assignment=successor.ASSIGNMENT, historical_fixture_sha256=successor.HISTORICAL_SHA,
        historical_evidence_sha256=successor.EVIDENCE_SHA, historical_owner_decision_changed=False,
        review_reference='invented software control; no human approval claimed',
        comparison_evidence_sha256='b' * 64, frozen_baseline_unchanged=True,
        baseline=deepcopy(parent['baseline']), exact_violations=deepcopy(parent['exact_violations']),
        arrays=deepcopy(parent['arrays']), reference_candidate=deepcopy(parent['reference_candidate']),
        tool_commit='a' * 40, tool_assets_sha256=deepcopy(parent['tool_assets_sha256']))
    value['reference_candidate']['commit'] = value['tool_commit']
    return value


def test_separately_pinned_successor_does_not_rewrite_historical_decision(parent_approval):
    original = gate.FIXTURE.read_bytes()
    value = invented_review(parent_approval)
    raw = successor.encoded(value)
    assert successor.require_successor(raw, successor.sha(raw), parent_approval) == value
    assert gate.approval() == parent_approval and gate.FIXTURE.read_bytes() == original
    assert successor.sha(original) == successor.HISTORICAL_SHA == gate.FIXTURE_SHA256
    assert successor.EVIDENCE_SHA == gate.EVIDENCE_SHA256
    with pytest.raises(ValueError, match='pin is not supplied'):
        successor.require_successor(raw, None, parent_approval)
    with pytest.raises(ValueError, match='bytes changed'):
        successor.require_successor(raw + b'\n', successor.sha(raw), parent_approval)


REVIEW_MUTATIONS = ('proposal', 'decision', 'version_bool', 'parent_fixture', 'parent_evidence',
    'owner_decision', 'missing_review', 'empty_review', 'bad_evidence', 'baseline',
    'violation', 'violation_order', 'frozen_bool', 'missing_array', 'before_count_bool',
    'before_hash', 'tool_commit', 'source_mask', 'source_roster', 'source_tree',
    'extra_asset', 'missing_asset', 'bad_asset_hash', 'changed_tokens')


def test_successor_loader_refuses_unreviewed_or_widened_claims(parent_approval, change):
    value = invented_review(parent_approval)
    if change == 'proposal': value['kind'] = 'pr6302_d128_successor_proposal'
    elif change == 'decision': value['assignment'] = 'new owner D128 approval'
    elif change == 'version_bool': value['version'] = True
    elif change == 'parent_fixture': value['historical_fixture_sha256'] = '0' * 64
    elif change == 'parent_evidence': value['historical_evidence_sha256'] = '0' * 64
    elif change == 'owner_decision': value['historical_owner_decision_changed'] = True
    elif change == 'missing_review': value.pop('review_reference')
    elif change == 'empty_review': value['review_reference'] = ' '
    elif change == 'bad_evidence': value['comparison_evidence_sha256'] = 'unknown'
    elif change == 'baseline': value['baseline']['commit'] = 'a' * 40
    elif change == 'violation': value['exact_violations'][0]['violation'] = False
    elif change == 'violation_order': value['exact_violations'].reverse()
    elif change == 'frozen_bool': value['frozen_baseline_unchanged'] = 1
    elif change == 'missing_array': value['arrays'].pop('test_dependencies')
    elif change == 'before_count_bool': value['arrays']['hits']['before_count'] = True
    elif change == 'before_hash': value['arrays']['hits']['before_sha256'] = '0' * 64
    elif change == 'tool_commit': value['tool_commit'] = 'b' * 40
    elif change == 'source_mask': value['reference_candidate']['physical_input_mask'] = ['src']
    elif change == 'source_roster': value['reference_candidate']['committed_roster_sha256'] = 'unknown'
    elif change == 'source_tree': value['reference_candidate']['tree'] = True
    elif change == 'extra_asset': value['tool_assets_sha256']['unreviewed.py'] = 'a' * 64
    elif change == 'missing_asset': value['tool_assets_sha256'].pop(successor.SKILL + '/tokens.yaml')
    elif change == 'bad_asset_hash': value['tool_assets_sha256'][successor.SKILL + '/scan.py'] = 'unknown'
    else: value['tool_assets_sha256'][successor.SKILL + '/tokens.yaml'] = 'a' * 64
    raw = successor.encoded(value)
    with pytest.raises(ValueError):
        successor.require_successor(raw, successor.sha(raw), parent_approval)


test_successor_loader_refuses_unreviewed_or_widened_claims = pytest.mark.parametrize(
    'change', REVIEW_MUTATIONS)(test_successor_loader_refuses_unreviewed_or_widened_claims)


def test_historical_bytes_and_complete_array_shapes_remain_required():
    with pytest.raises(ValueError, match='historical fixture or evidence'):
        successor.historical(b'{}', b'{}')
    for value in (None, {}, {'hits': [], 'violations': []},
                  dict(hits=[], violations=[], test_dependencies={}),
                  dict(hits=[True], violations=[], test_dependencies=[])):
        with pytest.raises(ValueError):
            successor.array_shape(value)
    with pytest.raises(ValueError, match='duplicate JSON key'):
        successor.decode(b'{"one":1,"one":2}')
    with pytest.raises(ValueError, match='nonfinite'):
        successor.decode(b'{"one":NaN}')
