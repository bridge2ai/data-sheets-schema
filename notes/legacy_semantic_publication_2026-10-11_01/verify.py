"""Verify a relocated legacy publication evidence package using stdlib only.

This checks copied artifacts and their preserved publication identities. It does
not regenerate records, rerun LinkML, or authenticate scientific assertions.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

LIMIT = 16 * 1024 * 1024
FORMS = ('CHORUS', 'VOICE', 'CM4AI_reduced', 'VOICE_provenance', 'CM4AI_original')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def local_path(repository, value):
    require(type(value) is str and value != '', 'invalid repository locator')
    pure = PurePosixPath(value)
    require(not pure.is_absolute() and '\\' not in value
            and all(p not in ('', '.', '..') for p in value.split('/')),
            'escaping repository locator')
    root = Path(repository).resolve()
    path = root.joinpath(*pure.parts)
    require(path.resolve() == path and path.is_relative_to(root), 'symlink repository locator')
    require(path.is_file(), 'missing repository artifact')
    return path


def file_bytes(path):
    require(path.stat().st_size <= LIMIT, 'artifact exceeds16MiB')
    raw = path.read_bytes()
    require(len(raw) <= LIMIT, 'artifact exceeds16MiB')
    return raw


def hash_fields(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked_artifact(repository, row):
    require(row.get('path_base') == 'repository_root', 'artifact path base')
    raw = file_bytes(local_path(repository, row['path']))
    require(hash_fields(raw) == {k: row[k] for k in ('bytes', 'sha256')}, 'artifact hash mismatch')
    return raw


def verify_release(repository, release, *, manifest=None, expected_state='complete'):
    root = Path(repository).resolve()
    if manifest is None:
        manifest = json.loads(file_bytes(local_path(root, release + '/manifest.json')))
    require(manifest['format'] == 'legacy_semantic_evidence_release_v1', 'manifest format')
    require(manifest['state'] == expected_state and manifest['release_root'] == release, 'manifest state/root')
    require(manifest['method'] == 'legacy_semantic_tsv'
            and manifest['policy'] == 'root_default_route_dispositions_v1', 'method/policy')
    rows = manifest['artifacts']
    require(type(rows) is list and 20 <= len(rows) <= 200, 'artifact roster bound')
    by_path, raw_by_path = {}, {}
    for row in rows:
        require(row['path'].startswith(release + '/'), 'artifact outside release')
        require(row['path'] not in by_path, 'duplicate artifact locator')
        by_path[row['path']] = row
        raw_by_path[row['path']] = checked_artifact(root, row)
    def member(path):
        require(path in raw_by_path, 'required artifact omitted')
        return raw_by_path[path]
    def historic_pin(path, historical):
        require(type(historical) is str and historical.startswith('/'), 'historical acquisition locator')
        return {'path': historical, **hash_fields(member(path))}
    publication = json.loads(member(manifest['publication_receipt']))
    require(publication['format'] == 'legacy4594_actual_cli_publication_release_v1'
            and publication['passed'] is True and publication['error'] is None,
            'publication completion binding')
    require(manifest['producer'] == publication['producer'], 'publication producer binding')
    require(all(manifest[k] == publication[k] for k in ('label', 'method', 'policy')),
            'publication label/method/policy binding')
    executions = publication['actual_executions']
    require([row['form'] for row in executions] == list(FORMS)
            and all(row['exit_code'] == 0 and row['error'] is None
                    and row['closure']['owned_group_absent'] is True
                    and row['closure']['signals'] == [] for row in executions),
            'publication natural closure binding')
    recorded_artifacts = {row['path']: row for row in publication['artifacts']}
    recorded_inputs = {row['form']: row for row in publication['inputs']}
    expected_locators = {}
    forms = manifest['forms']
    require([row['form'] for row in forms] == list(FORMS), 'five form order')
    checked = []
    for form in forms:
        for key in ('dataset', 'report', 'sidecar', 'input'):
            historical = form['historical'][key]
            actual_pin = historic_pin(form[key], historical)
            require(recorded_artifacts.get(historical) == actual_pin,
                    'publication core artifact binding')
            aliases = []
            if key == 'input':
                acquired = recorded_inputs[form['form']]
                require(acquired['staged'] == actual_pin, 'publication staged input binding')
                require({k: acquired['original'][k] for k in ('bytes', 'sha256')}
                        == hash_fields(member(form[key])), 'original acquisition bytes binding')
                aliases = [acquired['original']['path']]
            expected_locators[form[key]] = (historical, aliases)
        for key in ('schema', 'mapping'):
            local = manifest[key + '_snapshot']
            expected = (form['historical'][key], [])
            require(local not in expected_locators or expected_locators[local] == expected,
                    'inconsistent snapshot locator')
            expected_locators[local] = expected
        data = member(form['dataset'])
        member(form['report'])
        source = member(form['input'])
        sidecar = json.loads(member(form['sidecar']))
        require(sidecar['dataset'] == historic_pin(form['dataset'], form['historical']['dataset']),
                'sidecar Dataset binding mismatch')
        require(sidecar['schema'] == historic_pin(manifest['schema_snapshot'], form['historical']['schema']),
                'sidecar schema binding mismatch')
        evidence = sidecar['evidence']
        require(evidence['policy'] == manifest['policy'], 'sidecar policy mismatch')
        require(evidence['mapping'] == historic_pin(manifest['mapping_snapshot'], form['historical']['mapping']),
                'sidecar mapping binding mismatch')
        require(len(evidence['sources']) == 1, 'sidecar source count')
        occurrence = evidence['sources'][0]
        snapshot = occurrence['snapshot']
        require(occurrence['display_name'] == form['historical']['input'], 'source display locator')
        require(snapshot['kind'] == 'original_file'
                and snapshot['original_file'] == historic_pin(form['input'], form['historical']['input']),
                'source snapshot file binding')
        require(type(snapshot.get('json_text')) is str, 'missing full raw source text')
        require(snapshot['json_text'].encode('utf-8') == source, 'source snapshot raw bytes mismatch')
        require(snapshot['serialization'] == hash_fields(source), 'source serialization binding')
        require(snapshot['value_sha256'] == hashlib.sha256(encoded(json.loads(source))).hexdigest(),
                'source parsed-value digest mismatch')
        checked.append({'form': form['form'], 'dataset': hash_fields(data),
                        'full_source_bytes': len(source), 'sidecar': hash_fields(member(form['sidecar']))})
    relocation = json.loads(member(manifest['relocation_index']))
    require(relocation['format'] == 'legacy_evidence_relocation_index_v1', 'relocation index format')
    seen = set()
    for row in relocation['entries']:
        require(row['path_base'] == 'repository_root', 'relocation path base')
        require(row['path'] not in seen, 'duplicate relocation entry')
        seen.add(row['path'])
        raw = member(row['path'])
        require(hash_fields(raw) == {k: row[k] for k in ('bytes', 'sha256')}, 'relocation hash mismatch')
        require(row['historical_path_base'] == 'external_absolute'
                and type(row['historical_path']) is str and row['historical_path'].startswith('/'),
                'relocation historical role')
        if row['path'] in expected_locators:
            expected_history, expected_aliases = expected_locators[row['path']]
            require(row['historical_path'] == expected_history,
                    'required historical locator mismatch')
            require(row.get('historical_aliases', []) == expected_aliases,
                    'required acquisition alias mismatch')
    require(seen == set(manifest['relocated_artifacts']), 'relocation roster mismatch')
    required_local = {manifest['schema_snapshot'], manifest['mapping_snapshot']}
    for form in forms:
        required_local.update(form[k] for k in ('dataset', 'report', 'sidecar', 'input'))
    require(required_local <= seen, 'required local join absent')
    return {'passed': True, 'scope': 'Saved-byte integrity and complete local joins; no regeneration or new schema/scientific claim.',
            'forms': checked, 'artifacts_checked': len(rows), 'relocation_entries': len(seen),
            'external_paths_dereferenced': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--release', required=True)
    args = parser.parse_args()
    print(json.dumps(verify_release(args.repository, args.release), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
