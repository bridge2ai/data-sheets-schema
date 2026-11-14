"""Approved v3 bundle/current v2 owner-term migration; offline component tests.

Old evidence remains a readback fixture, never current approval. No provider or
native executable is invoked; current endpoint refusals precede any effect.
"""
from copy import deepcopy
from pathlib import Path

import pytest

from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard as wire
from tests.test_native_launch_review import evidence
from tests.utils.native_review_v3_fixtures import current_bundle_for, sequence_pin


def reword(bundle, word):
    raw = wire.canonical(bundle)
    token = wire.strict_json(word)
    token['review_sha256'] = wire.sha(raw)
    return raw, wire.canonical(token)


@pytest.fixture
def current_evidence(evidence, tmp_path):
    outer = wire.strict_json(evidence[0])
    outer['registration']['dependencies']['base']['package_sources'] = sequence_pin()
    raw = wire.canonical(outer)
    bundle, word = current_bundle_for(raw, tmp_path / 'capture')
    return raw, bundle, word


def test_new_pair_and_history_are_explicit(current_evidence, evidence):
    raw, bundle, word = current_evidence
    assert review.validate_bundle(raw, bundle, word, require_current=True)['account_quiet'] is True
    assert review.validate_bundle(raw, bundle, word)['version'] == 2
    before = tuple(evidence)
    terms = review.validate_bundle(*evidence)
    assert terms['version'] == 1 and 'account_quiet' not in terms
    with pytest.raises(ValueError, match='readback only'):
        review.validate_bundle(*evidence, require_current=True)
    assert tuple(evidence) == before
    assert review.validate_bundle(*evidence) == terms


@pytest.mark.parametrize('mutation', [
    'kind', 'version', 'bool_version', 'missing_hash', 'extra', 'uppercase_hash',
    'wrong_hash', 'integer_hash', 'old_terms', 'unknown_terms', 'term_version',
    'term_bool_version', 'missing_quiet', 'extra_term', 'false', 'null', 'one', 'string'])
def test_closed_new_pair_mutations(current_evidence, mutation):
    raw, bundle_raw, word = current_evidence
    bundle = wire.strict_json(bundle_raw)
    terms = bundle['owner_statement']
    if mutation == 'kind': bundle['kind'] = 'unknown'
    elif mutation == 'version': bundle['version'] = 2
    elif mutation == 'bool_version': bundle['version'] = True
    elif mutation == 'missing_hash': del bundle['sequence_script_sha256']
    elif mutation == 'extra': bundle['extra'] = True
    elif mutation == 'uppercase_hash': bundle['sequence_script_sha256'] = bundle['sequence_script_sha256'].upper()
    elif mutation == 'wrong_hash': bundle['sequence_script_sha256'] = '0' * 64
    elif mutation == 'integer_hash': bundle['sequence_script_sha256'] = 1
    elif mutation == 'old_terms':
        terms.update(kind=review.TERMS_KIND, version=1)
        del terms['account_quiet']
    elif mutation == 'unknown_terms': terms['kind'] = 'unknown'
    elif mutation == 'term_version': terms['version'] = 1
    elif mutation == 'term_bool_version': terms['version'] = True
    elif mutation == 'missing_quiet': del terms['account_quiet']
    elif mutation == 'extra_term': terms['extra'] = True
    else: terms['account_quiet'] = {'false': False, 'null': None, 'one': 1, 'string': 'true'}[mutation]
    changed, token = reword(bundle, word)
    for current in (False, True):
        with pytest.raises(ValueError):
            review.validate_bundle(raw, changed, token, require_current=current)
    assert review.validate_bundle(*current_evidence, require_current=True)['account_quiet'] is True


def test_old_bundle_cannot_carry_new_terms(evidence):
    raw, bundle, word = evidence
    value = wire.strict_json(bundle)
    value['owner_statement'].update(kind=review.CURRENT_TERMS_KIND, version=2, account_quiet=True)
    changed, token = reword(value, word)
    with pytest.raises(ValueError, match='historical owner terms'):
        review.validate_bundle(raw, changed, token)


@pytest.mark.parametrize('mutation', ['missing', 'wrong', 'invalid'])
def test_registration_script_pin_is_required(current_evidence, tmp_path, mutation):
    outer = wire.strict_json(current_evidence[0])
    pins = outer['registration']['dependencies']['base']['package_sources']
    if mutation == 'missing': del pins[review.SEQUENCE_SOURCE]
    elif mutation == 'wrong': pins[review.SEQUENCE_SOURCE] = '0' * 64
    else: pins[review.SEQUENCE_SOURCE] = 1
    raw = wire.canonical(outer)
    # Construct fresh invented authority for the changed registration, then
    # explicitly retain the original reviewed script digest.
    from tests.utils.native_u4b_fixtures import bundle_for
    old_bundle, word = bundle_for(raw, tmp_path / 'capture')
    bundle = wire.strict_json(old_bundle)
    bundle.update(kind=review.CURRENT_KIND, version=3,
                  sequence_script_sha256=wire.strict_json(current_evidence[1])['sequence_script_sha256'])
    bundle['owner_statement'].update(kind=review.CURRENT_TERMS_KIND, version=2, account_quiet=True)
    changed, word = reword(bundle, word)
    with pytest.raises(ValueError, match='source pin'):
        review.validate_bundle(raw, changed, word)


