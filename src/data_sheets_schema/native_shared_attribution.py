"""Fixed native26 initialization of the inherited ordered draft observer.

The surrounding capture/lifetime must verify E and run the phase observer
first. This module neither grants tools nor replaces execution, observation,
phase, terminal-evidence, or scientific checks. Saved replay must call finish().
"""
from __future__ import annotations

import os
from pathlib import Path
import shlex

import yaml

from . import native_attribution_registration_v2 as inherited
from . import native_shared_contract as c
from . import native_shared_policy as policy
from . import native_shared_render as render
from . import native_shared_selection as selected
from . import source_attribution_preflight as preflight


_KINDS = {'draft': 'draft', 'audit_evidence': 'evidence',
          'final_evidence': 'final_evidence', 'original_source_inventory': 'source_inventory',
          'final_source_inventory': 'source_inventory'}


def _need(value, message):
    if not value:
        raise ValueError(message)


def _joined(selection, execution_raw, spec, composition_raw, *, _admission=None):
    """Join exact v2 carriers; saved replay never rediscovers live authority.

    These joins observe attribution identity, not execution admission. The
    orchestration caller verifies current preparation/C for live construction;
    the outer lifetime must still obtain U3-D's complete admission separately.
    """
    from . import native_shared_controller as controller
    if _admission is None:
        from .api_runner import RunSpec
        _need(type(selection) is c.NativeSelectionCapture and type(spec) is RunSpec,
              'attribution requires captured S and the exact selected RunSpec')
    else:
        from .native_shared_callback_capture import require_admission
        admitted = require_admission(_admission)
        _need(selection is admitted.selection and spec is admitted.spec
              and execution_raw == admitted.registration_raw
              and composition_raw == admitted.composition_json,
              'attribution differs from its loader-minted callback admission')
    rebuilt = selected.rebuild(selection.registration, selection.authority,
                               selection.schemas, selection.receipt_policy)
    _need(rebuilt == selection, 'attribution selection differs from its captured authority')
    doc = selection.document()
    execution = controller.captured_execution_body(execution_raw)
    composition = c.strict_json(composition_raw, 'attribution composition', c.HARD_LIMITS['request_bytes'])
    c.exact(composition, controller._COMPOSITION_KEYS, 'attribution captured composition')
    _need(type(composition) is dict and composition.get('kind') == 'd4d_native_shared_callback_composition'
          and type(composition.get('version')) is int and composition['version'] == 1
          and type(composition.get('authority_version')) is int and composition['authority_version'] == 2
          and composition.get('execution') == controller.EXECUTION,
          'attribution requires the explicit v2-authority shared composition')
    _need(execution.get('composition_raw_json') == composition_raw.decode('utf-8')
          and execution.get('composition_sha256') == c.sha(composition_raw),
          'attribution execution differs from exact composition bytes')
    preparation_text = execution.get('preparation_raw_json')
    _need(type(preparation_text) is str, 'attribution requires captured v2 preparation bytes')
    preparation_raw = preparation_text.encode('utf-8')
    preparation = controller.captured_preparation_body(preparation_raw)
    dependencies = preparation['dependencies']
    _need(type(dependencies) is dict and type(dependencies.get('version')) is int
          and dependencies['version'] == 2 and type(dependencies.get('base')) is dict
          and type(dependencies['base'].get('authority_version')) is int
          and dependencies['base']['authority_version'] == 2,
          'attribution preparation requires explicit v2 dependency identity')
    _need(execution.get('preparation_sha256') == c.sha(preparation_raw)
          and composition.get('preparation_raw_json') == preparation_text
          and composition.get('preparation_sha256') == c.sha(preparation_raw)
          and execution.get('job_id') == preparation['job_id']
          and c.canonical(execution.get('dependencies')) == c.canonical(preparation['dependencies'])
          and c.canonical(composition.get('dependencies')) == c.canonical(preparation['dependencies']),
          'attribution execution/composition differs from its exact v2 preparation')
    selected_pin = {'path': selection.registration.pin.path,
                    'bytes': selection.registration.pin.bytes,
                    'sha256': selection.registration.pin.sha256}
    _need(c.canonical(preparation['selection']) == c.canonical(selected_pin),
          'attribution preparation differs from the exact captured selection pin')
    pins = preparation['pinned_files']
    _need(type(pins) is dict, 'attribution preparation requires its complete pin mapping')
    for item in (selection.registration, selection.receipt_policy, *selection.authority,
                 *(source for schema in selection.schemas for source in schema.sources)):
        _need(pins.get(item.pin.path) == item.pin.sha256,
              'attribution prepared pin differs from captured ' + item.pin.role)
    _need(composition.get('selection_raw_json') == selection.registration.raw.decode('utf-8')
          and composition.get('selection_sha256') == selection.registration.pin.sha256
          and execution.get('selection_sha256') == selection.registration.pin.sha256,
          'attribution execution/composition differs from captured selection')
    _need(render.validate_spec(spec) == doc, 'attribution spec differs from selected S')
    rendered = spec.render_spec()  # Native metadata is derived from immutable captures.
    _need(c.canonical(composition.get('render_spec')) == c.canonical(rendered)
          and c.canonical(preparation['render_spec']) == c.canonical(rendered),
          'attribution execution/composition differs from exact selected spec')
    maximum = c.positive_int(execution.get('max_draft_checks'), 'execution draft allowance')
    _need(type(composition.get('max_draft_checks')) is int
          and type(preparation['max_draft_checks']) is int
          and maximum == composition['max_draft_checks'] == preparation['max_draft_checks']
          == rendered['native_shared_max_draft_checks'],
          'attribution draft allowance differs between E, C and selected spec')
    runtime = rendered['native_shared_runtime_declaration']
    runtime_raw = runtime['raw_json'].encode('utf-8')
    _need(c.canonical(preparation['runtime']) == c.canonical({
              'path': runtime['path'], 'bytes': len(runtime_raw), 'sha256': c.sha(runtime_raw)})
          and runtime['sha256'] == c.sha(runtime_raw),
          'attribution preparation runtime pin differs from captured runtime bytes')
    _need(pins.get(runtime['path']) == runtime['sha256'],
          'attribution preparation omits its exact runtime pin')
    _need(composition.get('runtime_raw_json') == runtime['raw_json']
          and composition.get('runtime_sha256') == runtime['sha256']
          and composition.get('runtime_path') == runtime['path']
          and execution.get('runtime_declaration_sha256') == runtime['sha256']
          and c.canonical(execution.get('runtime')) == c.canonical(c.strict_json(runtime_raw)),
          'attribution runtime differs from the sole captured declaration')
    _need(execution.get('instruction_sha256') == composition.get('instruction_sha256')
          and preparation['instruction_sha256'] == composition.get('instruction_sha256')
          and type(preparation['instruction']) is str
          and c.sha(preparation['instruction'].encode('utf-8')) == preparation['instruction_sha256']
          and type(composition.get('instruction_sha256')) is str
          and len(composition['instruction_sha256']) == 64
          and all(ch in '0123456789abcdef' for ch in composition['instruction_sha256']),
          'attribution instruction identity differs between E and C')
    captured_policy = composition.get('policy')
    _need(composition.get('policy_sha256') == c.sha(c.canonical(captured_policy)),
          'attribution composition policy hash differs')
    commands = policy.helper_commands(captured_policy)
    _need(commands == {name: shlex.join(argv) for name, argv in render.commands(spec).items()},
          'attribution helper spellings differ from the selected renderer')
    directory = c.canonical_path(composition.get('working_directory'), 'attribution working directory')
    _need(execution.get('working_directory') == directory
          and preparation['working_directory'] == directory
          and captured_policy.get('readonly_lookups', {}).get('repository') == directory,
          'attribution execution/composition working directory differs')
    paths = dict(rendered['agentic_artifact_paths'])
    for role in ('full', 'core', 'report', 'receipt'):
        c.canonical_path(paths.get(role), 'attribution ' + role)
    _need(len(set(paths.values())) == len(paths), 'attribution output roles overlap')
    _need(doc['inputs']['source_manifest'] is not None and spec.manifest_used,
          'native26 attribution requires its explicit selected source manifest')
    inputs = {}
    for name, field in (('bundle', 'bundle'), ('chunk_manifest', 'chunk_manifest'), ('source_manifest', 'manifest')):
        pin = doc['inputs'][name]
        _need(str(getattr(spec, field)) == pin['path'], 'attribution spec input differs from selected ' + name)
        inputs[name] = {'path': pin['path'], 'sha256': pin['sha256']}
    return doc, commands, directory, paths, inputs, maximum


