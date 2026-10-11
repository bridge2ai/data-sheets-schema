"""#4929: whole-text constructors for three closed legacy documentary routes.

Source selection and merge precedence remain distinct from construction. These
objects preserve assertions, not verified mechanisms, access rights or licenses.
The scalar licensing route never collapses a list into a single assertion.
"""
from copy import deepcopy


MARKER = 'root_documentary_fields_v1'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'
ROUTES = {
    'collection_mechanisms': ('rai:dataCollection', 'rai:dataCollectionType'),
    'raw_data_sources': ('rai:dataCollectionRawData',),
    'license_and_use_terms': ('license', 'conditionsOfAccess'),
}
FIELDS = {
    'collection_mechanisms': 'mechanism_details',
    'raw_data_sources': 'source_description',
    'license_and_use_terms': 'license_terms',
}


def validate_rows(rows):
    """Refuse conflicting explicit routes before filtering or building output."""
    selected = {}
    for row in rows:
        if (row.get('Func') or '').strip() != MARKER:
            continue
        field = (row.get('D4D Property') or '').strip()
        sources = tuple(part.strip() for part in
                        (row.get('FAIRSCAPE RO-Crate Property') or '').split(','))
        covered = [other for other in rows
                   if (other.get('D4D Property') or '').strip() == field
                   and (other.get(COVERED) or '').strip() == '1']
        if (field not in ROUTES or sources != ROUTES[field]
                or len(covered) != 1 or covered[0] is not row):
            raise ValueError(f'{MARKER} requires one covered row for each marked '
                             'target and its ordered declared sources; duplicate '
                             'or conflicting documentary routes are not supported')
        selected[field] = sources
    return selected


def documentary_routes(mapping):
    return validate_rows(getattr(mapping, 'mappings', ()))


def documentary_source(root, sources):
    """Retain the first non-null selected-root value, including falsy values."""
    for source in sources:
        value = root.get(source)
        if value is not None:
            return value
    return None


def documentary_value(field, value):
    """Shape whole strings only; detach unsupported values for the real gate."""
    child = FIELDS[field]
    if field == 'license_and_use_terms':
        return {child: value} if isinstance(value, str) else deepcopy(value)
    if isinstance(value, str):
        return [{child: value}]
    if isinstance(value, list):
        return [{child: item} if isinstance(item, str) else deepcopy(item)
                for item in value]
    return deepcopy(value)