def test_source_mutation_refuses_current_but_preserves_readback(current_evidence, tmp_path, monkeypatch):
    from data_sheets_schema import native_execution_authority_v2 as authority
    # Redirect only the source-authority root to an isolated copy; never mutate
    # registered production bytes. The genuine source-byte verifier runs.
    copied = tmp_path / 'source' / review.SEQUENCE_SOURCE
    copied.parent.mkdir(parents=True)
    copied.write_bytes((authority.ROOT / review.SEQUENCE_SOURCE).read_bytes())
    monkeypatch.setattr(review, 'SOURCE_ROOT', tmp_path / 'source')
    assert review.validate_bundle(*current_evidence, require_current=True)['account_quiet'] is True
    copied.write_bytes(copied.read_bytes() + b'\n# mutation\n')
    with pytest.raises(ValueError, match='source bytes'):
        review.validate_bundle(*current_evidence, require_current=True)
    assert review.validate_bundle(*current_evidence)['account_quiet'] is True


def test_packet_copy_has_independent_hash(current_evidence, tmp_path):
    from data_sheets_schema import native_execution_authority_v2 as authority
    packet = tmp_path / 'packet'
    packet.mkdir()
    script = packet / 'sequence-script.py'
    script.write_bytes((authority.ROOT / review.SEQUENCE_SOURCE).read_bytes())
    args = dict(zip(('registration_raw', 'review_bundle_raw', 'launch_word_raw'), current_evidence))
    expected = wire.strict_json(current_evidence[1])['sequence_script_sha256']
    assert review.validate_packet_script(packet, **args) == expected
    script.write_bytes(script.read_bytes() + b'\n# changed\n')
    (packet / 'sequence.json').write_bytes(wire.canonical({'sequence_script_sha256': expected}))
    with pytest.raises(ValueError, match='saved packet'):
        review.validate_packet_script(packet, **args)
    assert review.validate_bundle(*current_evidence)['account_quiet'] is True


@pytest.mark.parametrize('value', [1, None, 'true'])
def test_current_dispatch_requires_boolean(evidence, value):
    with pytest.raises(ValueError, match='boolean'):
        review.validate_bundle(*evidence, require_current=value)
    terms = wire.strict_json(evidence[1])['owner_statement']
    with pytest.raises(ValueError, match='boolean'):
        review.validate_terms(terms, review.registration_fields(evidence[0])['runtime'],
                              word_owner=terms['owner'], require_current=value)


@pytest.fixture
def historical_runtime(tmp_path, monkeypatch):
    from tests.test_native_subscription_capture import component
    from tests.utils.native_u4b_fixtures import bundle_for
    arguments, value = component(tmp_path, monkeypatch)
    raw, word = bundle_for(arguments['registration_raw'], arguments['directory'])
    arguments.update(review_bundle_raw=raw, launch_word_raw=word)
    return arguments, value


@pytest.mark.parametrize('endpoint', ['capture', 'activate', 'lease', 'guard', 'require',
                                     'read', 'event', 'context', 'preflight'])
