"""Verify final score bytes against their original successful evaluator Writes.

Run from the repository root with PYTHONPATH=src:scripts after the complete audit.
"""
import json
from pathlib import Path
import reference_rescore as r

audit = json.loads((r.PLAN / 'completion_audit.json').read_bytes())
assert audit['status'] == 'verified' and audit['accepted'] == audit['planned'] == 56
assert audit['manifest_sha256'] == r.digest(r.PLAN / 'manifest.json')
verified = []
for row in audit['ratings']:
    source = r.ROOT / row['original_attempt']
    events = [json.loads(line) for line in (source / 'transcript.jsonl').read_text().splitlines() if line.strip()]
    directories = [e.get('cwd') for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    assert len(directories) == 1 and isinstance(directories[0], str), row['job_id']
    expected_output = (Path(directories[0]) / 'output_evaluation.json').resolve()
    writes, completed = {}, []
    for event in events:
        message = event.get('message')
        if not isinstance(message, dict) or not isinstance(message.get('content'), list):
            continue
        for block in message['content']:
            if not isinstance(block, dict):
                continue
            if event.get('type') == 'assistant' and block.get('type') == 'tool_use' and block.get('name') == 'Write':
                args = block.get('input') or {}
                path = args.get('file_path')
                if isinstance(path, str) and Path(path).is_absolute() and Path(path).resolve() == expected_output:
                    assert isinstance(args.get('content'), str), row['job_id']
                    writes[block['id']] = args['content'].encode('utf-8')
            if event.get('type') == 'user' and block.get('type') == 'tool_result' and not block.get('is_error') and block.get('tool_use_id') in writes:
                completed.append(writes.pop(block['tool_use_id']))
    target = r.ROOT / row['output']
    assert completed and completed[-1] == target.read_bytes() == (source / 'candidate.json').read_bytes(), row['job_id']
    assert r.digest(target) == row['evaluation_sha256'], row['job_id']
    verified.append({k: row[k] for k in ['job_id', 'output', 'original_attempt', 'evaluation_sha256']})
result = {'verified_at': r.now(), 'manifest_sha256': audit['manifest_sha256'], 'accepted': len(verified),
          'verification': 'Every final output and retained candidate exactly matches the last successful absolute Write at the original isolated runtime output path.',
          'model_calls_during_verification': 0, 'ratings': verified}
r.write_json(r.PLAN / 'final_written_output_audit.json', result)
print('Verified all 56 final output byte sequences against their original successful evaluator Writes.')