class _Attribution(inherited.NativeAttributionState):
    """Fixed initializer; inherited observe and report implementations remain intact."""

    def __init__(self, selection, *, execution_raw, spec, composition_raw, _admission=None):
        doc, commands, directory, paths, inputs, maximum = _joined(
            selection, execution_raw, spec, composition_raw, _admission=_admission)
        self.spec = spec
        self.reg = {'max_draft_checks': maximum, 'inputs': inputs, 'working_directory': directory}
        self.registration_raw = execution_raw
        self.live = True
        self.problems, self.observations = [], []
        self.pending, self.seen = {}, set()
        self.epoch, self.checks, self.accepted, self.terminal = 0, 0, None, False
        self.index = 0
        self._directory = directory
        self._paths = paths
        self.report_path = Path(paths['report'])
        self.protected = {Path(paths[name]) for name in ('full', 'core', 'receipt')}
        self.protected.update(Path(pin['path']) for pin in inputs.values())
        self.protected.update(Path(selection.role(name)) for name in
                              ('phase1_full', 'phase1_core', 'phase1_receipt', 'audit'))
        _need(self.report_path not in self.protected, 'attribution report overlaps protected authority')
        self._commands = {commands[name]: kind for name, kind in _KINDS.items()}
        _need(len(self._commands) == len(_KINDS), 'attribution helper kinds have ambiguous spellings')
        self._all_commands = frozenset(commands.values())
        self._sources = {name + '_raw': selection.raw(pin['path'])
                         for name, pin in inputs.items()}
        self._project = doc['run']['project']
        self._input_limit = doc['bounds']['max_input_bytes']

    @property
    def commands(self):
        return dict(self._commands)

    def _command_kind(self, command):
        if not isinstance(command, str):
            raise ValueError('helper command must be text')
        if command in self._all_commands:
            return self._commands.get(command)
        return inherited.command_kind(command, self.spec, expected=self._commands)

    def _target_path(self, path):
        _need(type(path) is str and bool(path) and '\x00' not in path,
              'attribution target path must be text')
        return Path(os.path.normpath(os.path.join(self._directory, path)))

    def _compare(self, problems, full, report, basis):
        try:
            current = preflight.check_bytes(report_raw=report, record_raw=full,
                **self._sources, protocol_version=7, project=self._project)
            if not current['passed'] or inherited._encoded(current) != inherited._encoded(self.accepted['payload']):
                problems.append('draft pass differs from actual checker on ' + basis + ' bytes')
            else:
                self.accepted['observation']['verified_against_current_saved_bytes'] = True
        except (TypeError, ValueError, KeyError, OSError, RecursionError, yaml.YAMLError) as exc:
            problems.append('current draft cannot be verified: ' + str(exc))

    def _check_current(self, problems):
        raise ValueError('attribution requires explicit saved evidence or the live orchestration boundary')