def test_current_entry_points_refuse_old_before_effects(historical_runtime, tmp_path, monkeypatch, endpoint):
    from data_sheets_schema import native_subscription_capture as capture
    from data_sheets_schema import native_subscription_admission as admission
    from data_sheets_schema import native_capture_words as words
    arguments, value = historical_runtime
    args = {key: val for key, val in arguments.items() if key != 'directory'}
    manifest = tmp_path / 'retained' / 'capture.json'
    def forbidden(*a, **kw):
        pytest.fail('historical authority reached a current effect or capture reconstruction')
    monkeypatch.setattr(words, 'locked', forbidden)
    monkeypatch.setattr(capture, '_perform_capture', forbidden)
    from data_sheets_schema import native_subscription_guard_v2 as guard
    # A closed selection shape reaches the bundle gate; the unused guard
    # contents are not evidence and must never reach guard reconstruction.
    guard_raw = wire.canonical({**dict.fromkeys(guard.KEYS), 'kind': guard.KIND,
                               'version': 2, 'capture_index': 1, 'capture_claim_count': 1})
    if endpoint == 'preflight':
        paths = {}
        for name, raw in (('guard', guard_raw), ('word', args['launch_word_raw']), ('review', args['review_bundle_raw'])):
            paths[name] = tmp_path / (name + '.json')
            paths[name].write_bytes(raw)
        selected = admission.select_current(paths['guard'], wire.sha(guard_raw),
            registration_raw=args['registration_raw'], runtime=value['runtime'],
            launch_word_path=paths['word'], review_path=paths['review'])
    before = sorted(str(path) for path in tmp_path.rglob('*'))
    with pytest.raises(ValueError, match='historical review bundles are readback only'):
        if endpoint == 'capture': capture.capture_subscription(**arguments)
        elif endpoint == 'activate': capture.activate_capture_word(**args)
        elif endpoint == 'lease':
            with capture.capture_admission_lease(**args): pytest.fail('lease yielded')
        elif endpoint == 'guard':
            with capture.current_guard_preparation(manifest, **args): pytest.fail('guard yielded')
        elif endpoint == 'require': capture.require_current_capture_authority(**args)
        elif endpoint == 'read': capture.read_capture(manifest, **args, require_current=True)
        elif endpoint == 'event': capture.read_capture_for_event(arguments['directory'], **args,
            event_json='{}', event_sha256=wire.sha(b'{}'), captured_at='2026-11-08T00:00:00Z', require_current=True)
        elif endpoint == 'context': admission.context(guard_raw, **args, runtime=value['runtime'], current=True)
        elif endpoint == 'preflight': admission.preflight_current_selection(selected,
            registration_raw=args['registration_raw'], value=value)
    assert sorted(str(path) for path in tmp_path.rglob('*')) == before
    assert review.validate_bundle(**args)['version'] == 1


@pytest.mark.parametrize('command', ['capture-subscription-event', 'prepare-subscription-guard-v2', 'record-capture-word'])
def test_cli_current_commands_refuse_old_pair(historical_runtime, tmp_path, monkeypatch, command):
    from data_sheets_schema import native_generation as cli
    from data_sheets_schema import native_shared_registration_orchestration as registration
    from data_sheets_schema import native_shared_render as render
    from data_sheets_schema import native_subscription_capture as capture
    arguments, value = historical_runtime
    # Only metadata/account-choice/full registration prerequisites are isolated.
    # The genuine prepared runtime and bundle validators run before actuators.
    checked = deepcopy(value)
    checked['selection'] = {'render_spec': {}}
    monkeypatch.setattr(registration, 'verified', lambda raw: checked)
    monkeypatch.setattr(render, 'validate_metadata', lambda value: None)
    monkeypatch.setattr(cli, '_account_choice', lambda *a: b'{}')
    def forbidden(*a, **kw): pytest.fail('old pair reached a CLI actuator')
    for name in ('capture_subscription', 'current_guard_preparation', 'activate_capture_word'):
        monkeypatch.setattr(capture, name, forbidden)
    argv = [command]
    for flag, raw in (('registration', arguments['registration_raw']), ('review', arguments['review_bundle_raw']),
                      ('launch-word', arguments['launch_word_raw']), ('account-choice', b'{}')):
        path = tmp_path / (flag + '.json')
        path.write_bytes(raw)
        argv += ['--' + flag, str(path)]
    if command == 'capture-subscription-event': argv += ['--output-directory', str(arguments['directory'])]
    elif command == 'prepare-subscription-guard-v2':
        argv += ['--capture', str(tmp_path / 'capture.json'), '--output', str(tmp_path / 'guard.json')]
    with pytest.raises(ValueError, match='historical review bundles are readback only'):
        cli.main(argv)


from tests.test_native_execution_registration_v2 import fabricated_authorizations
from tests.test_native_u4b_addendum_authority import bundle_reader_case


def test_execution_reader_decouples_review_from_authority_version(bundle_reader_case):
    from data_sheets_schema import native_execution_registration_v2 as reader
    raw, value, records, paths, persist = bundle_reader_case
    kwargs = {name + '_path': path for name, path in paths.items()}
    old_bytes = {name: path.read_bytes() for name, path in paths.items()}
    assert reader._authorizations(raw, value, **kwargs)['review'].raw == old_bytes['review']
    with pytest.raises(ValueError, match='readback only'):
        reader._authorizations(raw, value, **kwargs, require_current=True)
    value = deepcopy(value)
    value['dependencies']['base']['package_sources'] = sequence_pin()
    envelope = wire.strict_json(raw)
    envelope['registration'] = value
    raw = wire.canonical(envelope)
    directory = Path(records['review']['owner_statement']['quota_capture']['directory'])
    new_bundle, word = current_bundle_for(raw, directory, records['launch_word']['authorized_at'])
    records['review'], records['launch_word'] = wire.strict_json(new_bundle), wire.strict_json(word)
    for key in review.BINDING_KEYS:
        records['ci'][key] = records['review'][key]
    records['launch_word']['ci_sha256'] = wire.sha(wire.canonical(records['ci']))
    persist()
    result = reader._authorizations(raw, value, **kwargs, require_current=True)
    assert wire.strict_json(result['review'].raw)['version'] == 3
    assert wire.strict_json(result['ci'].raw)['version'] == 2
    assert wire.strict_json(result['launch_word'].raw)['version'] == 2
    # Changing review version must not permit CI/word version drift.
    for name in ('ci', 'launch_word'):
        original = paths[name].read_bytes()
        body = wire.strict_json(original)
        body['version'] = 3
        paths[name].write_bytes(wire.canonical(body))
        with pytest.raises(ValueError, match='exact v2 execution'):
            reader._authorizations(raw, value, **kwargs, require_current=True)
        paths[name].write_bytes(original)


