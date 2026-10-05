"""Actual public helper cycle over explicitly fictional omission declarations.

This is the same ordinary-Python peer and public execution used by the neutral
case. Observations, helper outputs, assembly and final gates are never replaced.
Scientific support, novelty and exhaustive recall remain unverified.
"""
from pathlib import Path

import yaml

from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_shared_contract as c
from tests.test_native_shared_execution import make_case, launch_case, assert_completed_case


def _report_only_correction(case):
    composition = c.strict_json(case['value']['composition_raw_json'].encode(),
                                max_bytes=c.HARD_LIMITS['request_bytes'])
    paths = composition['render_spec']['agentic_artifact_paths']
    draft = composition['policy']['native_shared_helpers']['draft']
    transcript = Path(case['value']['attempt_directory']) / 'transcript.jsonl'
    calls, results = {}, {}
    for line, raw in enumerate(transcript.read_bytes().splitlines()):
        event = c.strict_json(raw)
        for block in event.get('message', {}).get('content', []):
            if block['type'] == 'tool_use':
                assert block['id'] not in calls
                calls[block['id']] = (line, block)
            elif block['type'] == 'tool_result':
                assert block['tool_use_id'] not in results
                results[block['tool_use_id']] = (line, event)
    drafts = [(identity, line, block) for identity, (line, block) in calls.items()
              if block['name'] == 'Bash' and block['input']['command'] == draft]
    assert len(drafts) == 2
    assert [results[identity][1]['tool_use_result']['exitCode']
            for identity, _, _ in drafts] == [1, 0]
    writes = [(line, block['input']) for line, block in calls.values() if block['name'] == 'Write']
    report_writes = [(line, inputs) for line, inputs in writes if inputs['file_path'] == paths['report']]
    assert len(report_writes) == 2
    assert report_writes[0][1]['content'] != report_writes[1][1]['content']
    first_failure = results[drafts[0][0]][0]
    final_draft = drafts[1][1]
    assert [inputs['file_path'] for line, inputs in writes if first_failure < line < final_draft] == [paths['report']]
    assert [inputs['content'] for _, inputs in writes if inputs['file_path'] == paths['full']] == [case['full_raw'].decode()]
    assert [inputs['content'] for _, inputs in writes if inputs['file_path'] == paths['receipt']] == [case['receipt_raw'].decode()]
    assert Path(paths['full']).read_bytes() == case['full_raw']
    assert Path(paths['receipt']).read_bytes() == case['receipt_raw']


def test_actual_public_merged_omissions_and_all_chunk_statuses(tmp_path, monkeypatch):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'native26-omissions', fixture='omission')
    result = launch_case(case, monkeypatch)
    records = assert_completed_case(case, result)
    selection = case['selection']
    carry = c.strict_json(Path(selection.role('receipt_carry')).read_bytes())
    requests = [c.strict_json(Path(row['payload']['request']['path']).read_bytes(),
                              max_bytes=selection.bounds()['max_request_bytes'])['payload']
                for row in records if row['record_type'] == 'request_admitted']
    assert [request['cursor']['kind'] for request in requests] == [
        'receipt', 'worker', 'worker', 'worker', 'omission', 'integration']
    for request in requests[1:]:
        assert request['receipt_carry'] == carry
        assert len(request['receipt_carry']['unsupported_audit_candidates']) == 6
        assert request['generation_context'] == selection.generation_context()
        assert request['owner_context']['original_full_yaml'].encode() == case['full_raw']

    manifest = c.strict_json(Path(selection.document()['inputs']['chunk_manifest']['path']).read_bytes())
    original = yaml.safe_load(case['receipt_raw'])
    effective = yaml.safe_load(Path(selection.role('effective_receipt')).read_bytes())
    chunks = {row['id']: row for row in original['chunks']}
    assert len(chunks) == len(manifest['chunks']) == 3
    assert set(chunks) == {row['id'] for row in manifest['chunks']}
    assert {row['status'] for row in chunks.values()} == {'extracted', 'nothing_relevant', 'redundant_with'}
    assert effective['chunks'] == original['chunks']
    redundant = next(row for row in chunks.values() if row['status'] == 'redundant_with')
    assert len(redundant['chunks']) == 1
    assert chunks[redundant['chunks'][0]]['status'] == 'extracted'

    omission = next(row for row in records if row['record_type'] == 'response_consumed'
                    and row['payload']['cursor']['kind'] == 'omission')
    response = c.strict_json(Path(omission['payload']['response']['path']).read_bytes())
    assert {row['chunk'] for row in response['chunks']} == set(chunks)
    assert [row['status'] for row in response['chunks']].count('no_omission') == 2
    assert sum(len(row['candidates']) for row in response['chunks']) == 3

    assembly = c.strict_json(Path(selection.role('typed_assembly')).read_bytes(),
                             max_bytes=c.HARD_LIMITS['assembly_bytes'])
    lineage = assembly['lineage']['omission_candidates']
    assert len(lineage) == len({row['candidate']['id'] for row in lineage}) == 3
    retained = [row for row in lineage if row['disposition']['action'] == 'retain']
    dropped = [row for row in lineage if row['disposition']['action'] == 'drop']
    assert len(retained) == 2 and len(dropped) == 1
    assert len({row['final_finding_ordinal'] for row in retained}) == 1
    assert type(retained[0]['final_finding_ordinal']) is int
    assert dropped[0]['final_finding_ordinal'] is None
    assert dropped[0]['disposition']['reason'] and dropped[0]['disposition']['evidence']
    candidate = dropped[0]['candidate']
    assert {key: candidate[key] for key in ('source', 'chunk', 'quote')} in dropped[0]['disposition']['evidence']
    assert candidate['quote'] in Path(selection.document()['inputs']['bundle']['path']).read_text()
    for row in lineage:
        assert row['disposition']['candidate_id'] == row['candidate']['id']
    audit = yaml.safe_load(Path(selection.role('audit')).read_bytes())
    findings = [row for row in audit['findings'] if row['kind'] == 'omission']
    assert len(findings) == 1
    assert set(findings[0]['omission_candidates']) == {row['candidate']['id'] for row in retained}
    assert findings[0]['evidence']
    assert assembly['acceptance']['omission_counts']['retained'] == 2
    assert assembly['acceptance']['omission_counts']['dropped'] == 1
    assert assembly['acceptance']['scientific_support'] == 'unverified'
    _report_only_correction(case)
