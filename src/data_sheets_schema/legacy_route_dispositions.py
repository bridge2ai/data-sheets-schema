"""Finite default-route policy and recoverable assertions for legacy builders.

Only the explicit marker opts into this contract. Evidence is separate from
Dataset; neither declining a route nor constructing an object certifies a fact.
"""
from copy import deepcopy
import csv
from hashlib import sha256
import io
import json
from pathlib import Path

from .rocrate_map import _crate_json_from_bytes
from .rocrate_sources import select_root


MARKER = 'root_default_route_dispositions_v1'
FORMAT = 'legacy_route_dispositions_v1'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
# legacy field: (ordered predicates, output field, child, merge mode)
ROUTES = {
    'tasks': (('rai:dataUseCases',), 'tasks', 'response', 'concat'),
    'discouraged_uses': (('prohibitedUses',), 'discouraged_uses', 'discouragement_details', 'primary'),
    'future_use_impacts': (('rai:dataSocialImpact',), 'future_use_impacts', 'impact_details', 'concat'),
    'machine_annotation_analyses': (('rai:machineAnnotationTools',), 'machine_annotation_tools', 'tool_descriptions', 'primary'),
    'external_resource': (('associatedPublication',), 'external_resources', 'external_resources', 'concat'),
    'bytes': (('contentSize',), 'total_size_bytes', None, 'exact_size'),
    'encoding': (('evi:formats',), None, None, 'defer'),
    'existing_uses': (('rai:dataUseCases',), None, None, 'defer'),
    'other_tasks': (('rai:dataUseCases',), None, None, 'defer'),
    'data_protection_impacts': (('rai:dataSocialImpact',), None, None, 'defer'),
    'confidential_elements': (('rai:personalSensitiveInformation',), None, None, 'defer'),
    'ip_restrictions': (('license', 'conditionsOfAccess'), None, None, 'defer'),
    'extension_mechanism': (('license', 'conditionsOfAccess'), None, None, 'defer'),
    'version_access': (('version',), None, None, 'defer'),
}
EXACT_SIZE = 'evi:totalContentSizeBytes'


def _require(condition, message):
    if not condition:
        raise ValueError('Marked route evidence: ' + message)


