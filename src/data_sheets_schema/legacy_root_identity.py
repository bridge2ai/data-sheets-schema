"""Explicit scalar root identity for legacy mappings, never an inferred ID."""
from copy import deepcopy
import json

from data_sheets_schema.legacy_doi import doi_value
from data_sheets_schema.scope import bare_doi


MARKER = 'root_identifier_v1'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'


def validate_rows(rows):
    """Admit one explicit route; leave all unmarked custom mappings alone."""
    marked = [row for row in rows if (row.get('Func') or '').strip() == MARKER]
    if not marked:
        return False
    ids = [row for row in rows if (row.get('D4D Property') or '').strip() == 'id'
           and (row.get(COVERED) or '').strip() == '1']
    if (len(marked) != 1 or len(ids) != 1 or marked[0] is not ids[0]
            or [part.strip() for part in (marked[0].get(
                'FAIRSCAPE RO-Crate Property') or '').split(',')] != ['identifier', '@id']):
        raise ValueError(f'{MARKER} requires one covered id row with identifier,@id; '
                         'duplicate or conflicting ID declarations are not supported')
    return True


def root_identity_route(mapping):
    return validate_rows(getattr(mapping, 'mappings', ()))


def scoring_fields(mapping):
    """A construction-only marked ID must not change the existing ranking."""
    marked = root_identity_route(mapping)
    return [field for field in mapping.get_covered_fields()
            if not (marked and field == 'id')]


def _written_id(value):
    # The DOI helper removes only a recognised prefix and preserves the complete
    # suffix (#4671). Our stricter route does not trim outer whitespace either.
    if value == value.strip():
        body = doi_value(value)
        if body.startswith('10.') and bare_doi(body) is not None:
            return 'doi:' + body
    return value


def resolve_root_identity(root):
    """Read the selected root only, retaining absence and original assertions."""
    evidence = {'id': None, 'source_property': None, 'source_value': None,
                'inputs': {key: {'present': key in root, 'value': deepcopy(root.get(key))}
                           for key in ('identifier', '@id')}}
    for key in ('identifier', '@id'):
        value = root.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f'{MARKER}: root {key} must be scalar text; '
                             'no list item or non-text identifier was selected')
        if not value.strip():
            continue
        evidence.update(id=_written_id(value), source_property=key, source_value=value)
        break
    return evidence


def merge_identity_evidence(parsers, source_names, primary_index):
    """Preflight every root before changing merge state; no identity union."""
    primary_index = range(len(parsers))[primary_index]
    rows = []
    for index, (parser, name) in enumerate(zip(parsers, source_names)):
        try:
            evidence = resolve_root_identity(parser.require_root_dataset())
        except ValueError as exc:
            raise ValueError(f'{parser.rocrate_path}: {exc}') from exc
        rows.append({'source': name, 'path': str(parser.rocrate_path),
                     'selected_primary': index == primary_index, **evidence})
    primary_id = rows[primary_index]['id']
    for row in rows:
        row['different_written_id'] = (row['id'] != primary_id)
    return rows


def identity_report_lines(rows):
    if rows is None:
        return []
    return ['', 'ROOT IDENTITY SELECTION', '-' * 80,
            'Dataset.id uses only the configured primary source. '
            'Different written IDs do not assert entity equivalence.',
            'Required identity construction is excluded from informativeness scoring; '
            'it is not a source-coverage gain.',
            *(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows), '']
