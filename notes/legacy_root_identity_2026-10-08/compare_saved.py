"""Compare two completed root-ID replay arms using saved evidence only (stdlib)."""
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
ID_ERROR = "'id' is a required property in /"
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


def without_id(record):
    return {key: value for key, value in record.items() if key != 'id'}


def verify_arm(directory, replay, role, commit):
    d = document(directory / 'summary.json')
    check(d['format'] == 'legacy_root_identity_supplement_v1' and d['role'] == role and d['commit'] == commit, 'Wrong arm identity')
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


def normalize_report(text, row, baseline, candidate):
    if candidate:
        begin = text.index('\n\nROOT IDENTITY SELECTION\n')
        end = text.index('\nMERGE STATISTICS\n', begin)
        section = text[begin:end]
        check('Different written IDs do not assert entity equivalence.' in section, 'Missing identity limitation')
        check('it is not a source-coverage gain.' in section, 'Missing coverage limitation')
        disclosed = [json.loads(line) for line in section.splitlines() if line.startswith('{')]
        equal(disclosed, row['root_identity_sources'], 'Report identity disclosure differs')
        text = text[:begin] + text[end:]
        for label, key in (('Total unique D4D fields', 'total_unique_fields'), ('Fields from primary only', 'fields_from_primary')):
            old, new = f'{label}: {row["statistics"][key]}', f'{label}: {baseline["statistics"][key]}'
            check(text.count(old) == 1, 'Missing report construction statistic')
            text = text.replace(old, new)
        primary = row['primary_name']
        pattern = r'(' + re.escape(f'{row["primary_index"]+1}. {primary} (PRIMARY)') + r'\n   - Size: [^\n]+\n   - D4D fields contributed: )(\d+)'
        text, count = re.subn(pattern, lambda m: m[1] + str(int(m[2]) - 1), text)
        check(count == 1, 'Missing primary contribution line')
        check(text.count(f'  • id: {primary}\n') == 1, 'Missing identity contribution line')
        text = text.replace(f'  • id: {primary}\n', '')
        text, count = re.subn(r'General \((\d+) fields\):', lambda m: f'General ({int(m[1])-1} fields):', text)
        check(count == 1, 'Missing identity category')
    text, count = re.subn(r'^Generated: [^\n]+$', 'Generated: <observed timestamp>', text, flags=re.M)
    check(count == 1, 'Missing observed report timestamp')
    return text


