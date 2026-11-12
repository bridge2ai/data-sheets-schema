"""New invented v3/v2 review fixtures, separate from unchanged historical ones.

The named script pin is mandatory. These are offline component records, never
human approval or full-chain registration evidence (helper 2, 2026-11-12).
"""
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard as wire
from tests.utils.native_u4b_fixtures import bundle_for


def sequence_pin():
    from data_sheets_schema import native_execution_authority_v2 as authority
    return {review.SEQUENCE_SOURCE: wire.sha((authority.ROOT / review.SEQUENCE_SOURCE).read_bytes())}


def current_bundle_for(registration_raw, directory, now='2026-11-08T00:00:00Z'):
    """Build new wire bytes; never upgrade saved evidence or infer owner assent."""
    value = review.registration_fields(registration_raw)
    digest = value['dependencies']['base']['package_sources'][review.SEQUENCE_SOURCE]
    raw, word = bundle_for(registration_raw, directory, now)
    bundle, token = wire.strict_json(raw), wire.strict_json(word)
    bundle.update(kind=review.CURRENT_KIND, version=3, sequence_script_sha256=digest)
    bundle['owner_statement'].update(kind=review.CURRENT_TERMS_KIND, version=2, account_quiet=True)
    raw = wire.canonical(bundle)
    token['review_sha256'] = wire.sha(raw)
    return raw, wire.canonical(token)
