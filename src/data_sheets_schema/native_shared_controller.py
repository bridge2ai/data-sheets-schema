"""Explicit offline native-shared composition and fixed callback controller.

Runtime binding reads and fingerprints supplied declarations only. Native
version/auth observations and dispatch belong exclusively to the execution
lifetime, after independently supplied permission and launch evidence.
"""
from __future__ import annotations

from pathlib import Path
import sys
from copy import deepcopy
from dataclasses import asdict

from . import native_shared_contract as c
from . import native_shared_render as render
from . import native_shared_selection as selection
from . import native_shared_policy as policy
from . import native_attribution_controller as inherited
from . import native_execution_registration as runtime_registration
from .native_shared_evidence import read_regular

KIND = 'd4d_native_shared_callback_composition'
VERSION = 1
EXECUTION = 'offline_composition_only_requires_separate_native_execution_registration'


def bind_runtime(spec, runtime_path, max_draft_checks):
    """Bind the one explicit R and allowance, without executing any binary."""
    if render.validate_spec(spec) is None:
        raise ValueError('runtime binding requires explicitly selected native26')
    c.positive_int(max_draft_checks, 'native draft-check allowance')
    artifact = read_regular(str(runtime_path), 'runtime_declaration',
                            max_bytes=c.HARD_LIMITS['input_bytes']).captured
    runtime = runtime_registration.validate_runtime(c.strict_json(artifact.raw, 'runtime declaration'))
    if (runtime['provider'], runtime['effort']) != (spec.provider, spec.reasoning_effort):
        raise ValueError('runtime provider/effort differ from the explicit selected spec')
    previous = getattr(spec, '_native_shared_runtime_capture', None)
    if previous is not None and previous != artifact:
        raise ValueError('cannot rebind an existing native runtime authority')
    allowance = getattr(spec, '_native_shared_max_draft_checks', None)
    if allowance is not None and (type(allowance) is not int or allowance != max_draft_checks):
        raise ValueError('cannot rebind an existing native draft-check allowance')
    spec._native_shared_runtime_capture = artifact
    spec._native_shared_max_draft_checks = max_draft_checks
    return spec


def compose(spec, *, runtime_path, instruction_path, max_draft_checks):
    """Capture selected S/R/instruction/policy; this is not launch authority."""
    bind_runtime(spec, runtime_path, max_draft_checks)
    declared = render.validate_spec(spec)
    current = selection.capture(declared['registration_path'])
    if current.registration.raw != spec.native_shared_generation_registration.encode('utf-8'):
        raise ValueError('composition selection differs from actual S bytes')
    if current.generation_context() != render.metadata(spec)['native_shared_generation_context']:
        raise ValueError('composition generation context differs from captured S authority')
    spec._native_shared_generation_capture = current
    instruction = read_regular(str(instruction_path), 'instruction', max_bytes=c.HARD_LIMITS['request_bytes']).captured
    if instruction.raw != spec.instruction.encode('utf-8'):
        raise ValueError('composition instruction differs from the actual selected rendering')
    controls = inherited.load_controls()
    selected_policy = policy.command_policy(spec, instruction.pin.path, controls)
    runtime = spec._native_shared_runtime_capture
    return {'kind': KIND, 'version': VERSION, 'execution': EXECUTION,
        'selection_raw_json': current.registration.raw.decode('utf-8'),
        'selection_sha256': current.registration.pin.sha256,
        'runtime_path': runtime.pin.path, 'runtime_raw_json': runtime.raw.decode('utf-8'),
        'runtime_sha256': runtime.pin.sha256, 'max_draft_checks': max_draft_checks,
        'render_spec': spec.render_spec(), 'instruction_path': instruction.pin.path,
        'instruction_sha256': instruction.pin.sha256,
        'controller_sources': inherited.controller_sources(),
        'controller_sources_sha256': inherited.SOURCES_SHA256,
        'policy': selected_policy, 'policy_sha256': c.sha(c.canonical(selected_policy)),
        'working_directory': str(Path.cwd().resolve()), 'python': sys.executable, 'python_version': sys.version}


def verified_composition(raw):
    """Rebuild from exact captured metadata and recheck current S/R identities."""
    from .api_runner import RunSpec
    value = c.strict_json(raw, 'native shared composition', c.HARD_LIMITS['request_bytes'])
    if type(value) is not dict or value.get('kind') != KIND:
        raise ValueError('not a native shared callback composition')
    try:
        doc = c.parse_selection(value['selection_raw_json'].encode('utf-8'))
        run = doc['run']
        spec = RunSpec.from_render_spec(value['render_spec'], project=run['project'],
                                       method=run['method'], label=run['label'])
        expected = compose(spec, runtime_path=value['runtime_path'],
                           instruction_path=value['instruction_path'], max_draft_checks=value['max_draft_checks'])
    except (KeyError, AttributeError, TypeError) as exc:
        raise ValueError('malformed native shared callback composition') from exc
    if c.canonical(value) != c.canonical(expected):
        raise ValueError('native shared composition identity changed')
    return value


