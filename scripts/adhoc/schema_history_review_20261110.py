"""Inventory frozen April/November D4D schemas for the 2026-11-10 review.

Inputs: explicit Git revision plus label, or completed inventory JSONs.
Outputs: notes/schema_review_20261110/history_<label>.json and comparison JSON.
Uses one fixed installed SchemaView toolchain; no model calls or validation suite.
Extracted schema copies are disposable. Original tracked and untracked inputs stay intact.
Saved publication copies redact email-address strings only after counts, hashes
and comparisons are computed. Unredacted evidence stays in ignored local storage.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import tempfile
import re
import time
from urllib.request import Request, urlopen

import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.utils.schemaview import SchemaView

SCHEMA_DIR = 'src/data_sheets_schema/schema'
OUTPUT = Path(__file__).resolve().parents[2] / 'notes/schema_review_20261110'
RAW = Path(__file__).resolve().parents[2] / '.temp/schema-review-raw'
EMAIL = re.compile(r"(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@(?:[\w-]+\.)+[\w-]+(?![\w-])")
REDACTION = '[email address redacted]'
ROOTS = {'full': ('data_sheets_schema.yaml', 'Dataset'),
         'core': ('data_sheets_schema_core.yaml', 'CoreDataset')}
PROPERTIES = {'range', 'required', 'recommended', 'multivalued', 'inlined',
              'inlined_as_list', 'identifier', 'key', 'pattern', 'any_of',
              'all_of', 'none_of', 'exactly_one_of', 'minimum_cardinality',
              'maximum_cardinality', 'minimum_value', 'maximum_value',
              'slot_uri', 'exact_mappings', 'broad_mappings', 'close_mappings',
              'narrow_mappings', 'related_mappings', 'deprecated', 'annotations'}


def git(*args):
    return subprocess.check_output(['git', *args])


def plain(value):
    return json.loads(json.dumps(value, default=str))


def redact_email_strings(value):
    """Return a copy plus replacement count; never print matched addresses."""
    if isinstance(value, str):
        return EMAIL.subn(REDACTION, value)
    if isinstance(value, list):
        children = [redact_email_strings(item) for item in value]
        return [item for item, _ in children], sum(count for _, count in children)
    if isinstance(value, dict):
        result, count = {}, 0
        for key, item in value.items():
            clean_key, key_count = redact_email_strings(key)
            clean_item, item_count = redact_email_strings(item)
            if clean_key in result:
                raise ValueError('Email redaction would merge dictionary keys')
            result[clean_key] = clean_item
            count += key_count + item_count
        return result, count
    return value, 0


def retain_raw(target, raw_bytes):
    """Keep original bytes without replacing an existing historical copy."""
    RAW.mkdir(parents=True, exist_ok=True)
    ignore = RAW / '.gitignore'
    if not ignore.exists():
        ignore.write_text('*\n')
    candidate = RAW / target.name
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if candidate.exists() and candidate.read_bytes() != raw_bytes:
        candidate = RAW / f'{target.stem}.{digest}.json'
    if not candidate.exists():
        candidate.write_bytes(raw_bytes)
    if candidate.read_bytes() != raw_bytes:
        raise ValueError('Local raw evidence copy did not preserve the original bytes')
    git('check-ignore', str(candidate))
    return candidate, digest


def protected_evidence(value, path=()):
    """Independently select numeric/boolean evidence and SHA-256 strings."""
    if isinstance(value, dict):
        return {key: item for name, child in value.items()
                for key, item in protected_evidence(child, (*path, name)).items()}
    if isinstance(value, list):
        return {key: item for index, child in enumerate(value)
                for key, item in protected_evidence(child, (*path, index)).items()}
    if isinstance(value, (bool, int, float)) or (isinstance(value, str) and
                                               re.fullmatch('[0-9a-fA-F]{64}', value)):
        return {path: value}
    return {}


def write_public_json(target, value, original_bytes=None):
    """Redact only serialized evidence; source-byte identities stay original."""
    raw_bytes = original_bytes or (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
    raw_path, digest = retain_raw(target, raw_bytes)
    clean, count = redact_email_strings(value)
    # Every numeric, boolean and non-email string survives exactly; metadata
    # below describes only the publication copy and the retained raw JSON.
    clean['publication_redaction'] = {
        'email_address_replacements': count,
        'raw_json_sha256': digest,
        'raw_local_path': str(raw_path.relative_to(OUTPUT.parents[1])),
        'method': 'Email-address strings are redacted after counts, original-byte hashes and equality comparisons are computed. Recorded hashes and byte lengths refer to the original inputs, not redacted response text.'}
    target.write_text(json.dumps(clean, indent=2, ensure_ascii=False) + '\n')
    reloaded = json.loads(target.read_text())
    reloaded.pop('publication_redaction')
    expected, _ = redact_email_strings(value)
    if (reloaded != expected or EMAIL.search(target.read_text()) or
            protected_evidence(value) != protected_evidence(reloaded)):
        raise ValueError('Publication redaction verification failed')
    return count


def read_original_inventory(target):
    """Compare raw local evidence so email differences are not silently lost."""
    value = json.loads(target.read_text())
    metadata = value.get('publication_redaction')
    if not metadata:
        return value
    raw_path = (OUTPUT.parents[1] / metadata['raw_local_path']).resolve()
    if not raw_path.is_relative_to(RAW.resolve()):
        raise ValueError('Original evidence path escapes the local raw archive')
    raw_bytes = raw_path.read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != metadata['raw_json_sha256']:
        raise ValueError('Original evidence identity does not match the published metadata')
    return json.loads(raw_bytes)


def redact_existing():
    """Prepare existing evidence without rebuilding schemas or reading network."""
    names = ['history_comparison.json', 'history_current_2026_11_10.json',
             'history_generation_2026_04_10.json', 'history_hosted_snapshot13.json',
             'history_poster_2026_04_28.json']
    replacements = {}
    for name in names:
        target = OUTPUT / name
        original = target.read_bytes()
        value = json.loads(original)
        if 'publication_redaction' in value:
            if EMAIL.search(target.read_text()):
                raise ValueError('Already prepared publication copy contains an email address')
            replacements[name] = 0
            continue
        replacements[name] = write_public_json(target, value, original)
    print(json.dumps({'replacement_counts': replacements,
                      'total_replacements': sum(replacements.values())}, indent=2))


def fields(value):
    return {key: val for key, val in plain(json_dumper.to_dict(value)).items()
            if key in PROPERTIES}


def delta(old, new, path=()):
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(old.keys() | new.keys()):
            if key not in old:
                result.append({'path': [*path, key], 'change': 'added', 'after': new[key]})
            elif key not in new:
                result.append({'path': [*path, key], 'change': 'removed', 'before': old[key]})
            else:
                result.extend(delta(old[key], new[key], (*path, key)))
        return result
    return [] if old == new else [{'path': list(path), 'change': 'changed',
                                   'before': old, 'after': new}]


def inventory(revision, label):
    revision = git('rev-parse', revision).decode().strip()
    result = {'revision': revision, 'label': label,
              'toolchain': {name: version(name) for name in ['linkml-runtime', 'PyYAML']},
              'method': 'Imported source closure; class-induced fields include inheritance. Global slots and class attributes are separate declarations. Generated *_all.yaml files are hashed but do not add source definitions. Same installed SchemaView for each historical snapshot, not a historical-runtime recreation.',
              'files_sha256': {}, 'views': {}, 'source_attributes': {}}
    with tempfile.TemporaryDirectory(prefix='d4d-history-review-') as directory:
        folder = Path(directory)
        for path in git('ls-tree', '-r', '--name-only', revision, SCHEMA_DIR).decode().splitlines():
            if not path.endswith('.yaml'):
                continue
            content = git('show', f'{revision}:{path}')
            result['files_sha256'][path] = hashlib.sha256(content).hexdigest()
            if Path(path).name in {'digest_inventory.yaml', 'release_history.yaml'}:
                continue
            (folder / Path(path).name).write_bytes(content)
            if not path.endswith('_all.yaml'):
                source = yaml.safe_load(content)
                for cls, definition in source.get('classes', {}).items():
                    for slot, value in (definition or {}).get('attributes', {}).items():
                        result['source_attributes'][f'{Path(path).name}/{cls}/{slot}'] = value
        for kind, (filename, root) in ROOTS.items():
            view = SchemaView(str(folder / filename))
            classes = view.all_classes()
            all_fields = {name: {str(slot.name): fields(slot)
                                 for slot in view.class_induced_slots(name)}
                          for name in sorted(classes)}
            enums = {name: plain(json_dumper.to_dict(value))
                     for name, value in view.all_enums().items()}
            result['views'][kind] = {
                'version': str(view.schema.version) if view.schema.version else None,
                'classes': sorted(classes), 'root_fields': sorted(all_fields[root]),
                'required_root_fields': sorted(name for name, definition in all_fields[root].items()
                                               if definition.get('required')),
                'fields': all_fields,
                'enums': enums,
                'prefixes': {str(name): str(uri) for name, uri in view.namespaces().items()},
                'class_hierarchy': {name: {key: val for key, val in plain(json_dumper.to_dict(value)).items()
                                          if key in {'is_a', 'mixins', 'abstract', 'mixin', 'class_uri'}}
                                    for name, value in classes.items()},
                'counts': {'classes': len(classes), 'root_fields': len(all_fields[root]),
                           'enums': len(enums),
                           'enum_values': sum(len(value.get('permissible_values', {})) for value in enums.values()),
                           'global_slots': len(view.all_slots(attributes=False)),
                           'class_field_pairs': sum(map(len, all_fields.values()))}}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f'history_{label}.json'
    write_public_json(target, result)
    print(json.dumps({'path': str(target), 'revision': revision,
                      'views': {kind: {'version': data['version'], 'counts': data['counts'],
                                       'required_root_fields': data['required_root_fields']}
                                for kind, data in result['views'].items()}}, indent=2))


def compare(labels):
    records = {label: read_original_inventory(OUTPUT / f'history_{label}.json') for label in labels}
    result = {'method': 'Pairwise semantic/structural inventory comparison; inherited changes repeat per class.',
              'comparisons': {}}
    for old_label, new_label in zip(labels, labels[1:]):
        old, new = records[old_label], records[new_label]
        pair = {'old_revision': old['revision'], 'new_revision': new['revision'], 'views': {}}
        for kind in ROOTS:
            before, after = old['views'][kind], new['views'][kind]
            pair['views'][kind] = {
                'classes_added': sorted(set(after['classes']) - set(before['classes'])),
                'classes_removed': sorted(set(before['classes']) - set(after['classes'])),
                'root_fields_added': sorted(set(after['root_fields']) - set(before['root_fields'])),
                'root_fields_removed': sorted(set(before['root_fields']) - set(after['root_fields'])),
                'changes': delta({key: value for key, value in before.items() if key not in {'classes', 'root_fields', 'counts'}},
                                 {key: value for key, value in after.items() if key not in {'classes', 'root_fields', 'counts'}})}
        common = old['source_attributes'].keys() & new['source_attributes'].keys()
        pair['source_multivalued_true_lost'] = sorted(path for path in common
            if (old['source_attributes'][path] or {}).get('multivalued') is True
            and (new['source_attributes'][path] or {}).get('multivalued') is not True)
        pair['source_multivalued_true_added'] = sorted(path for path in common
            if (new['source_attributes'][path] or {}).get('multivalued') is True
            and (old['source_attributes'][path] or {}).get('multivalued') is not True)
        pair['source_scalarization_by_current_full_range'] = {}
        for path in pair['source_multivalued_true_lost']:
            _, cls, slot = path.split('/')
            definition = new['views']['full']['fields'].get(cls, {}).get(slot)
            group = definition.get('range', 'unspecified') if definition is not None else 'outside_full_closure'
            pair['source_scalarization_by_current_full_range'].setdefault(group, []).append(path)
        result['comparisons'][f'{old_label}..{new_label}'] = pair
    target = OUTPUT / 'history_comparison.json'
    write_public_json(target, result)
    print(json.dumps({'path': str(target), 'pairs': {key: {
        'views': {kind: {prop: value for prop, value in view.items() if prop != 'changes'}
                  for kind, view in value['views'].items()},
        'source_multivalued_true_lost_count': len(value['source_multivalued_true_lost']),
        'source_multivalued_true_added_count': len(value['source_multivalued_true_added'])}
        for key, value in result['comparisons'].items()}}, indent=2))


def capture_hosted():
    """Read public historical Synapse snapshot13; do not authenticate or mutate."""
    base = 'https://repo-prod.prod.sagebase.org/repo/v1/entity/syn68885644'
    def request(url, data=None):
        req = Request(url, data=json.dumps(data).encode() if data else None,
                      headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=20) as response:
            return response.status, json.load(response)
    _, versions = request(base + '/version?limit=100&offset=0')
    _, metadata = request(base + '/version/13')
    payload = {'concreteType': 'org.sagebionetworks.repo.model.table.QueryBundleRequest',
               'entityId': 'syn68885644', 'query': {'sql': 'SELECT * FROM syn68885644.13'},
               'partMask': 1}
    _, started = request(base + '/table/query/async/start', payload)
    token = started['token']
    for _ in range(10):
        status, result = request(base + '/table/query/async/get/' + token)
        if 'queryResult' in result:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('Public query did not complete within ten bounded polls')
    rowset = result['queryResult']['queryResults']
    headers = [header['name'] for header in rowset['headers']]
    files = {'B2AI_ORG:114': 'D4D_-_AI-READI_v4_human_readable.html',
             'B2AI_ORG:115': 'D4D_-_CHORUS_v4_human_readable.html',
             'B2AI_ORG:116': 'D4D_-_CM4AI_v4_human_readable.html',
             'B2AI_ORG:117': 'D4D_-_VOICE_v4_human_readable.html'}
    comparisons = []
    for row in rowset['rows']:
        values = dict(zip(headers, row['values']))
        name = 'datasheet-common.css' if values['content_type'] == 'css' else files[values['content_id']]
        path = 'src/html/output/' + name
        raw = git('show', 'e141852f532e6a0cea47992ffe9afc0f20a7c6a5:' + path)
        actual = values['content_text'].encode()
        comparisons.append({'path': path, 'rowId': row.get('rowId'), 'versionNumber': row.get('versionNumber'),
                            'git_sha256': hashlib.sha256(raw).hexdigest(),
                            'snapshot_sha256': hashlib.sha256(actual).hexdigest(),
                            'exact_match': raw == actual,
                            'consecutive_newlines_collapsed_match': re.sub(rb'\n{2,}', b'\n', raw) == actual,
                            'git_bytes': len(raw), 'snapshot_bytes': len(actual)})
    evidence = {'captured_on': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'versions_url': base + '/version?limit=100&offset=0',
                'query_payload': payload, 'versions': versions, 'metadata': metadata,
                'comparisons': comparisons, 'snapshot_query_result': result}
    target = OUTPUT / 'history_hosted_snapshot13.json'
    write_public_json(target, evidence)
    print(json.dumps({'path': str(target), 'metadata': metadata, 'comparisons': comparisons}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision')
    parser.add_argument('--label')
    parser.add_argument('--compare', nargs='+')
    parser.add_argument('--capture-hosted', action='store_true')
    parser.add_argument('--redact-existing', action='store_true')
    args = parser.parse_args()
    if args.redact_existing:
        redact_existing()
    elif args.capture_hosted:
        capture_hosted()
    elif args.compare:
        compare(args.compare)
    elif args.revision and args.label:
        inventory(args.revision, args.label)
    else:
        parser.error('Specify --revision and --label, or --compare labels')
