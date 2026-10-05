"""Native schema and pair gates over already captured selection and records.

The caller owns capture and chronology. These readers use only the selected
full/core schema closures and immutable final bytes, with no path fallback.
"""
from __future__ import annotations

from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin

from . import audit_omissions, d4d_pair_consistency as pair
from . import native_shared_contract as contract
from .native_shared_receipts import schema_snapshot
from .schema_view import captured_view


def _records(selection, full_raw, core_raw):
    limit = min(selection.bounds()['max_input_bytes'], contract.HARD_LIMITS['original_full_bytes'])
    return tuple(audit_omissions._mapping(raw, 'native final ' + kind, limit=limit)
                 for kind, raw in (('full', full_raw), ('core', core_raw)))


def check_schemas(selection, full_raw, core_raw):
    """Run the closed LinkML validator against each captured schema closure.

    Unusable input raises; valid mappings that violate the selected schema
    return checked conformance problems. Imports are merged within a fresh
    captured view before handing the definition to LinkML's validator, whose
    own schema reader therefore has no imports to reopen.
    """
    records = _records(selection, full_raw, core_raw)
    problems = []
    for (kind, cls), record in zip((('full', 'Dataset'), ('core', 'CoreDataset')), records):
        with captured_view(schema_snapshot(selection, kind)) as view:
            view.get_class(cls, strict=True)
            view.merge_imports()
            validator = Validator(view.schema, validation_plugins=[JsonschemaValidationPlugin(closed=True)])
            problems.extend(kind + ': ' + result.message
                            for result in validator.iter_results(record, target_class=cls))
    return {'passed': not problems, 'problems': problems}


def check_pair(selection, full_raw, core_raw):
    """Compare the same captured records using their selected identity rules."""
    full, core = _records(selection, full_raw, core_raw)
    with captured_view(schema_snapshot(selection, 'full')) as full_view, \
            captured_view(schema_snapshot(selection, 'core')) as core_view:
        schema = pair.pair_schema_from_views(full_view, core_view)
        result = pair.validate_pair_data(full, core, schema, schema_moved=False)
        return {'passed': result.passed, 'schema_moved': False,
                'basis': 'fresh attempt, same captured schemas and exact records',
                'diagnostic': str(result)}