@pytest.mark.parametrize('endpoint', ['admit', 'engine_authorizations'])
def test_execution_frontdoors_require_current_pair(bundle_reader_case, monkeypatch, endpoint):
    from contextlib import contextmanager
    from data_sheets_schema import native_execution_registration_v2 as registration
    from data_sheets_schema import native_shared_execution_orchestration as engine
    from data_sheets_schema import native_shared_controls_orchestration as controls
    raw, value, _, paths, _ = bundle_reader_case
    kwargs = {name + '_path': path for name, path in paths.items()}
    monkeypatch.setattr(registration, 'verified', lambda *a, **kw: deepcopy(value))
    def forbidden(*a, **kw): pytest.fail('old pair reached execution paths or reservation')
    monkeypatch.setattr(registration, '_consumer', forbidden)
    monkeypatch.setattr(engine.registration, 'execution_paths_v2', forbidden)
    @contextmanager
    def isolated_controls(dependencies):
        yield object()
    monkeypatch.setattr(controls, 'loaded_controls', isolated_controls)
    with pytest.raises(ValueError, match='readback only'):
        if endpoint == 'admit': registration.admit(raw, **kwargs, classifier_projection=object())
        else: engine.authorizations(raw, value, **kwargs)


def test_old_guard_dispatch_is_evidence_only():
    from data_sheets_schema import native_subscription_admission as admission
    args = dict(registration_raw=b'old', runtime={'limits_basis': 'historical'},
                launch_word_raw=b'old', review_bundle_raw=b'old')
    assert admission.context(b'{"version":1}', **args)[0].VERSION == 1
    with pytest.raises(ValueError, match='historical v1 guard'):
        admission.context(b'{"version":1}', **args, current=True)


from tests.test_native_subscription_guard_v2 import case as historical_guard_case


def test_guard_v2_hashes_complete_new_terms_and_preserves_old_replay(historical_guard_case):
    from data_sheets_schema import native_subscription_guard_v2 as guard
    from tests.test_native_subscription_guard_v2 import build, saved
    case = historical_guard_case
    old = build(case)
    old.before_dispatch()
    old.observe(case['event'])
    old_snapshot = old.snapshot()
    transcript = wire.canonical(case['event']) + b'\n'
    baseline = saved(case, old, transcript, snapshot=old_snapshot, complete=True)
    assert baseline['passed'] is True
    owner = deepcopy(case['owner'])
    owner.update(kind=review.CURRENT_TERMS_KIND, version=2, account_quiet=True)
    document = deepcopy(case['document'])
    document['owner_statement_sha256'] = wire.sha(wire.canonical(owner))
    current = build(case, document=document, owner=owner)
    assert current.value['version'] == 2
    assert current.value['owner_statement_sha256'] != case['document']['owner_statement_sha256']
    for quiet in (False, None, 1, 'true'):
        changed = {**owner, 'account_quiet': quiet}
        with pytest.raises(ValueError):
            build(case, document=document, owner=changed)
        rehashed = {**document, 'owner_statement_sha256': wire.sha(wire.canonical(changed))}
        with pytest.raises(ValueError, match='account_quiet'):
            build(case, document=rehashed, owner=changed)
    assert saved(case, old, transcript, snapshot=old_snapshot, complete=True) == baseline
    incomplete = saved(case, old, transcript, snapshot=old_snapshot, complete=False)
    assert incomplete['checked'] is False and incomplete['passed'] is False
    assert incomplete['transcript_diagnostic']['observed_rate_limit_events'] == 1


def test_current_review_never_imports_verifier_bootstrap(current_evidence, monkeypatch):
    import builtins
    original = builtins.__import__
    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name.endswith('native_execution_authority_v2') or 'native_execution_authority_v2' in (fromlist or ()):
            pytest.fail('current review crossed the verifier bootstrap boundary')
        return original(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, '__import__', guarded)
    assert review.validate_bundle(*current_evidence, require_current=True)['account_quiet'] is True