class _SavedAttribution(_Attribution):
    def __init__(self, selection, *, execution_raw, spec, composition_raw,
                 captured_instruction, final_full, final_report):
        from .native_shared_controller import captured_preparation_body
        composition = c.strict_json(composition_raw, 'saved attribution composition',
                                    c.HARD_LIMITS['request_bytes'])
        _need(type(composition) is dict and type(composition.get('preparation_raw_json')) is str,
              'saved attribution requires captured composition/preparation bytes')
        preparation = captured_preparation_body(composition['preparation_raw_json'].encode('utf-8'))
        _need(type(captured_instruction) is c.CapturedArtifact
              and captured_instruction.pin.role == 'instruction'
              and captured_instruction.pin.path == composition.get('instruction_path')
              and type(preparation['instruction']) is str
              and captured_instruction.raw == preparation['instruction'].encode('utf-8')
              and captured_instruction.pin.bytes == len(captured_instruction.raw)
              and captured_instruction.pin.bytes <= c.HARD_LIMITS['request_bytes']
              and captured_instruction.pin.sha256 == c.sha(captured_instruction.raw)
              and captured_instruction.pin.sha256 == preparation['instruction_sha256']
              and captured_instruction.pin.sha256 == composition.get('instruction_sha256'),
              'saved attribution instruction differs from its independent captured artifact')
        super().__init__(selection, execution_raw=execution_raw, spec=spec,
                         composition_raw=composition_raw)
        for artifact, role, path in ((final_full, 'final_full', self._paths['full']),
                                     (final_report, 'final_report', self._paths['report'])):
            _need(type(artifact) is c.CapturedArtifact and artifact.pin.role == role
                  and artifact.pin.path == path and artifact.pin.bytes <= self._input_limit,
                  'saved attribution final artifact has another role, path or byte bound')
        self._final_full, self._final_report = final_full.raw, final_report.raw
        self._finishing = False

    def _check_current(self, problems):
        # Earlier settled passes may name reports later corrected in this
        # same captured history. Only finish compares the surviving pass.
        if self._finishing:
            self._compare(problems, self._final_full, self._final_report, 'captured final')

    def finish(self):
        self._finishing = True
        return self.report(complete=True)


def saved(selection, *, execution_raw, spec, composition_raw, captured_instruction,
          final_full, final_report):
    """Observe saved identity/history against independently captured instruction.

    This pure replay neither proves canonical rendering nor grants admission.
    The caller independently verifies canonical C/E and supplies the actual
    instruction artifact. ``finish()`` is mandatory for attribution acceptance.
    """
    return _SavedAttribution(selection, execution_raw=execution_raw, spec=spec, composition_raw=composition_raw,
                             captured_instruction=captured_instruction,
                             final_full=final_full, final_report=final_report)
