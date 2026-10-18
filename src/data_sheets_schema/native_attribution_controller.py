"""Offline native callback composition; no launcher or execution approval (#4307).

The adapter is exercised with neutral local children through the unchanged
controller. A production launcher, runtime permission proof and fresh owner
approval remain separate. These controls do not meter direct provider spend.
"""
from __future__ import annotations

from copy import deepcopy
import importlib
import json
from pathlib import Path
import re
import shlex
import sys

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_source_attribution as supplement

KIND = 'd4d_native_attribution_callback_composition'
VERSION = 1
EXECUTION = 'offline_composition_only_no_production_launcher'
SOURCES_PATH = Path('src/data_sheets_schema/native_controller_sources_v1.json')
SOURCES_SHA256 = 'd1f13def58c0832aea3644fb68806d829eb4ab6e087045f14d86f439aed557c1'
ROOT = Path(__file__).resolve().parents[2]


def controller_sources():
    """Verify the frozen local controller closure before importing any of it."""
    raw = (ROOT / SOURCES_PATH).read_bytes()
    if draft._sha(raw) != SOURCES_SHA256:
        raise ValueError('native controller source manifest changed')
    manifest = draft._json(raw)
    for name, pin in manifest['modules'].items():
        path = ROOT / pin['path']
        if draft._sha(path.read_bytes()) != pin['sha256']:
            raise ValueError(f'frozen native controller bytes changed: {name}')
        loaded = sys.modules.get(name)
        if loaded is not None and Path(getattr(loaded, '__file__', '')).resolve() != path.resolve():
            raise ValueError(f'native controller dependency imported from another origin: {name}')
    return manifest


def load_controls():
    manifest = controller_sources()
    old = list(sys.path)
    base = ROOT / 'notes/matched_cborg_2026-09-13'
    try:
        sys.path[:0] = [str(base), str(base / 'native_controls')]
        modules = {name: importlib.import_module(name) for name in manifest['modules']}
    finally:
        sys.path[:] = old
    controller_sources()  # also checks origins of transitively imported modules
    return modules


def _classify(command, python, programs, policy, controls):
    if command == policy['attribution_command']:
        problem = controls['native_command_policy'].runtime_literal_problem(command, policy)
        if problem:
            return 'not_prescribed', problem
        return 'prescribed', 'exact registered attribution draft command'
    try:
        words = shlex.split(command)
    except (ValueError, TypeError):
        words = []
    if supplement.MODULE in words:
        return 'not_prescribed', 'attribution command differs from its exact registration'
    return controls['run_native_canary']._classify_command(command, python, programs, policy)


