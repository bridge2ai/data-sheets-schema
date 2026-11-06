#!/usr/bin/env python3
"""Observe U0 second-treatment guard costs without changing guards, 2026-11-06.

Inputs: a committed diagnostic source root and exact external configuration.
Outputs: R7/R8 phase JSONL plus bounded evidence from actual guard returns and
unwinds. Never calls a producer/guard to diagnose it; no callable replacement.
This identical extension belongs in both fresh T1 and T1+T2 diagnostic arms.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import time
import types


BASE_PATH = Path(__file__).with_name('native_recorder_thread_cpu_20261106.py')
_spec = importlib.util.spec_from_file_location('native_u0_second_thread_base', BASE_PATH)
thread = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(thread)
base = thread.base

CONFIG_NAME = 'native_recorder_second_cpu_20261106.config.json'
CONFIG_BYTES = b'{"output_parent":"/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-u0-20261106/second-observer-output"}\n'
PHASES = {module: dict(names) for module, names in thread.PHASES.items()}
PHASES.setdefault('native_catalog_reuse', {}).update({
    '_state': 'catalog_eligibility_state', 'runtime_token': 'catalog_eligibility'})
PHASES.setdefault('native_schema_event_reuse', {}).update({
    '_bindings': 'native_parser_bindings', '_token': 'native_parser_eligibility'})
GUARDS = frozenset(('native_catalog_reuse:runtime_token', 'native_schema_event_reuse:_token'))
MAX_REASON_DETAILS = 64
MAX_REASON_EXAMPLES = 4
MAX_PARENT_PHASES = 32
STATE_LABELS = ('functions', 'explicit_loader_parse', 'schema_state', 'metadata',
    'loaders', 'schema_snapshot_constructor', 'schema_definition_constructor',
    'namespace_constructor', 'namespace_methods', 'json_dumper_class',
    'json_dumper_singleton', 'json_dumper_getattribute', 'dumper_bindings',
    'json_classes', 'json_state', 'yaml_root', 'object_methods', 'copy_methods',
    'copy_dispatch', 'reducers', 'settings', 'yaml_constructor_state', 'primitive_state')


def primitive_difference(actual, expected, *, budget=256):
    """Tri-state comparison: exact built-ins only; never arbitrary eq/repr.

    A False result proves a primitive/shape mismatch; None means opaque or
    exhausted. It is diagnostic evidence, never a replacement admission rule.
    """
    remaining = [budget]
    first = []
    def compare(a, b, path):
        remaining[0] -= 1
        if remaining[0] < 0:
            return None
        if a is b:
            return True
        if type(a) is not type(b):
            if not first:
                first.append({'path': path, 'kind': 'exact_type_difference'})
            return False
        if type(a) in (str, bytes, int, float, bool, type(None)):
            if type(a) in (str, bytes) and max(len(a), len(b)) > 4096:
                return None
            equal = a == b
            if not equal and not first:
                first.append({'path': path, 'kind': 'primitive_value_difference'})
            return equal
        if type(a) is tuple:
            if len(a) != len(b):
                if not first:
                    first.append({'path': path, 'kind': 'tuple_length_difference'})
                return False
            opaque = False
            for index, (left, right) in enumerate(zip(a, b)):
                same = compare(left, right, [*path, index])
                if same is False:
                    return False
                opaque |= same is None
                if remaining[0] < 0:
                    break
            return None if opaque else True
        return None
    result = compare(actual, expected, [])
    return {'equal': result, 'first_difference': first[0] if first else None,
        'budget_exhausted': remaining[0] < 0, 'opaque_or_unclassified': result is None}


def state_components(actual, expected):
    if type(actual) is not tuple or type(expected) is not tuple:
        return {'state_shape': 'not_two_exact_tuples'}
    rows = []
    for index, (left, right) in enumerate(zip(actual[:32], expected[:32])):
        result = primitive_difference(left, right)
        if result['equal'] is not True:
            rows.append({'index': index,
                'component': STATE_LABELS[index] if index < len(STATE_LABELS) else 'unlabelled',
                **result})
    return {'actual_components': len(actual), 'baseline_components': len(expected),
        'component_limit_exceeded': max(len(actual), len(expected)) > 32,
        'nonidentical_or_unclassified_components': rows,
        'scope': 'bounded primitive comparison, not reevaluation of production equality'}


def exception_evidence(exception):
    cls = type(exception)
    try:
        arguments = BaseException.args.__get__(exception, cls)
    except (TypeError, AttributeError):
        arguments = ()
    values = []
    for value in arguments[:3]:
        if type(value) is str:
            values.append(value[:384])
        elif type(value) in (int, float, bool, type(None)):
            values.append(value)
        else:
            values.append('<opaque argument omitted>')
    return {'type': type.__getattribute__(cls, '__name__'),
        'module': type.__getattribute__(cls, '__module__'), 'primitive_args': values}


class SecondCPUObserver(thread.ThreadCPUObserver):
    def __init__(self, root, output, *, phases=None, **kwargs):
        self.reason_counts = {}
        self.reason_phase_counts = {}
        self.reason_examples = {}
        self.reason_details = 0
        self.reason_details_suppressed = 0
        self.guard_observations = {}
        self.reason_callback_thread_cpu_ns = 0
        super().__init__(root, output, phases=PHASES if phases is None else phases, **kwargs)
        initialization = self.root / 'src/data_sheets_schema/native_catalog_initialization.py'
        self.initialization_pin = base._pin(initialization) if initialization.is_file() else None

    def _initialization_provenance(self):
        """Read published startup pins only; never call or re-read dependencies."""
        module = sys.modules.get('data_sheets_schema.native_catalog_initialization')
        if module is None:
            return {'state': 'not_loaded', 'present_in_source': self.initialization_pin is not None}
        path = self.root / 'src/data_sheets_schema/native_catalog_initialization.py'
        if (type(module) is not types.ModuleType or self.initialization_pin is None
                or vars(module).get('__file__') != str(path)
                or base._pin(path) != self.initialization_pin):
            raise RuntimeError('initialization provenance module is not the pinned diagnostic source')
        attrs = vars(module)
        error = attrs.get('INITIALIZATION_ERROR')
        if error is not None and type(error) is not str:
            raise RuntimeError('initialization error evidence is not primitive text')
        evidence = {
            'rawloader': {'path': attrs.get('_PATH'), 'sha256': attrs.get('SOURCE_SHA256')},
            'yamlutils': {'path': attrs.get('DEFAULT_SOURCE_PATH', attrs.get('_root_path')),
                          'sha256': attrs.get('DEFAULT_SOURCE_SHA256')}}
        for row in evidence.values():
            name, digest = row['path'], row['sha256']
            if name is not None and (type(name) is not str or not Path(name).is_absolute()):
                raise RuntimeError('compiled dependency path is not an absolute primitive string')
            if digest is not None and (type(digest) is not str or len(digest) != 64
                    or any(character not in '0123456789abcdef' for character in digest)):
                raise RuntimeError('compiled dependency hash is not SHA-256')
            if error is None and (name is None or digest is None):
                raise RuntimeError('successful initialization lacks compiled dependency provenance')
        return {'state': 'loaded', 'source': self.initialization_pin,
            'compiled_dependency_sources': evidence,
            'initialization_error': error[:384] if error else None,
            'scope': 'Source-byte hashes captured when callback definitions were compiled during module initialization; dependencies are not reread or attested at checkpoint/end.'}

    def _inc(self, target, name, amount=1):
        # The frozen base originally had exactly one native_catalog_reuse
        # target. Its runtime-token return classifier must not label _state.
        if (target['module'] == 'native_catalog_reuse'
                and target['id'] != 'native_catalog_reuse:runtime_token'
                and name.startswith('runtime_token_')):
            return
        return super()._inc(target, name, amount)

    def _parents(self):
        return [{'call': row['id'], 'target': row['target']}
            for row in sorted(self.active.values(), key=lambda value: value['id'])][-MAX_PARENT_PHASES:]

    def _parent_guard(self):
        for row in reversed(self._parents()):
            if row['target'] in GUARDS:
                return row['call']
        return None

    def _reason(self, target, reason, *, detail=None):
        key = target + '/' + reason
        self.reason_counts[key] = self.reason_counts.get(key, 0) + 1
        parents = self._parents()
        for parent in parents:
            phase_key = parent['target'] + '|' + key
            self.reason_phase_counts[phase_key] = self.reason_phase_counts.get(phase_key, 0) + 1
        examples = self.reason_examples.get(key, 0)
        if self.reason_details >= MAX_REASON_DETAILS or examples >= MAX_REASON_EXAMPLES:
            self.reason_details_suppressed += 1
            return
        self.reason_examples[key] = examples + 1
        self.reason_details += 1
        self._emit('guard_observation', target=target, reason=reason, parents=parents,
            detail=detail, owner_thread=self.owner_thread,
            limitation='actual execution observations only; no guard or producer invoked again')
        os.fsync(self.fd)

    def _detail_available(self, target, reason):
        return (self.reason_details < MAX_REASON_DETAILS
            and self.reason_examples.get(target + '/' + reason, 0) < MAX_REASON_EXAMPLES)

    def _observe_return(self, code, frame, value):
        target = self.codes[code]['id']
        state = self.active.get((self.owner_thread, id(frame)))
        if state is None:
            return
        if target == 'native_schema_event_reuse:_bindings':
            parent = self._parent_guard()
            bound = frame.f_globals.get('_BOUND')
            if parent is not None and bound is not None:
                self.guard_observations.setdefault(parent, {})['bindings_result'] = primitive_difference(value, bound)
            return
        if target not in GUARDS:
            return
        context = self.guard_observations.pop(state['id'], {})
        if target == 'native_catalog_reuse:runtime_token':
            if value is not None:
                self._reason(target, 'token_available', detail={
                    'marker_kind': 'initial_READY' if value is frame.f_globals.get('_READY') else 'other_non_null_marker',
                    'marker_type': type.__getattribute__(type(value), '__name__')})
            elif 'actual' in frame.f_locals:
                # A real actual state exists and production returned None.
                # Do not infer whether equality itself raised an exception.
                actual = frame.f_locals['actual']
                reason = 'actual_state_available_refusal'
                detail = ({
                    'ordinary': state_components(actual, frame.f_globals.get('_STATE')),
                    'initialized': state_components(actual, frame.f_globals.get('_INITIALIZED_STATE'))}
                    if self._detail_available(target, reason) else {'bounded_detail_suppressed': True})
                self._reason(target, reason, detail=detail)
            elif context.get('unwinds'):
                self._reason(target, 'state_exception_refused', detail=context)
            else:
                self._reason(target, 'not_ready_or_unobserved_failure', detail=context)
        else:
            if value is not None:
                self._reason(target, 'token_available')
            elif frame.f_globals.get('_BOUND') is None:
                self._reason(target, 'initial_binding_unsupported')
            elif context.get('unwinds'):
                self._reason(target, 'bindings_exception_refused', detail=context)
            else:
                self._reason(target, 'token_none_without_observed_unwind', detail=context)

    def _returned(self, code, offset, value):
        if not self._owner_event('return', code):
            return
        frame = sys._getframe(1)
        tick = time.thread_time_ns()
        self.callback_depth += 1
        try:
            self._observe_return(code, frame, value)
        except Exception as exc:
            self._failure(exc)
        finally:
            self.reason_callback_thread_cpu_ns += time.thread_time_ns() - tick
            self.callback_depth -= 1
        self._finish(code, frame, 'returns', value)

    def _unwound(self, code, offset, exception):
        if not self._owner_event('unwind', code):
            return
        frame = sys._getframe(1)
        target = self.codes[code]['id']
        tick = time.thread_time_ns()
        self.callback_depth += 1
        try:
            if target in ('native_catalog_reuse:_state', 'native_schema_event_reuse:_bindings') or target in GUARDS:
                detail = exception_evidence(exception)
                parent = self._parent_guard()
                if parent is not None:
                    context = self.guard_observations.setdefault(parent, {})
                    context.setdefault('unwinds', []).append({'target': target, **detail})
                self._reason(target, 'actual_unwind', detail=detail)
            self.guard_observations.pop(self.active.get((self.owner_thread, id(frame)), {}).get('id'), None)
        except Exception as exc:
            self._failure(exc)
        finally:
            self.reason_callback_thread_cpu_ns += time.thread_time_ns() - tick
            self.callback_depth -= 1
        self._finish(code, frame, 'unwinds', None)

    def _emit(self, event, **values):
        if event == 'observer_start':
            values['second_observer'] = base._pin(Path(__file__).resolve())
            values['guard_reason_scope'] = 'actual returns/unwinds; bounded opaque-safe differences; parent recorder readback is not observed'
        elif event in ('thread_cpu_checkpoint', 'observer_end'):
            values['guard_reason_counts'] = dict(self.reason_counts)
            values['guard_reason_parent_phase_counts'] = dict(self.reason_phase_counts)
            values['guard_reason_details'] = self.reason_details
            values['guard_reason_details_suppressed'] = self.reason_details_suppressed
            values['guard_reason_callback_thread_cpu_ns'] = self.reason_callback_thread_cpu_ns
            values['catalog_initialization_provenance'] = self._initialization_provenance()
        return super()._emit(event, **values)


def install(root, output_parent):
    root, parent = Path(root).resolve(strict=True), Path(output_parent)
    if not parent.is_dir() or parent.resolve(strict=True) != parent or parent.is_relative_to(root):
        raise RuntimeError('observer output parent must be an existing exact external directory')
    return SecondCPUObserver(root, parent / ('recorder-' + str(os.getpid()) + '-' + str(time.time_ns()))).start()


def install_from_config(root):
    if sys.argv[1:3] != ['provenance', 'record']:
        return None
    root = Path(root).resolve(strict=True)
    config = root / 'scripts/adhoc' / CONFIG_NAME
    if config.read_bytes() != CONFIG_BYTES:
        raise RuntimeError('second observer config differs from declared bytes')
    parent = Path(base.json.loads(CONFIG_BYTES)['output_parent'])
    if not parent.is_dir() or parent.resolve(strict=True) != parent or parent.is_relative_to(root):
        raise RuntimeError('second observer output must be existing and external')
    return SecondCPUObserver(root, parent / ('recorder-' + str(os.getpid()) + '-' + str(time.time_ns()))).start(configuration=base._pin(config))


def preflight(root, output):
    """Separate ordinary-site import probe; never execute the recorder path."""
    import importlib
    root, output = Path(root).resolve(strict=True), Path(output).absolute()
    if (root.parent / 'plans/native_quiet_window.lock').exists():
        raise RuntimeError('measurement lock exists; preflight must pause')
    if output.is_relative_to(root) or output.parent.resolve(strict=True) != output.parent:
        raise RuntimeError('preflight needs a fresh exact external output path')
    if sys.flags.no_site:
        raise RuntimeError('preflight requires ordinary site startup, like the recorder child')
    if any(name == 'data_sheets_schema' or name.startswith('data_sheets_schema.') for name in sys.modules):
        raise RuntimeError('preflight requires a fresh project import namespace')
    sys.path.insert(0, str(root / 'src'))
    package = importlib.import_module('data_sheets_schema')
    if vars(package).get('__file__') != str(root / 'src/data_sheets_schema/__init__.py'):
        raise RuntimeError('preflight did not load the diagnostic ordinary package')
    output.mkdir(mode=0o700, exist_ok=False)
    seen = SecondCPUObserver(root, output / 'observer')
    imported = []
    try:
        seen.start(arm_trace=False)
        for name in sorted({target['module'] for target in seen.targets.values()}):
            module = importlib.import_module(name if name == 'yaml' else 'data_sheets_schema.' + name)
            imported.append({'module': module.__name__, 'file': vars(module).get('__file__')})
        seen._bind_loaded()
        expected = {target['id'] for target in seen.targets.values()}
        missing = sorted(expected - seen.bound_targets)
        if missing:
            raise RuntimeError('preflight failed to bind target roster: ' + ', '.join(missing))
    finally:
        seen.close()
    report = {'kind': 'second_observer_import_only_preflight_not_recorder_trial',
        'valid': seen.valid, 'root': str(root), 'observer': str(seen.output),
        'imported': imported, 'bound_targets': sorted(seen.bound_targets),
        'bound_count': len(seen.bound_targets), 'absent_in_source': seen.missing,
        'source_pins': seen.source_pins, 'source_closure': seen.source_closure,
        'python': {'executable': sys.executable, 'version': sys.version, 'no_site': sys.flags.no_site},
        'limitations': 'Imports only; no recorder path, native executable or provider invocation; process must inherit OS network denial.'}
    with (output / 'preflight.json').open('x') as stream:
        base.json.dump(report, stream, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    if not seen.valid:
        raise RuntimeError('preflight observer evidence is invalid')
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Import-only U0 second-observer preflight.')
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = preflight(args.tree, args.out)
    print(base.json.dumps({'valid': result['valid'], 'bound_count': result['bound_count'],
        'absent_in_source': result['absent_in_source'], 'output': str(args.out)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
