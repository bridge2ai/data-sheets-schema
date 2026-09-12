"""Audit registered reference outputs and original attempts without model calls."""
import json
import sys
from pathlib import Path
from datetime import datetime

root = Path.cwd()
sys.path[:0] = [str(root / 'src'), str(root / 'scripts')]
import reference_rescore as r

m = json.loads((r.PLAN / 'manifest.json').read_bytes())
r.verify_frozen(m)
r.require_canary(m, next(j for j in m['jobs'] if j['id'] != m['canary_id']))
canary = next(j for j in m['jobs'] if j['id'] == m['canary_id'])
canary_doc = json.loads((root / canary['output']).read_bytes())
names = [(e['id'], e['name']) for e in canary_doc['elements']]
sub_names = [(e['id'], s['name']) for e in canary_doc['elements'] for s in e['sub_elements']]
assert len(sub_names) == 50
rubric_text = ' '.join((root / m['instruments'][canary['rubric']]['rubric']).read_text().split()).casefold()
assert all(' '.join(name.split()).casefold() in rubric_text for _, name in sub_names)
ratings = []
calls = []
intervals = []
for j in m['jobs']:
    target = root / j['output']
    originals = []
    for p in (r.PLAN / 'attempts' / j['id']).glob('*/prompt.txt'):
        source = p.parent
        receipt_path = source / 'receipt.json'
        if not receipt_path.exists():
            continue
        rec = json.loads(receipt_path.read_bytes())
        assert p.read_bytes() == r.job_prompt(m, j).encode(), j['id']
        assert r.digest(p) == rec['user_prompt_sha256']
        assert rec['system_prompt_sha256'] == m['instruments'][j['rubric']]['definition_sha256']
        trace = [json.loads(line) for line in (source / 'transcript.jsonl').read_text().splitlines() if line.strip()]
        results = [e for e in trace if e.get('type') == 'result']
        cost = results[0].get('total_cost_usd') if len(results) == 1 else None
        calls.append({'job_id': j['id'], 'source': str(source.relative_to(root)),
                      'status': rec['status'], 'original_error': rec.get('error'),
                      'evaluator_validation_succeeded': r.evaluator_validated(trace, j['rubric']),
                      'cli_reported_cost_usd': cost})
        intervals.extend([(datetime.fromisoformat(rec['started_at']), 1),
                          (datetime.fromisoformat(rec['completed_at']), -1)])
        candidate = source / 'candidate.json'
        if target.exists() and candidate.exists() and candidate.read_bytes() == target.read_bytes():
            originals.append((source, trace))
    if not target.exists():
        continue
    receipt = r.successful_receipt(m, j)
    assert len(originals) == 1, (j['id'], 'ambiguous original evidence')
    source, trace = originals[0]
    evidence = r.validate_candidate(target, j, m, trace)
    assert evidence['evaluation_sha256'] == receipt['evaluation_sha256']
    doc = json.loads(target.read_bytes())
    if j['rubric'] == 'rubric10-semantic':
        assert [(e['id'], e['name']) for e in doc['elements']] == names, j['id']
        assert [(e['id'], s['name']) for e in doc['elements'] for s in e['sub_elements']] == sub_names, j['id']
    ratings.append({'job_id': j['id'], 'output': j['output'],
                    'evaluation_sha256': r.digest(target), 'original_attempt': str(source.relative_to(root)),
                    'definition_sha256': evidence['definition_sha256'], 'overall_score': doc['overall_score']})

active = peak = 0
for _, change in sorted(intervals):
    active += change
    peak = max(peak, active)
assert active == 0 and peak <= 4
for name in ('model_provenance_registration.json', 'model_provenance_fill_preservation.json',
             'canonical_validator_registration.json', 'canonical_validator_fill_preservation.json'):
    record = json.loads((r.PLAN / name).read_bytes())
    for rel, sha in {**record['retained_attempt_files'], **record['existing_outputs']}.items():
        assert r.digest(root / rel) == sha, rel
accepted_sources = {row['original_attempt'] for row in ratings}
for call in calls:
    call['accepted_source'] = call['source'] in accepted_sources
audit = {'audited_at': r.now(), 'manifest_sha256': r.digest(r.PLAN / 'manifest.json'),
         'accepted': len(ratings), 'planned': len(m['jobs']), 'actual_model_calls': len(calls),
         'model_call_unit': 'one isolated evaluator CLI session, which may contain multiple model/tool turns',
         'attempts_without_reported_cost': sum(c['cli_reported_cost_usd'] is None for c in calls),
         'excluded_original_attempts': sum(not c['accepted_source'] for c in calls),
         'cli_reported_total_cost_usd': round(sum(c['cli_reported_cost_usd'] or 0 for c in calls), 8),
         'peak_completed_session_concurrency': peak, 'prior_evaluations_unchanged': len(m['prior_evaluations']),
         'rubric10_source_aligned_headings_verified': True, 'ratings': ratings, 'original_calls': calls}
if '--complete' in sys.argv:
    assert len(ratings) == len(m['jobs']) == 56
    r.write_json(r.PLAN / 'completion_audit.json', audit)
print(json.dumps({k: v for k, v in audit.items() if k not in ('ratings', 'original_calls')}, indent=2))