def command_policy(spec, instruction_path, controls=None):
    """Build from the explicit spec; never call the frozen CBORG spec resolver."""
    controls = load_controls() if controls is None else controls
    grammar = controls['native_command_policy']
    phase = controls['native_phase_history']
    from data_sheets_schema.agentic_runtime import playbook_text, validate_toolchain
    environment = validate_toolchain(spec._agentic_toolchain)
    python = environment['python']
    artifacts = spec._agentic_artifact_paths
    instruction = spec.instruction
    if Path(instruction_path).read_bytes() != instruction.encode('utf-8'):
        raise ValueError('selected instruction file differs from the exact request')
    job = {'render_spec': spec.render_spec(), 'input_identity': spec.input_identity(),
           'bundle': str(spec.bundle), 'chunks': str(spec.chunk_manifest),
           'manifest': str(spec.manifest) if spec.manifest is not None else None,
           'instruction': str(Path(instruction_path).resolve()),
           'output_directories': sorted({str(Path(artifacts[k]).parent.resolve()) for k in ('full', 'core', 'report')})}
    replacements = {'<full_file>': artifacts['full'], '<full>': artifacts['full'],
                    '<core_file>': artifacts['core'], '<core>': artifacts['core'],
                    '<report_file>': artifacts['report'], '<bundle>': str(spec.bundle)}
    programs, examples = {}, set()
    for source in (instruction, playbook_text(environment)):
        for tokens in grammar.python_commands(source, python):
            program = grammar._bind_program(tokens[2], replacements)
            tail = [replacements.get(arg, arg) for arg in tokens[3:]]
            if any(re.search(r'<[a-z_]+>', arg) for arg in tail):
                raise ValueError('unbound placeholder in prescribed Python arguments')
            grammar._literal_rule(shlex.join([python, '-c', program]))
            programs[program] = programs.get(program, False) or bool(tail)
            examples.add(shlex.join([python, '-c', program, *tail]))
    manifests = {'none'}
    if spec.manifest is not None:
        absolute = Path(spec.manifest).resolve()
        manifests = {str(absolute)}
        if absolute.is_relative_to(Path.cwd().resolve()):
            manifests.add(str(absolute.relative_to(Path.cwd().resolve())))
    cli = [python, '-m', 'data_sheets_schema.cli']
    rules = ['Read', 'Write']
    for program in controls['native_readonly'].PROGRAMS:
        rules.append(grammar._literal_rule('sed -n' if program == 'sed' else program, arguments=True))
    for command in controls['prepare_overlay_roster'].PLAYBOOK_COMMANDS:
        rules.append(grammar._literal_rule(shlex.join([*cli, *command.split()]), arguments=True))
        for path in sorted(manifests):
            rules.append(grammar._literal_rule(shlex.join([*cli, '--manifest', path, *command.split()]), arguments=True))
    for module in controls['prepare_overlay_roster'].MODULE_ENTRY_POINTS:
        rules.append(grammar._literal_rule(shlex.join([python, '-m', f'data_sheets_schema.{module}']), arguments=True))
    for program, arguments in sorted(programs.items()):
        rules.append(grammar._literal_rule(shlex.join([python, '-c', program]), arguments=arguments))
    new_command = shlex.join(supplement.command_args(spec))
    rules.append(grammar._literal_rule(new_command))
    policy = {'version': grammar.POLICY_VERSION, 'literal_admission': grammar.LITERAL_ADMISSION,
              'pretool_control': deepcopy(controls['native_control'].HISTORY_CONTRACT),
              'python': python, 'manifest_paths': sorted(manifests),
              'programs': [{'code': code, 'arguments': args} for code, args in sorted(programs.items())],
              'command_examples': sorted(examples), 'allowed_tools': rules,
              'readonly_lookups': controls['native_readonly'].lookup_policy(job, Path.cwd()),
              'lookup_literal_admission': grammar.LOOKUP_LITERAL_ADMISSION,
              'helper_arguments': phase.helper_expectations(spec, Path.cwd()),
              'attribution_composition_version': VERSION, 'attribution_command': new_command}
    heads = {python, shlex.quote(python)}
    candidates = sorted(examples) + [line.strip() for line in instruction.splitlines()
        if any(line.strip().startswith(head + ' ') for head in heads)
        and not any(line.strip().startswith(head + ' -c ') for head in heads)
        and not re.search(r'<[a-z_]+>', line)]
    spellings = {}
    for command in candidates:
        kind, problem = phase.helper_argument_problem(command, policy)
        if kind and not problem:
            spellings.setdefault(kind, set()).add(command)
    policy['helper_arguments']['spellings'] = {k: sorted(v) for k, v in sorted(spellings.items())}
    recorders = [c for c in candidates if shlex.split(c)[:5] == [python, '-m', 'data_sheets_schema.cli', 'provenance', 'record']]
    if len(recorders) != 1:
        raise ValueError('composition requires one exact bound recorder command')
    destination = Path(artifacts['core']).resolve().parent / f'{spec.project}_provenance.yaml'
    protected = {Path(p).resolve() for p in artifacts.values()} | {Path(p).resolve() for p in policy['readonly_lookups']['inputs']}
    if destination in protected:
        raise ValueError('recorder destination overlaps a protected input or artifact')
    policy['post_final_recorder'] = {'command': recorders[0], 'destination': str(destination),
        'scope': 'Only the exact registered provenance record; no dataset/report mutation'}
    for command in candidates:
        verdict, basis = _classify(command, python, set(), policy, controls)
        if verdict != 'prescribed':
            raise ValueError(f'registered instruction command is not admitted ({basis}): {command[:200]}')
    return policy


def composition(registration_raw, instruction_path):
    """Capture an offline composition, without authorizing or starting a child."""
    spec, registration = draft.verified(registration_raw)
    controls = load_controls()
    path = Path(instruction_path).resolve()
    metadata_inputs = {}
    if spec.manifest is not None and not spec.manifest_used:
        metadata_inputs['selected_unused_manifest'] = {'path': str(Path(spec.manifest).resolve()),
            'sha256': draft._sha(Path(spec.manifest).read_bytes()),
            'scope': 'Recorder/profile metadata only; excluded from draft source authority'}
    policy = command_policy(spec, path, controls)
    for pin in metadata_inputs.values():
        if draft._sha(Path(pin['path']).read_bytes()) != pin['sha256']:
            raise ValueError('selected metadata input changed during composition')
    return {'kind': KIND, 'version': VERSION, 'execution': EXECUTION,
            'registration_raw_json': registration_raw.decode('utf-8'),
            'registration_sha256': draft._sha(registration_raw),
            'metadata_inputs': metadata_inputs,
            'instruction_path': str(path), 'instruction_sha256': draft._sha(path.read_bytes()),
            'controller_sources': controller_sources(), 'controller_sources_sha256': SOURCES_SHA256,
            'policy': policy, 'policy_sha256': draft._sha(draft._encoded(policy)),
            'python': sys.executable, 'python_version': sys.version}