def same(a, b):
    """JSON equality which does not equate bool, integer and float values."""
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def encoded(value):
    """The one declared evidence encoding, including escaped lone surrogates."""
    def check(v):
        if type(v) is dict:
            _require(all(type(k) is str for k in v), 'JSON keys must be strings')
            for item in v.values():
                check(item)
        elif type(v) is list:
            for item in v:
                check(item)
        else:
            _require(type(v) in (str, int, float, bool, type(None)), 'non-JSON assertion')
    check(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def _pin(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def _field(row):
    return (row.get('D4D Property') or '').strip()


def validate_rows(rows):
    """Validate all explicit rows and alias collisions before state changes."""
    selected = {}
    for row in rows:
        if (row.get('Func') or '').strip() != MARKER:
            continue
        field = _field(row)
        sources = tuple(p.strip() for p in (row.get('FAIRSCAPE RO-Crate Property') or '').split(','))
        matches = [r for r in rows if _field(r) == field and (r.get(COVERED) or '').strip() == '1']
        _require(field in ROUTES and sources == ROUTES[field][0]
                 and len(matches) == 1 and matches[0] is row,
                 'marker requires one covered row with its exact field and ordered sources')
        selected[field] = ROUTES[field]
    if selected:
        outputs = {}
        for row in rows:
            if (row.get(COVERED) or '').strip() != '1':
                continue
            field = _field(row)
            target = selected[field][1] if field in selected else field
            if target is not None:
                _require(target not in outputs, 'duplicate output target: ' + target)
                outputs[target] = field
    return selected


def capture_mapping(loader, raw, rows):
    """Retain bytes used by the loader, not a later read of its filename."""
    loader._route_mapping_capture = (str(Path(loader.tsv_path).resolve()), raw, deepcopy(rows))


def _mapping_state(rows):
    from .legacy_root_identity import MARKER as identity_marker
    mappings = [r for r in rows if r.get('D4D Property') and not r['D4D Property'].startswith('D4D:')]
    covered = [r for r in mappings if r.get(COVERED, '0').strip() == '1']
    forward, reverse, direct = {}, {}, set()
    for row in covered:
        field, source = _field(row), row.get('FAIRSCAPE RO-Crate Property', '').strip()
        if field and source:
            forward[field] = source
            for prop in source.split(','):
                prop = prop.strip()
                if prop:
                    if row.get('Func', '').strip() == identity_marker:
                        reverse.setdefault(prop, field)
                    else:
                        reverse[prop] = field
            if row.get('Direct mapping? Yes =1; No = 0', '0').strip() == '1':
                direct.add(field)
    return mappings, covered, forward, reverse, direct


def mapping_identity(loader):
    capture = getattr(loader, '_route_mapping_capture', None)
    _require(type(capture) is tuple and len(capture) == 3, 'loaded mapping capture required')
    path, raw, rows = capture
    _require(Path(loader.tsv_path).resolve() == Path(path) and Path(path).read_bytes() == raw,
             'mapping bytes changed after acquisition; load a new mapping')
    decoded = list(csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=None), delimiter='\t'))
    _require(same(rows, decoded), 'acquired mapping row snapshot differs')
    mappings, covered, forward, reverse, direct = _mapping_state(rows)
    _require(same(loader.mappings, mappings) and same(loader.covered_mappings, covered)
             and same(loader.d4d_to_rocrate, forward) and same(loader.rocrate_to_d4d, reverse)
             and type(loader.direct_mappings) is set and loader.direct_mappings == direct,
             'effective mapping state differs from acquired rows')
    fields = [_field(r) for r in covered if r.get('D4D Property')]
    _require(same(loader.get_covered_fields(), fields)
             and same(loader.get_d4d_to_rocrate_mapping(), forward)
             and same(loader.get_rocrate_to_d4d_mapping(), reverse), 'mapping getter differs')
    for field in fields:
        first = next(r for r in covered if _field(r) == field)
        _require(same(loader.get_mapping_info(field), first)
                 and same(loader.get_rocrate_property(field), forward.get(field))
                 and loader.is_direct_mapping(field) is (field in direct), 'mapping field getter differs')
    for prop, field in reverse.items():
        _require(loader.get_d4d_field(prop) == field, 'reverse mapping getter differs')
    _require(loader.get_all_mapped_rocrate_properties() == set(reverse), 'mapping property getter differs')
    return dict(_pin(raw), path=path)


def routes(loader):
    selected = validate_rows(getattr(loader, 'mappings', ()))
    # A removed or disabled marker in mutable rows must not erase the binding.
    capture = getattr(loader, '_route_mapping_capture', None)
    captured = validate_rows(capture[2]) if type(capture) is tuple and len(capture) == 3 else {}
    if selected or captured:
        mapping_identity(loader)
        _require(selected == captured, 'route policy differs after acquisition')
    return selected


def _graph(data):
    graph = data.get('@graph', [])
    return [graph] if type(graph) is dict else graph


def _root(data):
    graph = _graph(data)
    _require(type(graph) is list, 'graph must be a list or node object')
    root, reason = select_root(graph)
    _require(root is not None, 'no selected root: ' + reason)
    index = next(i for i, entity in enumerate(graph) if entity is root)
    pointer = '/@graph' if type(data.get('@graph')) is dict else '/@graph/' + str(index)
    return root, pointer


