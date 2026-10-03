"""Explicit, captured structured-issue Figure 11 reporting (#4333).

This is a report of evaluator declarations, not semantic adjudication. It has
no corpus discovery, legacy classifier, evaluator or provider execution path.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import tempfile

import jsonschema
import yaml

from data_sheets_schema.evaluation_context import normalize_context, unwrap_document
from data_sheets_schema.semantic_comparison import evaluator_key
from data_sheets_schema.semantic_evidence import ISSUE_CATEGORIES, check_issue_links
from data_sheets_schema.semantic_evidence_reporting import findings_to_dict, issue_taxonomy
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.semantic_scope import validate_scope
from data_sheets_schema.resources import resource_path

KIND = "semantic_taxonomy_figure_selection"
MAX_ROWS = 256
MAX_GROUPS = 24
MAX_LABEL_CHARS = 512
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_NODES = 250_000
MAX_DEPTH = 64
BOUND = "input_bound_mechanical_checks_passed"
DECLARED = "declaration_shape_and_links_checked"
LIMIT = ("Evaluator declarations only; mechanical checks do not establish semantic correctness. "
         "Repeated selections count as occurrences, not independent ratings.")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _tree(value, depth=0, active=None, budget=None):
    active = set() if active is None else active
    budget = [MAX_NODES] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_DEPTH:
        raise ValueError("document exceeds node/depth bound")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite document value")
    if isinstance(value, (dict, list)):
        if id(value) in active:
            raise ValueError("cyclic document")
        active.add(id(value))
        children = list(value.items()) if isinstance(value, dict) else enumerate(value)
        for key, child in children:
            if isinstance(value, dict) and not isinstance(key, str):
                raise ValueError("document mapping keys must be strings")
            _tree(child, depth + 1, active, budget)
        active.remove(id(value))


def _json(raw):
    def invalid(value):
        raise ValueError(f"nonfinite JSON: {value}")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=invalid)
    _tree(value)
    return value


def _yaml(raw):
    # Inspect the node graph before construction so aliases cannot cause an
    # unbounded expansion; refuse ambiguous keys/merges in these new inputs.
    text = raw.decode("utf-8")
    node = yaml.compose(text, Loader=yaml.SafeLoader)
    remaining = [MAX_NODES]
    def visit(item, depth, active):
        remaining[0] -= 1
        if remaining[0] < 0 or depth > MAX_DEPTH:
            raise ValueError("YAML exceeds node/depth bound")
        if item is None:
            return
        if id(item) in active:
            raise ValueError("cyclic YAML")
        active = active | {id(item)}
        if isinstance(item, yaml.MappingNode):
            seen = set()
            for key, value in item.value:
                if not isinstance(key, yaml.ScalarNode) or key.tag != 'tag:yaml.org,2002:str':
                    raise ValueError("YAML requires string mapping keys without merges")
                if key.value in seen:
                    raise ValueError(f"duplicate YAML key: {key.value}")
                seen.add(key.value)
                visit(key, depth + 1, active)
                visit(value, depth + 1, active)
        elif isinstance(item, yaml.SequenceNode):
            for value in item.value:
                visit(value, depth + 1, active)
    visit(node, 0, set())
    value = yaml.safe_load(text)
    _tree(value)
    return value


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class Capture:
    path: str
    resolved: str
    raw: bytes
    identity: tuple

    def pin(self):
        return {"path": self.path, "resolved": self.resolved, "sha256": _sha(self.raw),
                "bytes": len(self.raw), "file_identity": list(self.identity)}

    def verify(self):
        if Path(self.path).resolve(strict=True) != Path(self.resolved):
            raise ValueError(f"captured path changed: {self.path}")
        current = _read(Path(self.path))
        if current.identity != self.identity or current.raw != self.raw:
            raise ValueError(f"captured input/resource changed: {self.path}")


def _read(path):
    path = path.absolute()
    resolved = path.resolve(strict=True)
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError(f'expected bounded regular file: {path}')
    fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise ValueError(f"expected bounded regular file: {path}")
        raw = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > MAX_FILE_BYTES or _identity(before) != _identity(after):
        raise ValueError(f"file changed or exceeds byte bound: {path}")
    if path.resolve(strict=True) != resolved or _identity(resolved.stat()) != _identity(after):
        raise ValueError(f"file identity changed during capture: {path}")
    return Capture(str(path), str(resolved), raw, _identity(after))


@dataclass(frozen=True)
class PreparedFigure:
    """Immutable prepared payload; publication rechecks every captured file."""
    payload: bytes
    captures: tuple[Capture, ...]

    def report(self):
        return _json(self.payload)


def prepare(selection_path: str | Path) -> PreparedFigure:
    """Capture, validate and aggregate an explicit ordered selection, read-only."""
    cache = {}
    total_bytes = 0
    def capture(path):
        nonlocal total_bytes
        key = str(Path(path).absolute())
        if key not in cache:
            value = _read(Path(key))
            total_bytes += len(value.raw)
            if total_bytes > MAX_TOTAL_BYTES:
                raise ValueError("selection exceeds total captured byte bound")
            cache[key] = value
        return cache[key]

    selection = capture(selection_path)
    value = _json(selection.raw)
    if (not isinstance(value, dict) or set(value) != {"kind", "version", "ratings"}
            or value['kind'] != KIND or type(value['version']) is not int or value['version'] != 1
            or not isinstance(value['ratings'], list) or not 1 <= len(value['ratings']) <= MAX_ROWS):
        raise ValueError("expected a closed v1 selection with 1..256 ordered ratings")
    rows, groups, group_indices = [], [], {}
    for index, entry in enumerate(value['ratings']):
        if (not isinstance(entry, dict) or not {'rating', 'group'} <= set(entry)
                or set(entry) - {'rating', 'group', 'input', 'context'}
                or any(not isinstance(v, str) or not v.strip() for v in entry.values())
                or 'context' in entry and 'input' not in entry):
            raise ValueError(f"selection {index}: invalid rating/group/input/context declaration")
        if len(entry['group']) > MAX_LABEL_CHARS:
            raise ValueError('group label exceeds 512 characters')
        inputs = {key: capture(Path(selection.path).parent / entry[key])
                  for key in ('rating', 'input', 'context') if key in entry}
        result = _json(inputs['rating'].raw)
        if not isinstance(result, dict) or result.get('version') not in ('3.0', '4.0'):
            raise ValueError(f"selection {index}: only structured semantic versions 3.0/4.0 are supported")
        instrument = select_semantic_instrument(result.get('rubric'), result['version'])
        selected = {key: capture(resource_path(getattr(instrument, attr))) for key, attr in (
            ('schema', 'schema_path'), ('rubric', 'rubric_path'), ('definition', 'definition_path'),
            ('authority', 'evidence_authority_path'))}
        schema = _json(selected['schema'].raw)
        jsonschema.validators.validator_for(schema)(schema).validate(result)
        metadata = result['metadata']
        for key, digest in (('instrument_sha256', 'definition'), ('rubric_sha256', 'rubric'),
                            ('evidence_authority_sha256', 'authority')):
            if metadata.get(key) != _sha(selected[digest].raw):
                raise ValueError(f"selection {index}: {key} disagrees with selected resource")
        if 'input' in inputs:
            document = unwrap_document(_yaml(inputs['input'].raw))
            context = normalize_context(_yaml(inputs['context'].raw) if 'context' in inputs else None)
            evidence = validate_scope(result, document=document,
                                      input_sha256=_sha(inputs['input'].raw), expected_context=context)
            state = BOUND
        else:
            validate_scope(result)
            evidence = None
            state = DECLARED
        links = check_issue_links(result, result['rubric'])
        if not links.passed:
            raise ValueError(f"selection {index}: invalid issue links: " +
                             '; '.join(f'{f.code}: {f.message}' for f in links.errors))
        taxonomy = issue_taxonomy(result)
        model = result.get('model')
        evaluator = evaluator_key(result)
        if evaluator is not None and (not isinstance(evaluator, str) or not evaluator.strip()):
            raise ValueError("declared evaluator identity must be a nonblank string or unknown")
        if evaluator is not None and len(evaluator) > MAX_LABEL_CHARS:
            raise ValueError('evaluator label exceeds 512 characters')
        group_key = {'group': entry['group'], 'rubric': result['rubric'], 'version': result['version'],
                     'instrument': {key: _sha(item.raw) for key, item in selected.items()},
                     'evaluator': evaluator, 'evaluator_type': (model or {}).get('evaluation_type'),
                     'model_sha256': _sha(_encoded(model)),
                     'unknown_evaluator_occurrence': index if evaluator is None else None}
        encoded_key = _encoded(group_key)
        if encoded_key not in group_indices:
            if len(groups) >= MAX_GROUPS:
                raise ValueError("selection exceeds 24 distinct plot groups")
            group_indices[encoded_key] = len(groups)
            groups.append({'id': f'g{len(groups)}', **group_key, 'model': model,
                           'selection_indices': [], 'rating_occurrences': 0, 'zero_issue_occurrences': 0,
                           'validation_counts': {BOUND: 0, DECLARED: 0},
                           'category_counts': {k: 0 for k in sorted(ISSUE_CATEGORIES)},
                           'item_counts': {}, 'high_severity_lowered': 0, 'issue_count': 0})
        group = groups[group_indices[encoded_key]]
        group['selection_indices'].append(index)
        group['rating_occurrences'] += 1
        group['zero_issue_occurrences'] += not taxonomy['issues']
        group['validation_counts'][state] += 1
        group['issue_count'] += len(taxonomy['issues'])
        group['high_severity_lowered'] += taxonomy['high_severity_lowered']
        for category, count in taxonomy['category_counts'].items():
            group['category_counts'][category] += count
        for item, count in taxonomy['item_counts'].items():
            group['item_counts'][item] = group['item_counts'].get(item, 0) + count
        rows.append({'selection_index': index, 'group_id': group['id'], 'selection': entry,
                     'inputs': {key: cap.pin() for key, cap in inputs.items()},
                     'resources': {key: cap.pin() for key, cap in selected.items()},
                     'rubric': result['rubric'], 'version': result['version'], 'model': model,
                     'validation': state, 'issue_links': findings_to_dict(links),
                     'evidence': findings_to_dict(evidence) if evidence is not None else None,
                     'taxonomy': taxonomy})
    # Shared validators use their normal resources; verify the entire captured
    # resource/input set after validation. Rendering never reads selected paths.
    for cap in cache.values():
        cap.verify()
    payload = {'kind': 'semantic_taxonomy_figure', 'version': 1,
               'selection': selection.pin(), 'ratings': rows, 'groups': groups,
               'limits': LIMIT, 'count_units': {'categories': 'issue occurrences',
                  'high_severity_lowered': 'high-severity lowered issue occurrences',
                  'item_links': 'issue-to-item links', 'ratings': 'ordered selection occurrences'},
               'validation_states': {BOUND: 'Exact caller input/context and mechanical evidence checked; warnings retained.',
                                     DECLARED: 'Shape, internal scope and issue links checked; input evidence not checked.'}}
    return PreparedFigure(_encoded(payload), tuple(cache.values()))


def _csv(fields, rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _svg(report):
    # Plotting is optional for all other repository users. The repository's dev
    # environment supplies matplotlib; no new runtime dependency is introduced.
    from matplotlib.figure import Figure
    from matplotlib import rc_context
    groups = report['groups']
    with rc_context({'svg.fonttype': 'none', 'svg.hashsalt': 'semantic-taxonomy-figure-v1',
                     'text.usetex': False, 'text.parse_math': False}):
        fig = Figure(figsize=(15, max(4, len(groups) * 3.5)), layout='constrained')
        axes = fig.subplots(len(groups), 2, squeeze=False, width_ratios=[4, 1])
        for group, (left, right) in zip(groups, axes):
            keys = list(group['category_counts'])
            left.bar(range(len(keys)), [group['category_counts'][key] for key in keys])
            left.set_xticks(range(len(keys)), [key.replace('_', '\n') for key in keys], fontsize=7)
            left.set_ylabel('Issue occurrences')
            left.set_ylim(bottom=0, top=max(1, max(group['category_counts'].values())) * 1.2)
            label = (f"{group['id']} | {group['group']} | {group['rubric']} v{group['version']} | "
                     f"evaluator: {group['evaluator'] or 'unknown'}\n"
                     f"{group['rating_occurrences']} rating occurrences; "
                     f"input-bound: {group['validation_counts'][BOUND]}; "
                     f"declaration-only: {group['validation_counts'][DECLARED]}; "
                     f"zero-issue: {group['zero_issue_occurrences']}")
            left.set_title(label, fontsize=9, wrap=True)
            right.bar(['High severity\nlowered'], [group['high_severity_lowered']], color='#9b3333')
            right.set_ylim(bottom=0, top=max(1, group['high_severity_lowered']) * 1.2)
            right.set_ylabel('Issue occurrences')
        fig.suptitle('Figure 11 — structured evaluator-declared issue taxonomy\n' + LIMIT, fontsize=10)
        stream = io.BytesIO()
        fig.savefig(stream, format='svg', metadata={'Date': None, 'Description': LIMIT})
        return stream.getvalue()


def _artifacts(report):
    ratings, issues, categories, links, lowered = [], [], [], [], []
    for row in report['ratings']:
        common = {'selection_index': row['selection_index'], 'group_id': row['group_id']}
        ratings.append({**common, 'rating_sha256': row['inputs']['rating']['sha256'],
                        'rating_path': row['selection']['rating'], 'rubric': row['rubric'],
                        'version': row['version'], 'validation': row['validation'],
                        'issue_count': len(row['taxonomy']['issues']),
                        'warning_count': len([f for f in (row['evidence'] or row['issue_links'])['findings']
                                              if f['severity'] == 'warning'])})
        for issue in row['taxonomy']['issues']:
            base = {**common, 'issue_index': issue['index']}
            issues.append({**base, **{k: issue[k] for k in ('category', 'type', 'severity', 'score_effect')},
                           'item_ids_json': json.dumps(issue['item_ids'])})
            for item in issue['item_ids']:
                links.append({**base, 'item_id': item})
    for group in report['groups']:
        common = {'group_id': group['id'], 'rating_occurrences': group['rating_occurrences'],
                  'input_bound_occurrences': group['validation_counts'][BOUND],
                  'declaration_only_occurrences': group['validation_counts'][DECLARED]}
        categories.extend({**common, 'category': key, 'issue_count': count}
                          for key, count in group['category_counts'].items())
        lowered.append({**common, 'high_severity_lowered_issue_count': group['high_severity_lowered']})
    return {'fig11_semantic_taxonomy.svg': _svg(report),
            'ratings.csv': _csv(['selection_index', 'group_id', 'rating_sha256', 'rating_path', 'rubric',
                                'version', 'validation', 'issue_count', 'warning_count'], ratings),
            'issues.csv': _csv(['selection_index', 'group_id', 'issue_index', 'category', 'type', 'severity',
                               'score_effect', 'item_ids_json'], issues),
            'categories.csv': _csv(['group_id', 'rating_occurrences', 'input_bound_occurrences',
                                   'declaration_only_occurrences', 'category', 'issue_count'], categories),
            'item_links.csv': _csv(['selection_index', 'group_id', 'issue_index', 'item_id'], links),
            'lowered.csv': _csv(['group_id', 'rating_occurrences', 'input_bound_occurrences',
                                'declaration_only_occurrences', 'high_severity_lowered_issue_count'], lowered)}


def publish(prepared: PreparedFigure, output_dir: str | Path) -> dict:
    """Publish only to a fresh directory; report.json is the last completion file.

    On failure, any reserved partial directory is retained without a complete
    report. No existing destination or selected input is replaced or deleted.
    """
    if not isinstance(prepared, PreparedFigure):
        raise ValueError("expected a prepared taxonomy figure")
    output = Path(output_dir).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output must be fresh: {output}")
    parent = output.parent.resolve(strict=True)
    output = parent / output.name
    for cap in prepared.captures:
        path = Path(cap.resolved)
        if output == path or output in path.parents or path in output.parents:
            raise ValueError("output aliases a captured input/resource")
        cap.verify()
    report = prepared.report()
    artifacts = _artifacts(report)
    final = {'state': 'complete', 'payload_sha256': _sha(prepared.payload), 'report': report,
             'artifacts': {name: {'sha256': _sha(raw), 'bytes': len(raw)}
                           for name, raw in artifacts.items()}}
    # Render every byte before reserving the destination. Revalidate both raw
    # bytes and file identities after rendering, then publish exclusively.
    with tempfile.TemporaryDirectory(prefix='d4d-semantic-taxonomy-') as staging:
        for name, raw in artifacts.items():
            (Path(staging) / name).write_bytes(raw)
        for cap in prepared.captures:
            cap.verify()
        output.mkdir(mode=0o700)
        handle = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            if _identity(os.fstat(handle)) != _identity(output.stat(follow_symlinks=False)):
                raise ValueError("publication directory identity changed")
            for name, raw in artifacts.items():
                _publish_file(handle, name, raw)
            for name, raw in artifacts.items():
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=handle)
                with os.fdopen(fd, 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read(len(raw) + 1) != raw:
                        raise ValueError(f"published artifact changed: {name}")
            for cap in prepared.captures:
                cap.verify()
            if not os.path.samestat(os.fstat(handle), output.stat(follow_symlinks=False)):
                raise ValueError("publication directory moved or replaced")
            _publish_file(handle, 'report.json', _encoded(final))
            if not os.path.samestat(os.fstat(handle), output.stat(follow_symlinks=False)):
                raise ValueError("publication directory moved or replaced")
        finally:
            os.close(handle)
    return final


def _publish_file(directory_fd, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
