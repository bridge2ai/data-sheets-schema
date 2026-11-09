"""Invented closed-profile evidence for U3-J2 public software tests, 2026-11-09.

Inputs are fictional fixture values and the committed ordinary-Python peer.
Outputs are explicitly synthetic saved evidence consumed by real validators.
No observation, capture, native executable, provider or account is invoked.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys

from data_sheets_schema import native_shared_contract as c


def runtime_for(data, root):
    """Bind saved fake observations and two distinct copies of the fixed peer."""
    from data_sheets_schema import native_model_aliases as aliases
    from data_sheets_schema import native_u4b_runtime as runtime_api
    from data_sheets_schema.native_runtime_profiles import SYNTHETIC_PROFILE
    from tests.utils.native_u4b_observation import mint_observation
    from tests.utils.native_u4b_fixtures import admission_policy

    root = Path(root).resolve()
    directory = root / 'synthetic-runtime'
    directory.mkdir()
    updater = directory / 'updater'
    updater.mkdir()
    source, copied = updater / 'current', directory / 'ordinary-python-test-peer'
    peer = Path(__file__).parents[1] / 'fixtures/native_shared_execution/fake_cli.py'
    binary = ('#!' + sys.executable + '\n').encode() + peer.read_bytes()
    for path in (source, copied):
        path.write_bytes(binary)
        path.chmod(0o700)
    home = directory / 'synthetic-home'
    home.mkdir()
    pair = {'requested': 'synthetic-native-model', 'returned': 'synthetic-native-returned-model'}
    runtime = deepcopy(c.strict_json(data['runtime_path'].read_bytes()))
    runtime.update(model=pair['requested'], auxiliary_models=[], effort='high',
        provider='scripted-local', deadline_seconds=900, budget_guard_usd='1.0',
        executable={'path': str(copied), 'sha256': c.sha(binary),
            'version': 'SYNTHETIC PYTHON SOFTWARE TEST', 'init_version': 'synthetic-python-1'},
        auth={'loggedIn': False, 'authMethod': SYNTHETIC_PROFILE, 'apiProvider': 'scripted-local',
            'subscriptionType': SYNTHETIC_PROFILE, 'expected_api_key_source': 'none'},
        environment={'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin',
            'HOME': str(home), 'CLAUDE_SECURESTORAGE_CONFIG_DIR': '',
            'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'},
        limits_basis=c.canonical({'kind': aliases.PROVISIONAL_KIND, 'version': 1,
            'model_aliases': pair, 'profile': SYNTHETIC_PROFILE}).decode())
    runtime['keep_awake']['policy'] = 'not_applicable'
    runtime['keep_awake']['host_platform'] = sys.platform
    runtime['keep_awake']['basis'] = 'Synthetic software-test host; no native acceptance.'
    observation = directory / 'probe-sequence' / 'observation'
    observation.mkdir(parents=True)
    session = 'invented-synthetic-observation'
    rows = [
        {'type': 'system', 'subtype': 'init', 'model': pair['requested'],
            'claude_code_version': runtime['executable']['init_version'], 'session_id': session,
            'apiKeySource': 'ANTHROPIC_API_KEY'},
        {'type': 'assistant', 'session_id': session,
            'message': {'model': pair['returned'], 'content': []}},
        {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': session,
            'modelUsage': {pair['requested']: deepcopy(runtime['limits'])}},
    ]
    transcript = observation / 'transcript.jsonl'
    transcript.write_bytes(b''.join(c.canonical(row) + b'\n' for row in rows))
    request = observation / 'native_request.json'
    request.write_bytes(c.canonical({'model': pair['returned'], 'thinking': {'type': 'adaptive'}}))
    manifest = mint_observation(runtime, transcript, request)
    prepared = runtime_api.prepare_synthetic(runtime, probe_init_path=str(transcript),
        native_request_path=str(request), updater_source=str(source), updater_root=str(updater),
        thinking_setting={'type': 'adaptive'},
        thinking_basis='Invented scripted observation, never a real native/provider request.',
        observation_probe_path=str(manifest), admission_policy=admission_policy(root / 'synthetic-capture'))
    (directory / 'SYNTHETIC-EVIDENCE.txt').write_text(
        'Every observation and authority in this directory is fabricated software-test evidence.\n'
        'No native binary, provider or account was observed; this is not native acceptance.\n')
    return prepared


def bound_permission_for(expected, selection, source_raw):
    """Save the full seven traces and acyclic sequence without running a probe."""
    from data_sheets_schema import native_u4b_probe_sequence as sequence
    from tests.test_native_shared_permissions import fabricated_manifest

    runtime = expected['runtime']
    basis = c.strict_json(runtime['limits_basis'].encode())
    observed = sequence.validate_observation(basis['observation_probe']['path'],
        expected_pin=basis['observation_probe'], final_runtime=runtime,
        transcript_path=basis['probe']['path'], request_path=basis['request']['path'])
    root = Path(observed['sequence_directory'])
    auth_raw = (root / 'authorization.json').read_bytes()
    expected_raw = c.canonical(expected)
    claim = sequence._bound_claim(auth_raw, observed, runtime, expected_raw)
    claim_raw = c.canonical(claim)
    (root / 'bound-claim.json').write_bytes(claim_raw)
    (root / 'expectation.json').write_bytes(expected_raw)
    probe = root / 'permission' / 'permission-probe.json'
    probe.parent.mkdir()
    manifest = fabricated_manifest(expected, selection, probe.parent, source_raw)
    raw = c.canonical(manifest)
    probe.write_bytes(raw)
    completion = {'kind': sequence.COMPLETION_KIND, 'version': 1,
        'authorization_sha256': c.sha(auth_raw), 'observation': observed['pin'],
        'runtime_sha256': c.sha(c.canonical(runtime)),
        'expectation': sequence._pin(root / 'expectation.json', expected_raw),
        'claim': sequence._pin(root / 'bound-claim.json', claim_raw),
        'permission': sequence._pin(probe, raw), 'basis': sequence.BASIS}
    (root / 'sequence.json').write_bytes(c.canonical(completion))
    assert sequence.validate_bound_probe(runtime, probe)['passed'] is True
    return probe


def authority_for(registration_raw, ci_path, directory):
    """Mint fresh labelled review/capture/guard bytes; use genuine saved readers."""
    from data_sheets_schema import native_subscription_capture as capture
    from data_sheets_schema import native_subscription_guard_v2 as guard
    from data_sheets_schema import native_launch_review as review
    from data_sheets_schema import native_shared_registration_orchestration as registration
    from tests.utils.native_u4b_fixtures import bundle_for

    value = registration.verified(registration_raw)
    runtime = value['runtime']
    basis = c.strict_json(runtime['limits_basis'].encode())
    capture_root = Path(basis['admission']['capture_state_directory'])
    now = datetime.now(timezone.utc)
    stamp = now.isoformat().replace('+00:00', 'Z')
    review_raw, word_raw = bundle_for(registration_raw, capture_root, now=stamp)
    word = c.strict_json(word_raw)
    word['ci_sha256'] = c.sha(ci_path.read_bytes())
    word_raw = c.canonical(word)
    terms = review.validate_bundle(registration_raw, review_raw, word_raw)
    capture.activate_capture_word(registration_raw=registration_raw,
        review_bundle_raw=review_raw, launch_word_raw=word_raw)
    _, _, _, binding = capture._authority(registration_raw, review_raw, word_raw, capture_root)
    reservation = capture_root / 'captures' / c.sha(word_raw)
    reservation.mkdir(parents=True)
    reserve_raw = capture._reservation_raw(reservation, terms['quota_capture'], binding)
    (reservation / 'reserve.json').write_bytes(reserve_raw)
    slot = reservation / 'capture-1'
    slot.mkdir()
    bound = capture._slot_binding(binding, 1, reserve_raw, None)
    # The word predates authority reconstruction. The invented capture is made
    # only now: do not age its observation by reusing that earlier word time.
    capture_now = datetime.now(timezone.utc)
    capture_stamp = capture_now.isoformat().replace('+00:00', 'Z')
    claim = capture._claim(slot, terms['quota_capture'], runtime, bound, capture_stamp)
    claim_raw = c.canonical(claim)
    (reservation / 'claim-1.json').write_bytes(claim_raw)
    (slot / 'claim.json').write_bytes(claim_raw)
    event = {'type': 'rate_limit_event', 'rate_limit_info': {
        'status': 'allowed', 'isUsingOverage': False, 'unifiedWindows': {
            name: {'status': 'allowed', 'utilization': 0.2, 'resetsAt': int(capture_now.timestamp()) + 86400}
            for name in ('five_hour', 'seven_day')}}}
    session = 'invented-synthetic-capture'
    rows = [{'type': 'system', 'subtype': 'init', 'model': runtime['model'],
        'claude_code_version': runtime['executable']['init_version'], 'session_id': session,
        'apiKeySource': 'none'}, event,
        {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': session,
            'modelUsage': {runtime['model']: deepcopy(runtime['limits'])}}]
    stdout = b''.join(c.canonical(row) + b'\n' for row in rows)
    event_raw = c.canonical(event)
    observations = [{'line': 2, 'captured_at': capture_stamp,
        'event_sha256': c.sha(event_raw), 'event_json': event_raw.decode()}]
    files = {'stdout.jsonl': stdout, 'stderr.txt': b'',
        'observations.json': c.canonical(observations)}
    result = {'kind': capture.KIND, 'version': capture.VERSION, **bound, 'status': 'captured',
        'claim_sha256': c.sha(claim_raw), 'selected_event': capture._event(stdout, observations, capture_stamp),
        'terminal': capture._terminal(stdout, runtime), 'basis': capture.BASIS,
        'lifecycle': {'spawn_count': 1, 'returncode': 0,
            'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}},
        'files': {name: {'sha256': c.sha(raw), 'bytes': len(raw)} for name, raw in files.items()}}
    for name, raw in files.items():
        (slot / name).write_bytes(raw)
    manifest = slot / 'capture.json'
    manifest.write_bytes(c.canonical(result))
    captured = capture.read_capture(manifest, registration_raw=registration_raw,
        review_bundle_raw=review_raw, launch_word_raw=word_raw, require_current=True)
    selected = captured['selected_event']
    guard_raw = guard.prepare_guard(registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=word_raw, event_raw=selected['event_json'].encode(),
        captured_at=selected['captured_at'], owner_statement=terms,
        maximum_starting_utilization=terms['max_starting_weekly_utilization'],
        max_age_seconds=terms['max_age_seconds'])
    review_path, word_path, guard_path = (directory / name for name in (
        'invented-review.json', 'invented-owner.json', 'invented-subscription.json'))
    for path, raw in ((review_path, review_raw), (word_path, word_raw), (guard_path, guard_raw)):
        path.write_bytes(raw)
    (directory / 'SYNTHETIC-AUTHORITY.txt').write_text(
        'Fabricated software-test review, CI, word, capture and quota declarations.\n'
        'No actual reviewers, native captures, account evidence or launch approval.\n')
    return {'review_path': review_path, 'ci_path': ci_path, 'launch_word_path': word_path,
        'subscription_guard_path': guard_path, 'subscription_guard_sha256': c.sha(guard_raw)}
