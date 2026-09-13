"""Completed accounting must cover every surviving evidence channel."""
import json
import pytest
import yaml

from data_sheets_schema import api_runner as api, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.mark.parametrize('evidence', ['abandoned', 'reasoning', 'journal_counters'])
def test_completed_return_checks_all_surviving_accounting(external, evidence):
    api.execute(external, client=FakeClient())
    prior = external.provenance_path.read_bytes()
    record = yaml.safe_load(prior)
    if evidence == 'abandoned':
        api._record_incomplete_stream(external, 'full', 1, '2026-09-12T00:00:00Z',
                                     {'usage': {'input_tokens': 99, 'output_tokens': 7}}, [])
    elif evidence == 'reasoning':
        extra = {'usage_id': 'later-reasoning', 'generation_id': ledger.generation_id(external),
                 'run_identity': ledger.run_identity(external), 'phase': 'full',
                 'output_tokens': 7, 'stop_reason': 'end_turn'}
        with api._reasoning_path(external).open('a') as stream:
            stream.write(json.dumps(extra) + '\n')
    else:
        path = ledger.ledger_path(external)
        current = json.loads(path.read_text())
        current['rows'][0]['output_tokens'] = record['api_usage'][0]['output_tokens'] + 100
        path.write_text(json.dumps(current))
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match='account|attempt|charge|reasoning'):
        api.execute(external, client=client)
    assert client.messages.calls == []
    assert external.provenance_path.read_bytes() == prior