def source_snapshot(parser, *, raw=None, kind='original_file', parents=None, permutation=None, input_value=None):
    """Acquire a detached source, distinguishing actual and generated bytes.

    Adapters call this before deleting temporary inputs or reusing path labels.
    Generated snapshots carry their actual serialization, never an original-byte
    claim. Retained text permits later evidence validation after temp cleanup.
    """
    original = None
    if kind == 'original_file':
        capture = getattr(parser, '_route_source_capture', None)
        _require(type(capture) is tuple and len(capture) == 2, 'parser byte acquisition required')
        path, acquired = capture
        _require(raw is None and Path(path).read_bytes() == acquired, 'source bytes changed after parsing')
        raw = acquired
        original = dict(_pin(raw), path=path)
    else:
        _require(kind in ('generated_dict', 'generated_combined', 'declared_reordered_graph', 'declared_in_memory_graph'),
                 'unknown generated acquisition kind')
        if raw is None:
            raw = encoded(parser.rocrate_data)
    _require(type(raw) is bytes, 'source serialization must be bytes')
    data = _crate_json_from_bytes(raw, Path(str(parser.rocrate_path)))
    encoded(data)  # Nonfinite/non-JSON values are not transportable evidence.
    if kind == 'generated_dict':
        _require(type(input_value) is dict and same(input_value, data),
                 'generated dict serialization changed the supplied object')
        encoded(input_value)
    _require(same(data, parser.rocrate_data), 'source bytes do not match the current parser graph')
    root, pointer = _root(data)
    _require(same(root, parser.require_root_dataset()) and same(_graph(data), parser.graph),
             'parser root or entity view is stale')
    snapshot = {'kind': kind, 'serialization': _pin(raw), 'json_text': raw.decode('utf-8'),
                'original_file': original, 'root_pointer': pointer,
                'parents': deepcopy(parents or []), 'entity_origins': [],
                'value_sha256': sha256(encoded(data)).hexdigest(),
                'permutation': deepcopy(permutation)}
    if kind == 'declared_reordered_graph':
        _require(len(snapshot['parents']) == 1 and type(permutation) is list, 'reordering needs one parent and explicit indices')
        parent = _snapshot_data(snapshot['parents'][0])
        old, new = _graph(parent), _graph(data)
        _require(len(permutation) == len(old) == len(new)
                 and all(type(i) is int for i in permutation)
                 and sorted(permutation) == list(range(len(old))), 'invalid graph permutation')
        for new_index, old_index in enumerate(permutation):
            _require(same(new[new_index], old[old_index]), 'graph permutation changed an entity')
            snapshot['entity_origins'].append({'generated_index': new_index, 'parent_index': 0,
                                               'original_pointer': '/@graph' if type(parent.get('@graph')) is dict
                                               else '/@graph/' + str(old_index)})
    elif kind == 'generated_combined':
        entities, origins = [], []
        for parent_index, item in enumerate(snapshot['parents']):
            parent = _snapshot_data(item)
            for old_index, entity in enumerate(_graph(parent)):
                expected = deepcopy(entity)
                if type(expected) is dict and '@id' in expected:
                    # The adapter must declare the label it actually adds.
                    expected['_source'] = item['combined_source_label']
                origins.append({'generated_index': len(entities), 'parent_index': parent_index,
                                'original_pointer': '/@graph' if type(parent.get('@graph')) is dict
                                else '/@graph/' + str(old_index), 'generated_properties': ['_source']
                                if type(entity) is dict and '@id' in entity else []})
                entities.append(expected)
        _require(same(entities, _graph(data)), 'combined entities do not match explicit original occurrences')
        snapshot['entity_origins'] = origins
    _snapshot_data(snapshot)
    return snapshot


