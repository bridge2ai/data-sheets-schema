#!/usr/bin/env python3
"""Checked C10-to-C20 lead sequence, 2026-11-19.

Inputs: stage A uses the owner D117 files in the production config; stage B
uses the reviewed A handoff, owner timing bundle/result, r2d receipt and CI id;
all other real choices come from the explicitly selected cell's finalized config.
Outputs: exclusive per-command receipts and one summary with timings and pins.
Serves codex196-post-probe-chain-20261119. Default is a read-only plan. Execute
mode is for the lead after real owner authorization; A runs C10, B runs C12
and live host qualification. B never repeats C10/C11.
This assignment rehearses only through an explicitly injected test transport.
No model/provider generation, capture, reservation, retry, push or merge exists.
Retained helper copy for the explicit model-label amendment; source gates remain unchanged.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = E / 'codex-development-efficiency-20261111'
W = E / 'native-production-e7721b603763'
F = E / 'native-fastpath-e7721b603763'
HEAD = 'e7721b603763ec131540c5e1a8a1d4ab16df5a1c'
PY = W / '.venv/bin/python'
HERE = Path(__file__).resolve()
DRIVER = HERE.with_name('post_merge_fast_path_20261117.py')
CHECKER = HERE.with_name('codex196_check_fastpath_outcome_20261119.py')
QUALIFIER = HERE.with_name('produce_native_qualification_20261119.py')
COMPARATOR = HERE.with_name('compare_post_probe_envelopes_e772_20261119.py')
CI = HERE.with_name('pack_native_ci_v2_20261119.py')
RC3 = HERE.with_name('rc3_review_packets_20261119.py')
RECORDER = HERE.with_name('record_binary_timing_receipts_20261119.py')
STEPS = ('C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C19', 'C20')
PROJECTS = ('CHORUS', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC')
REVIEWERS = {'codex-claude': ['codex_cli', 'claude'], 'codex-agy': ['codex_cli', 'agy']}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def observed_model_usage(runtime, terminal):
    from data_sheets_schema import native_model_aliases as aliases
    pair = aliases.model_aliases(runtime)
    aliases.require_model_usage(terminal, pair)
    return terminal['modelUsage'][aliases.reported_model(pair)]

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result

def load(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def physical(path, *, exists=True):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=exists) == path and not path.is_symlink(),
            'physical absolute path required: ' + str(path))
    return path

def pin(path):
    path = physical(path)
    require(path.is_file(), 'ordinary file required: ' + str(path))
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def resolve_r2d_trace_receipt(path, expected_sha256):
    """Verify the lead's inventory receipt; never treat it as host qualification."""
    receipt = pin(path)
    require(isinstance(expected_sha256, str) and len(expected_sha256) == 64
            and all(char in '0123456789abcdef' for char in expected_sha256)
            and receipt['sha256'] == expected_sha256, 'C14 lead r2d receipt digest differs')
    document = load(path)
    require(document.get('kind') == 'lead_r2d_trace_receipt'
            and document.get('source_commit') == HEAD, 'C14 lead r2d receipt kind/source differs')
    files = document['files']
    attempt = physical(files['attempt_dir'])
    require(attempt.is_dir(), 'C14 r2d attempt must be a directory')
    result = dict(receipt=receipt, attempt_directory=str(attempt))
    for key, output_key, expected in (
            ('registration', 'registration_pin', attempt / 'registration.json'),
            ('controller_timing', 'timing_jsonl_pin', attempt / 'host-controller-timing.jsonl'),
            ('pre_dispatch', 'pre_dispatch_trace_pin', None)):
        claimed = files[key]
        require(type(claimed) is dict and set(claimed) == {'path', 'bytes', 'sha256'}
                and type(claimed['bytes']) is int, 'C14 lead r2d exact file pin required: ' + key)
        actual = pin(Path(claimed['path']))
        require(actual == claimed, 'C14 lead r2d file pin differs: ' + key)
        require(expected is None or actual['path'] == str(expected),
                'C14 lead r2d artifact is outside its attempt: ' + key)
        result[output_key] = actual
    require(pin(path) == receipt, 'C14 lead r2d receipt changed during read')
    return result

def save(path, value, *, raw=False):
    data = value if raw else canonical(value)
    require(bytes([64]) not in data, 'authored output contains forbidden character')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
    require(path.read_bytes() == data, 'output readback differs')
    return pin(path)

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def real_execute(argv, cwd, timeout):
    # No shell expansion. Child and descendants have an outside process timeout.
    process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
                 GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0'))
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        import signal
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        return dict(returncode=124, stdout=stdout, stderr=stderr, timed_out=True,
                    execution='real', actual_argv=argv)
    return dict(returncode=process.returncode, stdout=stdout, stderr=stderr,
                timed_out=False, execution='real', actual_argv=argv)

