"""Source-derived review/owner adapter; never constructs an authorization.

The running source owns kind/version and admission terms. Current validators
are requested where supported; old sources remain usable only for their own
historical contract. No margin or schema version is copied into this adapter.
"""
import inspect
import re


def source_contract():
    from data_sheets_schema import native_launch_review as review
    from data_sheets_schema.native_u4b_policy import TERM_VALUES
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
            'sequence_source': getattr(review, 'SEQUENCE_SOURCE', None)}


def validate_supplied(registration_raw, review_bundle_raw, launch_word_raw):
    from data_sheets_schema.native_launch_review import validate_bundle
    current = {'require_current': True} if 'require_current' in inspect.signature(validate_bundle).parameters else {}
    return validate_bundle(registration_raw, review_bundle_raw, launch_word_raw, **current)


def validate_supplied_terms(statement, runtime, *, word_owner):
    from data_sheets_schema.native_launch_review import validate_terms
    current = {'require_current': True} if 'require_current' in inspect.signature(validate_terms).parameters else {}
    return validate_terms(statement, runtime, word_owner=word_owner, **current)
