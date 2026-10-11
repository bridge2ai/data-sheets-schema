"""Root-only corruption/relocation controls of the actual metadata verifier."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from verify import FORMS, encoded, hash_fields, verify_release

CASES = ['complete', 'relocated_without_acquisition', 'missing_artifact',
         'changed_dataset_bytes', 'changed_sidecar_dataset_digest',
         'missing_full_raw_source', 'false_to_zero_source',
         'repository_path_escape', 'omitted_required_artifact',
         'changed_historical_locator', 'changed_acquisition_alias',
         'changed_producer', 'changed_label', 'changed_source_order']


def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), **hash_fields(raw)}


def fixture(root):
    release = 'notes/release'
    directory = root / release
    directory.mkdir(parents=True)
    artifacts = []
    def put(relative, raw):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        artifacts.append({'path': relative, 'path_base': 'repository_root', **hash_fields(raw)})
        return relative
    schema = put(release + '/schema.yaml', b'fixture schema bytes\n')
    mapping = put(release + '/mapping.tsv', b'fixture mapping bytes\n')
    forms = []
    base_history = root.parent / 'unavailable-acquisition'
    for form in FORMS:
        historical = {k: str(root.parent / 'unavailable-acquisition' / form / k)
                      for k in ('input', 'dataset', 'report', 'sidecar', 'schema', 'mapping')}
        historical['schema'] = str(base_history / 'schema')
        historical['mapping'] = str(base_history / 'mapping')
        raw = json.dumps({'flag': False, 'items': ['first', 'first', 'second'], 'name': form + ' \u00e9 \U0001f9ec'}, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        paths = {'input': put(release + '/' + form + '/input.json', raw),
                 'dataset': put(release + '/' + form + '/dataset.yaml', ('id: ' + form + '\n').encode()),
                 'report': put(release + '/' + form + '/report.txt', b'fixture report\n')}
        def bound(path, role):
            return {'path': historical[role], **hash_fields((root / path).read_bytes())}
        sidecar = {'dataset': bound(paths['dataset'], 'dataset'), 'schema': bound(schema, 'schema'),
            'evidence': {'policy': 'root_default_route_dispositions_v1',
                'mapping': bound(mapping, 'mapping'), 'sources': [{'display_name': historical['input'],
                    'snapshot': {'kind': 'original_file', 'original_file': bound(paths['input'], 'input'),
                        'json_text': raw.decode(), 'serialization': hash_fields(raw),
                        'value_sha256': hashlib.sha256(encoded(json.loads(raw))).hexdigest()}}]}}
        paths['sidecar'] = put(release + '/' + form + '/sidecar.json', encoded(sidecar))
        forms.append({'form': form, 'historical': historical, **paths})
    producer = {'head': '1' * 40, 'tree': '2' * 40}
    label = 'fixture-release'
    core_paths = {row[k]: row['historical'][k] for row in forms
                  for k in ('dataset', 'report', 'sidecar', 'input')}
    inputs = [{'form': f['form'], 'staged': {'path': f['historical']['input'],
               **hash_fields((root / f['input']).read_bytes())},
               'original': {'path': str(base_history / 'original' / f['form']),
               **hash_fields((root / f['input']).read_bytes())}} for f in forms]
    publication = {'format': 'legacy4594_actual_cli_publication_release_v1', 'passed': True,
        'error': None, 'producer': producer, 'label': label, 'method': 'legacy_semantic_tsv',
        'policy': 'root_default_route_dispositions_v1', 'inputs': inputs,
        'artifacts': [{'path': historical, **hash_fields((root / path).read_bytes())}
                      for path, historical in core_paths.items()],
        'actual_executions': [{'form': f, 'exit_code': 0, 'error': None,
            'closure': {'owned_group_absent': True, 'signals': []}} for f in FORMS]}
    publication_path = put(release + '/publication.json', encoded(publication))
    relocated = [r['path'] for r in artifacts]
    index = {'format': 'legacy_evidence_relocation_index_v1', 'entries': [
        dict(r, historical_path='/unavailable/' + r['path'], historical_path_base='external_absolute')
        for r in artifacts]}
    histories = dict(core_paths, **{schema: str(base_history / 'schema'),
                                     mapping: str(base_history / 'mapping')})
    for entry in index['entries']:
        if entry['path'] in histories:
            entry['historical_path'] = histories[entry['path']]
        entry['historical_aliases'] = [i['original']['path'] for f, i in zip(forms, inputs)
                                        if f['input'] == entry['path']]
    index_path = put(release + '/relocation-index.json', encoded(index))
    manifest = {'format': 'legacy_semantic_evidence_release_v1', 'state': 'complete',
        'release_root': release, 'method': 'legacy_semantic_tsv', 'policy': 'root_default_route_dispositions_v1',
        'artifacts': artifacts, 'forms': forms, 'schema_snapshot': schema, 'mapping_snapshot': mapping,
        'relocation_index': index_path, 'relocated_artifacts': relocated,
        'publication_receipt': publication_path, 'producer': producer, 'label': label}
    (directory / 'manifest.json').write_bytes(encoded(manifest))
    return release, manifest


def refresh(root, manifest, paths):
    # Corrupt evidence deliberately while keeping its outer file hashes coherent,
    # so the actual inner binding/raw-evidence check, not just a hash check, runs.
    index_path = root / manifest['relocation_index']
    index = json.loads(index_path.read_bytes())
    for path in paths:
        fields = hash_fields((root / path).read_bytes())
        next(r for r in manifest['artifacts'] if r['path'] == path).update(fields)
        next(r for r in index['entries'] if r['path'] == path).update(fields)
    index_path.write_bytes(encoded(index))
    next(r for r in manifest['artifacts'] if r['path'] == manifest['relocation_index']).update(hash_fields(index_path.read_bytes()))


def main():
    assert sys.argv[1:] == ['--run']
    output = HERE / 'controls-result.json'
    assert not os.path.lexists(output)
    watched = [pin(HERE / name) for name in ('verify.py', 'controls.py', 'configuration.disabled.json')]
    results = []
    error = None
    try:
        with tempfile.TemporaryDirectory(prefix='legacy-evidence-metadata-controls-') as temp:
            base = Path(temp)
            for name in CASES:
                root = base / name
                root.mkdir()
                release, manifest = fixture(root)
                form = manifest['forms'][0]
                expected = None
                if name == 'relocated_without_acquisition':
                    moved = base / 'different-location'
                    shutil.copytree(root, moved)
                    shutil.rmtree(root)
                    root = moved
                    assert not (base / 'unavailable-acquisition').exists()
                elif name == 'missing_artifact':
                    (root / form['dataset']).unlink()
                    expected = 'missing repository artifact'
                elif name == 'changed_dataset_bytes':
                    (root / form['dataset']).write_bytes(b'id: changed\n')
                    expected = 'artifact hash mismatch'
                elif name in ('changed_sidecar_dataset_digest', 'missing_full_raw_source', 'false_to_zero_source', 'changed_source_order'):
                    sidecar = json.loads((root / form['sidecar']).read_bytes())
                    snapshot = sidecar['evidence']['sources'][0]['snapshot']
                    touched = [form['sidecar']]
                    if name == 'changed_sidecar_dataset_digest':
                        sidecar['dataset']['sha256'] = '0' * 64
                        expected = 'sidecar Dataset binding mismatch'
                    elif name == 'missing_full_raw_source':
                        snapshot.pop('json_text')
                        expected = 'missing full raw source text'
                    else:
                        source = json.loads((root / form['input']).read_bytes())
                        if name == 'changed_source_order':
                            source['items'].reverse()
                        else:
                            source['flag'] = 0
                        raw = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
                        (root / form['input']).write_bytes(raw)
                        snapshot['original_file'].update(hash_fields(raw))
                        snapshot['serialization'] = hash_fields(raw)
                        touched.append(form['input'])
                        pub_path = manifest['publication_receipt']
                        pub = json.loads((root / pub_path).read_bytes())
                        for row in pub['artifacts']:
                            if row['path'] == form['historical']['input']:
                                row.update(hash_fields(raw))
                        for role in ('original', 'staged'):
                            pub['inputs'][0][role].update(hash_fields(raw))
                        (root / pub_path).write_bytes(encoded(pub))
                        touched.append(pub_path)
                        if name == 'false_to_zero_source':
                            snapshot['json_text'] = raw.decode('utf-8')
                            expected = 'source parsed-value digest mismatch'
                        else:
                            expected = 'source snapshot raw bytes mismatch'
                    (root / form['sidecar']).write_bytes(encoded(sidecar))
                    pub_path = manifest['publication_receipt']
                    pub = json.loads((root / pub_path).read_bytes())
                    for row in pub['artifacts']:
                        if row['path'] == form['historical']['sidecar']:
                            row.update(hash_fields((root / form['sidecar']).read_bytes()))
                    (root / pub_path).write_bytes(encoded(pub))
                    if pub_path not in touched:
                        touched.append(pub_path)
                    refresh(root, manifest, touched)
                elif name in ('changed_historical_locator', 'changed_acquisition_alias'):
                    index_path = root / manifest['relocation_index']
                    index = json.loads(index_path.read_bytes())
                    row = next(r for r in index['entries'] if r['path'] == form['input'])
                    if name == 'changed_historical_locator':
                        row['historical_path'] = '/different/acquisition'
                        expected = 'required historical locator mismatch'
                    else:
                        row['historical_aliases'] = ['/different/original']
                        expected = 'required acquisition alias mismatch'
                    index_path.write_bytes(encoded(index))
                    next(r for r in manifest['artifacts'] if r['path'] == manifest['relocation_index']).update(hash_fields(index_path.read_bytes()))
                elif name == 'changed_producer':
                    manifest['producer'] = dict(manifest['producer'], head='3' * 40)
                    expected = 'publication producer binding'
                elif name == 'changed_label':
                    manifest['label'] = 'different-release'
                    expected = 'publication label/method/policy binding'
                elif name == 'repository_path_escape':
                    manifest['artifacts'][0]['path'] = release + '/../escape'
                    expected = 'escaping repository locator'
                elif name == 'omitted_required_artifact':
                    manifest['artifacts'] = [r for r in manifest['artifacts'] if r['path'] != form['dataset']]
                    expected = 'required artifact omitted'
                try:
                    result = verify_release(root, release, manifest=manifest)
                except ValueError as exc:
                    assert expected is not None and str(exc) == expected, (name, str(exc), expected)
                else:
                    assert expected is None and result['passed'], (name, expected)
                results.append({'name': name, 'passed': True, 'expected_refusal': expected})
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        changed = [row['path'] for row in watched if pin(row['path']) != row]
        passed = error is None and not changed and [r['name'] for r in results] == CASES
        result = {'passed': passed, 'cases': results, 'error': error, 'watched_pins': watched,
            'preserved': not changed, 'changed': changed,
            'scope': 'Synthetic metadata corruption and relocation only; no project/schema/application acceptance.'}
        with output.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps({'passed': passed, 'cases': len(results), 'error': error}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