class Chain:
    def __init__(self, args, *, scratch=F, executor=real_execute, fixture=False, observation_reader=None):
        require(not fixture or executor is not real_execute, 'fixtures require an explicit fenced transport')
        requested = getattr(args, 'scratch', None)
        if requested is not None:
            require(scratch == F or scratch == requested, 'conflicting cell scratch inputs')
            scratch = Path(requested)
        self.project = getattr(args, 'project', 'CHORUS')
        self.rep = getattr(args, 'rep', 1)
        self.reviewer_pair = getattr(args, 'reviewer_pair', 'codex-claude')
        require(self.project in PROJECTS and type(self.rep) is int and self.rep > 0, 'invalid cell project or rep')
        require(self.reviewer_pair in REVIEWERS, 'unknown reviewer pair')
        require(self.project != 'AI_READI' or self.reviewer_pair == 'codex-agy', 'AI_READI requires codex-agy')
        self.legacy_cell1 = (self.project, self.rep, self.reviewer_pair) == ('CHORUS', 1, 'codex-claude')
        require(fixture or (observation_reader is None and (scratch == F if self.legacy_cell1 else
            scratch.is_relative_to(F) and len(scratch.relative_to(F).parts) >= 2)),
            'production cell requires a separate preparation root below the frozen fastpath root')
        self.args, self.scratch, self.executor, self.fixture = args, physical(scratch), executor, fixture
        self.observation_reader = observation_reader
        self.packet = self.scratch / 'packets' / self.project
        self.config_path = physical(getattr(args, 'config', None) or self.scratch / 'production-inputs.json')
        self.config = deepcopy(load(self.config_path))
        self.route = dict(project=self.project, rep=self.rep, reviewer_pair=self.reviewer_pair,
                          scratch=str(self.scratch), configuration=str(self.config_path), packet=str(self.packet))
        if not self.legacy_cell1:
            require(canonical(self.config.get('cell_route')) == canonical(
                    {key: self.route[key] for key in ('project', 'rep', 'reviewer_pair')}),
                    'cell config project, rep or reviewer pair differs')
        self.settings = self.config.get('post_probe_chain', {})
        require(args.stage in ('a', 'b'), 'explicit stage a or b required')
        self.stage = args.stage
        self.handoff = None
        self.sources = {str(path): pin(path) for path in
            (HERE, DRIVER, CHECKER, QUALIFIER, COMPARATOR, CI, RC3, RECORDER)}
        self.inputs = {str(self.config_path): pin(self.config_path)}
        if self.stage == 'b':
            self.read_handoff()
            self.check_owner_timings()
            self.selected_r2d = resolve_r2d_trace_receipt(args.r2d_trace_receipt,
                                                         args.r2d_trace_receipt_sha256)
            for key in ('receipt', 'registration_pin', 'timing_jsonl_pin', 'pre_dispatch_trace_pin'):
                self.bind(Path(self.selected_r2d[key]['path']))
            require(type(args.ci_run_id) is int and args.ci_run_id > 0, 'positive CI run id required')
            require(fixture or getattr(args, 'qualification', None) is None,
                    'production stage B must produce current qualification')
        self.unchanged()
        self.output = self.scratch / ('post-probe-stage-' + self.stage)
        require(not os.path.lexists(self.output), 'single-use chain output exists; preserve it, never retry automatically')
        self.output.mkdir()
        self.current = None
        self.rows = [dict(step=step, status='not_reached', wall_seconds=None, commands=[], receipts=[])
                     for step in (STEPS[:2] if self.stage == 'a' else STEPS[2:])]
        self.summary = dict(kind='post_probe_chain_e772_v2', stage=self.stage, source_commit=HEAD,
            scope='SYNTHETIC_TRANSPORT_NOT_AUTHORITY' if fixture else 'lead_checked_sequence',
            source_pins=self.sources, input_pins=self.inputs, steps=self.rows,
            production_acceptance=False, reviews_performed=False, owner_acts_created=False,
            automatic_retry=False, status='running')
        if not self.legacy_cell1:
            self.summary['cell_route'] = self.route

    def context(self):
        from types import SimpleNamespace
        recorder = module(RECORDER, '_stage_timing_recorder_reader')
        source, source_pins = recorder.load_source(W)
        expectation = self.packet / 'expectation/expectation.json'
        composition = self.packet / 'composition/composition.json'
        args = SimpleNamespace(checkout=W, registration=None, expectation=expectation,
            input_sha256=pin(expectation)['sha256'], composition=composition,
            composition_sha256=pin(composition)['sha256'],
            authorization_reference='Context projection only; not authorization')
        value, input_pin, mode, extra = recorder.select_context(args, source)
        return recorder, source_pins, value, input_pin, mode, extra

    def publish_handoff(self, summary_pin):
        recorder, sources, value, expected, mode, extra = self.context()
        snapshot = self.config_snapshot('handoff')
        # Retain every C11 packet byte, including operation receipts and preparation.
        pins = {**self.inputs, **{str(p): pin(p) for p in self.packet.rglob('*') if p.is_file()},
                **{str(p): pin(p) for p in self.output.rglob('*') if p.is_file()}}
        for row in self.rows:
            for item in row['receipts']:
                require(pin(Path(item['path'])) == item, 'stage A retained receipt changed before handoff')
                pins[item['path']] = item
        pins.update({x['path']: x for x in sources.values()})
        document = dict(kind='post_probe_stage_a_handoff_v1', version=1, stage='a',
            source_commit=HEAD, scratch=str(self.scratch), scope=self.summary['scope'],
            status='C11_complete_waiting_for_owner_timings', source_pins=self.sources,
            config_pin=pin(snapshot), original_config_pin=pin(self.config_path),
            summary_pin=summary_pin, artifact_pins=pins,
            observation=str(self.observation), observed=self.observed, limits=self.limits,
            recorder_context=dict(expectation=expected, composition=extra['composition'],
                context_pins=extra, input_mode=mode, working_directory=value['working_directory'],
                environment_sha256=recorder.sha(recorder.encoded(value['environment']))))
        if not self.legacy_cell1:
            document['cell_route'] = self.route
        self.unchanged()
        return save(self.output / 'handoff.json', document)

    def read_handoff(self):
        path = physical(self.args.stage_a_handoff)
        require(path == self.scratch / 'post-probe-stage-a/handoff.json', 'handoff is outside fixed stage A output')
        handoff_pin = pin(path)
        require(handoff_pin['sha256'] == self.args.stage_a_handoff_sha256, 'reviewed handoff SHA256 differs')
        h = load(path)
        require(canonical(h.get('cell_route')) == canonical(None if self.legacy_cell1 else self.route),
                'stage A cell project, rep, paths or reviewer pair differs')
        require(h['kind'] == 'post_probe_stage_a_handoff_v1' and h['version'] == 1
                and h['stage'] == 'a' and h['source_commit'] == HEAD and h['scratch'] == str(self.scratch)
                and h['status'] == 'C11_complete_waiting_for_owner_timings', 'invalid completed stage A handoff')
        require(h['scope'] == ('SYNTHETIC_TRANSPORT_NOT_AUTHORITY' if self.fixture else 'lead_checked_sequence'),
                'stage A authority scope differs')
        require(h['source_pins'] == self.sources, 'stage A source pins differ')
        require(h['original_config_pin'] == pin(self.config_path), 'stage A base config changed')
        for key, item in h['artifact_pins'].items():
            require(key == item['path'] and self.bind(Path(key)) == item, 'stage A artifact hash differs: ' + key)
        for key in ('config_pin', 'summary_pin'):
            item = h[key]
            require(self.bind(Path(item['path'])) == item, 'stage A receipt hash differs: ' + key)
        summary = load(h['summary_pin']['path'])
        require(canonical(summary.get('cell_route')) == canonical(None if self.legacy_cell1 else self.route),
                'stage A summary cell route differs')
        require(summary['stage'] == 'a' and summary['status'] == 'C11_complete_waiting_for_owner_timings'
                and [r['step'] for r in summary['steps']] == list(STEPS[:2])
                and all(r['status'] == 'completed' for r in summary['steps']), 'stage A is incomplete')
        self.config = deepcopy(load(h['config_pin']['path']))
        if not self.legacy_cell1:
            require(canonical(self.config.get('cell_route')) == canonical(
                    {key: self.route[key] for key in ('project', 'rep', 'reviewer_pair')}),
                    'stage A saved config cell route differs')
        self.settings = self.config.get('post_probe_chain', {})
        self.observation = physical(h['observation'])
        if self.observation_reader:
            self.observed = self.observation_reader(self.observation)
        else:
            from data_sheets_schema import native_u4b_probe_sequence as probes
            self.observed = probes.validate_observation(str(self.observation))
        require(self.observed == h['observed'], 'stage A observation revalidation differs')
        terminal = json.loads(
            Path(self.observed['transcript']['path']).read_bytes().splitlines()[-1])
        self.limits = observed_model_usage(self.observed['provisional_runtime'], terminal)
        require(self.limits == h['limits'], 'stage A observed limits differ')
        self.handoff = h
        self.bind(path)

    def check_owner_timings(self):
        recorder, sources, value, expected, mode, extra = self.context()
        h = self.handoff['recorder_context']
        require(h == dict(expectation=expected, composition=extra['composition'], context_pins=extra,
                input_mode=mode, working_directory=value['working_directory'],
                environment_sha256=recorder.sha(recorder.encoded(value['environment']))),
                'stage A recorder context differs')
        provenance_path = physical(self.args.timing_provenance)
        p = load(provenance_path)
        require(p['kind'] == 'd4d_native_binary_timing_provenance_v1' and p['version'] == 1
                and p['status'] == 'passed' and p['source_commit_of_pinned_functions'] == HEAD
                and p['source_pins'] == sources and p['recorder_pin'] == pin(RECORDER)
                and p['input_pin'] == expected and p['input_mode'] == mode and p['context_pins'] == extra
                and p['working_directory'] == value['working_directory']
                and p['environment_sha256'] == h['environment_sha256']
                and p['reserved_attempt_existed_before'] is False and p['reserved_attempt_exists_after'] is False,
                'owner timing provenance differs from stage A')
        binary = value['runtime']['executable']
        require(p['binary']['path'] == binary['path'] and p['binary']['sha256'] == binary['sha256'],
                'timing binary differs from stage A')
        require(not os.path.lexists(Path(value['environment']['CLAUDE_CONFIG_DIR']).parent),
                'future attempt already exists')
        require(len(p['calls']) == 2 and p['source_output_validation']['checked'] is True
                and p['source_output_validation']['passed'] is True
                and p['source_output_validation']['binary'] == p['binary']
                and p['source_output_validation']['environment_sha256'] == p['environment_sha256'],
                'timing source validation missing')
        qualifier = module(QUALIFIER, '_stage_timing_receipt_validator')
        validators = qualifier.load_checkout_validators(W)
        require(validators['source_commit'] == HEAD, 'timing validator source differs')
        for item in validators['validator_pins'].values():
            self.bind(Path(item['path']))
        require(p['source_output_validation']['version'] == binary['version']
                and canonical(p['source_output_validation']['auth']) == canonical({key: value['runtime']['auth'][key]
                    for key in ('loggedIn', 'authMethod', 'apiProvider', 'subscriptionType')}),
                'timing observed version or auth differs from selected runtime')
        require(p['calls'][0]['monotonic_finish_ns'] <= p['calls'][1]['monotonic_start_ns'],
                'metadata timing calls are out of order')
        timing_pins = {}
        for path, name, command, suffix, call in zip(
                (self.args.recorded_version_timing, self.args.recorded_auth_timing),
                ('version-timing.json', 'auth-timing.json'), ('version', 'auth_status_json'),
                (['--version'], ['auth', 'status', '--json']), p['calls']):
            path = physical(path)
            require(path == provenance_path.parent / name and path.parent.name == 'complete',
                    'timing pair is outside one completed recorder bundle')
            item = self.bind(path)
            require(p['receipts'][name] == {k: item[k] for k in ('sha256', 'bytes')}, 'timing receipt hash differs')
            require(call['command'] == command and call['argv'] == [binary['path'], *suffix]
                    and call['cwd'] == value['working_directory'] and call['timeout_seconds'] == 60
                    and call['environment_sha256'] == p['environment_sha256']
                    and call['new_process_session'] is True and call['returncode'] == 0
                    and call['timed_out'] is False and not call.get('cleanup_incomplete', False)
                    and type(call['monotonic_start_ns']) is int and call['monotonic_start_ns'] >= 0
                    and type(call['monotonic_finish_ns']) is int and type(call['duration_ns']) is int
                    and call['duration_ns'] == call['monotonic_finish_ns'] - call['monotonic_start_ns']
                    and call['duration_seconds'] == call['duration_ns'] / 1_000_000_000
                    and 0 < call['duration_seconds'] <= 60,
                    'owner timing call differs from source invocation')
            require(load(path) == recorder.make_receipt(call, value, p['authorization_reference']),
                    'timing receipt differs from provenance')
            qualifier.load_probe_timing_receipt(validators, path,
                expected_command=command, expected_binary_sha256=binary['sha256'], timeout_ceiling_seconds=60)
            timing_pins[name] = item
        self.bind(provenance_path)
        result = load(physical(self.args.timing_result))
        require(result['status'] == 'passed' and result['publication_committed'] is True
                and result['durability_confirmed'] is True
                and result['output_directory'] == str(provenance_path.parent.parent)
                and result['receipts'] == timing_pins and result['provenance'] == pin(provenance_path),
                'successful durable recorder result required')
        require(not (provenance_path.parent.parent / 'failure.json').exists(), 'recorder failure present')
        self.bind(physical(self.args.timing_result))
        self.timing_context = value

    def unchanged(self):
        for path, row in {**self.sources, **self.inputs}.items():
            require(pin(Path(path)) == row, 'bound input/source changed: ' + path)

    def bind(self, path):
        value = pin(path)
        self.inputs[value['path']] = value
        return value

    def receipt(self, path):
        row = pin(path)
        self.current['receipts'].append(row)
        return row

    def command(self, label, argv, *, allowed=(0,), timeout=1800, cwd=W):
        self.unchanged()
        location = self.output / self.current['step'] / label
        location.mkdir(parents=True)
        planned = dict(argv=list(map(str, argv)), cwd=str(cwd), timeout_seconds=timeout)
        save(location / 'planned.json', planned)
        start = time.monotonic()
        try:
            result = self.executor(planned['argv'], str(cwd), timeout)
        except Exception as exc:
            result = dict(returncode=125, stdout=b'',
                stderr=(type(exc).__name__ + ': ' + str(exc)).encode(),
                timed_out=False, execution='launch_error', actual_argv=planned['argv'])
        elapsed = time.monotonic() - start
        for name in ('stdout', 'stderr'):
            # Raw subprocess output is retained, including any upstream syntax.
            with (location / (name + '.log')).open('xb') as stream:
                stream.write(result[name])
        row = dict(label=label, planned=planned, returncode=result['returncode'],
            wall_seconds=elapsed, timed_out=result.get('timed_out', False),
            execution=result['execution'], actual_argv=result['actual_argv'],
            stdout=pin(location / 'stdout.log'), stderr=pin(location / 'stderr.log'))
        row['emitted_outputs'] = []
        for option in ('--output', '--diagnostic-output'):
            if option in planned['argv']:
                target = Path(planned['argv'][planned['argv'].index(option) + 1])
                paths = [target] if target.is_file() else sorted(target.rglob('*')) if target.is_dir() else []
                for path in paths:
                    if path.is_file():
                        row['emitted_outputs'].append(pin(path))
        record = save(location / 'receipt.json', row)
        self.current['commands'].append(dict(**row, receipt=record))
        self.unchanged()
        require(result['returncode'] in allowed and not row['timed_out'],
                label + ' failed with exit ' + str(result['returncode']))
        return result, location

    def config_snapshot(self, name):
        path = self.output / (name + '-config.json')
        save(path, self.config)
        self.bind(path)
        return path

    def driver(self, phase, step):
        config = self.config_snapshot(phase)
        operations = self.scratch / 'operations'
        before = set(operations.glob(step + '-*'))
        try:
            route_args = [] if self.legacy_cell1 else ['--project', self.project, '--rep', str(self.rep)]
            reviewer_args = [] if self.legacy_cell1 else ['--reviewer-pair', self.reviewer_pair]
            result, location = self.command('driver', [PY, '-P', '-s', '-B', DRIVER, step,
                '--main-sha', HEAD, '--checkout', W, '--scratch', self.scratch, '--config', config,
                *route_args, *reviewer_args],
                allowed=(0, 2), timeout=12600)
            outcome = json.loads(result['stdout'])
            matches = [path for path in sorted(set(operations.glob(step + '-*')) - before)
                       if (path / 'outcome.json').is_file() and load(path / 'outcome.json') == outcome]
            require(len(matches) == 1, 'ambiguous or missing current driver operation')
            operation = matches[0]
            self.command('phase-check', [PY, '-P', '-s', '-B', CHECKER, 'verify', '--phase', phase,
                '--scratch', self.scratch, '--operation', operation, '--stdout', location / 'stdout.log',
                '--returncode', str(result['returncode']), '--main-sha', HEAD,
                '--checkout', W, '--config', config, *route_args])
            return outcome
        finally:
            roots = sorted(set(operations.glob(step + '-*')) - before)
            self.current['new_operation_roots_observed'] = list(map(str, roots))
            self.index_preserved_evidence([path for root in roots for path in sorted(root.rglob('*'))])

    def index_preserved_evidence(self, paths):
        preserving_failure = sys.exc_info()[0] is not None
        try:
            for path in paths:
                if path.is_file():
                    self.receipt(path)
        except Exception as exc:
            self.current.setdefault('receipt_collection_errors', []).append(str(exc).replace(chr(64), '(at)'))
            if not preserving_failure:
                raise

    def stage_a_prerequisites(self):
        project = self.config.get('projects', {}).get(self.project, {})
        required = ('runtime_inputs', 'system_path', 'job_id', 'run_date', 'attempt_id',
                    'attempt_directory', 'evidence_directory', 'max_draft_checks', 'registration_id', 'label')
        require(all(project.get(key) is not None for key in required), 'finalized C11 choices required before C10')
        for key in ('runtime_inputs', 'system_path'):
            self.bind(physical(project[key]))
        inputs = load(project['runtime_inputs'])
        require(inputs['runtime_path'] == self.config.get('provisional_runtime'), 'C11 provisional input differs')
        require(all(inputs['arguments'].get(key) is not None for key in
                    ('updater_source', 'updater_root', 'thinking_setting', 'thinking_basis', 'admission_policy')),
                'finalized C11 runtime choices required before C10')
        ready_path = self.scratch / 'probe-prepare.json'
        self.bind(ready_path)
        ready = load(ready_path)
        require(ready['commands_executed'] is False and all(ready[key] is True for key in
            ('observation_inputs_ready', 'input_prefix_ready', 'observation_phase_ready')),
            'C09 observation readiness required before C10')
        prefix = self.packet / 'prefix-verification.json'
        self.bind(prefix)
        prepared = load(prefix)
        require(prepared['attempt_root_absent'] is True
                and not os.path.lexists(project['attempt_directory']), 'C08 attempt must remain absent')
        expected_files = {str(self.packet / 'input-prefix' / name) for name in
            ('receipt-policy.json', 'selection.json', 'environment-manifest.json', 'input-inventory.json', 'status.json')}
        require({x['path'] for x in prepared['artifacts']} == expected_files, 'C08 prefix artifact roster differs')
        for item in prepared['artifacts']:
            require(self.bind(Path(item['path'])) == item, 'C08 prefix artifact changed')
        upstream = dict(source_manifest=W / 'data/preprocessed/source_manifest.yaml',
            bundle=W / 'data/preprocessed/concatenated' / (self.project + '_preprocessed.txt'),
            chunk_manifest=W / 'data/preprocessed/chunks' / (self.project + '_chunks.yaml'),
            context=W / 'data/omission_contexts' / (self.project.lower() + '_omission_context.json'),
            full_schema=W / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
            core_schema=W / 'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml')
        command = [str(PY), '-P', '-B', str(W / 'scripts/build_native_canary_packet.py'),
            '--checkout', str(W), '--output', str(self.packet / 'input-prefix'),
            '--stage-root', str(Path(project['attempt_directory']) / 'stages'), '--project', self.project,
            '--profile', 'bridge2ai', '--registration-id', project['registration_id'], '--label', project['label']]
        for key, path in upstream.items():
            self.bind(path)
            command += ['--' + key.replace('_', '-'), str(path)]
        require(prepared['command']['requested_argv'] == command, 'C08 prefix choices differ from current config')
        copied = self.scratch / 'binary-copy.json'
        self.bind(copied)
        selected = load(copied)['copy']
        require(self.bind(Path(selected['path'])) == selected, 'durable selected binary changed')
        runtime_path = physical(self.config['provisional_runtime'])
        self.bind(runtime_path)
        runtime = load(runtime_path)
        require(runtime_path.read_bytes() == canonical(runtime)
                and runtime['executable']['path'] == selected['path']
                and runtime['executable']['sha256'] == selected['sha256'], 'C09 selected runtime differs')

    def c10(self):
        self.stage_a_prerequisites()
        for key in ('authorization', 'provisional_runtime', 'observation_account_choice'):
            require(self.config.get(key), 'finalized D117 config required: ' + key)
            self.bind(Path(self.config[key]))
        from data_sheets_schema import native_u4b_probe_sequence as probes
        authorized = probes.authorization(Path(self.config['authorization']).read_bytes(),
                                          load(self.config['provisional_runtime']))
        directory = physical(authorized['directory'], exists=False)
        require(not os.path.lexists(directory), 'C10 directory already exists; no automatic retry')
        try:
            result, _ = self.command('observation-probe', [PY, '-P', '-s', '-B', '-m',
                'data_sheets_schema.native_generation', 'observation-probe',
                '--authorization', self.config['authorization'], '--runtime', self.config['provisional_runtime'],
                '--account-choice', self.config['observation_account_choice']],
                timeout=authorized['observation_deadline_seconds'] + 120)
            receipt = json.loads(result['stdout'])
            require(receipt['command'] == 'observation-probe'
                    and receipt['result']['manifest'] == str(directory / 'observation/observation.json')
                    and receipt['result']['sha256'] == pin(directory / 'observation/observation.json')['sha256'],
                    'C10 observation result differs')
        finally:
            self.index_preserved_evidence(sorted(directory.rglob('*')))
        observation = directory / 'observation/observation.json'
        self.bind(observation)
        if self.observation_reader:
            observed = self.observation_reader(observation)
        else:
            from data_sheets_schema import native_u4b_probe_sequence as probes
            observed = probes.validate_observation(str(observation))
        self.observed, self.observation = observed, observation
        for key in ('pin', 'transcript', 'request'):
            require(self.bind(Path(observed[key]['path'])) == observed[key], 'C10 pin mismatch: ' + key)
        terminal = json.loads(Path(observed['transcript']['path']).read_bytes().splitlines()[-1])
        self.limits = observed_model_usage(observed['provisional_runtime'], terminal)
        require(type(self.limits['maxOutputTokens']) is int and self.limits['maxOutputTokens'] >= 64000,
                'C10 observed output floor is not met')
        path = self.output / 'C10-observation-binding.json'
        save(path, dict(observation=observed, limits=self.limits, source_commit=HEAD,
                        synthetic_transport=self.fixture))
        self.receipt(path)

    def c11(self):
        project = self.config.get('projects', {}).get(self.project, {})
        required = ('runtime_inputs', 'system_path', 'job_id', 'run_date', 'attempt_id',
                    'attempt_directory', 'evidence_directory', 'max_draft_checks', 'registration_id', 'label')
        missing = ['projects.' + self.project + '.' + key for key in required if project.get(key) is None]
        missing += [key for key in ('authorization', 'provisional_runtime', 'observation_account_choice')
                    if self.config.get(key) is None]
        require(not missing, 'finalized production config required: ' + ', '.join(missing))
        for key in ('authorization', 'provisional_runtime', 'observation_account_choice'):
            self.bind(Path(self.config[key]))
        self.bind(Path(project['system_path']))
        source = Path(project['runtime_inputs']); self.bind(source)
        runtime_inputs = deepcopy(load(source))
        require(runtime_inputs['runtime_path'] == self.config['provisional_runtime'], 'provisional runtime differs')
        from data_sheets_schema import native_u4b_runtime as runtime_api
        from data_sheets_schema import native_model_aliases as model_aliases
        provisional = load(Path(self.config['provisional_runtime']))
        require(canonical(provisional) == canonical(self.observed['provisional_runtime']), 'C10 provisional bytes differ')
        model_pair = model_aliases.model_aliases(provisional)
        _, probe_values = runtime_api._saved_probe(self.observed['transcript']['path'], model_pair)
        _, thinking = runtime_api._saved_request(self.observed['request']['path'], model_pair)
        final_declaration = deepcopy(provisional)
        final_declaration['limits'] = probe_values['limits']
        declaration_path = self.output / 'runtime-declaration-from-C10.json'
        save(declaration_path, final_declaration)
        self.receipt(declaration_path)
        runtime_inputs['runtime_path'] = str(declaration_path)
        arguments = runtime_inputs['arguments']
        for key in ('updater_source', 'updater_root', 'thinking_setting', 'thinking_basis', 'admission_policy'):
            require(key in arguments and arguments[key] is not None, 'missing runtime declaration: ' + key)
        require(canonical(arguments['thinking_setting']) == canonical(thinking['value']),
                'actual C10 thinking differs from the explicit configured declaration')
        arguments.update(observation_probe_path=str(self.observation),
            probe_init_path=self.observed['transcript']['path'], native_request_path=self.observed['request']['path'])
        path = self.output / 'runtime-inputs.json'; save(path, runtime_inputs)
        project['runtime_inputs'] = str(path)
        # C11 deliberately stops at the missing live-permission boundary.
        project.pop('permission_probe', None); project.pop('probe_sequence', None)
        for key in ('qualification', 'registration_commit', 'ci', 'permission_probe'):
            self.config.pop(key, None)
        self.driver('C11', 'register-chorus' if self.legacy_cell1 else 'register-project')

    def choice(self, name, subject):
        # Copy only the previously validated selected intent; derive new hashes.
        from data_sheets_schema import native_generation as generation
        from data_sheets_schema import native_shared_contract as contract
        original = Path(self.config['observation_account_choice'])
        provisional_raw = Path(self.config['provisional_runtime']).read_bytes()
        generation._account_choice(original, provisional_raw, load(Path(self.config['provisional_runtime'])))
        selected = load(original)
        raw = subject.read_bytes(); value = json.loads(raw)
        runtime = value['runtime'] if name == 'permission' else value
        selected.update(subject_sha256=hashlib.sha256(raw).hexdigest(),
                        runtime_sha256=hashlib.sha256(contract.canonical(runtime)).hexdigest())
        path = self.output / (name + '-account-choice.json'); save(path, selected)
        generation._account_choice(path, raw, runtime)
        self.receipt(path)
        return path

    def c12(self):
        expectation = self.packet / 'expectation/expectation.json'
        choice = self.choice('permission', expectation)
        self.bind(expectation); self.bind(choice)
        root = Path(self.observed['sequence_directory'])
        # Saved successful evidence is validated in C13; spent failures never retry.
        permission = root / 'permission/permission-probe.json'
        if permission.is_file():
            self.permission = permission
            self.current['saved_evidence_reuse'] = self.bind(permission)
            return
        require(not (root / 'bound-claim.json').exists() and not (root / 'bound-failure.json').exists(),
                'C12 phase already spent or failed; owner/lead must resolve, no automatic retry')
        try:
            result, _ = self.command('bound-permission', [PY, '-P', '-s', '-B', '-m',
                'data_sheets_schema.native_generation', 'bound-permission-probe',
                '--authorization', self.config['authorization'], '--expectation', expectation,
                '--account-choice', choice], timeout=900)
        finally:
            self.index_preserved_evidence([root / 'bound-claim.json', root / 'bound-failure.json',
                root / 'sequence.json', *sorted((root / 'permission').rglob('*'))])
        value = json.loads(result['stdout'])
        require(value['command'] == 'bound-permission-probe', 'C12 command receipt differs')
        self.permission = Path(value['result']['manifest'])
        require(self.permission == permission and self.bind(permission)['sha256'] == value['result']['sha256'],
                'C12 permission output pin/path differs')

    def c13(self):
        runtime = self.packet / 'runtime/runtime.json'
        choice = self.choice('final-runtime', runtime)
        self.bind(runtime); self.bind(choice)
        result, _ = self.command('validate-sequence', [PY, '-P', '-s', '-B', '-m',
            'data_sheets_schema.native_generation', 'validate-probe-sequence',
            '--runtime', runtime, '--probe', self.permission, '--account-choice', choice])
        value = json.loads(result['stdout'])['result']
        require(value['checked'] is True and value['passed'] is True, 'C13 verification failed')
        for key in ('sequence', 'observation', 'permission'):
            require(self.bind(Path(value[key]['path'])) == value[key], 'C13 pin differs: ' + key)
        require(value['observation'] == self.observed['pin'], 'C13 observation differs from C10')
        self.config['permission_probe'] = str(self.permission)
        self.config['projects'][self.project].update(permission_probe=str(self.permission),
                                               probe_sequence=value['sequence']['path'])

    def c14(self):
        selected = None
        if getattr(self.args, 'r2d_trace_receipt', None) is not None:
            selected = resolve_r2d_trace_receipt(self.args.r2d_trace_receipt,
                                                self.args.r2d_trace_receipt_sha256)
            self.current['selected_lead_r2d_trace'] = selected
            for key in ('receipt', 'registration_pin', 'timing_jsonl_pin', 'pre_dispatch_trace_pin'):
                item = selected[key]
                require(self.bind(Path(item['path'])) == item, 'C14 selected r2d changed: ' + key)
                self.receipt(Path(item['path']))
        timing_paths = {
            'version': getattr(self.args, 'recorded_version_timing', None),
            'auth_status_json': getattr(self.args, 'recorded_auth_timing', None),
        }
        require(all(path is not None for path in timing_paths.values()),
                'C14 requires both recorded version and auth timing receipts')
        timing_pins = {}
        for name, path in timing_paths.items():
            path = physical(path)
            timing_pins[name] = self.bind(path)
            self.receipt(path)
        self.current['selected_timing_receipts'] = timing_pins
        supplied = getattr(self.args, 'qualification', None)
        if supplied is not None:
            require(self.fixture, 'only offline fixtures may supply an existing qualification')
            qualification = physical(supplied)
        else:
            qualification = self.output / 'qualification.json'
            binary = self.timing_context['runtime']['executable']
            self.command('produce-qualification', [PY, '-P', '-s', '-B', QUALIFIER,
                '--checkout', W, '--source-commit', HEAD, '--output', qualification,
                '--scratch-dir', self.output / 'host-qualification',
                '--diagnostic-output', self.output / 'qualification-diagnostic.json',
                '--durable-binary', binary['path'], '--expected-binary-sha256', binary['sha256'],
                '--expected-binary-version', binary['version'],
                '--recorded-version-timing', timing_paths['version'],
                '--recorded-auth-timing', timing_paths['auth_status_json'],
                '--synthetic-trace-attempt', selected['attempt_directory'],
                '--synthetic-pre-dispatch', selected['pre_dispatch_trace_pin']['path'],
                '--bound-permission-probe', self.permission], timeout=1800)
        self.bind(qualification)
        result, _ = self.command('validate-qualification', [PY, '-P', '-s', '-B', QUALIFIER,
            '--checkout', W, '--source-commit', HEAD, '--validate-only', qualification,
            '--recorded-version-timing', timing_paths['version'],
            '--recorded-auth-timing', timing_paths['auth_status_json']], timeout=1800)
        checked = json.loads(result['stdout'])
        require(checked['status'] == 'ok' and checked['mode'] == 'validate_only'
                and checked['validation']['passed'] is True
                and checked['validated_pin'] == pin(qualification), 'C14 receipt mismatch')
        document = load(qualification)
        require(document['production_admissible'] is True and document['qualified'] is True
                and document['evidence_mode'] == 'live_host_offline_qualification', 'C14 is not live qualification')
        selected_timings = checked.get('selected_probe_timings')
        require(type(selected_timings) is dict and set(selected_timings) == set(timing_paths),
                'C14 qualifier did not validate the exact selected timing pair')
        for name, field in (('version', 'version_probe_allowance'),
                            ('auth_status_json', 'auth_status_probe_allowance')):
            allowance = selected_timings[name]
            require(type(allowance) is dict
                    and allowance.get('basis') == 'recorded_authorized_binary_run'
                    and allowance.get('receipt_pin') == timing_pins[name]
                    and canonical(allowance) == canonical(document['n18ab_timing'][field]),
                    'C14 selected timing differs from qualification: ' + name)
            require(pin(timing_paths[name]) == timing_pins[name],
                    'C14 selected timing changed during validation: ' + name)
        self.current['selected_probe_timings'] = selected_timings
        binary = document['durable_binary_hash']
        require(binary['sha256'] == self.observed['provisional_runtime']['executable']['sha256'],
                'C14 binary differs from C10')
        bound = document['n18ab_timing']['bound_permission_probe_reference']
        if bound is not None:
            require(bound['pin'] == pin(self.permission), 'C14 optional permission reference differs from C12')
        trace = document['n18ab_timing']['synthetic_r2d']
        attempt = physical(selected['attempt_directory'] if selected else self.args.r2d_attempt)
        pre = physical(selected['pre_dispatch_trace_pin']['path'] if selected else self.args.r2d_pre_dispatch)
        require(trace['attempt_directory'] == str(attempt), 'C14 r2d attempt differs')
        for key, path in (('registration_pin', attempt / 'registration.json'),
                          ('timing_jsonl_pin', attempt / 'host-controller-timing.jsonl'),
                          ('pre_dispatch_trace_pin', pre)):
            require(self.bind(path) == trace[key], 'C14 supplied r2d pin differs: ' + key)
        self.config['qualification'] = str(qualification)
        self.receipt(qualification)

    def c15(self):
        self.driver('C15', 'register-chorus' if self.legacy_cell1 else 'register-project')
        self.registration = self.packet / 'registration/registration.json'
        self.bind(self.registration); self.receipt(self.registration)
        body = load(self.registration)['registration']
        require(canonical({key: body[key] for key in ('runtime', 'environment', 'working_directory')}) == canonical(self.timing_context),
                'C15 registration differs from measured C11 timing context')

    def c16(self):
        root = physical(self.settings['registration_archive_repository'])
        project = self.config['projects'][self.project]
        from data_sheets_schema.native_u4b_policy import registered_policy
        capture = Path(registered_policy(load(self.registration)['registration']['runtime'])['capture_state_directory'])
        protected_paths = (W, R, F, self.scratch, Path(project['attempt_directory']),
                           Path(project['evidence_directory']), capture, *map(Path, self.inputs))
        for protected in protected_paths:
            require(not root.is_relative_to(protected) and not protected.is_relative_to(root),
                    'archive must be persistent and disjoint from source, packet and attempt roots')
        def git(label, *args):
            return self.command(label, ['/usr/bin/git', '-C', root, *args], cwd=root)[0]['stdout'].decode().strip()
        require(git('archive-root', 'rev-parse', '--show-toplevel') == str(root), 'archive must be exact Git root')
        branch = git('archive-branch', 'branch', '--show-current')
        require(branch and branch not in ('main', 'master'), 'archive requires dedicated non-main branch')
        require(not git('archive-clean', 'status', '--porcelain', '--untracked-files=all'), 'archive must be clean')
        result, _ = self.command('author-date', [PY, '-P', '-s', '-B', W / 'scripts/native_registration_timestamp.py',
            '--registration', self.registration, '--author-date-only'])
        valid_from = result['stdout'].decode().strip()
        attempt = load(self.registration)['registration']['attempt_id']
        require(attempt and Path(attempt).name == attempt and attempt not in ('.', '..'), 'invalid archive attempt basename')
        relative = Path('registrations') / attempt / 'registration.json'
        target = root / relative
        physical(target, exists=False)
        save(target, self.registration.read_bytes(), raw=True)
        git('archive-add', 'add', '--', str(relative))
        require(git('archive-index', 'diff', '--cached', '--name-only') == str(relative), 'archive index contains unrelated paths')
        git('archive-commit', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit',
            '--date', valid_from, '-m', 'Archive exact native ' + self.project + ' registration ' + attempt)
        commit = git('archive-head', 'rev-parse', 'HEAD')
        evidence = self.output / 'registration-commit.json'
        save(evidence, dict(repository=str(root), path=str(relative), commit=commit))
        self.command('archive-verify', [PY, '-P', '-s', '-B', W / 'scripts/native_registration_timestamp.py',
            '--registration', self.registration, '--verify-evidence', evidence])
        self.bind(evidence); self.receipt(evidence)
        self.config['registration_commit'] = str(evidence)

    def c17(self):
        gate = physical(self.config['gate_root'])
        expected = Path(self.config['gate_expected_pins']); self.bind(expected)
        for name, row in load(expected)['tools'].items():
            require(self.bind(gate / 'scripts' / name) == row, 'selected gate root/tool differs from approved pin')
        tuples = Path(self.settings['np1b_tuples']); floor = Path(self.settings['floor'])
        self.bind(tuples); self.bind(floor)
        output = self.packet / 'np15-gate-check'
        self.command('actual-comparison', [PY, '-I', '-B', gate / 'scripts/native_registration_pin_gate.py',
            '--reference', self.registration, '--candidate', self.registration, '--tuple', tuples,
            '--floor', floor, '--expected-tool-pins', expected, '--reference-root', W,
            '--python', PY, '--dependency-prefix', W / '.venv', '--dependency-root', W / '.venv/lib/python3.13/site-packages',
            '--timeout-seconds', '1800', '--output', output, '--source-bound-validation'], timeout=2000)
        comparison = output / 'comparison-result.json'
        require(load(comparison)['status'] == 'equal' and not load(comparison).get('unknown'), 'C17 comparison is not equal')
        for path in sorted(output.rglob('*')):
            if path.is_file(): self.receipt(path)

    def c18(self):
        self.driver('C18', 'preflight-all')
        evidence = Path(self.settings['envelope_measurements'])
        expected = self.settings['envelope_measurements_sha256']
        require(self.bind(evidence)['sha256'] == expected, 'C18 approved measurements pin differs')
        output = self.output / 'all-five-envelope-comparison.json'
        self.command('complete-envelope', [PY, '-P', '-s', '-B', COMPARATOR,
            '--observation', self.observation, '--evidence', evidence,
            '--evidence-sha256', expected, '--output', output])
        require(load(output)['overall'] == 'PASS', 'C18 complete envelope remains unresolved')
        self.receipt(output)
        self.actual_sizing = Path(self.settings['actual_chorus_sizing' if self.legacy_cell1 else 'actual_sizing'])
        sizing = load(self.actual_sizing)
        require(sizing.get('head') == HEAD, 'actual ' + self.project + ' sizing is not e772-bound')
        if not self.legacy_cell1:
            require(sizing.get('project') == self.project, 'actual sizing belongs to another project')
        self.bind(self.actual_sizing)

    def c19(self):
        output = self.output / 'ci.json'
        argv = [PY, '-P', '-s', '-B', CI, '--checkout', W, '--registration', self.registration,
                '--source-commit', HEAD, '--tested-commit', HEAD,
                '--workflow-event', 'push', '--workflow-ref', 'refs/heads/main', '--output', output]
        saved = self.settings.get('saved_ci')
        if saved:
            run = Path(saved['run_json']); jobs = Path(saved['jobs_json'])
            require(str(load(run)['id']) == str(self.args.ci_run_id), 'saved CI run id differs')
            self.bind(run); self.bind(jobs)
            argv += ['--run-json', run, '--jobs-json', jobs]
            for item in saved.get('extra_runs', []):
                run = Path(item['run_json']); jobs = Path(item['jobs_json'])
                self.bind(run); self.bind(jobs)
                argv += ['--companion-run-json', run, '--companion-jobs-json', jobs]
        else:
            argv += ['--run-id', str(self.args.ci_run_id)]
            for run_id in self.settings.get('extra_ci_run_ids', []):
                argv += ['--companion-run-id', str(run_id)]
        result, _ = self.command('pack-ci', argv, timeout=900)
        packed = json.loads(result['stdout'])
        require(packed['status'] == 'ok' and packed['output'] == pin(output)
                and self.args.ci_run_id in packed['run_ids'] and packed['workflow_event'] == 'push'
                and packed['workflow_ref'] == 'refs/heads/main'
                and packed['source_commit'] == packed['tested_commit'] == HEAD,
                'C19 successful receipt or output binding differs')
        self.bind(output); self.receipt(output)
        self.config['ci'] = str(output)
        self.driver('C19', 'register-chorus' if self.legacy_cell1 else 'register-project')

    def c20(self):
        comparison = self.packet / 'np15-gate-check/comparison-result.json'
        sums = self.output / ('actual-chorus-review-inputs.sha256' if self.legacy_cell1 else
                             'actual-' + self.project.lower() + '-rep' + str(self.rep) + '-review-inputs.sha256')
        save(sums, ''.join(pin(path)['sha256'] + '  ' + str(path) + '\n'
                          for path in (comparison, self.actual_sizing)).encode(), raw=True)
        config = self.config_snapshot('C20')
        output = self.scratch / 'rc3-post-probe-review-packets'
        route_args = [] if self.legacy_cell1 else ['--project', self.project, '--rep', str(self.rep)]
        self.command('stage-reviews', [PY, '-I', '-B', RC3, '--scratch', self.scratch,
            '--checkout', W, '--main-sha', HEAD, '--config', config, '--actual-sizing', self.actual_sizing,
            '--review-inputs-sha256', sums, '--output', output, '--reviewer-pair', self.reviewer_pair, *route_args], allowed=(2,))
        value = load(output / 'result.json')
        require(value['stage'] == 'complete' and value['reviewer_pair'] == self.reviewer_pair
            and value['reviewer_kinds'] == REVIEWERS[self.reviewer_pair] and value['acceptance_granted'] is False
            and value['driver_status_code'] == 2 and value['driver_status'] == 'draft_with_holds',
            'C20 did not produce the exact draft pair')
        if not self.legacy_cell1:
            require(canonical(value.get('cell_route')) == canonical(
                    {key: self.route[key] for key in ('project', 'rep', 'reviewer_pair')}),
                    'C20 staged packet cell route differs')
        for root in (output, self.scratch / 'reviews'):
            for path in sorted(root.rglob('*')):
                if path.is_file(): self.receipt(path)

    def run(self):
        actions = ((self.c10, self.c11) if self.stage == 'a' else
                   (self.c12, self.c13, self.c14, self.c15, self.c16, self.c17, self.c18, self.c19, self.c20))
        try:
            for row, action in zip(self.rows, actions):
                self.current = row
                start = time.monotonic()
                row['status'] = 'running'
                try:
                    self.unchanged()
                    action()
                    self.unchanged()
                    row['status'] = 'completed'
                except Exception as exc:
                    row.update(status='refused', error_type=type(exc).__name__, error=str(exc).replace(chr(64), '(at)'))
                    raise
                finally:
                    row['wall_seconds'] = time.monotonic() - start
                    save(self.output / (row['step'] + '-summary.json'), row)
            self.summary['status'] = ('C11_complete_waiting_for_owner_timings' if self.stage == 'a'
                                      else 'draft_reviews_staged_with_holds')
        except Exception:
            self.summary.update(status='stopped', stopped_step=self.current['step'])
        self.summary['finished_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        result = save(self.output / 'summary.json', self.summary)
        outcome = dict(summary=result, status=self.summary['status'], stopped_step=self.summary.get('stopped_step'))
        if self.stage == 'a' and self.summary['status'] == 'C11_complete_waiting_for_owner_timings':
            try:
                outcome['handoff'] = self.publish_handoff(result)
            except Exception as exc:
                outcome.update(status='stopped', stopped_step='handoff', error=str(exc).replace(chr(64), '(at)'))
                save(self.output / 'handoff-failure.json', outcome)
        return outcome

def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('stage', choices=('a', 'b'))
    parser.add_argument('--project', choices=PROJECTS, default='CHORUS')
    parser.add_argument('--rep', type=int, default=1)
    parser.add_argument('--scratch', type=Path, default=F,
        help='Cell preparation root; a new cell requires its own execution directory below the frozen fastpath root.')
    parser.add_argument('--config', type=Path, help='Finalized cell config; default is SCRATCH/production-inputs.json.')
    parser.add_argument('--reviewer-pair', choices=tuple(REVIEWERS), default='codex-claude')
    parser.add_argument('--execute', action='store_true',
        help='Lead execution: A owner-authorized C10; B C12 plus host qualification, archive and CI; no retries.')
    parser.add_argument('--stage-a-handoff', type=Path)
    parser.add_argument('--stage-a-handoff-sha256')
    parser.add_argument('--recorded-version-timing', type=Path)
    parser.add_argument('--recorded-auth-timing', type=Path)
    parser.add_argument('--timing-provenance', type=Path)
    parser.add_argument('--timing-result', type=Path, help='Saved recorder stdout proving passed and durability_confirmed.')
    parser.add_argument('--r2d-trace-receipt', type=Path)
    parser.add_argument('--r2d-trace-receipt-sha256')
    parser.add_argument('--ci-run-id', type=int)
    args = parser.parse_args()
    require(args.rep > 0, 'positive cell rep required')
    require(args.project != 'AI_READI' or args.reviewer_pair == 'codex-agy', 'AI_READI requires codex-agy')
    b_inputs = ('stage_a_handoff', 'stage_a_handoff_sha256', 'recorded_version_timing',
                'recorded_auth_timing', 'timing_provenance', 'timing_result',
                'r2d_trace_receipt', 'r2d_trace_receipt_sha256', 'ci_run_id')
    require(all(getattr(args, key) is not None for key in b_inputs) if args.stage == 'b'
            else all(getattr(args, key) is None for key in b_inputs), 'stage-specific inputs differ')
    require(Path(sys.prefix).resolve() == W / '.venv', 'use the frozen production interpreter')
    sys.path.insert(0, str(W / 'src'))
    require((W / '.git/HEAD').read_text().strip() == HEAD, 'frozen source HEAD differs')
    if not args.execute:
        plan = dict(kind='post_probe_stage_plan_only', source_commit=HEAD, stage=args.stage,
            configuration=str(args.config or args.scratch / 'production-inputs.json'),
            steps=list(STEPS[:2] if args.stage == 'a' else STEPS[2:]), executes=False,
            inputs_validated=False, output=str(args.scratch / ('post-probe-stage-' + args.stage)),
            qualification_mode='B produces then validates current host qualification.',
            live_boundary='A C10 and B C12 require actual owner D117 authorization; timing and host permission are separate.')
        if (args.project, args.rep, args.reviewer_pair) != ('CHORUS', 1, 'codex-claude'):
            plan['cell_route'] = dict(project=args.project, rep=args.rep, reviewer_pair=args.reviewer_pair,
                scratch=str(args.scratch), configuration=plan['configuration'],
                packet=str(args.scratch / 'packets' / args.project))
        print(json.dumps(plan, indent=2))
        return 0
    result = Chain(args).run()
    print(json.dumps(result))
    return 2 if result['status'] == 'stopped' else 0

if __name__ == '__main__':
    raise SystemExit(main())
