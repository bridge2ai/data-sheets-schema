"""Current-source composition verification and fixed callback actuation.

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
from . import native_attribution_controller_v2 as inherited
from . import native_execution_registration_v2 as registration
from . import native_execution_authority_v2 as authority
from . import native_shared_controller as consumer
from .native_shared_evidence import read_regular
from . import native_shared_streams as live_streams
from . import native_shared_controls_orchestration as control_loading
from . import native_shared_permission_protocol_orchestration as protocol_loading
from . import native_shared_callback_orchestration as callback_loading

EXECUTION = consumer.EXECUTION


def _file_pin(artifact):
    return {'path': artifact.pin.path, 'bytes': artifact.pin.bytes, 'sha256': artifact.pin.sha256}


def _compose(preparation_raw, instruction_path, *, submitted_raw=None):
    """Reconstruct only after the full current preparation has verified.

    RunSpec boundary: guarded
    """
    from .api_runner import RunSpec, _require_registered_input_spellings
    declared = consumer.captured_preparation_body(preparation_raw)
    prepared = registration.verify_preparer(preparation_raw, job_id=declared['job_id'])
    current = selection.capture(prepared['selection']['path'])
    if _file_pin(current.registration) != prepared['selection']:
        raise ValueError('composition selection changed after preparation verification')
    doc = current.document()
    run = doc['run']
    spec = RunSpec.from_render_spec(prepared['render_spec'], project=run['project'],
                                   method=run['method'], label=run['label'])
    if (render.validate_spec(spec) != doc
            or current.generation_context() != render.metadata(spec)['native_shared_generation_context']):
        raise ValueError('composition selection differs from prepared rendering')
    runtime = read_regular(prepared['runtime']['path'], 'runtime_declaration',
                           max_bytes=c.HARD_LIMITS['input_bytes']).captured
    if _file_pin(runtime) != prepared['runtime']:
        raise ValueError('composition runtime changed after preparation verification')
    spec._native_shared_generation_capture = current
    spec._native_shared_runtime_capture = runtime
    instruction = read_regular(str(instruction_path), 'instruction',
                                max_bytes=c.HARD_LIMITS['request_bytes']).captured
    if (instruction.raw != prepared['instruction'].encode('utf-8')
            or instruction.raw != spec.instruction.encode('utf-8')
            or instruction.pin.sha256 != prepared['instruction_sha256']):
        raise ValueError('composition instruction differs from the exact prepared rendering')
    _require_registered_input_spellings(spec)
    if spec.render_spec() != prepared['render_spec']:
        raise ValueError('composition rendering differs from the exact prepared rendering')
    command_argv = render.commands(spec)
    repository = str(Path.cwd().resolve())
    artifacts = spec._agentic_artifact_paths
    output_directories = tuple(str(Path(artifacts[key]).parent.resolve())
                               for key in ('full', 'core', 'report'))
    dependencies = prepared['dependencies']
    with control_loading.loaded_controls(dependencies) as controls, protocol_loading.loaded_protocol(dependencies) as protocol, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_selection',
                package_sources=dependencies['base']['package_sources']) as verified_selection, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_evidence',
                package_sources=dependencies['base']['package_sources']) as verified_evidence, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_controller',
                package_sources=dependencies['base']['package_sources']) as verified_consumer:
        controller_sources = inherited.controller_sources()
        # Exact carrier classes belong to the verified package lifetime too.
        # Recapture through those real source-loaded producers and compare every
        # nested captured value before handing them to the pure consumer. Keep
        # the caller's ordinary captures intact after this bounded scope.
        verified_current = verified_selection.capture(prepared['selection']['path'])
        verified_runtime = verified_evidence.read_regular(runtime.pin.path, 'runtime_declaration',
            max_bytes=c.HARD_LIMITS['input_bytes']).captured
        verified_instruction = verified_evidence.read_regular(instruction.pin.path, 'instruction',
            max_bytes=c.HARD_LIMITS['request_bytes']).captured
        if any(asdict(before) != asdict(after) for before, after in (
                (current, verified_current), (runtime, verified_runtime),
                (instruction, verified_instruction))):
            raise ValueError('composition capture changed across verified source handoff')
        captures = dict(prepared=prepared, spec=spec, current=verified_current, runtime=verified_runtime,
            instruction=verified_instruction, controller_sources=controller_sources, command_argv=command_argv,
            repository=repository, output_directories=output_directories,
            python=sys.executable, python_version=sys.version)
        spec._native_shared_generation_capture = verified_current
        spec._native_shared_runtime_capture = verified_runtime
        try:
            if submitted_raw is None:
                value = verified_consumer.compose(preparation_raw, classifier_projection=controls, **captures)
            else:
                value, _, _ = verified_consumer.reconstruct_composition(
                    submitted_raw, classifier_projection=controls, **captures)
        finally:
            spec._native_shared_generation_capture = current
            spec._native_shared_runtime_capture = runtime
        # Consume the real six-function protocol at the policy boundary. The
        # selected contract must have its exact recognized initialization frame.
        contract = protocol.history_contract()
        if value['policy']['pretool_control'] != contract:
            raise ValueError('composition policy differs from the source-bound history contract')
        frame = protocol.initialize_frame(value['policy']['pretool_control'])
        expected_frame = {'type': 'control_request', 'request_id': protocol.initialization_id(),
            'request': {'subtype': 'initialize', 'hooks': {contract['event']: [{
                'matcher': contract['matcher'], 'hookCallbackIds': [contract['callback_id']],
                'timeout': contract['runtime_callback_timeout_seconds']}]}}}
        if c.canonical(frame) != c.canonical(expected_frame):
            raise ValueError('composition initialization frame differs from the selected contract')
    # Recheck the complete source/input selection after policy rendering, and
    # keep instruction bytes under the same current-file capture discipline.
    if (registration.verify_preparer(preparation_raw, job_id=prepared['job_id']) != prepared
            or read_regular(instruction.pin.path, 'instruction',
                max_bytes=c.HARD_LIMITS['request_bytes']).captured != instruction):
        raise ValueError('composition authority changed during construction')
    if len(c.canonical(value)) > c.HARD_LIMITS['request_bytes']:
        raise ValueError('native shared composition exceeds its complete byte bound')
    return value, spec, current


def compose(preparation_raw: bytes, *, instruction_path):
    """Compose actual U3-A preparation and instruction bytes, without effects."""
    return _compose(preparation_raw, instruction_path)[0]


def reconstruct_composition(raw):
    """Fresh live-source reconstruction; never use in captured-only replay."""
    value = consumer.captured_composition(raw)
    try:
        expected, spec, current = _compose(value['preparation_raw_json'].encode('utf-8'),
                                          value['instruction_path'], submitted_raw=raw)
    except (KeyError, AttributeError, TypeError) as exc:
        raise ValueError('malformed native shared callback composition') from exc
    if c.canonical(value) != c.canonical(expected):
        raise ValueError('native shared composition identity changed')
    return value, spec, current


def verified_composition(raw):
    """Recheck the entire closed composition against fresh U3-A preparation."""
    return reconstruct_composition(raw)[0]


class CallbackAdapter:
    """Fixed observer/classifier supplied only to the authorized shared lifetime.

    The phase observer runs before any effect permission or attribution credit.
    Stage Read/Write evidence is recorded at the real ordered observer barrier;
    command classification remains the exact selected fixed policy.
    """
    def __setattr__(self, name, value):
        if name in ('_classifier', '_callbacks') and name in self.__dict__:
            raise AttributeError('preloaded callback reference cannot be replaced')
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if name in ('_classifier', '_callbacks'):
            raise AttributeError('preloaded callback reference cannot be removed')
        super().__delattr__(name)

    def __init__(self, composition_raw, *, execution, registration_raw):
        # The first live boundary is full U3-A verification of OUTER v2 E.
        # A captured parser, offline C or invented prefix cannot activate it.
        with control_loading.loaded_controls() as controls:
            verified = registration.verified(registration_raw, classifier_projection=controls)
        if c.canonical(execution) != c.canonical(verified):
            raise ValueError('callback execution differs from freshly verified outer v2 E')
        from .native_shared_phase import PhaseState
        from . import native_shared_attribution_orchestration as attribution
        from .native_shared_receipts import _ReceiptCatalogContext
        self.raw = composition_raw
        self.value, self.spec, self.selection = reconstruct_composition(composition_raw)
        if (execution['composition_raw_json'].encode('utf-8') != composition_raw
                or execution['composition_sha256'] != c.sha(composition_raw)
                or type(execution['max_draft_checks']) is not int
                or execution['max_draft_checks'] != self.value['max_draft_checks']):
            raise ValueError('callback adapter differs from its exact verified execution composition')
        self.execution, self.registration_raw = deepcopy(execution), registration_raw
        with control_loading.loaded_controls(self.value['dependencies']) as controls:
            self._budget_stop = controls['budgeted_cborg'].BudgetStop
        self.policy = deepcopy(self.value['policy'])
        paths = self.spec._agentic_artifact_paths
        self.phase = PhaseState(render.commands(self.spec), full_path=paths['full'], core_path=paths['core'],
            report_path=paths['report'], receipt_path=paths['receipt'], working_directory=self.value['working_directory'])
        self.state = attribution.live(self.selection, execution_raw=registration_raw, spec=self.spec, composition_raw=composition_raw)
        self.failure = self.final_evidence = self.recorder_identity = None
        self._stream_diagnostic_json = None
        self.recorder_call = None
        self.recorder_done = False
        self._activated = self._initialized = False
        self._stream_prefixes = {}
        self._stream_files = {}
        self._stream_members = ()
        self._receipt_catalogs = _ReceiptCatalogContext()

    def require_phase_authority(self):
        if (not self.policy or self.policy != self.value['policy'] or self.spec.render_version != 26
                or self.spec.native_shared_generation_version != 1 or self.phase is None):
            raise ValueError('native26 requires its actual fixed phase observer and selected policy')

    def activate_before_dispatch(self, started_raw):
        if self._activated:
            raise ValueError('native shared callback identity is already spent')
        with control_loading.loaded_controls(self.value['dependencies']) as controls:
            if c.canonical(registration.verified(self.registration_raw,
                    classifier_projection=controls)) != c.canonical(self.execution):
                raise ValueError('callback execution changed before activation')
        scope = callback_loading.preloaded_callbacks(self.value, self.spec, self.selection,
            self.execution, self.registration_raw, render.commands(self.spec))
        self._callbacks = scope.__enter__()
        self._classifier = self._callbacks.classifier
        self._classifier_scope = scope
        self.state, self.phase = self._callbacks.state, self._callbacks.phase
        self._receipt_catalogs = self._callbacks.catalogs
        # Latch before any fallible write: partial activation cannot redispatch.
        self._activated = True
        try:
            self._callbacks.capture.activate_admitted(self._callbacks.admission, started_raw)
        except BaseException:
            scope.__exit__(*sys.exc_info())
            raise

    def _callback_resources(self):
        resources = getattr(self, '_callbacks', None)
        if resources is None:
            # The main-thread diagnostic helpers also exercise this body
            # without admission. A worker never takes that loading route.
            callback_loading.require_main_thread()
            return None
        resources.admission.check_active()
        if (self.state is not resources.state or self.phase is not resources.phase
                or self._receipt_catalogs is not resources.catalogs
                or self._classifier is not resources.classifier):
            raise ValueError('preloaded callback state reference changed')
        if (self.raw != resources.admission.composition_json
                or c.canonical(self.execution) != resources.admission.execution_json
                or self.selection.registration.raw != resources.admission.selection.registration.raw
                or c.canonical(self.policy) != c.canonical(c.strict_json(
                    resources.admission.composition_json, max_bytes=c.HARD_LIMITS['request_bytes'])['policy'])):
            raise ValueError('preloaded callback authority changed')
        return resources

    def _stop(self, reason):
        if self.failure is None:
            self.failure = str(reason)
        raise self._budget_stop(self.failure)

    def _failure_detail(self, exc):
        # Preserve the historical first-stop text, not the private subclass
        # name. The first failure alone may contribute optional diagnostics.
        resources = getattr(self, '_callbacks', None)
        streams = resources.streams if resources is not None else live_streams
        is_stream = isinstance(exc, streams._LiveStreamRefusal)
        if self.failure is None and is_stream:
            try:
                raw = exc.diagnostic_json
                streams.diagnostic_document(raw)
                if getattr(self, '_stream_diagnostic_json', None) is None:
                    self._stream_diagnostic_json = raw
            except Exception:
                pass  # Diagnostic failure must never replace the refusal.
        return ('ValueError' if is_stream else type(exc).__name__) + ': ' + str(exc)

    def _observed_endpoint(self, event):
        resources = self._callback_resources()
        streams = resources.streams if resources is not None else live_streams
        members, prefixes = [], {}
        for role in streams.ROLES:
            path = str(Path(self.execution['attempt_directory']) / (role + '.jsonl'))
            previous = self._stream_prefixes.get(role)
            member = streams.read_live_stream(path, role,
                max_bytes=c.HARD_LIMITS['stream_bytes'], previous=previous,
                identity=self._stream_files.get(role))
            members.append(member)
            if role == 'transcript':
                start = previous.bytes if previous is not None else 0
                end = member.captured.raw.find(b'\n', start)
                if end < 0:
                    raise ValueError('observer has no complete corresponding native physical frame')
                actual = c.strict_json(member.captured.raw[start:end + 1], 'observed native frame', 16 * 1024 * 1024)
                if c.canonical(actual) != c.canonical(event):
                    raise ValueError('observer event differs from its next exact raw native frame')
                prefixes[role] = streams.prefix(member, end + 1)
            else:
                prefixes[role] = streams.prefix(member)
        # Neither cursor advances if either acquisition or the event fails.
        anchors = streams.stream_files(tuple(members))
        self._stream_prefixes, self._stream_files = prefixes, anchors
        self._stream_members = tuple(members)
        return prefixes['transcript'].bytes, prefixes['control'].bytes

    def _run(self, endpoints=None):
        resources = self._callback_resources()
        if resources is not None:
            capture = resources.capture
            admission = {'_admission': resources.admission}
        else:
            from . import native_shared_capture_orchestration as capture
            admission = {}
        if endpoints is None:
            return capture._load(self.selection.registration.pin.path, **admission)
        run = capture._load_live(self.selection.registration.pin.path,
            transcript_bytes=endpoints[0], control_bytes=endpoints[1], stream_files=self._stream_files,
            _catalogs=self._receipt_catalogs, **admission)
        if self._stream_prefixes != {'transcript': run.transcript, 'control': run.control}:
            raise ValueError('recaptured streams differ from exact parent-observed prefixes')
        return run

    def _phase_state(self, endpoints, *, refresh=False):
        # U3-B owns bounded schema/catalog derivation reuse only. Always
        # reconstruct current streams/history/decision; no earlier accepted
        # phase, callback or chronology verdict is an authority cache.
        run = self._run(endpoints)
        return run, run.decision()

    def _current_final(self, run):
        resources = self._callback_resources()
        if resources is not None:
            current_evidence = resources.gates.current_evidence
        else:
            from .native_shared_gates import current_evidence
        result = current_evidence(run)
        if result.get('checked') is not True or result.get('findings') != []:
            raise ValueError('current selected final evidence did not pass')
        return result

    def _final_unchanged(self, run):
        if self.final_evidence is not None and c.canonical(self._current_final(run)) != c.canonical(self.final_evidence):
            raise ValueError('final evidence changed after its actual successful check')
        if self.recorder_identity is not None:
            resources = self._callback_resources()
            read = resources.evidence.read_regular if resources is not None else read_regular
            item = read(self.recorder_identity['path'], 'provenance', max_bytes=c.HARD_LIMITS['request_bytes']).captured
            if item.pin.sha256 != self.recorder_identity['sha256']:
                raise ValueError('completed selected provenance record changed')

    def _effect_stop(self, run, event, classification, basis):
        """Persist exact observer restriction before the frozen callback grant."""
        resources = self._callback_resources()
        if resources is not None:
            durable_new = resources.capture.durable_new
        else:
            from .native_shared_callback_io import durable_new
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
        resources = self._callback_resources()
        if resources is not None:
            current_effect_view = resources.captured.current_effect_view
        else:
            from .native_shared_capture import current_effect_view
        return current_effect_view(run, correction_window=bool(self.state.checks), exclude_pending=exclude_pending)

    def observe(self, event):
        resources = self._callback_resources()
        if resources is None:
            return self._observe(event)
        with resources.classifier._lock:
            return self._observe(event)

    def _observe(self, event):
        resources = self._callback_resources()
        if resources is not None:
            capture, captured = resources.capture, resources.captured
            effects, evidence = resources.effects, resources.evidence
            selected_policy = resources.policy
            admission = {'_admission': resources.admission}
        else:
            from . import native_shared_capture_orchestration as capture
            from . import native_shared_capture as captured
            from . import native_shared_effects as effects
            from . import native_shared_evidence as evidence
            selected_policy = policy
            admission = {}
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
                    transcript_bytes=endpoints[0], control_bytes=endpoints[1], stream_files=self._stream_files,
                    observed_prefixes=self._stream_prefixes, **admission)
                self._initialized = True
            if not self._initialized:
                if event.get('type') != 'control_response':
                    raise ValueError('native effects precede actual initialization binding')
                self.phase.observe(event)
                self.state.observe(event)
                return
            run, decision = self._phase_state(endpoints)
            content = event.get('message', {}).get('content', [])
            content = content if type(content) is list else ()
            # Validate actual advance effects before the phase checker can
            # credit a tool result's claimed post-state.
            for block in content:
                if type(block) is not dict or block.get('type') != 'tool_result':
                    continue
                call = run.trace().calls.get(block.get('tool_use_id'))
                if call and call[2].get('input', {}).get('command') == self.policy['native_shared_helpers']['advance']:
                    run = self._run(endpoints)
                    capture.observe_advance_settled(run, block['tool_use_id'])
                    run, decision = self._phase_state(endpoints, refresh=True)
            if event.get('type') == 'control_request':
                data = event.get('request', {}).get('input', {})
                name, inputs = data.get('tool_name'), data.get('tool_input')
                # Mandatory phase-before-effect and phase-before-attribution.
                self.phase.before(name, inputs, stage_decision=decision)
                view = captured._effect_view_from_decision(run, decision,
                    correction_window=bool(self.state.checks), exclude_pending=data.get('tool_use_id'))
                if selected_policy.stage_overlay_governs(view, tool_name=name, tool_input=inputs, policy=self.policy):
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
                            readonly = self._classifier.readonly(command, self.policy['readonly_lookups'])
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
                        run, decision = self._phase_state(endpoints, refresh=True)
                        current = self._current_final(run)
                        actual = trace.settled(identity)
                        observed_result = evidence.event(run.transcript, actual.result)
                        meta = event.get('tool_use_result', {})
                        for raw in (observed_result.get('content'), meta.get('stdout')):
                            if type(raw) is not str or c.canonical(c.strict_json(raw.encode(), max_bytes=c.HARD_LIMITS['request_bytes'])) != c.canonical(current):
                                raise ValueError('final helper stdout differs from actual captured final evidence')
                        self.final_evidence = current
                    elif identity == self.recorder_call:
                        run, decision = self._phase_state(endpoints, refresh=True)
                        metadata = event.get('tool_use_result', {})
                        codes = [metadata[k] for k in ('exitCode', 'exit_code') if k in metadata]
                        if not codes or any(type(code) is not int or code != 0 for code in codes) or block.get('is_error') is not False:
                            raise ValueError('selected final recorder did not settle successfully')
                        item = evidence.read_regular(self.policy['post_final_recorder']['destination'], 'provenance', max_bytes=c.HARD_LIMITS['request_bytes']).captured
                        if resources is not None:
                            _mapping = resources.mapping
                        else:
                            from .audit_omissions import _mapping
                        record = _mapping(item.raw, 'native provenance')
                        if c.canonical(record.get('native_shared_generation')) != c.canonical(captured._provenance_block(run)):
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
            self._stop('native shared observation failed: ' + self._failure_detail(exc))

    def classify(self, command, python, programs, selected_policy):
        if hasattr(self, '_callbacks'):
            self._callback_resources()
        if self.failure is not None:
            self._stop(self.failure)
        if c.canonical(selected_policy) != c.canonical(self.policy):
            self._stop('native callback command policy differs from its exact composition')
        if not hasattr(self, '_classifier'):
            raise ValueError('native callback requires main-thread preloading at admission')
        return self._classifier.classify(command, python, programs, selected_policy)

    def report(self, *, complete=False):
        if hasattr(self, '_classifier_scope'):
            with self._classifier._lock:
                return self._report_and_close(complete=complete)
        return self._report(complete=complete)

    def _report_and_close(self, *, complete=False):
        try:
            return self._report(complete=complete)
        finally:
            if complete and hasattr(self, '_classifier_scope'):
                callback_loading.require_main_thread()
                scope = self._classifier_scope
                del self._classifier_scope
                scope.__exit__(None, None, None)

    def _report(self, *, complete=False):
        if complete and self.failure is None:
            try:
                run = self._run()
                resources = self._callback_resources()
                phase, _ = (resources.captured.phase_replay(run, complete=True) if resources is not None
                            else capture_phase(run, complete=True))
                if not phase['passed']:
                    raise ValueError('; '.join(phase['problems']))
                self._final_unchanged(run)
            except Exception as exc:
                self.failure = 'completed native shared history cannot be verified: ' + self._failure_detail(exc)
        out = self.state.report(complete=complete)
        diagnostic = {}
        if self.failure is not None and getattr(self, '_stream_diagnostic_json', None) is not None:
            try:
                diagnostic['stream_diagnostic'] = live_streams.diagnostic_document(self._stream_diagnostic_json)
            except Exception:
                pass  # Existing failed reports remain available without it.
        return {**out, 'execution': EXECUTION, 'composition_sha256': c.sha(self.raw),
            'controller_stop': self.failure, 'final_evidence': deepcopy(self.final_evidence),
            'recorder_completed': self.recorder_done, 'recorder_identity': deepcopy(self.recorder_identity),
            'phase_history': self.phase.report(complete=complete),
            'draft_gate_passed': out['draft_gate_passed'] and self.failure is None, **diagnostic}


def capture_phase(run, *, complete):
    from .native_shared_capture import phase_replay
    return phase_replay(run, complete=complete)
