"""Explicit whole-text description lists for closed legacy TSV routes.

These constructors preserve source assertions; table relation/loss declarations
are not upgraded and no step type, order, annotator, MIME type or format is inferred.
The narrative marker remains restricted to its original four routes (#4913).
The separate distribution marker preserves root format literals only (#4921);
it does not settle the evi:formats vocabulary/alignment issue (#4037).
"""
from copy import deepcopy


MARKER = 'description_list_narrative_v1'
DISTRIBUTION_MARKER = 'distribution_formats_description_v1'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
ROUTES = {
    'preprocessing_strategies': 'rai:dataPreprocessingProtocol',
    'cleaning_strategies': 'rai:dataManipulationProtocol',
    'labeling_strategies': 'rai:dataAnnotationProtocol',
    'annotation_analyses': 'rai:dataAnnotationAnalysis',
}

DISTRIBUTION_ROUTES = {'distribution_formats': 'evi:formats'}


def validate_rows(rows):
    """Validate explicit routes before filtering can hide a conflicting row."""
    marked = [row for row in rows
              if (row.get('Func') or '').strip() in (MARKER, DISTRIBUTION_MARKER)]
    selected = {}
    for row in marked:
        marker = (row.get('Func') or '').strip()
        routes = ROUTES if marker == MARKER else DISTRIBUTION_ROUTES
        field = (row.get('D4D Property') or '').strip()
        covered = [other for other in rows
                   if (other.get('D4D Property') or '').strip() == field
                   and (other.get(COVERED) or '').strip() == '1']
        if (field not in routes or len(covered) != 1 or covered[0] is not row
                or (row.get('FAIRSCAPE RO-Crate Property') or '').strip() != routes[field]):
            raise ValueError(f'{marker} requires one covered row for each marked '
                             'description-list target and its declared source; '
                             f'duplicate or conflicting {"narrative" if marker == MARKER else "distribution"} '
                             'routes are not supported')
        selected[field] = routes[field]
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
