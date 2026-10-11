"""Explicit Creator assertion construction and separately measured source facts.

The literal marker wraps whole assertions; the separate reference marker opts
into the bounded same-crate author projection in legacy_creator_references.
Construction counts and the raw author measurement are not source coverage.
"""
from copy import deepcopy
import json


MARKER = 'creator_author_literals_v1'
REFERENCE_MARKER = 'creator_author_references_v1'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
SOURCE_FORMAT = 'legacy_author_source_presence_v1'
KEY_BASIS_LABEL = 'Constructed-field presence (output keys; null-valued keys included)'
VALUE_BASIS_LABEL = 'Constructed-field presence (non-null mapped values)'
MEASUREMENT_LIMIT = 'Construction counts are not source coverage or validation success.'


def _creator_rows(rows):
    return [row for row in rows
            if (row.get('D4D Property') or '').strip() == 'creators'
            and (row.get(COVERED) or '').strip() == '1']


def validate_rows(rows):
    """Check the marker before ignored-row filtering; custom Func text is inert."""
    marked = [row for row in rows
              if (row.get('Func') or '').strip() in (MARKER, REFERENCE_MARKER)]
    if not marked:
        return False
    creators = _creator_rows(rows)
    if (len(marked) != 1 or len(creators) != 1 or marked[0] is not creators[0]
            or (marked[0].get('FAIRSCAPE RO-Crate Property') or '').strip() != 'author'):
        marker = (marked[0].get('Func') or '').strip()
        raise ValueError(f'{marker} requires one covered creators row with author; '
                         'duplicate or conflicting Creator routes are not supported')
    return True


def creator_route(mapping):
    return validate_rows(getattr(mapping, 'mappings', ()))


def creator_reference_route(mapping):
    rows = getattr(mapping, 'mappings', ())
    return validate_rows(rows) and any(
        (row.get('Func') or '').strip() == REFERENCE_MARKER for row in rows)


def creator_value(value):
    """Preserve immediate assertion units, including unsupported typed values."""
    units = value if isinstance(value, list) else [value]
    return [{'description': unit} if isinstance(unit, str) else deepcopy(unit)
            for unit in units]


def author_source_presence(mapping, parsers, source_names, primary_index=0):
    """Measure one exact raw-root route independently of its constructor.

    source_index names the supplied parser list, after any caller ranking.
    Rows visit each selected source once, primary then remaining input order.
    Historical unmarked negative-index mergers can construct repeated visits;
    this raw roster does not measure those visits or claim their output ranges.
    """
    rows = _creator_rows(getattr(mapping, 'mappings', ()))
    reason = ('no_covered_creators_route' if not rows else
              'multiple_covered_creators_routes' if len(rows) != 1 else
              'different_source_property' if (rows[0].get(
                  'FAIRSCAPE RO-Crate Property') or '').strip() != 'author' else None)
    result = {'format': SOURCE_FORMAT,
              'status': 'not_measured' if reason else 'measured', 'reason': reason,
              'target': 'creators', 'source_property': 'author',
              'root_scope': 'selected_root', 'sources': []}
    if reason:
        return result
    if len(source_names) != len(parsers):
        raise ValueError('source_names must match the selected RO-Crates')
    # A raw roster visits each source once even when an old unmarked merger
    # accepts Python negative indexing and historically repeats that source.
    # range indexing rejects empty/out-of-bounds/non-index values explicitly.
    selected = range(len(parsers))[primary_index]
    order = [selected] + [i for i in range(len(parsers)) if i != selected]
    for processing_index, index in enumerate(order):
        root = parsers[index].require_root_dataset()
        value = root.get('author')
        count = 0 if value is None else len(value) if isinstance(value, list) else 1
        result['sources'].append({
            'source_index': range(len(parsers))[index],
            'processing_index': processing_index, 'source_name': source_names[index],
            'selected_primary': processing_index == 0,
            'root_id': deepcopy(root.get('@id')), 'author_present': 'author' in root,
            'nonnull': value is not None, 'immediate_assertion_units': count,
            'raw_value': deepcopy(value),
        })
    return result


def merge_creator_values(presence, constructed_values):
    """Concatenate already constructed units once; no equality implies identity."""
    if presence['status'] != 'measured' or len(presence['sources']) != len(constructed_values):
        raise ValueError('Creator merge requires its exact measured source roster')
    units, contributors, ledger = [], [], []
    present = False
    for evidence, value in zip(presence['sources'], constructed_values):
        start = len(units)
        if evidence['nonnull']:
            if not isinstance(value, list):
                raise ValueError('Marked Creator value must be an assertion list')
            units.extend(deepcopy(value))
            contributors.append(evidence['source_name'])
            present = True
        row = deepcopy(evidence)
        row['output_range'] = [start, len(units)]
        ledger.append(row)
    return units if present else None, contributors, ledger


def construction_basis(numerator, denominator):
    """Qualify the retained API compatibility metric without changing its math."""
    return {'kind': 'constructed_field_presence', 'count_rule': 'non_null_mapped_value',
            'numerator': numerator, 'denominator': denominator,
            'is_source_coverage': False, 'is_validation_success': False}


def source_presence_lines(presence, *, raw=True):
    """Render source facts, not constructed success; escape complete raw text."""
    if presence is None:
        return []
    lines = ['', 'ROOT AUTHOR SOURCE PRESENCE', '-' * 80,
             'Immediate assertion units are not people, unique facts or validation successes.',
             f"Route creators <- author: {presence['status']}"]
    if presence['reason']:
        lines.append('Reason: ' + presence['reason'])
    for row in presence['sources']:
        shown = deepcopy(row)
        if not raw:
            shown.pop('raw_value')
        lines.append(json.dumps(shown, ensure_ascii=False, sort_keys=True))
    return lines + ['']


def creator_assertion_lines(ledger):
    if ledger is None:
        return []
    return ['', 'CREATOR ASSERTION CONSTRUCTION', '-' * 80,
            'All source assertion units retained in order; output ranges are half-open. '
            'Equal values do not establish one person.',
            *(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in ledger), '']
