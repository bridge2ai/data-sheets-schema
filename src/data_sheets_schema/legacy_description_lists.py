"""Explicit whole-text description lists for four legacy TSV routes.

These constructors preserve source assertions; table relation/loss declarations
are not upgraded and no step type, order, annotator or evidence code is inferred.
"""
from copy import deepcopy


MARKER = 'description_list_narrative_v1'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
ROUTES = {
    'preprocessing_strategies': 'rai:dataPreprocessingProtocol',
    'cleaning_strategies': 'rai:dataManipulationProtocol',
    'labeling_strategies': 'rai:dataAnnotationProtocol',
    'annotation_analyses': 'rai:dataAnnotationAnalysis',
}


def validate_rows(rows):
    """Validate explicit routes before filtering can hide a conflicting row."""
    marked = [row for row in rows if (row.get('Func') or '').strip() == MARKER]
    selected = {}
    for row in marked:
        field = (row.get('D4D Property') or '').strip()
        covered = [other for other in rows
                   if (other.get('D4D Property') or '').strip() == field
                   and (other.get(COVERED) or '').strip() == '1']
        if (field not in ROUTES or len(covered) != 1 or covered[0] is not row
                or (row.get('FAIRSCAPE RO-Crate Property') or '').strip() != ROUTES[field]):
            raise ValueError(f'{MARKER} requires one covered row for each marked '
                             'description-list target and its declared source; '
                             'duplicate or conflicting narrative routes are not supported')
        selected[field] = ROUTES[field]
    return selected


def description_list_routes(mapping):
    return validate_rows(getattr(mapping, 'mappings', ()))


def description_list_value(value):
    """Wrap whole strings; detach all other units for the unchanged validator.

    Lists retain their immediate order and multiplicity. Non-string units,
    including numbers, objects and nested lists, are never stringified,
    flattened or discarded.
    Existing schema-valid objects remain subject to the same publication gate.
    """
    if isinstance(value, str):
        return [{'description': value}]
    if isinstance(value, list):
        return [{'description': item} if isinstance(item, str) else deepcopy(item)
                for item in value]
    return deepcopy(value)
