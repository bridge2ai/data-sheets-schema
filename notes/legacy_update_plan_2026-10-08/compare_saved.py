"""Compare two completed maintenance-plan replay arms using saved evidence only (stdlib)."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re

NAMES = ('CHORUS', 'VOICE', 'CM4AI_reduced', 'VOICE_provenance', 'CM4AI_original')
KINDS, ORDERS = ('packaged', 'hidden'), ('original', 'reversed')
MODES = ('ranked_primary', 'voice_provenance_primary')
IDS = dict(zip(NAMES, ('doi:10.18130/V3/XNBOPG', 'doi:10.13026/k81f-qr68',
    'doi:10.18130/V3/HIGT4C', 'ark:59853/b2ai-voice-dataset-feature-ppgs', 'doi:10.18130/V3/HIGT4C')))
SOURCE = "rai:dataReleaseMaintenancePlan"
LIMIT = 64 * 1024 * 1024


def check(ok, why):
    if not ok:
        raise ValueError(why)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def equal(a, b, why):
    check(canonical(a) == canonical(b), why)


def raw(path):
    check(path.is_file() and not path.is_symlink(), 'Not a regular evidence file')
    with path.open('rb') as handle:
        value = handle.read(LIMIT + 1)
    check(len(value) <= LIMIT, 'Evidence exceeds byte bound')
    return value


def sha(value):
    return hashlib.sha256(value).hexdigest()


def pin(path):
    value = raw(path)
    return {'bytes': len(value), 'sha256': sha(value)}


def pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def document(path):
    return json.loads(raw(path), object_pairs_hook=pairs,
                      parse_constant=lambda value: check(False, 'Nonfinite JSON'))


def local(directory, name):
    check(isinstance(name, str) and name and not Path(name).is_absolute(), 'Invalid captured relative name')
    path = directory / name
    check(directory in path.resolve().parents, 'Captured path escapes evidence directory')
    return path


def indexed(rows, fields, required):
    result = {}
    for row in rows:
        key = tuple(row[name] for name in fields)
        check(key not in result and row['status'] == 'recorded', 'Duplicate or failed evidence row')
        result[key] = row
    check(set(result) == set(required), 'Missing or unexpected evidence denominator')
    return result


def verify_arm(directory, replay, role, commit):
    d = document(directory / 'summary.json')
    check(d['format'] == 'legacy_update_plan_supplement_v1' and d['role'] == role and d['commit'] == commit, 'Wrong arm identity')
    equal(d['roster'], list(NAMES), 'Unexpected input roster')
    equal(d['expected'], {'records': 20, 'rankings': 4, 'merges': 8}, 'Unexpected denominator')
    equal(d['missing'], {'records': 0, 'rankings': 0, 'merges': 0}, 'Missing controls')
    check(d['errors'] == [] and d['gate_errors'] == [], 'Recorded collection errors')
    for key in ('collection_complete', 'inputs_preserved', 'replay_preserved', 'runtime_preserved', 'driver_preserved'):
        check(d[key] is True, 'Collection/preservation failed')
    check(d['scientific_eligibility'] is False and d['historical_publication'] is False, 'Unexpected acceptance claim')
    equal(d['preservation_before'], d['preservation_after'], 'Selected files changed')
    for name, identity in d['source_pins'].items():
        equal(identity, d['preservation_before'][name], 'Source preservation pin differs')
    for name, identity in d['replay_pins'].items():
        equal(pin(local(replay, name)), identity, 'Saved replay pin differs')
    old = document(replay / 'summary.json')
    for name, identity in old['code_sha256'].items():
        check(d['source_pins'][name]['sha256'] == identity, 'Replay/source declarations differ')
    for key in ('mapping', 'schema'):
        check(d['source_pins'][old[key]['path']]['sha256'] == old[key]['sha256'], 'Resource declarations differ')
    rows = indexed(d['rows'], ('input', 'implementation', 'order'), itertools.product(NAMES, KINDS, ORDERS))
    ranks = indexed(d['rankings'], ('implementation', 'order'), itertools.product(KINDS, ORDERS))
    merges = indexed(d['merges'], ('implementation', 'order', 'mode'), itertools.product(KINDS, ORDERS, MODES))
    for (name, kind, order), row in rows.items():
        previous = old['inputs'][name]['consumers'][kind][order]
        check(previous['parse'] == previous['build'] == 'PASS', 'Replay parse/build failed')
        check(sha(canonical(row['root'])) == previous['root_sha256'], 'Root binding differs')
        check(sha(canonical(row['record'])) == previous['record_sha256'], 'Record binding differs')
        equal(row['original_validation_errors'], previous['validation_errors'], 'Validation errors differ')
        equal(row['original_validation'], previous['validation'], 'Validation outcome differs')
        gate = row['gate']
        errors = previous['validation_errors']
        check(gate['status'] == ('refused' if errors else 'accepted'), 'Gate status and actual validator disagree')
        if errors:
            schema = old['schema']['sha256']
            expected = f'Dataset publication refused against data_sheets_schema_all.yaml (sha256 {schema}): ' + '; '.join(errors) + '.'
            equal(gate['exception'], {'type': 'data_sheets_schema.legacy_publication.PublicationError', 'message': expected, 'args': repr((expected,))}, 'Exact Dataset gate refusal differs')
        else:
            check(type(gate['bytes']) is int and gate['bytes'] > 0 and re.fullmatch('[0-9a-f]{64}', gate['sha256']), 'Invalid accepted-byte pin')
    for row in merges.values():
        equal(pin(local(directory, row['report']['path'])), {k: row['report'][k] for k in ('bytes', 'sha256')}, 'Merge report changed')
        check(row['gate']['status'] == 'refused' and row['gate']['exception']['type'] == 'data_sheets_schema.legacy_publication.PublicationError', 'Mixed merge gate outcome differs')
    return d, rows, ranks, merges


def normalized_report(text, row):
    check(text.count('ROOT IDENTITY SELECTION') == 1, 'Missing root identity report')
    check('Different written IDs do not assert entity equivalence.' in text, 'Missing identity limitation')
    check('it is not a source-coverage gain.' in text, 'Missing coverage limitation')
    lines = text.splitlines(keepends=True)
    disclosed = [json.loads(line) for line in lines if line.startswith('{')]
    equal(disclosed, row['root_identity_sources'], 'Report identity disclosure differs')
    result = []
    for line in lines:
        if line.startswith('{'):
            value = json.loads(line)
            # Exact paths were verified against the corresponding saved input.
            value['path'] = '<captured input>/' + Path(value['path']).name
            line = json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n'
        result.append(line)
    text, count = re.subn(r'^Generated: [^\n]+$', 'Generated: <observed timestamp>', ''.join(result), flags=re.M)
    check(count == 1, 'Missing observed timestamp')
    return text


def update_error(text):
    return repr(text) + ' is not valid under any of the given schemas in /updates'


def expected_record(left):
    expected = dict(left)
    if 'updates' in left:
        check(isinstance(left['updates'], str), 'Expected retained scalar maintenance fixture')
        expected['updates'] = {'update_details': left['updates']}
    return expected


def identity_disclosure(row, rows, replay):
    check(len(row['root_identity_sources']) == len(NAMES), 'Identity denominator differs')
    for i, evidence in enumerate(row['root_identity_sources']):
        name = NAMES[i]; root = rows[(name, row['implementation'], row['order'])]['root']
        prop = '@id' if name == 'VOICE_provenance' else 'identifier'
        expected = {'source': name, 'path': str(replay / 'inputs' / (name + ('.reversed' if row['order'] == 'reversed' else '') + '.json')),
            'selected_primary': i == row['primary_index'], 'id': IDS[name], 'source_property': prop, 'source_value': root[prop],
            'inputs': {key: {'present': key in root, 'value': root.get(key)} for key in ('identifier', '@id')},
            'different_written_id': IDS[name] != row['record']['id']}
        equal(evidence, expected, 'Raw root identity declaration changed')


def compare(args):
    paths = [path.resolve() for path in (args.baseline, args.candidate, args.baseline_replay, args.candidate_replay)]
    b, br, bk, bm = verify_arm(paths[0], paths[2], 'baseline', args.baseline_commit)
    c, cr, ck, cm = verify_arm(paths[1], paths[3], 'candidate', args.candidate_commit)
    check(args.baseline_commit != args.candidate_commit, 'Same comparison role')
    equal(b['runtime'], c['runtime'], 'Runtime declarations differ')
    equal(b['driver'], c['driver'], 'Supplement driver differs')
    changed = {name for name, identity in b['source_pins'].items() if c['source_pins'].get(name) != identity}
    allowed = {'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'} | {
        prefix + name + '.py' for prefix in ('src/fairscape_integration/utils/', '.claude/agents/scripts/')
        for name in ('d4d_builder', 'mapping_loader')}
    check(changed == allowed, 'Unexpected selected source/resource change')
    check(set(c['source_pins']) - set(b['source_pins']) == {'src/data_sheets_schema/legacy_update_plan.py'}, 'Unexpected new helper declaration')
    records = []
    for key, left in br.items():
        right = cr[key]
        equal(left['root'], right['root'], 'Selected root changed')
        check(left['record']['id'] == right['record']['id'] == IDS[key[0]], 'Root-ID changed')
        equal(expected_record(left['record']), right['record'], 'Change beyond maintenance construction')
        errors = left['original_validation_errors']
        if key[0] == 'VOICE_provenance':
            check('updates' not in left['record'] and SOURCE not in left['root'], 'Unexpected provenance maintenance value')
            expected_errors = errors
        else:
            equal(left['record']['updates'], left['root'][SOURCE], 'Original maintenance text did not match root')
            error = update_error(left['record']['updates'])
            check(errors.count(error) == 1, 'Expected exact maintenance construction error once')
            expected_errors = [value for value in errors if value != error]
        equal(expected_errors, right['original_validation_errors'], 'Other validation errors changed')
        check(left['gate']['status'] == right['gate']['status'], 'Individual gate acceptance changed')
        records.append({'input': key[0], 'implementation': key[1], 'order': key[2],
            'maintenance_constructed': key[0] != 'VOICE_provenance',
            'baseline_errors': len(errors), 'candidate_errors': len(expected_errors),
            'remaining_errors_sha256': sha(canonical(expected_errors)),
            'baseline_gate': left['gate']['status'], 'candidate_gate': right['gate']['status']})
    for key in bk:
        equal(bk[key], ck[key], 'Scores, ranks or source order changed')
    merges = []
    for key, left in bm.items():
        right = cm[key]
        for field in ('primary_index', 'primary_name', 'provenance', 'statistics'):
            equal(left[field], right[field], 'Merge selection/provenance/accounting changed')
        check(left['record']['id'] == right['record']['id'] == IDS[right['primary_name']], 'Merged ID changed')
        equal(expected_record(left['record']), right['record'], 'Other merge content changed')
        sources = left['provenance']['updates']
        check(len(sources) == 1, 'Maintenance provenance must select one complete source')
        selected = br[(sources[0], key[0], key[1])]
        equal(left['record']['updates'], selected['root'][SOURCE], 'Maintenance merge does not match selected source')
        # Compare actual inherited policy: non-null primary, else the first
        # non-null secondary in the fixed source order, without combining.
        order = [left['primary_name']] + [name for name in NAMES if name != left['primary_name']]
        available = [name for name in order if br[(name,key[0],key[1])]['root'].get(SOURCE) is not None]
        check(sources == available[:1], 'Existing whole-value primary/fallback policy changed')
        identity_disclosure(left, br, paths[2]); identity_disclosure(right, cr, paths[3])
        lb = raw(local(paths[0], left['report']['path'])).decode(); rb = raw(local(paths[1], right['report']['path'])).decode()
        equal(normalized_report(lb,left), normalized_report(rb,right), 'Unexpected full report change')
        le, re_ = left['gate']['exception'], right['gate']['exception']
        removal = '; ' + update_error(left['record']['updates'])
        check(le['message'].count(removal) == 1, 'Exact mixed-merge maintenance error missing')
        message = le['message'].replace(removal, '', 1)
        equal(re_, {'type': le['type'], 'message': message, 'args': repr((message,))}, 'Mixed merge refusal changed beyond maintenance shape')
        merges.append({'implementation': key[0], 'order': key[1], 'mode': key[2],
            'primary': right['primary_name'], 'maintenance_source': sources[0], 'statistics': right['statistics'],
            'baseline_report': left['report'], 'candidate_report': right['report'],
            'gate': 'refused', 'remaining_gate_sha256': sha(canonical(re_))})
    for arm_rows, arm_ranks, arm_merges in ((br,bk,bm),(cr,ck,cm)):
        for name in NAMES:
            ref = arm_rows[(name,'packaged','original')]
            for kind, order in itertools.product(KINDS,ORDERS):
                for field in ('root','record','gate','original_validation_errors'):
                    equal(ref[field], arm_rows[(name,kind,order)][field], 'Graph/implementation record divergence')
        for kind, order in itertools.product(KINDS,ORDERS):
            equal(arm_ranks[('packaged','original')]['rows'], arm_ranks[(kind,order)]['rows'], 'Graph/implementation rank divergence')
            for mode in MODES:
                ref = arm_merges[('packaged','original',mode)]; row = arm_merges[(kind,order,mode)]
                for field in ('record','provenance','statistics','primary_name','primary_index','gate'):
                    equal(ref[field],row[field], 'Graph/implementation merge divergence')
    return {'format': 'legacy_update_plan_comparison_v1', 'verified': True,
        'artifacts': {role: {'supplement': pin(paths[i] / 'summary.json'), 'replay': pin(paths[i+2] / 'summary.json')} for i,role in enumerate(('baseline','candidate'))},
        'commits': {'baseline':b['commit'],'candidate':c['commit']},
        'denominators': {'record_pairs':20,'ranking_pairs':4,'merge_pairs':8,'gates_per_arm':28},
        'records':records, 'ranking':bk[('packaged','original')]['rows'], 'merges':merges,
        'selected_replay_source_changes':sorted(changed),
        'new_source_declarations':sorted(set(c['source_pins'])-set(b['source_pins'])),
        'scientific_eligibility':False,'source_coverage_gain':False,'general_legacy_validity':False,
        'limits':['Saved-evidence comparison only; no producer, schema validator, scorer or merger executes here.',
            'Source/runtime declarations are compared, not reauthenticated from original paths.',
            'Prepared accepted-byte pins are recorded execution observations; complete records and refusal messages are compared directly.',
            'Full report normalization permits only verified input-path role changes and observed timestamps.',
            'Constructor compatibility does not establish scientific correctness, entity equivalence, exactMatch, none, or general publication validity.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'baseline-replay', 'candidate-replay', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--baseline-commit', required=True)
    parser.add_argument('--candidate-commit', required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    check(all(path.resolve().parent == out.parent for path in (args.baseline, args.candidate, args.baseline_replay, args.candidate_replay)),
          'Output must be a new sibling file of the four evidence directories')
    for path in (args.baseline, args.candidate, args.baseline_replay, args.candidate_replay, Path(__file__).resolve().parents[2]):
        protected = path.resolve()
        check(out != protected and protected not in out.parents and out not in protected.parents, 'Output overlaps protected evidence/source')
    check(not out.exists() and not args.output.is_symlink(), 'Output must be new')
    result = compare(args)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('xb') as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n')
    print(json.dumps({'verified': True, **result['denominators']}))


if __name__ == '__main__':
    main()
