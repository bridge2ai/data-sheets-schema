"""Version-isolated G13 review/owner adapter, 2026-11-12.

Only delegates validation of supplied bytes. Never constructs an owner word,
review, or terms document. This branch uses bundle v2 / terms v1. Switch this
adapter with helper2's reviewed versions before production packet assembly.
"""
BUNDLE_VERSION = 2
TERMS_VERSION = 1


def validate_supplied(registration_raw, review_bundle_raw, launch_word_raw):
    from data_sheets_schema.native_launch_review import validate_bundle
    return validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)


def validate_supplied_terms(statement, runtime, *, word_owner):
    from data_sheets_schema.native_launch_review import validate_terms
    return validate_terms(statement, runtime, word_owner=word_owner)