class CallbackAdapter:
    """Fixed observer/classifier supplied only to the authorized shared lifetime.

    The phase observer runs before any effect permission or attribution credit.
    Stage Read/Write evidence is recorded at the real ordered observer barrier;
    command classification remains the exact selected fixed policy.
    """
    def __init__(self, composition_raw, *, execution, registration_raw):
        from .api_runner import RunSpec
        from .native_shared_phase import PhaseState
        from . import native_shared_attribution as attribution
        self.raw = composition_raw
        self.value = verified_composition(composition_raw)
        if (c.canonical(execution) != c.canonical(c.strict_json(registration_raw, 'execution', c.HARD_LIMITS['request_bytes']))
                or execution['composition_raw_json'].encode('utf-8') != composition_raw
                or execution['composition_sha256'] != c.sha(composition_raw)
                or type(execution['max_draft_checks']) is not int
                or execution['max_draft_checks'] != self.value['max_draft_checks']):
            raise ValueError('callback adapter differs from its exact verified execution composition')
        self.execution, self.registration_raw = deepcopy(execution), registration_raw
        doc = c.parse_selection(self.value['selection_raw_json'].encode('utf-8'))
        run = doc['run']
        self.spec = RunSpec.from_render_spec(self.value['render_spec'], project=run['project'], method=run['method'], label=run['label'])
        self.selection = selection.capture(doc['registration_path'])
        self.controls = inherited.load_controls()
        self.policy = deepcopy(self.value['policy'])
        paths = self.spec._agentic_artifact_paths
        self.phase = PhaseState(render.commands(self.spec), full_path=paths['full'], core_path=paths['core'],
            report_path=paths['report'], receipt_path=paths['receipt'], working_directory=self.value['working_directory'])
        self.state = attribution.live(self.selection, execution_raw=registration_raw, spec=self.spec, composition_raw=composition_raw)
        self.failure = self.final_evidence = self.recorder_identity = None
        self.recorder_call = None
        self.recorder_done = False
        self._activated = self._initialized = False
        self._through_bytes = 0
        self._prefix_sha256 = c.sha(b'')

    def require_phase_authority(self):
        if (not self.policy or self.policy != self.value['policy'] or self.spec.render_version != 26
                or self.spec.native_shared_generation_version != 1 or self.phase is None):
            raise ValueError('native26 requires its actual fixed phase observer and selected policy')

    def activate_before_dispatch(self, started_raw):
        from . import native_shared_capture as capture
        if self._activated:
            raise ValueError('native shared callback identity is already spent')
        # Latch before any fallible write: partial activation cannot redispatch.
        self._activated = True
        capture.activate(self.selection, self.registration_raw, started_raw)

    def _stop(self, reason):
        if self.failure is None:
            self.failure = str(reason)
        raise self.controls['budgeted_cborg'].BudgetStop(self.failure)

    def _observed_endpoint(self, event):
        path = str(Path(self.execution['attempt_directory']) / 'transcript.jsonl')
        item = read_regular(path, 'transcript', max_bytes=c.HARD_LIMITS['stream_bytes']).captured
        if c.sha(item.raw[:self._through_bytes]) != self._prefix_sha256:
            raise ValueError('previously observed native stream prefix changed')
        end = item.raw.find(b'\n', self._through_bytes)
        if end < 0:
            raise ValueError('observer has no complete corresponding native physical frame')
        actual = c.strict_json(item.raw[self._through_bytes:end + 1], 'observed native frame', 16 * 1024 * 1024)
        if c.canonical(actual) != c.canonical(event):
            raise ValueError('observer event differs from its next exact raw native frame')
        self._through_bytes = end + 1
        self._prefix_sha256 = c.sha(item.raw[:end + 1])
        control = read_regular(str(Path(self.execution['attempt_directory']) / 'control.jsonl'),
            'control', max_bytes=c.HARD_LIMITS['stream_bytes']).captured
        return self._through_bytes, len(control.raw)

    def _run(self, endpoints=None):
        from . import native_shared_capture as capture
        if endpoints is None:
            return capture._load(self.selection.registration.pin.path)
        return capture._load(self.selection.registration.pin.path,
            transcript_bytes=endpoints[0], control_bytes=endpoints[1])

    def _current_final(self, run):
        from .native_shared_gates import current_evidence
        result = current_evidence(run)
        if result.get('checked') is not True or result.get('findings') != []:
            raise ValueError('current selected final evidence did not pass')
        return result

    def _final_unchanged(self, run):
        if self.final_evidence is not None and c.canonical(self._current_final(run)) != c.canonical(self.final_evidence):
            raise ValueError('final evidence changed after its actual successful check')
        if self.recorder_identity is not None:
            item = read_regular(self.recorder_identity['path'], 'provenance', max_bytes=c.HARD_LIMITS['request_bytes']).captured
            if item.pin.sha256 != self.recorder_identity['sha256']:
                raise ValueError('completed selected provenance record changed')

    def _effect_stop(self, run, event, classification, basis):
        """Persist exact observer restriction before the frozen callback grant."""
        from .native_attempt_supervisor import durable_new
        data = event['request']['input']
        trace = run.trace(); request = trace.request(data['tool_use_id'])
        view = self._view(run, exclude_pending=data['tool_use_id'])
        body = {'kind': 'native_shared_effect_stop', 'version': 1, 'reason_code': 'prohibited_file_effect',
            'selection_sha256': run.selection.registration.pin.sha256, 'policy_sha256': run.composition['policy_sha256'],
            'view_sha256': c.sha(c.canonical(asdict(view))), 'tool_use_id': request.tool_use_id,
            'callback_id': event['request_id'], 'tool_name': request.tool_name,
            'tool_input_sha256': c.sha(request.input_json), 'classification': classification, 'basis': basis,
            'call_event_sha256': c.sha(c.canonical(trace.frames[request.call.line])),
            'callback_event_sha256': c.sha(c.canonical(event))}
        durable_new(Path(self.execution['attempt_directory']) / 'native-shared-effect-stop.json', c.canonical(body))
        self._stop('native shared observer restriction: ' + basis)

    def _view(self, run, *, exclude_pending=None):
        from .native_shared_capture import current_effect_view
        return current_effect_view(run, correction_window=bool(self.state.checks), exclude_pending=exclude_pending)

    def observe(self, event):
        from . import native_shared_capture as capture
        from . import native_shared_effects as effects
        from . import native_shared_evidence as evidence
        if self.failure is not None:
            self._stop(self.failure)
        try:
            if not self._activated:
                raise ValueError('native observation precedes consumed execution activation')
            endpoints = self._observed_endpoint(event)
            if event.get('type') == 'system' and event.get('subtype') == 'init':
                if self._initialized:
                    raise ValueError('native initialization repeated')
                capture.initialize(self.selection.registration.pin.path,
                    transcript_bytes=endpoints[0], control_bytes=endpoints[1])
                self._initialized = True
            if not self._initialized:
                if event.get('type') != 'control_response':
                    raise ValueError('native effects precede actual initialization binding')
                self.phase.observe(event)
                self.state.observe(event)
                return
            run = self._run(endpoints)
            decision = run.decision()
            content = event.get('message', {}).get('content', [])
            content = content if type(content) is list else ()
            # Validate actual advance effects before the phase checker can
            # credit a tool result's claimed post-state.
            for block in content:
                if type(block) is not dict or block.get('type') != 'tool_result':
                    continue
                call = run.trace().calls.get(block.get('tool_use_id'))
                if call and call[2].get('input', {}).get('command') == self.policy['native_shared_helpers']['advance']:
                    capture.observe_advance_settled(run, block['tool_use_id'])
                    run = self._run(endpoints); decision = run.decision()
            if event.get('type') == 'control_request':
                data = event.get('request', {}).get('input', {})
                name, inputs = data.get('tool_name'), data.get('tool_input')
                # Mandatory phase-before-effect and phase-before-attribution.
                self.phase.before(name, inputs, stage_decision=decision)
                view = self._view(run, exclude_pending=data.get('tool_use_id'))
                if policy.stage_overlay_governs(view, tool_name=name, tool_input=inputs, policy=self.policy):
                    classification, basis = effects.classify_effect(view, tool_name=name, tool_input=inputs)
                    if classification != 'prescribed':
                        if name in ('Read', 'Write', 'Edit', 'MultiEdit'):
                            self._effect_stop(run, event, classification, basis)
                        raise ValueError('native stage callback refused: ' + basis)
                    if name == 'Write':
                        capture.observe_response_intent(run, data['tool_use_id'])
                if inputs.get('command') == self.policy['native_shared_helpers']['recorder']:
                    if self.final_evidence is None or self.state.accepted is None or self.recorder_call != data['tool_use_id']:
                        raise ValueError('recorder callback lacks its settled fresh draft/final evidence')
                    if run.trace().pending() != (data['tool_use_id'],):
                        raise ValueError('recorder callback overlaps another pending effect')
                    target = Path(self.policy['post_final_recorder']['destination'])
                    if target.exists() or target.is_symlink():
                        raise ValueError('recorder destination already exists; never overwrite')
                    self._final_unchanged(run)
            actions = self.phase.observe(event, stage_decision=decision)
            preserved = set()
            for block in content:
                if type(block) is not dict:
                    continue
                if block.get('type') == 'tool_use':
                    if self.recorder_done:
                        raise ValueError('tool continuation after final recorder')
                    inputs = block.get('input', {})
                    if block.get('name') == 'Write':
                        self.final_evidence = None
                    if block.get('name') == 'Bash':
                        command = inputs.get('command')
                        if command == self.policy['native_shared_helpers']['draft']:
                            self.final_evidence = None
                        elif command == self.policy['native_shared_helpers']['recorder']:
                            if self.final_evidence is None or self.recorder_call is not None:
                                raise ValueError('recorder requires exactly one settled final pass')
                            self.recorder_call = block['id']; preserved.add(command)
                        elif self.state.checks and self.state._command_kind(command) is None:
                            readonly = self.controls['native_readonly'].lookup_command(command,
                                self.policy['readonly_lookups'], self.controls['native_command_policy']._simple_command)
                            if not readonly:
                                raise ValueError('draft correction permits only report Writes and registered read-only checks')
                            preserved.add(command)
                elif block.get('type') == 'tool_result':
                    identity = block['tool_use_id']; trace = run.trace(); call = trace.calls[identity][2]
                    inputs = call['input']
                    if call['name'] == 'Read' and decision is not None and decision.request is not None and inputs.get('file_path') == decision.request.pin.path:
                        capture.observe_request_read(run, identity)
                    elif call['name'] == 'Write' and decision is not None and decision.response is not None and inputs.get('file_path') == decision.response.path:
                        capture.observe_response_written(run, identity)
                    elif call['name'] == 'Bash' and inputs.get('command') == self.policy['native_shared_helpers']['final_evidence']:
                        current = self._current_final(run)
                        actual = trace.settled(identity)
                        observed_result = evidence.event(run.transcript, actual.result)
                        meta = event.get('tool_use_result', {})
                        for raw in (observed_result.get('content'), meta.get('stdout')):
                            if type(raw) is not str or c.canonical(c.strict_json(raw.encode(), max_bytes=c.HARD_LIMITS['request_bytes'])) != c.canonical(current):
                                raise ValueError('final helper stdout differs from actual captured final evidence')
                        self.final_evidence = current
                    elif identity == self.recorder_call:
                        metadata = event.get('tool_use_result', {})
                        codes = [metadata[k] for k in ('exitCode', 'exit_code') if k in metadata]
                        if not codes or any(type(code) is not int or code != 0 for code in codes) or block.get('is_error') is not False:
                            raise ValueError('selected final recorder did not settle successfully')
                        item = read_regular(self.policy['post_final_recorder']['destination'], 'provenance', max_bytes=c.HARD_LIMITS['request_bytes']).captured
                        from .audit_omissions import _mapping
                        record = _mapping(item.raw, 'native provenance')
                        if c.canonical(record.get('native_shared_generation')) != c.canonical(capture._provenance_block(run)):
                            raise ValueError('recorder did not preserve exact native selected stage lineage')
                        self.recorder_done = True
                        self.recorder_identity = {'path': item.pin.path, 'sha256': item.pin.sha256}
            for action in actions:
                # These fixed side effects independently replay the settled
                # phase boundary before creating any original seal.
                capture.seal_originals(self._run(endpoints), action)
            self.state.observe(event, preserved_shell_commands=preserved)
            problems = self.state.report()['problems']
            if problems:
                raise ValueError('native attribution: ' + '; '.join(problems))
            self._final_unchanged(run)
        except Exception as exc:
            self._stop('native shared observation failed: ' + type(exc).__name__ + ': ' + str(exc))

    def classify(self, command, python, programs, selected_policy):
        if self.failure is not None:
            self._stop(self.failure)
        if c.canonical(selected_policy) != c.canonical(self.policy):
            self._stop('native callback command policy differs from its exact composition')
        return policy.classify_bash(command, python, programs, selected_policy, controls=self.controls)

    def report(self, *, complete=False):
        if complete and self.failure is None:
            try:
                run = self._run()
                phase, _ = capture_phase(run, complete=True)
                if not phase['passed']:
                    raise ValueError('; '.join(phase['problems']))
                self._final_unchanged(run)
            except Exception as exc:
                self.failure = 'completed native shared history cannot be verified: ' + type(exc).__name__ + ': ' + str(exc)
        out = self.state.report(complete=complete)
        return {**out, 'execution': EXECUTION, 'composition_sha256': c.sha(self.raw),
            'controller_stop': self.failure, 'final_evidence': deepcopy(self.final_evidence),
            'recorder_completed': self.recorder_done, 'recorder_identity': deepcopy(self.recorder_identity),
            'phase_history': self.phase.report(complete=complete),
            'draft_gate_passed': out['draft_gate_passed'] and self.failure is None}


def capture_phase(run, *, complete):
    from .native_shared_capture import phase_replay
    return phase_replay(run, complete=complete)
