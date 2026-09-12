"""Write the dated completion record after the registered 56-rating audit.

Run from the repository root after the complete audit, report and Write audit.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

plan = Path('notes/reference_rescore_2026-09-11')
manifest = json.loads((plan / 'manifest.json').read_bytes())
audit = json.loads((plan / 'completion_audit.json').read_bytes())
results = json.loads((plan / 'results.json').read_bytes())
assert results['completed'] == results['planned'] == audit['accepted'] == audit['planned'] == 56
assert not results['pending'] and not audit['unresolved_attempts']
assert results['percentage_basis'] == 'computed_from_point_totals_and_denominators'
assert audit['cost_accounting_complete'] and audit['session_accounting_complete']
assert hashlib.sha256((plan / 'manifest.json').read_bytes()).hexdigest() == audit['manifest_sha256']
assert audit['prior_evaluations_unchanged'] == 202
assert len({j['input'] for j in manifest['jobs']}) == 24
assert sum(j['purpose'] == 'primary' for j in manifest['jobs']) == 48
assert all(r['ratings'] == 3 for r in results['repeatability'])
lines = [
    '# Pinned v7/v8 reference rescore completion', '',
    f"Recorded {datetime.now(timezone.utc).isoformat()} for #1248, #1080, #1062, #1327, #1335 and #1336.", '',
    'All 24 existing production D4Ds (v7 and v8, three generation replicates per project) now have both semantic rubric ratings: 48 primary ratings. Eight additional rubric10 ratings complete three independent ratings of v7 rep1 per project, for 56 accepted ratings. Each rating used its supplied D4D and pinned rubric resources in a fresh isolated session. No D4D generation or source download was performed.', '',
    f"The [completion audit](completion_audit.json) verifies {audit['actual_model_calls']} original evaluator CLI sessions, {audit['excluded_original_attempts']} preserved and excluded attempts, complete terminal usage evidence, a maximum concurrency of {audit['peak_completed_session_concurrency']}, and all 202 prior evaluations unchanged. CLI-reported usage totals ${audit['cli_reported_total_cost_usd']:.8f}, including excluded attempts and any auxiliary CLI-model usage. A session can contain multiple model/tool turns; this is not an API-request count or an independently reconciled bill. Codex review usage is outside this figure.", '',
    f"The final registered runner commit is `{manifest['definition_commit']}` and the manifest SHA256 is `{audit['manifest_sha256']}`. [Registration history](manifest.json) links the dated runner/reporting amendments. Complete scoring prompts, input bytes, rubrics, schemas and evaluator definitions stayed fixed through those amendments; existing accepted outputs were revalidated without rerating or editing their scores. Every accepted output passed the check-echo, runtime identity, exact-file schema validation, arithmetic and final-attestation checks.", '',
    'The [input audit](input_yaml_key_audit.json) confirms that all 24 frozen YAML inputs parse without duplicate mapping keys. The [write audit](final_written_output_audit.json) checks every accepted output byte-for-byte against its original successful evaluator Write.', '',
    'The quoted evaluator definition SHA256 values are:', '',
]
for rubric, instrument in manifest['instruments'].items():
    lines.append(f"- {rubric}: `{instrument['definition_sha256']}`")
lines += ['', 'The evaluator selector was `claude-opus-5[1m]`, effort `high`, temperature unspecified, with a $5 cap per attempt. The separately accepted CHORUS v7 rep1 rubric10 canary preceded the fill. Failed attempts and retry decisions remain in the dated plan and attempt directories.', '',
    '## Repeated-rating observations', '',
    'These are descriptive results for one v7 record per project under this exact rubric10 instrument. They do not estimate population uncertainty, and rubric20 repeatability remains unmeasured. Generation-replicate spread is reported separately in [results.md](results.md); the primary-rating arrays do not include the extra repeatability ratings. Small score differences do not establish a preferred run.', '',
    '| Project | Fixed percentages | N/A-adjusted percentages | Fixed sample SD | Adjusted sample SD | Fixed range | Adjusted range | Same applicability |',
    '|---|---|---|---|---|---|---|---|']
for r in results['repeatability']:
    fixed_values = ', '.join(f'{v:.3f}' for v in r['fixed_percentages'])
    adjusted_values = ', '.join(f'{v:.3f}' for v in r['adjusted_percentages'])
    lines.append(f"| {r['project']} | {fixed_values} | {adjusted_values} | {r['fixed_sample_sd']:.3f} | {r['adjusted_sample_sd']:.3f} | {r['fixed_range']:.3f} | {r['adjusted_range']:.3f} | {r['applicability_stable']} |")
lines += ['', 'Table percentages, sample SDs and ranges are displayed to three decimal places; SDs and ranges are in percentage points. Calculations use the unrounded point ratios, and the JSON report retains their precision. The fixed maximum is 50 for rubric10 and 88 for rubric20. N/A-adjusted percentages use each rating\'s applicable maximum. The individual results retain excluded item identities; equal totals or maxima alone do not establish equivalent applicability. Neither score basis establishes rater reliability by itself.', '',
    '## Fractional historical ratings (#1062)', '',
    'The historical files remain unchanged. Their replacements are independent ratings under the current pinned integer-band instrument, not rounded versions of the old ratings. Every numeric rubric20 question score in the new 24-record set is integral.', '',
    '| Record | Historical total | Historical fractional questions | Fresh reference total | Fresh evaluation |',
    '|---|---|---|---|---|']
for project, rep in [('AI_READI', 2), ('VOICE', 3)]:
    oldpath = Path(f'data/evaluation_llm/rubric20_semantic/label_aware/{project}_2026-09-01api_rep{rep}_evaluation.json')
    old = json.loads(oldpath.read_bytes())
    cats = old['categories']
    qs = [q for c in (cats.values() if isinstance(cats, dict) else cats) for q in c['questions']]
    fractions = ', '.join(f"Q{q['id']}={q['score']}" for q in qs if isinstance(q.get('score'), float) and not q['score'].is_integer())
    job = next(j for j in manifest['jobs'] if j['id'] == f'{project}_v7_rep{rep}_r20_rating1')
    new = json.loads(Path(job['output']).read_bytes())
    s = new['overall_score']
    lines.append(f"| {project} v7 rep{rep} | {old['overall_score']['total_points']}/88 | {fractions} | {s['total_points']}/{s['max_points']} fixed; {s['total_points']}/{s['adjusted_max_points']} adjusted | [{job['id']}](../../{job['output']}) |")
for job in manifest['jobs']:
    if job['rubric'] != 'rubric20-semantic':
        continue
    doc = json.loads(Path(job['output']).read_bytes())
    cats = doc['categories']
    questions = [q for c in (cats.values() if isinstance(cats, dict) else cats) for q in c['questions']]
    assert len(questions) == 20
    assert all(q.get('score') is None or (type(q['score']) in (int, float) and float(q['score']).is_integer()) for q in questions), job['id']
lines += ['', 'This completion covers the registered manuscript reference evaluation. It does not certify a new generation release, resolve the separate general-user packaging and vocabulary issues, or change historical prediction verdicts on the basis of small score gaps.', '']
(plan / 'completion_summary.md').write_text('\n'.join(lines))
print(plan / 'completion_summary.md')
