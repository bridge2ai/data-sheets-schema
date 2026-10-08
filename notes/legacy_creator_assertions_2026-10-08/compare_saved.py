"""Compare two completed Creator replay arms using saved evidence only (stdlib)."""
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
SOURCE = "author"
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
    check(d['format'] == 'legacy_creator_supplement_v1' and d['role'] == role and d['commit'] == commit, 'Wrong arm identity')
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


def author_evidence(root):
    value = root.get('author')
    return {'author_present': 'author' in root, 'nonnull': value is not None,
            'immediate_assertion_units': (0 if value is None else len(value) if isinstance(value, list) else 1),
            'raw_value': value}


def assertion_units(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def constructed_units(value):
    return [{'description': unit} if isinstance(unit, str) else unit for unit in assertion_units(value)]


def presence(roots, names, primary):
    indices = [primary] + [i for i in range(len(roots)) if i != primary]
    return {'format': 'legacy_author_source_presence_v1', 'status': 'measured', 'reason': None,
            'target': 'creators', 'source_property': 'author', 'root_scope': 'selected_root',
            'sources': [dict(source_index=i, processing_index=j, source_name=names[i],
                             selected_primary=i == primary, root_id=roots[i].get('@id'),
                             **author_evidence(roots[i])) for j, i in enumerate(indices)]}


def creator_errors(record):
    """Golden expectation only for this closed retained roster, not a validator."""
    result = []
    for i, unit in enumerate(record.get('creators', [])):
        if isinstance(unit, dict) and set(unit) == {'description'}:
            check(isinstance(unit['description'], str), 'Unexpected constructed description')
        else:
            check(isinstance(unit, dict) and set(unit) == {'@id'}, 'Unexpected retained invalid assertion')
            result.append(f"Additional properties are not allowed ('@id' was unexpected) in /creators/{i}")
    return result


def is_creator_error(value):
    return re.search(r' in /creators(?:/|$)', value) is not None


def validate_error_delta(left, right, record):
    equal([e for e in left if not is_creator_error(e)],
          [e for e in right if not is_creator_error(e)], 'Unrelated validation errors changed')
    equal([e for e in right if is_creator_error(e)], creator_errors(record),
          'Reference-error count, type or position changed')


def without_creator(value):
    return {k: v for k, v in value.items() if k != 'creators'}


def gate_errors(row, schema_sha):
    errors = row['schema_errors']
    check(errors, 'Mixed retained merge unexpectedly valid')
    message = f'Dataset publication refused against data_sheets_schema_all.yaml (sha256 {schema_sha}): ' + '; '.join(errors) + '.'
    equal(row['gate']['exception'], {'type': 'data_sheets_schema.legacy_publication.PublicationError',
                                    'message': message, 'args': repr((message,))},
          'Exact merged gate refusal differs from complete schema errors')


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


def normalize_report(text, row):
    check(text.count('ROOT IDENTITY SELECTION') == 1, 'Missing root identity report')
    lines, identities = [], []
    for line in text.splitlines(keepends=True):
        if line.startswith('{'):
            value = json.loads(line)
            if 'path' in value:
                identities.append(value)
                value['path'] = '<captured input>/' + Path(value['path']).name
                line = json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n'
        lines.append(line)
    # Copies of the parsed dictionaries were normalized above. Compare the
    # unmodified report declarations independently against the captured ledger.
    original = [json.loads(line) for line in text.splitlines() if line.startswith('{')]
    equal([x for x in original if 'path' in x], row['root_identity_sources'], 'Report identity disclosure differs')
    normalized, count = re.subn(r'^Generated: [^\n]+$', 'Generated: <observed timestamp>', ''.join(lines), flags=re.M)
    check(count == 1, 'Missing or duplicate timestamp')
    return normalized


def compare_reports(left_dir, left, right_dir, right):
    before = raw(local(left_dir, left['report']['path'])).decode()
    after = raw(local(right_dir, right['report']['path'])).decode()
    before = normalize_report(before, left)
    after = normalize_report(after, right)
    check(before.count('D4D fields contributed:') == len(NAMES), 'Baseline contribution labels differ')
    check(before.count('Total unique D4D fields:') == 1, 'Baseline total label differs')
    before = before.replace('D4D fields contributed:', 'Constructed Dataset fields contributed:')
    before = before.replace('Total unique D4D fields:', 'Total constructed Dataset fields:')
    expected_lines = ['', 'ROOT AUTHOR SOURCE PRESENCE', '-' * 80,
        'Immediate assertion units are not people, unique facts or validation successes.',
        'Route creators <- author: measured',
        *(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in right['source_presence']['sources']), '',
        '', 'CREATOR ASSERTION CONSTRUCTION', '-' * 80,
        'All source assertion units retained in order; output ranges are half-open. Equal values do not establish one person.',
        *(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in right['creator_assertion_sources']), '']
    check(before.count('MERGE STATISTICS') == 1, 'Missing merge statistics boundary')
    expected = before.replace('MERGE STATISTICS', '\n'.join(expected_lines) + '\nMERGE STATISTICS', 1)
    equal(expected, after, 'Full report changed beyond verified labels, raw-source disclosures, paths and timestamp')


def compare(args):
    paths = [path.resolve() for path in (args.baseline, args.candidate, args.baseline_replay, args.candidate_replay)]
    b, br, bk, bm = verify_arm(paths[0], paths[2], 'baseline', args.baseline_commit)
    c, cr, ck, cm = verify_arm(paths[1], paths[3], 'candidate', args.candidate_commit)
    check(args.baseline_commit != args.candidate_commit, 'Same comparison role')
    equal(b['runtime'], c['runtime'], 'Runtime declarations differ')
    equal(b['driver'], c['driver'], 'Supplement driver differs')
    changed = {name for name, identity in b['source_pins'].items() if c['source_pins'].get(name) != identity}
    allowed = {'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv',
               'src/transformation/transform_api.py', 'src/fairscape_integration/cli.py',
               '.claude/agents/scripts/rocrate_to_d4d.py'} | {
        prefix + name + '.py' for prefix in ('src/fairscape_integration/utils/', '.claude/agents/scripts/')
        for name in ('d4d_builder', 'mapping_loader', 'rocrate_merger')}
    check(changed == allowed, 'Unexpected selected source/resource change')
    equal(sorted(set(c['source_pins']) - set(b['source_pins'])),
          ['src/data_sheets_schema/legacy_creators.py'], 'Unexpected new helper declaration')
    records = []
    for key, left in br.items():
        right = cr[key]
        equal(left['root'], right['root'], 'Selected root changed')
        equal(left['raw_author_evidence'], author_evidence(left['root']), 'Baseline raw author evidence differs')
        equal(left['raw_author_evidence'], right['raw_author_evidence'], 'Raw source author evidence changed')
        equal(without_creator(left['record']), without_creator(right['record']), 'Change beyond Creator construction')
        if left['root'].get('author') is None:
            check('creators' not in left['record'] and 'creators' not in right['record'], 'Absent author unexpectedly constructed')
        else:
            equal(left['record']['creators'], left['root']['author'], 'Historical retained author shape differs')
            equal(right['record']['creators'], constructed_units(left['root']['author']), 'Literal assertion construction differs')
        check(left['source_presence'] is None, 'Baseline unexpectedly has new measurement')
        equal(right['source_presence'], presence([right['root']], [key[0]], 0), 'Single raw source measurement differs')
        validate_error_delta(left['original_validation_errors'], right['original_validation_errors'], right['record'])
        check(left['gate']['status'] == right['gate']['status'], 'Individual gate acceptance changed')
        records.append({'input': key[0], 'implementation': key[1], 'order': key[2],
            'literal_units_constructed': sum(isinstance(x, str) for x in assertion_units(left['root'].get('author'))),
            'baseline_errors': len(left['original_validation_errors']),
            'candidate_errors': len(right['original_validation_errors']),
            'reference_errors_retained': len(creator_errors(right['record'])),
            'gate': right['gate']['status'], 'raw_author_evidence_sha256': sha(canonical(right['raw_author_evidence']))})
    for key in bk:
        equal(bk[key], ck[key], 'Scores, ranks or source order changed')
    merges = []
    for key, left in bm.items():
        right = cm[key]
        for field in ('primary_index', 'primary_name', 'statistics'):
            equal(left[field], right[field], 'Merge selection/accounting changed')
        equal(without_creator(left['record']), without_creator(right['record']), 'Other merged content changed')
        equal(without_creator(left['provenance']), without_creator(right['provenance']), 'Other merged provenance changed')
        roots = [cr[(name, key[0], key[1])]['root'] for name in NAMES]
        expected_presence = presence(roots, list(NAMES), right['primary_index'])
        equal(right['source_presence'], expected_presence, 'Merge raw source measurement differs')
        expected_units, expected_ranges, contributors = [], [], []
        for row in expected_presence['sources']:
            units = constructed_units(row['raw_value'])
            expected_ranges.append(dict(row, output_range=[len(expected_units), len(expected_units) + len(units)]))
            expected_units.extend(units)
            if row['nonnull']:
                contributors.append(row['source_name'])
        equal(right['record']['creators'], expected_units, 'Merged assertions reordered, changed or deduplicated')
        equal(right['creator_assertion_sources'], expected_ranges, 'Output range ledger differs')
        equal(right['provenance']['creators'], contributors, 'Creator source attribution differs')
        check(left['source_presence'] is None and left['creator_assertion_sources'] is None, 'Unexpected baseline new diagnostics')
        identity_disclosure(left, br, paths[2]); identity_disclosure(right, cr, paths[3])
        for arm, row in ((b, left), (c, right)):
            gate_errors(row, arm['source_pins']['src/data_sheets_schema/schema/data_sheets_schema_all.yaml']['sha256'])
        validate_error_delta(left['schema_errors'], right['schema_errors'], right['record'])
        # Filled against the actual reviewed renderer before any comparison run.
        compare_reports(paths[0], left, paths[1], right)
        merges.append({'implementation': key[0], 'order': key[1], 'mode': key[2],
            'primary': right['primary_name'], 'baseline_assertion_units': len(left['record']['creators']),
            'candidate_assertion_units': len(expected_units), 'reference_errors_retained': len(creator_errors(right['record'])),
            'statistics': right['statistics'], 'baseline_report': left['report'], 'candidate_report': right['report'],
            'gate': 'refused', 'candidate_gate_sha256': sha(canonical(right['gate']))})
    for arm_rows, arm_ranks, arm_merges in ((br, bk, bm), (cr, ck, cm)):
        for name in NAMES:
            ref = arm_rows[(name, 'packaged', 'original')]
            for kind, order in itertools.product(KINDS, ORDERS):
                for field in ('root', 'record', 'gate', 'original_validation_errors', 'raw_author_evidence', 'source_presence'):
                    equal(ref[field], arm_rows[(name, kind, order)][field], 'Graph/implementation record divergence')
        for kind, order in itertools.product(KINDS, ORDERS):
            equal(arm_ranks[('packaged', 'original')]['rows'], arm_ranks[(kind, order)]['rows'], 'Rank divergence')
            for mode in MODES:
                ref = arm_merges[('packaged', 'original', mode)]; row = arm_merges[(kind, order, mode)]
                for field in ('record', 'provenance', 'statistics', 'primary_name', 'primary_index', 'gate',
                              'schema_errors', 'source_presence', 'creator_assertion_sources'):
                    equal(ref[field], row[field], 'Graph/implementation merge divergence')
    return {'format': 'legacy_creator_comparison_v1', 'verified': True,
        'artifacts': {role: {'supplement': pin(paths[i] / 'summary.json'), 'replay': pin(paths[i+2] / 'summary.json')} for i, role in enumerate(('baseline', 'candidate'))},
        'commits': {'baseline': b['commit'], 'candidate': c['commit']},
        'denominators': {'record_pairs': 20, 'ranking_pairs': 4, 'merge_pairs': 8, 'gates_per_arm': 28},
        'records': records, 'ranking': bk[('packaged', 'original')]['rows'], 'merges': merges,
        'selected_replay_source_changes': sorted(changed), 'new_source_declarations': ['src/data_sheets_schema/legacy_creators.py'],
        'scientific_eligibility': False, 'source_coverage_gain': False, 'general_legacy_validity': False,
        'limits': ['Saved-evidence comparison only; no producer, validator, scorer or merger executes here.',
                  'Source/runtime pins are compared; they are not authenticated execution receipts.',
                  'Assertion units and retained duplicate references are not counts of distinct people.',
                  'Constructed field preservation does not establish exactMatch, none, scientific correctness or publication validity.']}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'baseline-replay', 'candidate-replay', 'baseline-source', 'candidate-source', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--baseline-commit', required=True)
    parser.add_argument('--candidate-commit', required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    check(all(path.resolve().parent == out.parent for path in (args.baseline, args.candidate, args.baseline_replay, args.candidate_replay)),
          'Output must be a new sibling file of the four evidence directories')
    for path in (args.baseline, args.candidate, args.baseline_replay, args.candidate_replay, args.baseline_source, args.candidate_source, Path(__file__).resolve()):
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
