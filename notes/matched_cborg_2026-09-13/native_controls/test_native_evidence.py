"""The independent native final check must use the registered evidence version."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import chunking
from run_native_canary import native_evidence_check


@pytest.mark.parametrize('version', [9, 10, 11])
@pytest.mark.parametrize('outcome', ['removed', 'retained', 'changed_anchor'])
def test_native_final_check_uses_registered_protocol_and_preserves_files(tmp_path, version, outcome):
    bundle = tmp_path/'bundle.txt'
    bundle.write_text('FILE: source.txt\nPATH: source.txt\nDocumented clinical records.\n')
    manifest = tmp_path/'chunks.yaml'
    manifest.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    evidence = tmp_path/'evidence';evidence.mkdir()
    original = {'instances': [{'instance_type': 'clinical record', 'counts': 12,
                              'data_substrate': 'urn:unsupported'}]}
    final = copy.deepcopy(original)
    if outcome != 'retained': final['instances'][0].pop('data_substrate')
    if outcome == 'retained': final['instances'][0]['notes'] = 'The source does not establish the relationship.'
    if outcome == 'changed_anchor': final['instances'][0]['counts'] = 13
    for variant in ['full', 'core']:
        (evidence/f'original_{variant}.yaml').write_text(yaml.safe_dump(original))
        (tmp_path/f'{variant}.yaml').write_text(yaml.safe_dump(final))
    (evidence/'audit.json').write_text(json.dumps({'findings': [{
        'severity': 'medium', 'record': 'full', 'slot': 'instances[0].data_substrate',
        'issue': 'Unsupported assignment',
        'evidence': [{'artifact': 'original_full', 'path': '/instances/0/data_substrate',
                     'op': 'contains', 'quote': 'urn:unsupported'}],
        'remove_relationship': {'path': '/instances/0/data_substrate'},
    }], 'summary': 'One medium finding.'}))
    report = tmp_path/'report.md'
    report.write_text('## Evidence assertions\n```json\n{"claims": []}\n```\n')
    spec = SimpleNamespace(metadata_dir=tmp_path, bundle=bundle, chunk_manifest=manifest,
        report_path=report, full_path=tmp_path/'full.yaml', core_path=tmp_path/'core.yaml',
        render_version=version)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    before = {p: sha(p) for p in tmp_path.rglob('*') if p.is_file()}
    result = native_evidence_check(spec)
    assert result['checked'] and result['assertions_checked'] == 1
    assert result['instrument'].startswith('evidence_assertions v' + ('2' if version == 11 else '1'))
    if version == 11 and outcome == 'removed':
        assert result['findings'] == []
    else:
        assert result['findings']
        if version == 11 and outcome == 'retained':
            assert result['findings'][0]['kind'] == 'unsupported_relationship_retained'
    assert before == {p: sha(p) for p in tmp_path.rglob('*') if p.is_file()}
