"""U4b capture component tests; only a scripted Python fake is executable.

Registration reconstruction alone is isolated because the complete protected
constructor remains an integration gate. The actual review/word validator,
saved runtime evidence, process supervisor, durable claim and readback execute.
These tests do not prove full-chain registration or real subscription acceptance.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_shared_registration_orchestration as registration
from data_sheets_schema import native_u4b_runtime as runtime_evidence
from tests.test_native_u4b_runtime import runtime_inputs
from tests.utils.native_review_v3_fixtures import current_bundle_for as bundle_for


def peer(mode):
    """Fixed local script bytes, not a native/provider executable or live prompt."""
    body = '''import json, os, sys, time
assert sys.argv[-1] == 'Reply with OK.'
assert sys.argv[sys.argv.index('--tools') + 1] == ''
assert sys.argv[sys.argv.index('--setting-sources') + 1] == ''
assert sys.argv[sys.argv.index('--mcp-config') + 1] == '{"mcpServers":{}}'
assert sys.argv[sys.argv.index('--settings') + 1] == '{"disableAllHooks":true}'
assert not any(key in os.environ for key in ('ANTHROPIC_API_KEY','OPENAI_API_KEY',
    'CBORG_API_KEY','CLAUDE_CODE_OAUTH_TOKEN','PYTHONPATH','PYTEST_ADDOPTS'))
print(json.dumps({'type':'system','subtype':'init','synthetic':True,
    'argv':sys.argv[1:],'cwd':os.getcwd(),'config':os.environ['CLAUDE_CONFIG_DIR']}), flush=True)
MODE = %r
if MODE == 'timeout':
    time.sleep(10)
if MODE == 'overflow':
    print('x' * 1048577, flush=True)
    time.sleep(10)
    raise SystemExit(0)
if MODE == 'malformed':
    print('{broken', flush=True)
    raise SystemExit(0)
if MODE != 'missing':
    print(json.dumps({'type':'rate_limit_event','rate_limit_info':{
        'status':'allowed','isUsingOverage':False,'unifiedWindows':{
            'seven_day':{'status':'allowed','utilization':0.2,'resetsAt':int(time.time())+3600},
            'five_hour':{'status':'allowed','utilization':0.1,'resetsAt':int(time.time())+1800}}}}), flush=True)
if MODE == 'nonzero':
    print('synthetic failed capture', file=sys.stderr, flush=True)
    raise SystemExit(7)
if MODE != 'missing_terminal':
    limits = {'contextWindow':1000000,'maxOutputTokens':64000}
    if MODE in ('mismatch', 'mismatch_nonzero') or (MODE == 'second_mismatch' and os.path.basename(os.path.dirname(os.getcwd())) == 'capture-2'):
        limits['contextWindow'] = 200000
    print(json.dumps({'type':'result','subtype':'success','is_error':False,
        'modelUsage':{'claude-opus-5[1m]':limits}}), flush=True)
if MODE == 'mismatch_nonzero':
    raise SystemExit(7)
''' % mode
    return ('#!' + sys.executable + '\n' + body).encode()


def component(tmp_path, monkeypatch, *, mode='success', deadline=5):
    from tests.utils.native_review_v3_fixtures import sequence_pin
    # Capture traps/counters must observe the capture child, not mutate the
    # shared stdlib module used by genuine registration-commit Git reads.
    monkeypatch.setattr(capture, 'subprocess', SimpleNamespace(
        Popen=subprocess.Popen, DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE))
    runtime, arguments = runtime_inputs(tmp_path, binary_bytes=peer(mode))
    runtime = runtime_evidence.prepare_runtime(runtime, **arguments)
    source = tmp_path / 'source.txt'
    source.write_text('PRIVATE REPOSITORY CONTENT MUST NOT ENTER CAPTURE PROMPT\n')
    value = {'attempt_id': 'invented-capture-component', 'runtime': runtime,
        'attempt_directory': str(tmp_path / 'generation-attempt'),
        'evidence_directory': str(tmp_path / 'generation-evidence'),
        'composition': str(tmp_path / 'composition.json'),
        'system_path': str(tmp_path / 'system.md'),
        'permission_probe': str(tmp_path / 'permission.json'), 'permission_probe_sha256': '2' * 64,
        'composition_raw_json': json.dumps({'policy': {'readonly_lookups': {
            'inputs': [str(source)], 'output_directories': [str(tmp_path / 'outputs')]}}}),
        'dependencies': {'base': {'source_commit': 'a' * 40,
                                  'package_sources': sequence_pin()}}}
    raw = capture.canonical({'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
                             'registration': value})
    directory = tmp_path / 'one-capture'
    now = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat().replace('+00:00', 'Z')
    bundle_raw, word_raw = bundle_for(raw, directory, now=now)
    bundle, word = capture.strict_json(bundle_raw), capture.strict_json(word_raw)
    bundle['owner_statement']['quota_capture']['deadline_seconds'] = deadline
    bundle_raw = capture.canonical(bundle)
    word['review_sha256'] = capture.sha(bundle_raw)
    word_raw = capture.canonical(word)

    def fixture_reconstruction(submitted):
        assert submitted == raw, 'component isolation cannot accept substituted registration bytes'
        return deepcopy(value)

    def fixture_recheck(submitted, initial):
        envelope = capture.strict_json(submitted)
        if (envelope != {'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
                         'registration': initial}
                or capture.canonical(envelope) != submitted):
            raise ValueError('component isolation rejected mismatched registration recheck')
        if submitted == raw and initial != value:
            raise ValueError('component registration value changed during event lookup')
        return deepcopy(value if submitted == raw else initial)

    monkeypatch.setattr(registration, 'verified', fixture_reconstruction)
    monkeypatch.setattr(registration, '_recheck_verified', fixture_recheck)
    return {'registration_raw': raw, 'review_bundle_raw': bundle_raw,
            'launch_word_raw': word_raw, 'directory': directory}, value


def read_arguments(arguments):
    return {key: value for key, value in arguments.items() if key != 'directory'}


def word_directory(arguments):
    return arguments['directory'] / 'captures' / capture.sha(arguments['launch_word_raw'])


def test_one_fake_capture_persists_exact_observation_and_refuses_reuse(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    for key in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'CBORG_API_KEY',
                'CLAUDE_CODE_OAUTH_TOKEN', 'PYTHONPATH', 'PYTEST_ADDOPTS'):
        monkeypatch.setenv(key, 'invented-forbidden-inherited-value')
    original = capture.subprocess.Popen
    calls = []

    def child(argv, **kwargs):
        assert (word_directory(arguments) / 'claim-1.json').is_file()
        assert (word_directory(arguments) / 'capture-1' / 'claim.json').is_file()
        assert not Path(value['attempt_directory']).exists()
        assert not Path(value['evidence_directory']).exists()
        calls.append((argv, kwargs))
        return original(argv, **kwargs)

    monkeypatch.setattr(capture.subprocess, 'Popen', child)
    manifest = capture.capture_subscription(**arguments)
    assert manifest.is_file() and manifest.stat().st_size > 0
    result = capture.read_capture(manifest, **read_arguments(arguments))
    assert result['status'] == 'captured'
    assert result['lifecycle'] == {'spawn_count': 1, 'returncode': 0,
        'cleanup': {'child_started': True, 'leader_reaped': True, 'group_absent': True}}
    assert len(calls) == 1 and calls[0][0][0] == value['runtime']['executable']['path']
    assert calls[0][0][-1] == capture.CAPTURE_PROMPT
    assert '--version' not in calls[0][0] and 'auth' not in calls[0][0]
    stdout = (manifest.parent / 'stdout.jsonl').read_bytes()
    assert b'PRIVATE REPOSITORY CONTENT' not in stdout
    init = json.loads(stdout.splitlines()[0])
    assert init['cwd'] == str(manifest.parent / 'cwd')
    assert init['config'] == str(manifest.parent / 'config')
    event = result['selected_event']
    assert event['line'] == 2
    assert event['event_json'].encode() == stdout.splitlines()[1]
    assert event['event_sha256'] == capture.sha(stdout.splitlines()[1])
    assert capture._timestamp(event['captured_at']) >= capture._timestamp(
        capture.strict_json(arguments['launch_word_raw'])['authorized_at'])
    assert manifest.parent == word_directory(arguments) / 'capture-1'
    assert not (word_directory(arguments) / 'capture-2').exists()
    with pytest.raises(ValueError, match='directory differs'):
        capture.capture_subscription(**{**arguments, 'directory': manifest.parent})
    assert len(calls) == 1


@pytest.mark.parametrize('mode,error', [('missing', ValueError), ('malformed', ValueError),
    ('nonzero', ValueError), ('overflow', ValueError), ('timeout', TimeoutError)])
def test_failed_fake_capture_retains_claim_streams_and_cannot_retry(tmp_path, monkeypatch, mode, error):
    arguments, _ = component(tmp_path, monkeypatch, mode=mode, deadline=1 if mode == 'timeout' else 5)
    with pytest.raises(error):
        capture.capture_subscription(**arguments)
    root = word_directory(arguments) / 'capture-1'
    result = json.loads((root / 'capture.json').read_bytes())
    assert result['status'] == 'failed' and result['error']
    assert result['lifecycle']['spawn_count'] == 1
    assert result['lifecycle']['cleanup']['group_absent'] is True
    for name in ('claim.json', 'stdout.jsonl', 'stderr.txt', 'observations.json'):
        assert (root / name).is_file()
    assert (root / 'stdout.jsonl').stat().st_size <= capture.MAX_STREAM_BYTES
    with pytest.raises(ValueError):
        capture.read_capture(root / 'capture.json', **read_arguments(arguments))
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('spent capture spawned again'))
    with pytest.raises(ValueError, match='directory differs'):
        capture.capture_subscription(**{**arguments, 'directory': root})


@pytest.mark.parametrize('change', ['review_hash', 'extra_word_field', 'two_captures', 'prompt',
    'directory', 'overlap_attempt', 'source_tree', 'runtime_key', 'changed_binary', 'future_word'])
def test_invalid_bindings_refuse_before_any_claim_or_spawn(tmp_path, monkeypatch, change):
    arguments, value = component(tmp_path, monkeypatch)
    bundle = capture.strict_json(arguments['review_bundle_raw'])
    word = capture.strict_json(arguments['launch_word_raw'])
    if change == 'review_hash':
        word['review_sha256'] = 'f' * 64
    elif change == 'extra_word_field':
        word['allow_more'] = True
    elif change == 'two_captures':
        bundle['owner_statement']['quota_capture']['count'] = 2
    elif change == 'prompt':
        bundle['owner_statement']['quota_capture']['prompt_sha256'] = 'f' * 64
    elif change == 'directory':
        arguments['directory'] = tmp_path / 'unapproved-directory'
    elif change in ('overlap_attempt', 'source_tree'):
        target = Path(value['attempt_directory']) if change == 'overlap_attempt' else capture.ROOT / 'new-capture'
        arguments['directory'] = target
        bundle['owner_statement']['quota_capture']['directory'] = str(target)
    elif change == 'runtime_key':
        value['runtime']['environment']['ANTHROPIC_API_KEY'] = 'invented-key'
    elif change == 'changed_binary':
        Path(value['runtime']['executable']['path']).write_bytes(b'changed after registration')
    else:
        word['authorized_at'] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
    arguments['review_bundle_raw'] = capture.canonical(bundle)
    if change != 'review_hash':
        word['review_sha256'] = capture.sha(arguments['review_bundle_raw'])
    arguments['launch_word_raw'] = capture.canonical(word)
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('invalid capture spawned'))
    with pytest.raises(ValueError):
        capture.capture_subscription(**arguments)
    assert not arguments['directory'].exists()


@pytest.mark.parametrize('change', ['stdout', 'observations', 'claim', 'lifecycle_type',
                                   'result_index_type', 'selected_event'])
def test_saved_capture_reconstructs_and_refuses_changed_evidence(tmp_path, monkeypatch, change):
    arguments, _ = component(tmp_path, monkeypatch)
    path = capture.capture_subscription(**arguments)
    result = json.loads(path.read_bytes())
    if change == 'stdout':
        (path.parent / 'stdout.jsonl').write_bytes(b'{}\n')
    elif change == 'observations':
        (path.parent / 'observations.json').write_bytes(b'[]')
    elif change == 'claim':
        claim = json.loads((path.parent / 'claim.json').read_bytes())
        claim['count'] = True
        raw = capture.canonical(claim)
        (path.parent / 'claim.json').write_bytes(raw)
        result['claim_sha256'] = capture.sha(raw)
    elif change == 'lifecycle_type':
        result['lifecycle']['spawn_count'] = True
    elif change == 'result_index_type':
        result['capture_index'] = True
    else:
        result['selected_event']['line'] += 1
    path.write_bytes(capture.canonical(result))
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('readback invoked binary'))
    with pytest.raises(ValueError):
        capture.read_capture(path, **read_arguments(arguments))


def test_cleanup_refusal_retains_failure_and_never_claims_success(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    original = capture._cleanup

    def refused(process):
        original(process)
        raise PermissionError('synthetic cleanup observation refused after actual cleanup')

    monkeypatch.setattr(capture, '_cleanup', refused)
    with pytest.raises(PermissionError):
        capture.capture_subscription(**arguments)
    result = json.loads((word_directory(arguments) / 'capture-1' / 'capture.json').read_bytes())
    assert result['status'] == 'failed' and result['lifecycle']['cleanup'] is None
    assert result['lifecycle']['cleanup_error']['type'] == 'PermissionError'


def test_registration_reconstruction_refusal_prevents_capture(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    def refuse(raw):
        raise ValueError('synthetic reproduction of unresolved protected registration gate')
    monkeypatch.setattr(registration, 'verified', refuse)
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('refused registration spawned'))
    with pytest.raises(ValueError, match='registration gate'):
        capture.capture_subscription(**arguments)
    assert not arguments['directory'].exists()


def test_read_capture_for_event_rechecks_authority_after_slot_scan_without_repeating_full_verified(
        tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    manifest = capture.capture_subscription(**arguments)
    saved = capture.read_capture(manifest, **read_arguments(arguments), require_current=True)
    event = saved['selected_event']
    trace = []
    base_verified = registration.verified
    base_recheck = registration._recheck_verified
    base_claims = capture._claims

    def traced_verified(submitted):
        trace.append('verified')
        return base_verified(submitted)

    def traced_recheck(submitted, initial):
        trace.append('recheck_verified')
        return base_recheck(submitted, initial)

    def traced_claims(root, *authority):
        trace.append('outer-claims' if 'recheck_verified' not in trace else 'inner-claims')
        return base_claims(root, *authority)

    monkeypatch.setattr(registration, 'verified', traced_verified)
    monkeypatch.setattr(registration, '_recheck_verified', traced_recheck)
    monkeypatch.setattr(capture, '_claims', traced_claims)
    matched = capture.read_capture_for_event(
        arguments['directory'], **read_arguments(arguments), require_current=True,
        **{key: event[key] for key in ('event_json', 'event_sha256', 'captured_at')})
    assert matched == saved
    assert trace == ['verified', 'outer-claims', 'recheck_verified', 'inner-claims']

    trace.clear()
    direct = capture.read_capture(manifest, **read_arguments(arguments), require_current=True)
    assert direct == saved
    assert trace == ['verified', 'outer-claims']


@pytest.mark.parametrize('mutation', [
    'binary', 'observation_probe', 'review_document', 'registration_recheck',
    'initial_value', 'overlap_input',
])
def test_read_capture_for_event_refuses_mutations_between_outer_authority_and_inner_slot_recheck(
        tmp_path, monkeypatch, mutation):
    arguments, value = component(tmp_path, monkeypatch)
    manifest = capture.capture_subscription(**arguments)
    saved = capture.read_capture(manifest, **read_arguments(arguments), require_current=True)
    event = saved['selected_event']
    trace = []
    base_verified = registration.verified
    base_recheck = registration._recheck_verified
    base_claims = capture._claims

    def single_verified(submitted):
        assert 'verified' not in trace, 'read_capture_for_event repeated full registration.verified'
        trace.append('verified')
        return base_verified(submitted)

    def traced_recheck(submitted, initial):
        trace.append('recheck_verified')
        if mutation == 'registration_recheck':
            raise ValueError('pinned preparation input changed between outer and inner authority checks')
        return base_recheck(submitted, initial)

    def mutate_after_outer_authority(root, *authority):
        if 'mutated' not in trace:
            trace.append('mutated')
            if mutation == 'binary':
                Path(value['runtime']['executable']['path']).write_bytes(b'changed during slot scan')
            elif mutation == 'observation_probe':
                basis = json.loads(value['runtime']['limits_basis'])
                Path(basis['observation_probe']['path']).write_bytes(b'{"corrupted":true}\n')
            elif mutation == 'review_document':
                bundle = capture.strict_json(arguments['review_bundle_raw'])
                Path(bundle['reviews'][0]['document']['path']).write_bytes(b'changed review document\n')
            elif mutation == 'initial_value':
                value['attempt_id'] = 'mutated-during-slot-scan'
            elif mutation == 'overlap_input':
                value['composition_raw_json'] = json.dumps({'policy': {'readonly_lookups': {
                    'inputs': [str(arguments['directory'])],
                    'output_directories': [str(tmp_path / 'outputs')]}}})
        return base_claims(root, *authority)

    monkeypatch.setattr(registration, 'verified', single_verified)
    monkeypatch.setattr(registration, '_recheck_verified', traced_recheck)
    monkeypatch.setattr(capture, '_claims', mutate_after_outer_authority)
    with pytest.raises(ValueError) as refused:
        capture.read_capture_for_event(
            arguments['directory'], **read_arguments(arguments), require_current=True,
            **{key: event[key] for key in ('event_json', 'event_sha256', 'captured_at')})
    if mutation == 'review_document':
        assert str(refused.value) == 'review document differs from its pinned bytes'
        assert trace == ['verified', 'mutated']
    else:
        assert trace[:2] == ['verified', 'mutated']
        assert 'recheck_verified' in trace
        assert trace.count('verified') == 1


def test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root(
        tmp_path, monkeypatch):
    from tests.test_native_shared_execution import make_case
    monkeypatch.chdir(registration.authority.ROOT)
    original_popen = subprocess.Popen

    def git_only(argv, *args, **kwargs):
        assert not kwargs.get('shell'), 'genuine registration witness must not launch a shell'
        assert isinstance(argv, (list, tuple)) and Path(argv[0]).name == 'git', (
            'genuine registration witness must not execute a native, auth, provider or peer child')
        return original_popen(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', git_only)
    case = make_case((tmp_path / 'case').resolve())
    raw = case['raw']
    value = case['value']
    review_raw = case['kwargs']['review_path'].read_bytes()
    word_raw = case['kwargs']['launch_word_path'].read_bytes()
    guard_doc = capture.strict_json(case['kwargs']['subscription_guard_path'].read_bytes())
    basis = capture.strict_json(value['runtime']['limits_basis'].encode())
    capture_dir = Path(basis['admission']['capture_state_directory'])
    manifest = capture_dir / 'captures' / capture.sha(word_raw) / 'capture-1' / 'capture.json'
    expected_record = capture.read_capture(
        manifest, registration_raw=raw, review_bundle_raw=review_raw,
        launch_word_raw=word_raw, require_current=True)
    stage_root = Path(case['selection'].document()['stage_root'])
    assert not stage_root.exists()

    trace = []
    real_verified = registration.verified
    real_recheck = registration._recheck_verified
    real_claims = capture._claims
    mutate_stage_root = [False]

    def traced_verified(submitted):
        trace.append('verified')
        return real_verified(submitted)

    def traced_recheck(submitted, initial):
        trace.append('recheck_verified')
        return real_recheck(submitted, initial)

    def traced_claims(root, *authority):
        phase = 'outer-claims' if 'recheck_verified' not in trace else 'inner-claims'
        trace.append(phase)
        result = real_claims(root, *authority)
        if phase == 'outer-claims' and mutate_stage_root[0]:
            stage_root.parent.mkdir(parents=True, exist_ok=True)
            stage_root.write_bytes(b'regular file blocking stage root\n')
        return result

    monkeypatch.setattr(registration, 'verified', traced_verified)
    monkeypatch.setattr(registration, '_recheck_verified', traced_recheck)
    monkeypatch.setattr(capture, '_claims', traced_claims)

    matched = capture.read_capture_for_event(
        capture_dir, registration_raw=raw, review_bundle_raw=review_raw,
        launch_word_raw=word_raw, require_current=True,
        event_json=guard_doc['event_json'], event_sha256=guard_doc['event_sha256'],
        captured_at=guard_doc['captured_at'])
    assert matched == expected_record
    assert trace == ['verified', 'outer-claims', 'recheck_verified', 'inner-claims']

    trace.clear()
    mutate_stage_root[0] = True
    with pytest.raises(ValueError, match='native stage root is not a directory'):
        capture.read_capture_for_event(
            capture_dir, registration_raw=raw, review_bundle_raw=review_raw,
            launch_word_raw=word_raw, require_current=True,
            event_json=guard_doc['event_json'], event_sha256=guard_doc['event_sha256'],
            captured_at=guard_doc['captured_at'])
    assert trace == ['verified', 'outer-claims', 'recheck_verified']
    with pytest.raises(ValueError, match='native stage root is not a directory'):
        real_verified(raw)
    with pytest.raises(ValueError, match='native stage root is not a directory'):
        real_recheck(raw, deepcopy(value))
