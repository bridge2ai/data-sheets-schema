"""Source-derived review/owner adapter; never constructs an authorization.

The running source owns kind/version and admission terms. Current validators
are requested where supported; old sources remain usable only for their own
historical contract. No margin or schema version is copied into this adapter.
"""
import inspect
import re
import ast


def literal_constraint(function, field):
    """Read a unique literal comparison from the running validator, or refuse.

    This extracts a source-owned constant; it does not implement validation.
    Used where older source exposes no public version constant.
    """
    values = set()
    for node in ast.walk(ast.parse(inspect.getsource(function))):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Subscript)
                and isinstance(node.left.slice, ast.Constant) and node.left.slice.value == field
                and len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant)
                and isinstance(node.ops[0], (ast.NotEq, ast.Eq))):
            values.add(node.comparators[0].value)
    if len(values) != 1:
        raise ValueError('source does not expose one literal constraint for ' + field)
    return values.pop()


def source_contract():
    from data_sheets_schema import native_launch_review as review
    from data_sheets_schema.native_u4b_policy import TERM_VALUES
    from data_sheets_schema.native_shared_contract import parse_receipt_policy
    def kind_version(kind):
        found = re.search(r'_v([0-9]+)$', kind)
        if found is None:
            raise ValueError('source kind has no explicit version suffix')
        return int(found.group(1))
    bundle = getattr(review, 'CURRENT_KIND', review.KIND)
    terms = getattr(review, 'CURRENT_TERMS_KIND', review.TERMS_KIND)
    return {'bundle_kind': bundle, 'bundle_version': kind_version(bundle),
            'terms_kind': terms, 'terms_version': kind_version(terms),
            'admission_terms': dict(TERM_VALUES),
            'receipt_instrument_version': literal_constraint(parse_receipt_policy, 'receipt_instrument_version'),
            'sequence_source': getattr(review, 'SEQUENCE_SOURCE', None)}


def validate_supplied(registration_raw, review_bundle_raw, launch_word_raw):
    from data_sheets_schema.native_launch_review import validate_bundle
    current = {'require_current': True} if 'require_current' in inspect.signature(validate_bundle).parameters else {}
    return validate_bundle(registration_raw, review_bundle_raw, launch_word_raw, **current)


def validate_supplied_terms(statement, runtime, *, word_owner):
    from data_sheets_schema.native_launch_review import validate_terms
    current = {'require_current': True} if 'require_current' in inspect.signature(validate_terms).parameters else {}
    return validate_terms(statement, runtime, word_owner=word_owner, **current)
