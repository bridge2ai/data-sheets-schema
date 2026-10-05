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

from . import native_attribution_registration as inherited
from . import native_shared_contract as c
from . import native_shared_policy as policy
from . import native_shared_render as render
from . import native_shared_selection as selected
from . import source_attribution_preflight as preflight
from .native_shared_evidence import read_regular


_KINDS = {'draft': 'draft', 'audit_evidence': 'evidence',
          'final_evidence': 'final_evidence', 'original_source_inventory': 'source_inventory',
          'final_source_inventory': 'source_inventory'}


def _need(value, message):
    if not value:
        raise ValueError(message)


def _joined(selection, execution_raw, spec, composition_raw):
    from .api_runner import RunSpec
    _need(type(selection) is c.NativeSelectionCapture and type(spec) is RunSpec,
          'attribution requires captured S and the exact selected RunSpec')
    rebuilt = selected.rebuild(selection.registration, selection.authority,
                               selection.schemas, selection.receipt_policy)
    _need(rebuilt == selection, 'attribution selection differs from its captured authority')
    doc = selection.document()
    execution = c.strict_json(execution_raw, 'attribution execution', c.HARD_LIMITS['request_bytes'])
    composition = c.strict_json(composition_raw, 'attribution composition', c.HARD_LIMITS['request_bytes'])
    _need(type(execution) is dict and execution.get('kind') == c.KINDS['execution']
          and type(execution.get('version')) is int and execution['version'] == 1,
          'attribution requires native shared execution bytes')
    _need(type(composition) is dict and composition.get('kind') == 'd4d_native_shared_callback_composition'
          and type(composition.get('version')) is int and composition['version'] == 1,
          'attribution requires native shared composition bytes')
    _need(execution.get('composition_raw_json') == composition_raw.decode('utf-8')
          and execution.get('composition_sha256') == c.sha(composition_raw),
          'attribution execution differs from exact composition bytes')
    _need(composition.get('selection_raw_json') == selection.registration.raw.decode('utf-8')
          and composition.get('selection_sha256') == selection.registration.pin.sha256
          and execution.get('selection_sha256') == selection.registration.pin.sha256,
          'attribution execution/composition differs from captured selection')
    _need(render.validate_spec(spec) == doc, 'attribution spec differs from selected S')
    rendered = spec.render_spec()  # Native metadata is derived from immutable captures.
    _need(c.canonical(composition.get('render_spec')) == c.canonical(rendered)
          and c.canonical(execution.get('selection')) == c.canonical({**doc['run'], 'render_spec': rendered}),
          'attribution execution/composition differs from exact selected spec')
    maximum = c.positive_int(execution.get('max_draft_checks'), 'execution draft allowance')
    _need(type(composition.get('max_draft_checks')) is int
          and maximum == composition['max_draft_checks'] == rendered['native_shared_max_draft_checks'],
          'attribution draft allowance differs between E, C and selected spec')
    runtime = rendered['native_shared_runtime_declaration']
    _need(composition.get('runtime_raw_json') == runtime['raw_json']
          and composition.get('runtime_sha256') == runtime['sha256']
          and composition.get('runtime_path') == runtime['path']
          and execution.get('runtime_declaration_sha256') == runtime['sha256']
          and c.canonical(execution.get('runtime')) == c.canonical(c.strict_json(runtime['raw_json'].encode('utf-8'))),
          'attribution runtime differs from the sole captured declaration')
    _need(execution.get('instruction_sha256') == composition.get('instruction_sha256')
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

    def __init__(self, selection, *, execution_raw, spec, composition_raw):
        doc, commands, directory, paths, inputs, maximum = _joined(selection, execution_raw, spec, composition_raw)
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
        try:
            full = read_regular(self._paths['full'], 'final_full', max_bytes=self._input_limit).captured
            report = read_regular(self._paths['report'], 'final_report', max_bytes=self._input_limit).captured
        except (TypeError, ValueError, KeyError, OSError) as exc:
            problems.append('current draft cannot be verified: ' + str(exc))
            return
        self._compare(problems, full.raw, report.raw, 'current captured')


class _SavedAttribution(_Attribution):
    def __init__(self, selection, *, execution_raw, spec, composition_raw, final_full, final_report):
        super().__init__(selection, execution_raw=execution_raw, spec=spec, composition_raw=composition_raw)
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


def live(selection, *, execution_raw, spec, composition_raw):
    """Create the live extra observer after the outer boundary has verified E."""
    return _Attribution(selection, execution_raw=execution_raw, spec=spec, composition_raw=composition_raw)


def saved(selection, *, execution_raw, spec, composition_raw, final_full, final_report):
    """Create immutable replay; finish() is mandatory for final acceptance."""
    return _SavedAttribution(selection, execution_raw=execution_raw, spec=spec, composition_raw=composition_raw,
                             final_full=final_full, final_report=final_report)