def _snapshot_data(snapshot):
    _require(snapshot['kind'] in ('original_file', 'generated_dict', 'generated_combined',
             'declared_reordered_graph', 'declared_in_memory_graph'), 'unknown snapshot kind')
    raw = snapshot['json_text'].encode('utf-8')
    _require(_pin(raw) == snapshot['serialization'], 'snapshot serialization changed')
    original = snapshot['original_file']
    if snapshot['kind'] not in ('generated_combined', 'declared_reordered_graph'):
        _require(snapshot['parents'] == [], 'this acquisition kind has no claimed parent transformation')
    if snapshot['kind'] != 'declared_reordered_graph':
        _require(snapshot['permutation'] is None, 'only a declared reordering may claim a permutation')
    _require((original is not None) == (snapshot['kind'] == 'original_file'), 'original/generated identity differs')
    if original is not None:
        _require(snapshot['kind'] == 'original_file' and _pin(raw) ==
                 {k: original[k] for k in ('bytes', 'sha256')}
                 and Path(original['path']).read_bytes() == raw, 'original source changed before staging')
    for parent in snapshot['parents']:
        _snapshot_data(parent)
    value = _crate_json_from_bytes(raw, Path(original['path'] if original else '<generated>'))
    _require(sha256(encoded(value)).hexdigest() == snapshot['value_sha256'], 'source value digest differs')
    expected_origins = []
    if snapshot['kind'] == 'generated_combined':
        combined = []
        for parent_index, parent in enumerate(snapshot['parents']):
            data = _snapshot_data(parent)
            _require(type(parent.get('original_index')) is int and parent['original_index'] >= 0
                     and parent.get('occurrence_id') == 'input:' + str(parent['original_index']),
                     'combined parent occurrence is not explicitly bound')
            for index, entity in enumerate(_graph(data)):
                copied = deepcopy(entity)
                generated = type(entity) is dict and '@id' in entity
                if generated:
                    copied['_source'] = parent['combined_source_label']
                expected_origins.append({'generated_index': len(combined), 'parent_index': parent_index,
                    'original_pointer': '/@graph' if type(data.get('@graph')) is dict else '/@graph/' + str(index),
                    'generated_properties': ['_source'] if generated else []})
                combined.append(copied)
        _require(same(combined, _graph(value)), 'combined snapshot changed its entity transformation')
    elif snapshot['kind'] == 'declared_reordered_graph':
        _require(len(snapshot['parents']) == 1, 'permutation parent missing')
        parent = _snapshot_data(snapshot['parents'][0])
        old, new, permutation = _graph(parent), _graph(value), snapshot['permutation']
        _require(type(permutation) is list and len(permutation) == len(old) == len(new)
                 and all(type(i) is int for i in permutation)
                 and sorted(permutation) == list(range(len(old))), 'invalid retained permutation')
        for index, old_index in enumerate(permutation):
            _require(same(new[index], old[old_index]), 'permutation entity changed')
            expected_origins.append({'generated_index': index, 'parent_index': 0,
                'original_pointer': '/@graph' if type(parent.get('@graph')) is dict else '/@graph/' + str(old_index)})
    _require(same(expected_origins, snapshot['entity_origins']), 'source entity pointer joins differ')
    _, pointer = _root(value)
    _require(pointer == snapshot['root_pointer'], 'selected-root pointer changed')
    return value


def validate_source(parser, snapshot):
    data = _snapshot_data(snapshot)
    root, _ = _root(data)
    _require(same(data, parser.rocrate_data) and same(_graph(data), parser.graph)
             and same(root, parser.require_root_dataset()), 'parser changed after source acquisition')


def _escape(text):
    return text.replace('~', '~0').replace('/', '~1')


def _assertions(root, pointer, predicates, supplemental=False):
    selected = next((p for p in predicates if root.get(p) is not None), None)
    return [{'property': p, 'present': p in root,
             **({'raw': deepcopy(root[p])} if p in root else {}),
             'pointer': pointer + '/' + _escape(p), 'selected_within_source': p == selected,
             'supplemental': supplemental, 'selected_for_merge': False,
             'disposition': 'missing' if p not in root else 'null' if root[p] is None else 'unselected',
             'units': []} for p in predicates]


