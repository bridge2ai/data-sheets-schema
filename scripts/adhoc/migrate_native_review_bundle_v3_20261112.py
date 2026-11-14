#!/usr/bin/env python3
"""Apply approved helper-2 Part C migration, 2026-11-12.
Inputs: launch-sequence branch sources. Outputs: versioned readers and gates.
Serves the eligibility-audit-and-bundle-v3 assignment; offline, no pin updates.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def edit(name, old, new, count=1):
    path = ROOT / 'src/data_sheets_schema' / name
    raw = path.read_text()
    assert raw.count(old) == count, (name, old, raw.count(old))
    path.write_text(raw.replace(old, new))
edit('native_launch_review.py', "TERMS_KIND = 'd4d_native_owner_launch_terms_v1'", """TERMS_KIND = 'd4d_native_owner_launch_terms_v1'
# Historical names remain stable for retained evidence and fixtures.
CURRENT_KIND = 'd4d_native_execution_review_bundle_v3'
CURRENT_TERMS_KIND = 'd4d_native_owner_launch_terms_v2'
SEQUENCE_SOURCE = 'src/data_sheets_schema/native_launch_sequence.py'""")
edit('native_launch_review.py', 'def validate_terms(statement, runtime, *, word_owner):', 'def validate_terms(statement, runtime, *, word_owner, require_current=False):')
edit('native_launch_review.py', "    _exact(statement, TERMS_KEYS, 'owner launch terms')\n    _version(statement, TERMS_KIND, 1)", """    if type(require_current) is not bool:
        raise ValueError('current owner terms selection must be boolean')
    current = type(statement) is dict and statement.get('kind') == CURRENT_TERMS_KIND
    _exact(statement, TERMS_KEYS | ({'account_quiet'} if current else set()), 'owner launch terms')
    _version(statement, CURRENT_TERMS_KIND if current else TERMS_KIND, 2 if current else 1)
    if require_current and not current:
        raise ValueError('historical owner terms are readback only')
    # Owner declaration, not authenticated account telemetry: every session on
    # the registered account stands down before capture through attempt end,
    # including sessions that would monitor account utilization.
    if current and statement['account_quiet'] is not True:
        raise ValueError('owner must explicitly confirm account_quiet as boolean true')""")
edit('native_launch_review.py', 'def validate_bundle(registration_raw, review_bundle_raw, launch_word_raw):', 'def validate_bundle(registration_raw, review_bundle_raw, launch_word_raw, *, require_current=False):')
edit('native_launch_review.py', '    value = registration_fields(registration_raw)', """    if type(require_current) is not bool:
        raise ValueError('current review selection must be boolean')
    value = registration_fields(registration_raw)""")
edit('native_launch_review.py', "    _exact(bundle, BINDING_KEYS | {'kind', 'version', 'author', 'operator', 'reviews',\n                                 'owner_statement', 'registration_commit'}, 'review bundle')\n    _version(bundle, KIND, 2)", """    current = type(bundle) is dict and bundle.get('kind') == CURRENT_KIND
    _exact(bundle, BINDING_KEYS | {'kind', 'version', 'author', 'operator', 'reviews',
                                 'owner_statement', 'registration_commit'} |
           ({'sequence_script_sha256'} if current else set()), 'review bundle')
    _version(bundle, CURRENT_KIND if current else KIND, 3 if current else 2)
    if require_current and not current:
        raise ValueError('historical review bundles are readback only')
    if current:
        digest = bundle['sequence_script_sha256']
        if type(digest) is not str or re.fullmatch('[0-9a-f]{64}', digest) is None:
            raise ValueError('sequence script requires lowercase sha256')
        try:
            registered = value['dependencies']['base']['package_sources'][SEQUENCE_SOURCE]
        except (KeyError, TypeError) as exc:
            raise ValueError('registration lacks the sequence script source pin') from exc
        if registered != digest:
            raise ValueError('sequence script differs from registered source pin')
        if require_current:
            from . import native_execution_authority_v2 as authority
            authority._verified_source_bytes(authority.ROOT / SEQUENCE_SOURCE, digest)""")
edit('native_launch_review.py', "    statement = validate_terms(bundle['owner_statement'], runtime, word_owner=word['owner'])", """    statement = validate_terms(bundle['owner_statement'], runtime, word_owner=word['owner'],
                               require_current=current)
    if not current and statement['kind'] != TERMS_KIND:
        raise ValueError('historical review bundle requires historical owner terms')""")
edit('native_launch_review.py', '\ndef registration_fields(raw):', '''
def validate_packet_script(packet_directory, *, registration_raw, review_bundle_raw, launch_word_raw):
    """Verify retained script bytes against a v3 bundle, without current admission.

    A sequence record's asserted digest/path is never used. This proves only
    the copied script binding; it does not approve the packet or its execution.
    """
    validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)
    bundle = wire.strict_json(review_bundle_raw)
    if bundle['kind'] != CURRENT_KIND:
        raise ValueError('historical review bundle has no sequence script pin')
    raw = wire.read_regular(Path(packet_directory) / 'sequence-script.py')
    if wire.sha(raw) != bundle['sequence_script_sha256']:
        raise ValueError('saved packet sequence script differs from the review bundle')
    return bundle['sequence_script_sha256']


def registration_fields(raw):''')
edit('native_execution_registration_v2.py', 'def _authorizations(raw, value, *, review_path, ci_path, launch_word_path):', 'def _authorizations(raw, value, *, review_path, ci_path, launch_word_path, require_current=False):')
edit('native_execution_registration_v2.py', "    paths = {'review': str(review_path), 'ci': str(ci_path), 'launch_word': str(launch_word_path)}", """    if type(require_current) is not bool:
        raise ValueError('current execution authorization selection must be boolean')
    paths = {'review': str(review_path), 'ci': str(ci_path), 'launch_word': str(launch_word_path)}""")
edit('native_execution_registration_v2.py', "                or record['version'] != VERSION or any(record.get(k) != v for k, v in binding.items())):", "                or (name != 'review' and record['version'] != VERSION)\n                or any(record.get(k) != v for k, v in binding.items())):")
edit('native_execution_registration_v2.py', "    if review.get('kind') == launch_review.KIND:\n        launch_review.validate_bundle(raw, captured['review'].raw, captured['launch_word'].raw)", """    if review.get('kind') in (launch_review.KIND, launch_review.CURRENT_KIND):
        launch_review.validate_bundle(raw, captured['review'].raw, captured['launch_word'].raw,
                                      require_current=require_current)""")
edit('native_execution_registration_v2.py', "        if is_prepared_runtime(value.get('runtime')):", "        if require_current or is_prepared_runtime(value.get('runtime')):")
edit('native_execution_registration_v2.py', "        if review['kind'] != 'd4d_native_execution_review_v2':", "        if review['kind'] != 'd4d_native_execution_review_v2' or review['version'] != VERSION:")
edit('native_execution_registration_v2.py', '                               launch_word_path=launch_word_path)', '                               launch_word_path=launch_word_path, require_current=True)')
edit('native_execution_orchestration.py', "        ci_path=inputs['ci'], launch_word_path=inputs['launch_word'])", "        ci_path=inputs['ci'], launch_word_path=inputs['launch_word'], require_current=True)")
edit('native_generation.py', '        review.validate_bundle(subject_raw, bundle_raw, word_raw)', '        review.validate_bundle(subject_raw, bundle_raw, word_raw, require_current=True)')
edit('native_subscription_admission.py', '    terms = review.validate_bundle(registration_raw, bundle, word)', '    terms = review.validate_bundle(registration_raw, bundle, word, require_current=True)')
edit('native_subscription_admission.py', '        if is_prepared_runtime(runtime):', '        if current or is_prepared_runtime(runtime):')
edit('native_subscription_admission.py', '    terms = review.validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)', '    terms = review.validate_bundle(registration_raw, review_bundle_raw, launch_word_raw,\n                                   require_current=current)')
# Validate before reconstruction, journalling, reservation or a process.
edit('native_subscription_capture.py', "    from .native_launch_review import registration_fields\n", "    from .native_launch_review import registration_fields, validate_bundle\n")
edit('native_subscription_capture.py', "    require_production(registration_fields(registration_raw)['runtime'])", "    require_production(registration_fields(registration_raw)['runtime'])\n    validate_bundle(registration_raw, review_bundle_raw, launch_word_raw, require_current=True)")
edit('native_subscription_capture.py', "def _current_authority(registration_raw, review_bundle_raw, launch_word_raw):\n    from .native_launch_review import validate_bundle\n    statement = validate_bundle(registration_raw, review_bundle_raw, launch_word_raw)", "def _current_authority(registration_raw, review_bundle_raw, launch_word_raw):\n    from .native_launch_review import validate_bundle\n    statement = validate_bundle(registration_raw, review_bundle_raw, launch_word_raw, require_current=True)")
# Use explicit current dispatch for both public readback entry points; history
# keeps the original authority reconstruction and does not require live source.
edit('native_subscription_capture.py', "    authority = _authority(registration_raw, review_bundle_raw, launch_word_raw, root)\n    return _read_capture_records(", "    authority = (_current_authority(registration_raw, review_bundle_raw, launch_word_raw)\n                 if require_current else\n                 _authority(registration_raw, review_bundle_raw, launch_word_raw, root))\n    return _read_capture_records(")
edit('native_subscription_capture.py', "    authority = _authority(registration_raw, review_bundle_raw, launch_word_raw, directory)\n    directory = _read_root", "    authority = (_current_authority(registration_raw, review_bundle_raw, launch_word_raw)\n                 if require_current else\n                 _authority(registration_raw, review_bundle_raw, launch_word_raw, directory))\n    if directory != _path(authority[1]['quota_capture']['directory']):\n        raise ValueError('capture directory differs from the owner statement')\n    directory = _read_root")
