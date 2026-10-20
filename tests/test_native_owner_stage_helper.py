"""One actual stage-helper process inside an ordinary software peer attempt.

Earlier tool settlements are explicit protocol fixtures. A fixed pre-registration
choice executes either receipt7 or the first advance as the actual helper. Real
installed schemas, source/permission proof, clock domains, owner streams and
parent-owned phase seals/publication are not replaced.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading
import time

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_execution_registration as runtime_registration
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller as controller
from data_sheets_schema import native_shared_execution as execution_api
from data_sheets_schema import native_shared_policy as policy
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_render as render
from data_sheets_schema import native_shared_selection as selected
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_stream_coordination_v1 as coordination
from data_sheets_schema.chunking import build_manifest
from data_sheets_schema.native_attempt_supervisor import durable_new
from data_sheets_schema.native_execution import _mkdir_durable
from data_sheets_schema.resources import resource_path
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_native_shared_permissions import fabricated_manifest
from tests.test_native_shared_live_capture import started, native_init, stream_capture
from tests.test_native_shared_registration import execution, bound, native_spec, declaration


SESSION = '11111111-2222-4333-8444-555555555555'
IDENTIFIER = 'https://example.invalid/native-owner-stage-fixture'
NAME = 'Complete synthetic source.'
FULL_RAW = ('id: ' + IDENTIFIER + '\nname: ' + NAME + '\n').encode()
TERMINAL_REFUSAL = 'native terminal precedes all final obligations'
_REAL_POPEN = subprocess.Popen


PEER = r'''
import hashlib, json, os, pathlib, shlex, subprocess, sys, time
root = pathlib.Path(__file__).parent
attempt = root / 'attempt'
execution_raw = (attempt / 'registration.json').read_bytes()
execution = json.loads(execution_raw)
composition = json.loads(execution['composition_raw_json'])
commands = composition['policy']['native_shared_helpers']
callback_id = composition['policy']['pretool_control']['callback_id']
paths = composition['render_spec']['agentic_artifact_paths']
cwd = str(pathlib.Path.cwd())
assert cwd == execution['working_directory']
assert sys.argv == execution['argv']
def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
def emit(value):
    print(encoded(value).decode(), flush=True)
def incoming():
    raw = sys.stdin.buffer.readline()
    assert raw, 'parent ended before actual callback grant'
    return json.loads(raw)
init = incoming()
emit({'type':'control_response','response':{'subtype':'success',
     'request_id':init['request_id'],'response':{}}})
prompt = incoming()
(root / 'received-instruction.bin').write_bytes(prompt['message']['content'].encode())
emit({'type':'system','subtype':'init','session_id':SESSION,'cwd':cwd,
      'model':execution['runtime']['model'],
      'claude_code_version':execution['runtime']['executable']['init_version'],
      'apiKeySource':'none','tools':['Bash','Read','Write']})
ordinal = 0
def begin(tool, inputs):
    global ordinal
    ordinal += 1
    identity = 'stage-fixture-' + str(ordinal)
    request = 'callback-' + identity
    emit({'type':'assistant','session_id':SESSION,'message':{'role':'assistant','content':[
        {'type':'tool_use','id':identity,'name':tool,'input':inputs}]}})
    emit({'type':'control_request','request_id':request,'request':{
        'subtype':'hook_callback','callback_id':callback_id,'input':{
        'hook_event_name':'PreToolUse','cwd':cwd,'tool_use_id':identity,
        'tool_name':tool,'tool_input':inputs}}})
    response = incoming()
    assert response['response'] == {'subtype':'success','request_id':request,'response':{}}
    return identity
def settle(identity, content, metadata):
    emit({'type':'user','session_id':SESSION,'message':{'role':'user','content':[
        {'type':'tool_result','tool_use_id':identity,'content':content,'is_error':False}]},
        'tool_use_result':metadata})
def synthetic_helper(name):
    identity = begin('Bash', {'command':commands[name]})
    text = 'Explicit synthetic prerequisite settlement; helper not executed.'
    settle(identity, text, {'stdout':text,'stderr':'','exitCode':0})
def write(role, text):
    path = pathlib.Path(paths[role])
    identity = begin('Write', {'file_path':str(path),'content':text})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(text.encode())
    settle(identity, 'File created successfully at: ' + str(path),
        {'type':'create','filePath':str(path),'content':text,'originalFile':None,
         'structuredPatch':[],'userModified':False})
synthetic_helper('chunk_check')
synthetic_helper('source_scope')
write('full', FULL_TEXT)
write('receipt', RECEIPT_TEXT)
synthetic_helper('full_schema')
synthetic_helper('full_terms')
if HELPER_ROLE == 'advance':
    synthetic_helper('phase1_receipts')
else:
    assert HELPER_ROLE == 'phase1_receipts'
command = commands[HELPER_ROLE]
argv = shlex.split(command)
if HELPER_ROLE == 'advance':
    assert len(argv) == 6 and argv[1:4] == ['-m','data_sheets_schema.native_shared_stage','advance']
    assert argv[4:] == ['--registration', SELECTION_PATH]
else:
    assert argv[:3] == [composition['policy']['python'], '-m', 'data_sheets_schema.cli']
    assert argv[3] == '--manifest' and argv[5:7] == ['receipts', 'check']
    assert argv[-1] == '--strict' and '--write' not in argv
    assert argv[argv.index('--native-shared-selection') + 1] == SELECTION_PATH
identity = begin('Bash', {'command':command})
pending = {'tool_use_id':identity,'argv':argv,'command':command,'cwd':cwd,
           'execution_sha256':hashlib.sha256(execution_raw).hexdigest()}
marker = 'pending-advance' if HELPER_ROLE == 'advance' else 'pending-receipt'
pending_temp = root / (marker + '.partial')
pending_temp.write_bytes(encoded(pending))
os.replace(pending_temp, root / (marker + '.json'))
if MODE == 'hold_before_stage':
    # The fixture parent cancellation/deadline owns termination. This peer
    # never invents a success result for an in-process fault control.
    until = time.monotonic() + 60
    while not (root / 'peer-abort').exists():
        if time.monotonic() >= until:
            raise RuntimeError('fixture hold exceeded its finite wait')
        time.sleep(0.01)
    raise SystemExit(17)
assert MODE == 'subprocess'
owner = json.loads((attempt / 'stream-owner.json').read_bytes())
remaining = (owner['deadline_ns'] - time.monotonic_ns()) / 1_000_000_000
assert remaining > 0
environment = dict(execution['environment'])
def retain_helper_timeout(primary, child, buffers, drained, cleanup_errors, exit_outcome):
    # Bounded failure evidence only; never the helper success/settlement files.
    def error_name(error):
        return type(error).__module__ + '.' + type(error).__qualname__
    info = {'format':'stage_helper_timeout_diagnostic_v1', 'status':'timeout',
        'argv':argv, 'cwd':execution['working_directory'], 'pid':child.pid,
        'returncode':child.returncode, 'timeout_seconds':primary.timeout,
        'primary_error_type':error_name(primary), 'drain_completed':drained,
        'cleanup_errors':cleanup_errors, 'context_exit_outcome':exit_outcome,
        'streams':{}}
    for name, raw in zip(('stdout', 'stderr'), buffers):
        row = {'available':raw is not None, 'observed_bytes':None, 'truncated':None,
               'saved':False, 'retained_bytes':None, 'retained_sha256':None,
               'capture_error_type':None}
        info['streams'][name] = row
        if raw is None:
            continue
        try:
            if type(raw) is not bytes:
                raise TypeError('binary helper output required')
            prefix = raw[:1024 * 1024]
            row.update(observed_bytes=len(raw), truncated=len(prefix) < len(raw))
            with (root / ('helper-timeout-' + name + '.bin')).open('xb') as stream:
                if stream.write(prefix) != len(prefix):
                    raise OSError('short timeout evidence write')
            row.update(saved=True, retained_bytes=len(prefix),
                       retained_sha256=hashlib.sha256(prefix).hexdigest())
        except BaseException as error:
            row['capture_error_type'] = error_name(error)
    metadata = encoded(info)
    if len(metadata) > 16 * 1024:
        raise ValueError('timeout metadata exceeds its fixed bound')
    with (root / 'helper-timeout.json').open('xb') as stream:
        if stream.write(metadata) != len(metadata):
            raise OSError('short timeout metadata write')


def run_helper():
    primary = primary_traceback = None
    buffers = (None, None)
    drained = False
    cleanup_errors = {}
    exit_outcome = 'primary_suppressed'
    try:
        with subprocess.Popen(argv, cwd=execution['working_directory'], env=environment,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
            try:
                stdout, stderr = child.communicate(timeout=remaining)
            except subprocess.TimeoutExpired as error:
                primary, primary_traceback = error, error.__traceback__
                buffers = (error.output, error.stderr)
                try:
                    child.kill()
                except BaseException as cleanup_error:
                    cleanup_errors['kill'] = (type(cleanup_error).__module__ + '.' +
                                              type(cleanup_error).__qualname__)
                else:
                    try:
                        buffers = child.communicate()
                        drained = True
                    except BaseException as cleanup_error:
                        cleanup_errors['drain'] = (type(cleanup_error).__module__ + '.' +
                                                   type(cleanup_error).__qualname__)
                raise
            except BaseException:
                child.kill()
                child.communicate()
                raise
            result = {'argv':argv,'cwd':execution['working_directory'],
                'environment_sha256':hashlib.sha256(encoded(environment)).hexdigest(),
                'pid':child.pid,'returncode':child.returncode,
                'stdout_bytes':len(stdout),'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
                'stderr_bytes':len(stderr),'stderr_sha256':hashlib.sha256(stderr).hexdigest()}
    except BaseException as error:
        if primary is None:
            raise
        if error is primary:
            exit_outcome = 'primary_propagated'
        else:
            exit_outcome = 'secondary_error'
            cleanup_errors['context_exit'] = type(error).__module__ + '.' + type(error).__qualname__
    finally:
        if primary is not None:
            try:
                retain_helper_timeout(primary, child, buffers, drained, cleanup_errors, exit_outcome)
            except BaseException:
                pass  # Diagnostic failures never replace the original timeout.
            raise primary.with_traceback(primary_traceback) from None
    return stdout, stderr, result


def readonly_receipt_state():
    files = {}
    for role, value in (('full', paths['full']), ('receipt', paths['receipt']),
                        ('journal', JOURNAL_PATH)):
        path = pathlib.Path(value)
        assert not path.is_symlink()
        raw = path.read_bytes()
        files[role] = {'path':str(path), 'bytes':len(raw),
                       'sha256':hashlib.sha256(raw).hexdigest()}
    forbidden = {
        'provenance':pathlib.Path(composition['policy']['post_final_recorder']['destination']),
        'claims':pathlib.Path(paths['core']).parent / (PROJECT + '_receipts.yaml'),
        'phase1_seal':pathlib.Path(PHASE1_SEAL_PATH)}
    return {'files':files, 'forbidden':{role:{'path':str(path), 'exists':path.exists(),
            'is_symlink':path.is_symlink()} for role, path in forbidden.items()}}


if HELPER_ROLE == 'phase1_receipts':
    assert ordinal == 7
    readonly_before = readonly_receipt_state()
    assert all(not row['exists'] and not row['is_symlink'] for row in readonly_before['forbidden'].values())
    (root / 'receipt-readonly-before.json').write_bytes(encoded(readonly_before))
stdout, stderr, result = run_helper()
(root / 'helper-stdout.bin').write_bytes(stdout)
(root / 'helper-stderr.bin').write_bytes(stderr)
(root / 'helper-result.json').write_bytes(encoded(result))
if HELPER_ROLE == 'phase1_receipts':
    readonly_after = readonly_receipt_state()
    (root / 'receipt-readonly-after.json').write_bytes(encoded(readonly_after))
    assert readonly_after == readonly_before
assert result['returncode'] == 0, stderr.decode(errors='replace')
if HELPER_ROLE == 'advance':
    answer = json.loads(stdout)
    assert answer['state'] == 'await_core'
settle(identity, stdout.decode(), {'stdout':stdout.decode(),'stderr':stderr.decode(),'exitCode':0})
emit({'type':'result','session_id':SESSION,'result':'Fixture stops before core/final obligations.'})
'''


def _pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': c.sha(raw)}


def _selection_inputs(root):
    """Actual installed schema authority, unchanged in the helper process."""
    inputs = root / 'inputs'; inputs.mkdir()
    bundle_raw = (IDENTIFIER + '\n' + NAME + '\n').encode()
    bundle = inputs / 'bundle.md'; bundle.write_bytes(bundle_raw)
    chunks = build_manifest(bundle)
    manifest_path = inputs / 'chunks.json'; manifest_raw = c.canonical(chunks)
    manifest_path.write_bytes(manifest_raw)
    source = inputs / 'source-manifest.json'
    source_raw = c.canonical({'profile': 'neutral', 'projects': {'SYNTHETIC': {
        'sources': [{'id': 'synthetic-source', 'processed_file': '<unsegmented>',
                     'source_type': 'documentation'}]}}})
    source.write_bytes(source_raw)
    context = inputs / 'context.json'
    context_raw = c.canonical({'format': 'omission_context_v1', 'root_class': 'Dataset',
        'scopes': [{'owner': '', 'referent': NAME, 'release': None,
                    'scope': 'The supplied synthetic source only.'}],
        'source_policy': {'allowed': 'declared bundle'}, 'vocabulary': {}})
    context.write_bytes(context_raw)
    schema_inputs = {}
    for kind, cls, relative in (('full', 'Dataset', api.FULL_SCHEMA_PATH),
                                ('core', 'CoreDataset', api.CORE_SCHEMA_PATH)):
        path = resource_path(relative).absolute()
        snapshot = capture_schema(path, strict=True)
        schema_inputs[kind + '_schema'] = {'root': str(path), 'root_class': cls,
            'sources': [{'name': str(name), **_pin(member, raw)}
                        for name, member, raw in snapshot.sources]}
    receipt_policy = {'kind': c.KINDS['receipt_policy'], 'version': 1,
        'registration_id': 'synthetic-stage-helper-receipt-policy', 'condition': 'generic_v10',
        'runtime_policy_sha256': selected.RECEIPT_POLICY_SHA256, 'receipt_instrument_version': 4,
        'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}}
    receipt_policy_path = inputs / 'receipt-policy.json'
    receipt_policy_raw = c.canonical(receipt_policy); receipt_policy_path.write_bytes(receipt_policy_raw)
    assets = selected.capture_assets()
    axes = {k: v for k, v in selected.descriptor().items()
            if k not in {'typed_protocol', 'projection', 'receipt_policy', 'assets'}}
    doc = {'kind': c.KINDS['selection'], 'version': 1,
        'registration_id': 'synthetic-real-helper', 'registration_path': str(inputs / 'selection.json'),
        'run': {'project': 'SYNTHETIC', 'arm': 'BASELINE (input documents only)',
                'method': 'claudecode_direct', 'label': 'real-stage-helper'},
        'selection': {**axes, 'descriptor_sha256': selected.descriptor_capture().sha256,
            'assets': {a.pin.role[len('asset:'):]: _pin(a.pin.path, a.raw) for a in assets}},
        'inputs': {'project': 'SYNTHETIC', 'bundle': _pin(bundle, bundle_raw),
            'chunk_manifest': _pin(manifest_path, manifest_raw), 'context': _pin(context, context_raw),
            'source_manifest': _pin(source, source_raw), **schema_inputs,
            'profile': {'name': 'neutral', 'basis': 'explicit caller', 'vocabulary': None}},
        'receipt_policy': _pin(receipt_policy_path, receipt_policy_raw),
        'bounds': dict(c.BOUND_CEILINGS), 'stage_root': str(root / 'stage')}
    raw = c.canonical(doc); Path(doc['registration_path']).write_bytes(raw)
    selection = selected.capture(doc['registration_path'])
    receipt_raw = c.canonical({'bundle_md5': hashlib.md5(bundle_raw).hexdigest(), 'chunks': [
        {'id': row['id'], 'status': 'extracted', 'extracted': [
            {'slot': 'id', 'snippet': IDENTIFIER}, {'slot': 'name', 'snippet': NAME}]}
        for row in chunks['chunks']]})
    # Actual released accounting, before authority/timing starts; the adapter
    # and separate helper will reconstruct these inputs independently again.
    initial = receipts.check_initial(selection, full_raw=FULL_RAW, receipt_raw=receipt_raw)
    assert initial['passed'] and initial['slots']['without_receipt'] == []
    return selection, doc, receipt_raw


def _prepare_case(root, controls, mode, helper_role='advance'):
    if helper_role not in ('advance', 'phase1_receipts'):
        raise ValueError('unsupported fixed helper role')
    selection, doc, receipt_raw = _selection_inputs(root)
    spec = api.RunSpec(**doc['run'], bundle=Path(doc['inputs']['bundle']['path']),
        manifest=Path(doc['inputs']['source_manifest']['path']),
        chunk_manifest=Path(doc['inputs']['chunk_manifest']['path']), condition='generic_v10',
        render_version=26, runtime=c.RUNTIME, profile='neutral', profile_basis='explicit caller',
        provider='synthetic provider', reasoning_effort='high', prompt_text_env=True,
        run_date='2026-10-08', native_shared_generation_version=1,
        native_shared_generation_registration=selection.registration.raw.decode())
    peer = root / 'ordinary-stage-peer'
    constants = '\n'.join(name + ' = ' + repr(value) for name, value in (
        ('SESSION', SESSION), ('MODE', mode), ('FULL_TEXT', FULL_RAW.decode()),
        ('RECEIPT_TEXT', receipt_raw.decode()), ('SELECTION_PATH', doc['registration_path']),
        ('HELPER_ROLE', helper_role), ('PROJECT', doc['run']['project']),
        ('JOURNAL_PATH', selection.role('journal')), ('PHASE1_SEAL_PATH', selection.role('phase1_seal'))))
    peer.write_bytes(('#!' + sys.executable + '\n' + constants + '\n' + PEER).encode())
    peer.chmod(0o700)
    runtime = {'route': runtime_registration.ROUTE,
        'executable': {'path': str(peer), 'sha256': c.sha(peer.read_bytes()),
                       'version': 'synthetic', 'init_version': 'synthetic'},
        'model': 'synthetic-native-model', 'auxiliary_models': [], 'effort': 'high',
        'limits': {'contextWindow': 10000, 'maxOutputTokens': 1000},
        'limits_basis': 'explicit software fixture, not native observation',
        'provider': 'synthetic provider',
        'auth': {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
                 'subscriptionType': 'synthetic-software-test', 'expected_api_key_source': 'none'},
        'environment': {'PATH': str(Path(sys.executable).parent) + os.pathsep + '/usr/bin:/bin',
            'HOME': str(root), 'CLAUDE_SECURESTORAGE_CONFIG_DIR': '',
            'CLAUDE_CODE_DISABLE_1M_CONTEXT': '1'},
        'deadline_seconds': 60, 'budget_guard_usd': '1',
        'keep_awake': {'policy': 'not_applicable', 'host_platform': sys.platform,
            'basis': 'ordinary software peer; no native invocation'}}
    runtime_path = root / 'runtime.json'; runtime_path.write_bytes(c.canonical(runtime))
    controller.bind_runtime(spec, runtime_path, 3)
    instruction = root / 'instruction.md'; instruction.write_bytes(spec.instruction.encode())
    dependencies = authority.dependency_identity(stream_snapshot_profile=1)
    chosen = deepcopy(dependencies['stream_snapshot_profile'])
    composition = controller._compose_in_scope(spec, runtime_path=runtime_path,
        instruction_path=instruction, max_draft_checks=3, profile=chosen)
    composition_raw = c.canonical(composition)
    composition_path = root / 'composition.json'; composition_path.write_bytes(composition_raw)
    system = root / 'system.txt'; system.write_bytes(b'Explicit synthetic protocol fixture.\n')
    attempt, output = root / 'attempt', root / 'evidence'
    expected = registration.permission_expectation(runtime, composition, spec,
        system.read_text() + policy._command_guidance_in_scope(composition['policy'], chosen),
        attempt / 'cli_config', dependencies)
    fabricated = fabricated_manifest(expected, selection.document(), root / 'fabricated-permission-records',
                                    spec.bundle.read_bytes())
    permission = root / 'fabricated-permission.json'; permission.write_bytes(c.canonical(fabricated))
    value = registration._registration_in_scope(composition_path, system, permission_probe_path=permission,
        attempt_id=attempt.name, attempt_directory=attempt, evidence_directory=output, max_draft_checks=3)
    raw = c.canonical(value)
    assert registration._verified_in_scope(raw) == value
    authority.require_committed(value['dependencies'])
    helper_argv = tuple(render.commands(spec)[helper_role])
    helper_command = composition['policy']['native_shared_helpers'][helper_role]
    assert tuple(shlex.split(helper_command)) == helper_argv
    for path in registration._paths(value, composition, fresh=True):
        _mkdir_durable(path)
    durable_new(attempt / 'registration.json', raw)
    started_value = {'kind': c.KINDS['attempt'], 'version': 1, 'state': 'started',
        'attempt_id': value['attempt_id'], 'registration_sha256': c.sha(raw),
        'composition_sha256': value['composition_sha256'], 'dispatch_limit': 1}
    started_raw = c.canonical(started_value); durable_new(attempt / 'started.json', started_raw)
    _mkdir_durable(attempt / 'cli_config')
    adapter = controller._callback_adapter_in_scope(composition_raw, execution=value, registration_raw=raw)
    runner = profile.bind_runner(chosen, controls)
    proxy = controls['run_direct_canary'].NoProxy()
    inputs, input_bytes = {}, {}
    for name in ('review', 'ci', 'launch'):
        inputs[name] = root / (name + '-fixture-precondition.json')
        input_bytes[name] = c.canonical({'fixture': name, 'execution_authorized': False})
        inputs[name].write_bytes(input_bytes[name])
    authority_inputs = {'inputs': inputs, 'raw': input_bytes}
    observed, stops = [], []
    def verify_launch():
        execution_api._unchanged_in_scope(value, raw, authority_inputs)
        assert (attempt / 'registration.json').read_bytes() == raw
        assert (attempt / 'started.json').read_bytes() == started_raw
        owner_raw = runner.owner_raw()
        case['owner_raw_for_timing'] = owner_raw
        adapter.activate_before_dispatch(started_raw, owner_raw=owner_raw)
    def observe(event):
        adapter.observe(event)
        observed.append(deepcopy(event))
    kwargs = {'argv': list(value['argv']), 'proxy': proxy, 'instruction': instruction,
        'attempt': attempt, 'cwd': value['working_directory'], 'env': dict(value['environment']),
        'deadline_seconds': runtime['deadline_seconds'], 'verify_launch': verify_launch,
        'record_stop': stops.append, 'command_policy': adapter.policy,
        'command_classifier': adapter.classify, 'event_observer': observe,
        'execution_raw': raw, 'started_raw': started_raw}
    case = {'root': root, 'mode': mode, 'helper_role': helper_role, 'selection': selection, 'spec': spec, 'profile': chosen,
        'execution': value, 'execution_raw': raw, 'composition': composition,
        'composition_raw': composition_raw, 'started_raw': started_raw, 'attempt': attempt,
        'helper_argv': helper_argv, 'helper_command': helper_command, 'environment': value['environment'],
        'cwd': value['working_directory'], 'full_raw': FULL_RAW, 'receipt_raw': receipt_raw,
        'adapter': adapter, 'runner': runner, 'proxy': proxy, 'controls': controls,
        'parent_scope': profile._ACTIVE.get(), 'kwargs': kwargs, 'observed': observed, 'stops': stops,
        'peer': peer, 'instruction': instruction, 'owner_raw_for_timing': None}
    return case


class StageHelperSession:
    """Own the loader/runner Thread; caller never borrows its original scope."""
    def __init__(self, root, mode, helper_role='advance'):
        if mode not in ('subprocess', 'hold_before_stage'):
            raise ValueError('unsupported stage fixture mode')
        if helper_role not in ('advance', 'phase1_receipts') or (
                helper_role == 'phase1_receipts' and mode != 'subprocess'):
            raise ValueError('unsupported fixed helper role/mode')
        self.root, self.mode, self.helper_role = root, mode, helper_role
        self.case = None
        self.error = self.report = self.result = self.diagnostic_error = None
        self.ready, self.done = threading.Event(), threading.Event()
        self._start, self._abort = threading.Event(), threading.Event()
        self.dispatches = 0
        self.owner_thread = threading.Thread(target=self._owner, name='stage-fixture-owner', daemon=True)
        self.owner_thread.start()
        if not self.ready.wait(300):
            self.stop()
            raise AssertionError('stage fixture preparation did not finish within its finite bound')
        if self.error is not None:
            self.stop()
            raise self.error

    def _owner(self):
        try:
            with authority.loaded_dependencies(authority.dependency_identity(stream_snapshot_profile=1)) as controls:
                self.case = _prepare_case(self.root, controls, self.mode, self.helper_role)
                self.ready.set()
                if not self._start.wait(60):
                    raise AssertionError('prepared stage fixture was never started')
                if self._abort.is_set():
                    return
                self.result = self.case['runner'].execute_child(**self.case['kwargs'])
        except BaseException as error:
            self.error = error
        finally:
            try:
                if self.case is not None:
                    self.report = self.case['runner'].report()
            except BaseException as error:
                if self.error is None:
                    self.error = error
            finally:
                # The runner and original loader have exited. This bounded
                # diagnostic never calls a fresh authority getter or changes
                # the operation's primary error when retention fails.
                if self.helper_role == 'phase1_receipts':
                    try:
                        raw = c.canonical({'format':'receipt_process_owner_diagnostic_v1',
                            'report_available':self.report is not None, 'runner_report':self.report,
                            'primary_error_type':None if self.error is None else
                                type(self.error).__module__ + '.' + type(self.error).__qualname__,
                            'owner_sha256':None if self.case is None or
                                self.case['owner_raw_for_timing'] is None else
                                c.sha(self.case['owner_raw_for_timing'])})
                        if len(raw) > 128 * 1024:
                            raise ValueError('receipt owner diagnostic exceeds its fixed bound')
                        with (self.root / 'owner-runner-report.json').open('xb') as stream:
                            if stream.write(raw) != len(raw):
                                raise OSError('short receipt owner diagnostic write')
                    except BaseException as diagnostic_error:
                        self.diagnostic_error = diagnostic_error
                self.ready.set(); self.done.set()

    def start(self):
        assert not self._start.is_set() and not self.done.is_set(), 'one fixture dispatch only'
        self._start.set()
        return self

    def wait_pending(self):
        assert self._start.is_set()
        limit = time.monotonic() + 65
        path = self.root / ('pending-advance.json' if self.helper_role == 'advance'
                            else 'pending-receipt.json')
        while not path.exists():
            if self.done.wait(0.01):
                if self.error is not None:
                    raise self.error
                raise AssertionError('owner exited before a genuine admitted advance')
            if time.monotonic() >= limit:
                raise AssertionError('no pending advance within the unchanged attempt window')
        pending = c.strict_json(path.read_bytes())
        assert pending['argv'] == list(self.case['helper_argv'])
        assert pending['command'] == self.case['helper_command']
        assert pending['execution_sha256'] == c.sha(self.case['execution_raw'])
        assert pending['cwd'] == self.case['cwd']
        self.case['pending'] = pending
        return self.case

    def wait_finished(self):
        assert self._start.is_set()
        if not self.done.wait(70):
            self.stop()
            raise AssertionError('owner did not end within its original attempt plus cleanup margin')
        self.owner_thread.join(1)
        assert not self.owner_thread.is_alive()
        return self

    def stop(self):
        self._abort.set(); self._start.set()
        if self.case is not None and not self.done.is_set():
            self.case['proxy'].failed.set()
            (self.root / 'peer-abort').write_bytes(b'stop\n')
        self.owner_thread.join(75)
        assert not self.owner_thread.is_alive(), 'fixture owner failed to stop; retain all evidence'


@pytest.fixture
def stage_helper_factory(tmp_path, monkeypatch):
    sessions = []
    def only_declared(argv, *args, **kwargs):
        assert isinstance(argv, (list, tuple)) and argv
        if argv[0] != 'git':
            matches = [s for s in sessions if s.case is not None and list(argv) == s.case['execution']['argv']]
            assert len(matches) == 1, 'only actual registered ordinary peer may launch here'
            session = matches[0]
            assert kwargs['cwd'] == session.case['cwd'] and kwargs['env'] == session.case['environment']
            assert session.dispatches == 0
            session.dispatches += 1
        return _REAL_POPEN(argv, *args, **kwargs)
    monkeypatch.setattr(subprocess, 'Popen', only_declared)
    def factory(*, mode='subprocess', helper_role='advance'):
        assert not sessions, 'one actual live owner per test'
        root = tmp_path.resolve() / 'stage-helper-fixture'; root.mkdir()
        session = StageHelperSession(root, mode, helper_role)
        sessions.append(session)
        return session
    yield factory
    for session in reversed(sessions):
        session.stop()


def capture_current_invocation(session, context):
    """Actual current helper capture/proposal, with no publication or stubs."""
    invocation = capture.capture_stage(session.case['selection'].registration.pin.path,
                                       owner_context=context)
    selected_args = (invocation.selection, invocation.execution, invocation.phase1, invocation.history)
    replay = stage._Replay(*selected_args).run()
    if replay.pending is not None and replay.pending[-1] is not None:
        response, _ = replay.pending[-1]
        proposal = stage.check_response(*selected_args, replay.pending[2].raw, response.raw)
    else:
        proposal = stage.prepare_next(*selected_args)
    return invocation, proposal


def test_registered_helper_process_publishes_first_receipt_stage_with_real_clock(stage_helper_factory):
    session = stage_helper_factory()
    case = session.case
    assert profile._ACTIVE.get() is None and coordination.current_reader_budget() is None
    with pytest.raises(ValueError):
        registration.verified(case['execution_raw'])
    assert session.dispatches == 0
    session.start().wait_finished()
    assert isinstance(session.error, case['controls']['budgeted_cborg'].BudgetStop)
    assert TERMINAL_REFUSAL in str(session.error)
    assert session.dispatches == 1 and session.report['state'] == 'failed'
    result = c.strict_json((session.root / 'helper-result.json').read_bytes())
    stdout = (session.root / 'helper-stdout.bin').read_bytes()
    stderr = (session.root / 'helper-stderr.bin').read_bytes()
    assert result['returncode'] == 0 and result['pid'] != os.getpid()
    assert result['argv'] == list(case['helper_argv']) and result['cwd'] == case['cwd']
    assert result['environment_sha256'] == c.sha(json.dumps(case['environment'], sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode())
    assert result['stdout_bytes'] == len(stdout) and result['stdout_sha256'] == c.sha(stdout)
    assert result['stderr_bytes'] == len(stderr) and result['stderr_sha256'] == c.sha(stderr)
    answer = c.strict_json(stdout)
    assert answer['state'] == 'await_core' and answer['execution_sha256'] == c.sha(case['execution_raw'])
    assert answer['selection_sha256'] == case['selection'].registration.pin.sha256
    assert answer['session_id'] == SESSION
    for row in answer['publications']:
        raw = Path(row['path']).read_bytes()
        assert row['bytes'] == len(raw) and row['sha256'] == c.sha(raw)
    journal = c.strict_json(Path(case['selection'].role('journal')).read_bytes())
    records = [c.strict_json(Path(row['path']).read_bytes()) for row in journal['records']]
    assert [row['record_type'] for row in records] == [
        'genesis', 'session_bound', 'phase1_sealed', 'receipt_zero_work']
    assert c.sha(Path(case['selection'].role('journal')).read_bytes()) == answer['after_history_sha256']
    observations = [c.strict_json(p.read_bytes()) for p in sorted(
        Path(case['selection'].role('observations_root')).glob('*.json'))]
    assert [v['observation_type'] for v in observations] == [
        'initialized', 'phase1_sealed', 'advance_admitted', 'advance_settled']
    assert observations[0]['version'] == 2
    assert all(v['version'] == 1 for v in observations[1:])
    assert case['adapter']._initialized and not case['parent_scope'].live
    assert Path(case['selection'].role('phase1_full')).read_bytes() == FULL_RAW
    assert Path(case['selection'].role('phase1_receipt')).read_bytes() == case['receipt_raw']
    assert (session.root / 'received-instruction.bin').read_bytes() == case['instruction'].read_bytes()
    owner = c.strict_json(case['runner'].owner_raw())
    assert owner['duration_ns'] == 60_000_000_000
    assert owner['deadline_ns'] - owner['start_ns'] == owner['duration_ns']
    assert owner['clock'] == 'monotonic_ns' and owner['clock_domain']['platform'] == sys.platform
    contract = case['controls']['native_control'].HISTORY_CONTRACT
    assert contract['callback_timeout_seconds'] == 2 and contract['observer_timeout_seconds'] == 120
    assert not Path(case['selection'].role('phase1_core')).exists()


def test_default_helper_scope_yields_no_owner_and_preserves_actual_initialization(started):
    selection, value, composition, _, _ = started
    transcript, control = native_init(selection, value, composition)
    capture.initialize(selection.registration.pin.path, transcript_bytes=len(transcript),
        control_bytes=len(control), **stream_capture(value))
    before = Path(selection.role('journal')).read_bytes()
    with capture._helper_owner_scope(selection.registration.pin.path) as context:
        assert context is None
        with pytest.raises(ValueError, match='sealed originals'):
            capture.capture_stage(selection.registration.pin.path, owner_context=context)
    assert Path(selection.role('journal')).read_bytes() == before
    assert profile._ACTIVE.get() is None and coordination.current_reader_budget() is None