def _construct(field, raw, pointer):
    _, target, child, mode = ROUTES[field]
    if mode == 'exact_size':
        valid = type(raw) is int and raw >= 0
        return (raw if valid else None), [{'pointer': pointer, 'raw': deepcopy(raw),
                'disposition': 'constructed' if valid else 'declined',
                'reason': 'exact_nonnegative_integer' if valid else 'not_an_exact_nonnegative_integer',
                'output_pointer': '/' + target if valid else None}]
    if child is None:
        return None, [{'pointer': pointer, 'raw': deepcopy(raw), 'disposition': 'declined',
                       'reason': 'predicate_does_not_establish_target_assertion', 'output_pointer': None}]
    items = raw if type(raw) is list else [raw]
    values, units = [], []
    for index, item in enumerate(items):
        valid = type(item) is str
        unit = {'pointer': pointer + ('/' + str(index) if type(raw) is list else ''),
                'list_index': index if type(raw) is list else None, 'raw': deepcopy(item),
                'disposition': 'constructed' if valid else 'declined',
                'reason': 'whole_literal' if valid else 'unsupported_assertion_unit', 'output_pointer': None}
        if valid:
            unit['output_pointer'] = '/' + target + '/' + str(len(values)) + '/' + child
            values.append({child: [item] if field == 'external_resource' else item})
        units.append(unit)
    # An unsupported scalar has no Dataset value; an explicit list retains []
    # even if all its individual assertions are declined.
    return (values if type(raw) in (str, list) else None), units


def build_evidence(mapping, parsers, *, snapshots=None, source_indices=None, source_names=None, primary_index=0):
    """Return marked Dataset values and complete detached source assertions."""
    selected = routes(mapping)
    if not selected:
        return {}, None
    count = len(parsers)
    _require(type(primary_index) is int and 0 <= primary_index < count, 'invalid primary source index')
    if snapshots is None:
        snapshots = [source_snapshot(p) for p in parsers]
    if source_indices is None:
        source_indices = list(range(count))
    if source_names is None:
        source_names = [str(p.rocrate_path) for p in parsers]
    _require(len(snapshots) == len(source_indices) == len(source_names) == count,
             'source occurrences must be aligned')
    originals = [i for i in source_indices if i is not None]
    _require(all(type(i) is int and i >= 0 for i in originals)
             and len(set(originals)) == len(originals)
             and all(i is not None or snapshot['kind'] == 'generated_combined'
                     for i, snapshot in zip(source_indices, snapshots)), 'source occurrences must be unique')
    sources = []
    for processed, (parser, snapshot, original, name) in enumerate(zip(parsers, snapshots, source_indices, source_names)):
        validate_source(parser, snapshot)
        root, pointer = _root(_snapshot_data(snapshot))
        rows = {}
        for field, (predicates, _, _, _) in selected.items():
            rows[field] = _assertions(root, pointer, predicates)
            if field == 'bytes':
                rows[field].extend(_assertions(root, pointer, (EXACT_SIZE,), True))
        occurrence = ('input:' + str(original) if original is not None else
                      'combined:' + str(processed) + ':' + snapshot['serialization']['sha256'])
        sources.append({'occurrence_id': occurrence, 'original_index': original,
                        'processed_index': processed, 'display_name': str(name),
                        'primary': processed == primary_index, 'snapshot': deepcopy(snapshot),
                        'root_id': deepcopy(root.get('@id')), 'routes': rows})
    order = [primary_index] + [i for i in range(count) if i != primary_index]
    values, policies = {}, []
    for field, (_, target, _, mode) in selected.items():
        policies.append({'legacy_field': field, 'target': target, 'merge': mode})
        chosen = False
        for i in order:
            assertions = sources[i]['routes'][field]
            candidates = [a for a in assertions if a['selected_within_source']
                          and (a['supplemental'] == (mode == 'exact_size'))]
            # contentSize remains declined evidence, independent of exact evi.
            if mode == 'exact_size':
                for a in assertions:
                    if not a['supplemental'] and a['selected_within_source']:
                        a['disposition'] = 'declined'
                        a['units'] = [{'pointer': a['pointer'], 'raw': deepcopy(a['raw']),
                                      'disposition': 'declined', 'reason': 'rounded_size_not_converted',
                                      'output_pointer': None}]
            for assertion in candidates:
                participates = mode not in ('primary', 'exact_size') or not chosen
                assertion['selected_for_merge'] = participates
                if not participates:
                    assertion['disposition'] = 'superseded'
                    continue
                chosen = True
                value, units = _construct(field, assertion['raw'], assertion['pointer'])
                assertion['units'] = units
                assertion['disposition'] = 'constructed' if value is not None else 'declined'
                if value is None:
                    continue
                if mode == 'concat':
                    offset = len(values.get(target, []))
                    for unit in units:
                        if unit['output_pointer'] is not None:
                            bits = unit['output_pointer'].split('/')
                            bits[2] = str(int(bits[2]) + offset)
                            unit['output_pointer'] = '/'.join(bits)
                    values.setdefault(target, []).extend(value)
                else:
                    values[target] = value
    evidence = {'format': FORMAT, 'policy': MARKER, 'mapping': mapping_identity(mapping),
                'sources': sources, 'processed_occurrences': [s['occurrence_id'] for s in sources],
                'merge_order': [sources[i]['occurrence_id'] for i in order],
                'primary_occurrence': sources[primary_index]['occurrence_id'], 'routes': policies,
                'constructed_values': deepcopy(values)}
    encoded(evidence)
    return values, evidence


