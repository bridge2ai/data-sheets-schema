"""Explicit lossless maintenance-plan construction for legacy TSV mappings."""
from copy import deepcopy


MARKER = 'update_plan_narrative_v1'
SOURCE = 'rai:dataReleaseMaintenancePlan'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'


def validate_rows(rows):
    """Admit one named source/target route; leave unmarked mappings unchanged."""
    marked = [row for row in rows if (row.get('Func') or '').strip() == MARKER]
    if not marked:
        return False
    updates = [row for row in rows
               if (row.get('D4D Property') or '').strip() == 'updates'
               and (row.get(COVERED) or '').strip() == '1']
    if (len(marked) != 1 or len(updates) != 1 or marked[0] is not updates[0]
            or (marked[0].get('FAIRSCAPE RO-Crate Property') or '').strip() != SOURCE):
        raise ValueError(f'{MARKER} requires one covered updates row with {SOURCE}; '
                         'duplicate or conflicting maintenance routes are not supported')
    return True


def update_plan_route(mapping):
    return validate_rows(getattr(mapping, 'mappings', ()))


def update_plan_value(value):
    """Wrap complete text; preserve other assertions for the publication gate.

    No list joining, key filtering, inferred subfields or scalar stringification
    is permitted. Detached values cannot mutate the parser's original evidence.
    """
    if isinstance(value, str):
        return {'update_details': value}
    return deepcopy(value)
