"""Explicit whole-text SensitiveElement construction for one legacy TSV route.

This preserves existing assertions without inferring a presence flag,
confidentiality, or a stronger mapping/fidelity declaration.
"""
from copy import deepcopy


MARKER = 'sensitive_elements_details_v1'
SOURCE = 'rai:personalSensitiveInformation'
COVERED = 'Covered by FAIRSCAPE? Yes =1; No = 0'


def validate_rows(rows):
    """Admit only the fixed marked source/target before row filtering."""
    marked = [row for row in rows if (row.get('Func') or '').strip() == MARKER]
    if not marked:
        return False
    sensitive = [row for row in rows
                 if (row.get('D4D Property') or '').strip() == 'sensitive_elements'
                 and (row.get(COVERED) or '').strip() == '1']
    if (len(marked) != 1 or len(sensitive) != 1 or marked[0] is not sensitive[0]
            or (marked[0].get('FAIRSCAPE RO-Crate Property') or '').strip() != SOURCE):
        raise ValueError(f'{MARKER} requires one covered sensitive_elements row with {SOURCE}; '
                         'duplicate or conflicting sensitivity routes are not supported')
    return True


def sensitive_elements_route(mapping):
    return validate_rows(getattr(mapping, 'mappings', ()))


def sensitive_elements_value(value):
    """Wrap each whole string and detach other units for ordinary validation.

    No splitting, trimming, flattening, deduplication, key filtering or boolean
    inference. Existing structured units remain subject to the same schema gate.
    """
    if isinstance(value, str):
        return [{'sensitivity_details': value}]
    if isinstance(value, list):
        return [{'sensitivity_details': item} if isinstance(item, str) else deepcopy(item)
                for item in value]
    return deepcopy(value)