def validate_evidence(evidence, dataset, mapping):
    """Check evidence binding before staging, without certifying source facts."""
    selected = routes(mapping)
    if not selected:
        _require(evidence is None, 'unmarked output cannot claim route policy')
        return
    _require(type(evidence) is dict and evidence.get('format') == FORMAT
             and evidence.get('policy') == MARKER, 'marked output requires explicit bound evidence')
    _require(evidence['mapping'] == mapping_identity(mapping), 'mapping evidence differs')
    # Reconstruct only the finite policy from the pinned snapshots, so a changed
    # assertion, output pointer, order or claimed disposition cannot pass staging.
    class CapturedParser:
        def __init__(self, snapshot, name):
            self.rocrate_data = _snapshot_data(snapshot)
            self.graph = _graph(self.rocrate_data)
            self.rocrate_path = name
        def require_root_dataset(self):
            return _root(self.rocrate_data)[0]
    sources = evidence['sources']
    parsers = [CapturedParser(s['snapshot'], s['display_name']) for s in sources]
    primary = [i for i, s in enumerate(sources) if s['primary']]
    _require(len(primary) == 1, 'exactly one primary occurrence required')
    values, expected = build_evidence(mapping, parsers,
        snapshots=[s['snapshot'] for s in sources], source_indices=[s['original_index'] for s in sources],
        source_names=[s['display_name'] for s in sources], primary_index=primary[0])
    _require(same(evidence, expected), 'route evidence changed after construction')
    for field, (_, target, _, _) in selected.items():
        if target is not None:
            _require((target in dataset) == (target in values)
                     and (target not in values or same(dataset[target], values[target])), 'constructed output differs')
        if field != target:
            _require(field not in dataset, 'declined or obsolete Dataset field present: ' + field)


def prepare_sidecar(output_path, dataset, dataset_raw, evidence, mapping):
    """Prepare mandatory sidecar after the unchanged Dataset readback gate."""
    from .resources import PACKAGE_ROOT
    validate_evidence(evidence, dataset, mapping)
    if evidence is None:
        return []
    schema = PACKAGE_ROOT / 'schema/data_sheets_schema_all.yaml'
    document = {'format': FORMAT, 'dataset': dict(_pin(dataset_raw), path=str(Path(output_path).resolve())),
                'schema': dict(_pin(schema.read_bytes()), path=str(schema)), 'evidence': deepcopy(evidence)}
    raw = encoded(document)
    _require(same(json.loads(raw), document), 'sidecar serialization changed types or values')
    path = Path(output_path)
    return [(path.with_name(path.stem + '_route_dispositions.json'), raw)]


def protected_sources(evidence):
    paths = []
    def visit(snapshot):
        if snapshot['original_file'] is not None:
            paths.append(Path(snapshot['original_file']['path']))
        for parent in snapshot['parents']:
            visit(parent)
    if evidence is not None:
        for source in evidence['sources']:
            visit(source['snapshot'])
    return paths
