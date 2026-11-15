"""Cold worker evidence checks for the run 43664211357 assembly stop."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import sys

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_callback_orchestration as preload
from tests.test_native_shared_callback_preloading import work, isolated_modules


def test_cold_callback_audit_acceptance_preserves_valid_source_evidence(isolated_modules, monkeypatch):
    dependencies = authority.dependency_identity()
    import data_sheets_schema
    monkeypatch.delitem(sys.modules, 'data_sheets_schema.anonymous_removals', raising=False)
    monkeypatch.delattr(data_sheets_schema, 'anonymous_removals', raising=False)
    raw = 'id: urn:synthetic:record\n'
    audit = {'findings': [], 'source_review': {
        'artifact': 'original_full',
        'sha256': hashlib.sha256(raw.encode()).hexdigest(),
        'values': [{'path': '/id', 'claims': [{
            'text': 'urn:synthetic:record', 'verdict': 'supported', 'attributed_to': [],
            'claim_status': 'fact', 'source_status': 'fact',
            'evidence': [{'source': 'source.txt', 'chunk': 'c1', 'quote': 'urn:synthetic:record'}],
            'reason': 'Explicit fictional identifier.',
        }]}],
    }}
    with ExitStack() as stack:
        stack.enter_context(preload.preloaded_classifier(dependencies))
        stack.enter_context(preload.preloaded_callback_utilities(dependencies))
        evidence = stack.enter_context(authority.loaded_verified_package_module(
            'data_sheets_schema.evidence_assertions',
            package_sources=dependencies['base']['package_sources']))
        # Match preloaded_callbacks: the worker guard is installed last, ahead
        # of every source loader, after all main-thread preload scopes enter.
        stack.enter_context(preload._worker_load_guard(dependencies))
        for kind in ('observer', 'classifier'):
            result = work(sys.modules['native_control'], kind, lambda: evidence.check_audit(
                audit, artifacts={'original_full': raw},
                chunks={'c1': {'source': 'source.txt', 'text': 'urn:synthetic:record'}}, protocol_version=7))
            assert not isinstance(result, BaseException), repr(result)
            assert result['findings'] == [], result
        invalid = deepcopy(audit)
        invalid['source_review']['values'][0]['claims'][0]['evidence'][0]['quote'] = 'Absent quote'
        refused = work(sys.modules['native_control'], 'observer', lambda: evidence.check_audit(
            invalid, artifacts={'original_full': raw},
            chunks={'c1': {'source': 'source.txt', 'text': 'urn:synthetic:record'}}, protocol_version=7))
        assert not isinstance(refused, BaseException), repr(refused)
        assert [item['kind'] for item in refused['findings']] == ['source_quote_not_found']