def verified_composition(raw):
    if type(raw) is not bytes:
        raise ValueError('controller composition must be captured bytes')
    value = draft._json(raw)
    if not isinstance(value, dict) or value.get('kind') != KIND:
        raise ValueError('not an offline native attribution composition')
    try:
        expected = composition(value['registration_raw_json'].encode('utf-8'), value['instruction_path'])
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError('malformed native attribution composition') from exc
    if draft._encoded(value) != draft._encoded(expected):
        raise ValueError('native attribution composition identity changed')
    return value


def write_composition(registration_raw, instruction_path, destination):
    raw = draft._encoded(composition(registration_raw, instruction_path))
    verified_composition(raw)
    target = Path(destination).resolve()
    if target.is_relative_to(ROOT / 'src') or target.is_relative_to(ROOT / 'notes'):
        raise ValueError('composition output cannot modify captured source or historical controls')
    with Path(destination).open('xb') as stream:
        stream.write(raw)
    return {'path': str(destination), 'sha256': draft._sha(raw), 'execution': EXECUTION}


class CallbackAdapter:
    """Supply only observer/classifier hooks to an already authorized controller.

    No process-spawning method is provided. Tests use the real frozen controller
    with a neutral local child. Production selection remains unsupported.
    """

    def __init__(self, composition_raw):
        self.raw = composition_raw
        self.value = verified_composition(composition_raw)
        self.controls = load_controls()
        self.state = draft.NativeAttributionState(self.value['registration_raw_json'].encode('utf-8'), live=True)
        self.spec = self.state.spec
        self.policy = deepcopy(self.value['policy'])
        self.failure = None
        self.final_evidence = None
        self.recorder_call = None
        self.recorder_done = False
        self.recorder_identity = None

    def _stop(self, reason):
        if self.failure is None:
            self.failure = reason
        raise self.controls['budgeted_cborg'].BudgetStop(self.failure)

    def _current_final(self):
        # Replay binds agentic artifact paths without changing historical
        # RunSpec full_path/core_path layout properties. Project the exact
        # registered destinations expected by the frozen pure checker.
        from types import SimpleNamespace
        paths = self.spec._agentic_artifact_paths
        view = SimpleNamespace(render_version=self.spec.render_version, manifest_used=self.spec.manifest_used,
            manifest=self.spec.manifest, project=self.spec.project, bundle=self.spec.bundle,
            chunk_manifest=self.spec.chunk_manifest, metadata_dir=Path(paths['core']).parent,
            full_path=Path(paths['full']), core_path=Path(paths['core']), report_path=Path(paths['report']))
        current = self.controls['run_native_canary'].native_evidence_check(view)
        if not current.get('checked') or current.get('findings'):
            raise ValueError('unchanged final evidence checker did not pass')
        return current

    def _recorder_destination(self):
        path = Path(self.policy['post_final_recorder']['destination'])
        if path.exists() or path.is_symlink():
            raise ValueError('recorder destination exists; never overwrite or resume it')

    def _check_final_current(self):
        if self.final_evidence is not None:
            if draft._encoded(self._current_final()) != draft._encoded(self.final_evidence):
                raise ValueError('final evidence inputs changed after the successful final check')
        if self.recorder_identity is not None:
            path = Path(self.recorder_identity['path'])
            if (not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1
                    or draft._sha(path.read_bytes()) != self.recorder_identity['sha256']):
                raise ValueError('completed recorder metadata changed')

    def observe(self, event):
        if self.failure is not None:
            self._stop(self.failure)
        try:
            verified_composition(self.raw)
            preserved = set()
            recorder = self.policy['post_final_recorder']['command']
            message = event.get('message') if isinstance(event, dict) else None
            content = message.get('content', []) if isinstance(message, dict) else []
            final_results = []
            for item in content if isinstance(content, list) else []:
                if not isinstance(item, dict):
                    continue
                if item.get('type') == 'tool_use':
                    if self.recorder_done:
                        raise ValueError('tool continuation after completed final recorder')
                    args = item.get('input') or {}
                    if item.get('name') == 'Write':
                        self.final_evidence = None
                    if item.get('name') == 'Bash':
                        command = args.get('command')
                        kind = draft.command_kind(command, self.spec)
                        if kind == 'draft':
                            self.final_evidence = None
                        elif command == recorder:
                            if self.final_evidence is None or self.recorder_call is not None or self.state.pending:
                                raise ValueError('recorder requires one settled final evidence pass and cannot repeat')
                            self._recorder_destination()
                            self.recorder_call = item.get('id')
                            preserved.add(command)
                        elif self.state.checks and kind is None:
                            readonly = self.controls['native_readonly'].lookup_command(command,
                                self.policy['readonly_lookups'], self.controls['native_command_policy']._simple_command)
                            if not readonly:
                                raise ValueError('draft correction permits report Writes and registered read-only checks only')
                            preserved.add(command)
                elif item.get('type') == 'tool_result':
                    identity = item.get('tool_use_id')
                    row = self.state.pending.get(identity)
                    if row and row['kind'] == 'final_evidence':
                        final_results.append(item)
                    if identity == self.recorder_call:
                        meta = event.get('tool_use_result') or {}
                        exits = [meta[k] for k in ('exitCode', 'exit_code') if k in meta]
                        if (not exits or any(type(code) is not int or code != 0 for code in exits)
                                or item.get('is_error') is not False
                                or any(meta.get(k) for k in ('interrupted', 'backgroundTaskId', 'background_task_id'))):
                            raise ValueError('registered recorder failed or has unusable result; preserve the attempt')
                        target = Path(self.policy['post_final_recorder']['destination'])
                        if not target.is_file() or target.is_symlink() or target.stat().st_nlink != 1:
                            raise ValueError('recorder did not leave one regular metadata file')
                        self.recorder_done = True
                        self.recorder_identity = {'path': str(target), 'sha256': draft._sha(target.read_bytes())}
            # Another block can introduce a pending tool after a check call was
            # observed. Recheck at the actual callback before its publication.
            if isinstance(event, dict) and event.get('type') == 'control_request':
                data = (event.get('request') or {}).get('input') or {}
                identity = data.get('tool_use_id')
                row = self.state.pending.get(identity)
                if row and row['kind'] in ('draft', 'final_evidence'):
                    if set(self.state.pending) != {identity}:
                        raise ValueError('draft/final callback overlaps another pending tool')
                    if row['kind'] == 'final_evidence' and self.state.accepted is None:
                        raise ValueError('final callback lacks a current passing draft')
                if identity == self.recorder_call:
                    if set(self.state.pending) != {identity} or self.final_evidence is None:
                        raise ValueError('recorder callback is not settled after final evidence')
                    self._recorder_destination()
            self.state.observe(event, preserved_shell_commands=preserved)
            problems = self.state.report()['problems']
            if not problems:
                for item in final_results:
                    current = self._current_final()
                    payload = draft._json(item.get('content'))
                    meta = event.get('tool_use_result') or {}
                    if 'stdout' in meta and draft._encoded(draft._json(meta['stdout'])) != draft._encoded(payload):
                        raise ValueError('final evidence tool output and stdout disagree')
                    if draft._encoded(payload) != draft._encoded(current):
                        raise ValueError('final evidence result differs from the actual current checker')
                    self.final_evidence = current
                self._check_final_current()
        except Exception as exc:
            self._stop(f'native attribution identity or observation failed: {type(exc).__name__}: {exc}')
        if problems:
            self._stop('native attribution draft: ' + '; '.join(problems))

    def classify(self, command, python, programs, policy):
        if self.failure is not None:
            self._stop(self.failure)
        if draft._encoded(policy) != draft._encoded(self.value['policy']):
            self._stop('native attribution callback policy differs from composition')
        return _classify(command, python, programs, policy, self.controls)

    def report(self, *, complete=False):
        if complete and self.failure is None:
            try:
                verified_composition(self.raw)
                self._check_final_current()
            except Exception as exc:
                self.failure = f'completed attribution composition cannot be verified: {type(exc).__name__}: {exc}'
        out = self.state.report(complete=complete)
        return {**out, 'execution': EXECUTION, 'composition_sha256': draft._sha(self.raw),
                'controller_stop': self.failure, 'final_evidence': deepcopy(self.final_evidence),
                'recorder_completed': self.recorder_done, 'recorder_identity': deepcopy(self.recorder_identity),
                'draft_gate_passed': out['draft_gate_passed'] and self.failure is None}