def compare(args):
    paths = [path.resolve() for path in (args.baseline, args.candidate, args.baseline_replay, args.candidate_replay)]
    b, br, bk, bm = verify_arm(paths[0], paths[2], 'baseline', args.baseline_commit)
    c, cr, ck, cm = verify_arm(paths[1], paths[3], 'candidate', args.candidate_commit)
    check(args.baseline_commit != args.candidate_commit, 'Same comparison role')
    equal(b['runtime'], c['runtime'], 'Runtime declarations differ')
    equal(b['driver'], c['driver'], 'Supplement driver differs')
    changed = {name for name, identity in b['source_pins'].items() if c['source_pins'].get(name) != identity}
    allowed = {'data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv'} | {
        prefix + name + '.py'
        for prefix in ('src/fairscape_integration/utils/', '.claude/agents/scripts/')
        for name in ('d4d_builder', 'mapping_loader', 'informativeness_scorer', 'rocrate_merger')}
    check(changed == allowed, 'Unexpected source/resource declaration change')
    check(set(c['source_pins']) - set(b['source_pins']) == {'src/data_sheets_schema/legacy_root_identity.py'}, 'Unexpected new source declaration')
    records = []
    for key, left in br.items():
        right = cr[key]
        equal(left['root'], right['root'], 'Selected root changed')
        check('id' not in left['record'] and right['record']['id'] == IDS[key[0]], 'Unexpected constructed ID')
        equal(left['record'], without_id(right['record']), 'Non-ID record changed')
        check(left['original_validation_errors'].count(ID_ERROR) == 1, 'Missing baseline identity error')
        equal([e for e in left['original_validation_errors'] if e != ID_ERROR], right['original_validation_errors'], 'Non-ID validation errors changed')
        records.append({'input': key[0], 'implementation': key[1], 'order': key[2], 'id': right['record']['id'],
            'baseline_errors': len(left['original_validation_errors']), 'candidate_errors': len(right['original_validation_errors']),
            'remaining_errors_sha256': sha(canonical(right['original_validation_errors'])),
            'baseline_gate': left['gate']['status'], 'candidate_gate': right['gate']['status']})
    for key in bk:
        equal(bk[key], ck[key], 'Scores, ranks or source order changed')
    merge_checks = []
    for key, left in bm.items():
        right = cm[key]
        equal(left['primary_index'], right['primary_index'], 'Selected primary changed')
        equal(left['primary_name'], right['primary_name'], 'Selected primary name changed')
        check('id' not in left['record'] and right['record']['id'] == IDS[right['primary_name']], 'Merged ID not primary-only')
        equal(left['record'], without_id(right['record']), 'Non-ID merge record changed')
        check('id' not in left['provenance'] and right['provenance']['id'] == [right['primary_name']], 'ID provenance not primary-only')
        equal(left['provenance'], without_id(right['provenance']), 'Non-ID merge provenance changed')
        expected_stats = dict(left['statistics'])
        for name in ('fields_from_primary', 'total_unique_fields'):
            check(type(expected_stats[name]) is int, 'Invalid construction statistic')
            expected_stats[name] += 1
        equal(expected_stats, right['statistics'], 'Unexpected statistics change')
        check(left['root_identity_sources'] is None, 'Unexpected baseline identity report')
        check(len(right['root_identity_sources']) == len(NAMES), 'Identity disclosure denominator differs')
        for i, evidence in enumerate(right['root_identity_sources']):
            name = NAMES[i]; root = cr[(name, key[0], key[1])]['root']
            prop = '@id' if name == 'VOICE_provenance' else 'identifier'
            expected = {'source': name, 'path': str(paths[3] / 'inputs' / (name + ('.reversed' if key[1] == 'reversed' else '') + '.json')),
                'selected_primary': i == right['primary_index'], 'id': IDS[name], 'source_property': prop, 'source_value': root[prop],
                'inputs': {k: {'present': k in root, 'value': root.get(k)} for k in ('identifier', '@id')},
                'different_written_id': IDS[name] != right['record']['id']}
            equal(evidence, expected, 'Raw identity disclosure differs')
        lb = raw(local(paths[0], left['report']['path'])).decode(); rb = raw(local(paths[1], right['report']['path'])).decode()
        equal(normalize_report(lb, left, left, False), normalize_report(rb, right, left, True), 'Unexplained merge report change')
        le, re_ = left['gate']['exception'], right['gate']['exception']
        suffix = '; ' + ID_ERROR + '.'
        check(le['message'].endswith(suffix), 'Baseline mixed merge identity error missing')
        expected_message = le['message'][:-len(suffix)] + '.'
        equal(re_, {'type': le['type'], 'message': expected_message, 'args': repr((expected_message,))}, 'Mixed merge gate changed beyond ID')
        merge_checks.append({'implementation': key[0], 'order': key[1], 'mode': key[2], 'primary': right['primary_name'],
            'baseline_statistics': left['statistics'], 'candidate_statistics': right['statistics'],
            'baseline_report': left['report'], 'candidate_report': right['report'],
            'gate': 'refused', 'remaining_gate_sha256': sha(canonical(re_))})
    # Compare complete records/roots/errors/gates across implementations and graph order.
    for arm_rows, arm_ranks, arm_merges in ((br, bk, bm), (cr, ck, cm)):
        for name in NAMES:
            ref = arm_rows[(name, 'packaged', 'original')]
            for kind, order in itertools.product(KINDS, ORDERS):
                row = arm_rows[(name, kind, order)]
                for field in ('root', 'record', 'gate', 'original_validation_errors'):
                    equal(ref[field], row[field], 'Graph/implementation record divergence')
        for kind, order in itertools.product(KINDS, ORDERS):
            equal(arm_ranks[('packaged', 'original')]['rows'], arm_ranks[(kind, order)]['rows'], 'Graph/implementation ranking divergence')
            for mode in MODES:
                ref = arm_merges[('packaged', 'original', mode)]; row = arm_merges[(kind, order, mode)]
                for field in ('record', 'provenance', 'statistics', 'primary_name', 'primary_index', 'gate'):
                    equal(ref[field], row[field], 'Graph/implementation merge divergence')
    return {'format': 'legacy_root_identity_comparison_v1', 'verified': True,
        'artifacts': {role: {'supplement': pin(paths[i] / 'summary.json'), 'replay': pin(paths[i+2] / 'summary.json')} for i, role in enumerate(('baseline', 'candidate'))},
        'commits': {'baseline': b['commit'], 'candidate': c['commit']}, 'denominators': {'record_pairs': 20, 'ranking_pairs': 4, 'merge_pairs': 8, 'gates_per_arm': 28},
        'records': records, 'ranking': bk[('packaged', 'original')]['rows'], 'merges': merge_checks,
        'declared_source_changes': [name for name, identity in b['source_pins'].items() if c['source_pins'].get(name) != identity],
        'new_source_declarations': sorted(set(c['source_pins']) - set(b['source_pins'])),
        'scientific_eligibility': False, 'general_legacy_validity': False,
        'limits': ['Saved-evidence comparison; no producer, schema validator, scorer or merger executed here.',
            'Source/runtime declarations are compared, not reauthenticated from their original paths.',
            'Accepted Dataset-byte pins are saved producer observations; full records and preserved validation errors are compared directly.',
            'Report normalization permits only observed timestamp, the separately verified ID disclosure, and explicit construction-count deltas.',
            'No source-coverage, entity-equivalence, scientific-accuracy or general publication-validity conclusion.']}


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
