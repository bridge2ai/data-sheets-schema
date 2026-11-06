#!/usr/bin/env python3
"""Owner-thread U0 phase/counter observer, R8/#4354, 2026-11-06.

Inputs: one committed diagnostic source tree and its fixed external output
configuration. Outputs: durable phase/counter JSONL and the 170s stack. Uses
local sys.monitoring code events, never cProfile or replacement callables.
Periodic SIGALRM checkpoints execute on the recorder thread, not a worker.
"""
from __future__ import annotations

import atexit
import faulthandler
import hashlib
import importlib.util
import os
from pathlib import Path
import resource
import signal
import sys
import threading
import time
import types


BASE_PATH = Path(__file__).with_name('native_recorder_observer_20261026.py')
_spec = importlib.util.spec_from_file_location('native_recorder_thread_observer_base', BASE_PATH)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

CONFIG_NAME = 'native_recorder_thread_cpu_20261106.config.json'
CONFIG_BYTES = b'{"output_parent":"/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-u0-20261106/pair-observer-output"}\n'
PHASES = {module: dict(names) for module, names in base.PHASES.items()}
for _module, _names in {
    'native_shared_selection': {'_rebuild': 'selection_rebuild', '_schemas': 'selection_schemas'},
    'schema_snapshot': {'_capture_native_schema': 'native_schema_capture', 'capture_schema': 'schema_capture'},
    'audit_omissions': {'_mapping': 'document_mapping', '_load_yaml': 'document_yaml',
        '_schema_yaml': 'schema_yaml', '_schema_with_root_bases': 'schema_roots',
        '_schema_product': 'schema_catalog'},
    'provenance': {'build_record': 'record_construction'},
    'record_schema': {'compile_record_schema': 'record_schema_compile'},
    'native_shared_capture': {'phase_replay': 'native_phase_replay', '_document': 'native_document'},
}.items():
    PHASES.setdefault(_module, {}).update(_names)
DOCUMENT_ARGUMENTS = {'audit_omissions:_mapping': 'raw', 'audit_omissions:_load_yaml': 'text',
                      'audit_omissions:_schema_yaml': 'text', 'native_shared_capture:_document': 'raw'}
RUSAGE_FIELDS = ('ru_utime', 'ru_stime', 'ru_minflt', 'ru_majflt', 'ru_nvcsw', 'ru_nivcsw')
MAX_DOCUMENT_HASHES = 256
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024


def usage():
    value = resource.getrusage(resource.RUSAGE_SELF)
    return {**{key: getattr(value, key) for key in RUSAGE_FIELDS},
        'thread_cpu_ns': time.thread_time_ns(), 'process_cpu_ns': time.process_time_ns(),
        'monotonic_ns': time.monotonic_ns(),
        'max_rss_bytes': value.ru_maxrss * (1 if sys.platform == 'darwin' else 1024)}


def delta(before, after):
    return {**{key: after[key] - before[key] for key in (*RUSAGE_FIELDS,
            'thread_cpu_ns', 'process_cpu_ns', 'monotonic_ns')},
        'max_rss_bytes': after['max_rss_bytes'],
        'peak_rss_growth_bytes': after['max_rss_bytes'] - before['max_rss_bytes']}


def assert_closure(root):
    path = Path(__file__).with_name('native_u0_source_closure_20261106.py')
    spec = importlib.util.spec_from_file_location('native_u0_thread_closure_check', path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper.assert_source_closure(root)


class ThreadCPUObserver(base.Observer):
    def __init__(self, root, output, *, phases=None, cache_targets=None,
                 checkpoint_seconds=5.0, closure_checker=assert_closure, parser_path=None):
        if not 0 < checkpoint_seconds <= 60:
            raise ValueError('checkpoint interval must be positive and at most 60 seconds')
        self.owner_thread = threading.get_ident()
        self.checkpoint_seconds = checkpoint_seconds
        self.closure_checker = closure_checker
        self.source_closure = None
        self.non_owner_events = {}
        self.phase_usage = {}
        self.document_counts = {}
        self.parser_frames = set()
        self.expected_codes = {}
        self.bound_targets = set()
        self.bound_code_identities = {}
        self.callback_depth = 0
        self.checkpoint_pending = False
        self.checkpoint_count = 0
        self.checkpoint_thread_cpu_ns = 0
        self.started = False
        self.closing = False
        self._audit_installed = False
        self._alarm_installed = None
        self._prior_alarm = None
        self.optional_treatment_pin = None
        super().__init__(root, output, phases=PHASES if phases is None else phases,
                         cache_targets=cache_targets)
        # Pin/compile code objects without importing or executing production.
        for path in tuple(self.source_pins):
            self._index_expected(Path(path))
        if parser_path is None:
            found = importlib.util.find_spec('yaml')
            if found is None or found.origin is None:
                raise RuntimeError('cannot locate the existing PyYAML source')
            parser_path = Path(found.origin)
        self.parser_path = Path(parser_path).resolve(strict=True)
        raw = self.parser_path.read_bytes()
        self.source_pins[str(self.parser_path)] = {'bytes': len(raw), 'sha256': base._sha(raw)}
        self._index_expected(self.parser_path, parser=True)
        treatment = self.root / 'src/data_sheets_schema/native_schema_event_reuse.py'
        if treatment.is_file():
            self.optional_treatment_pin = base._pin(treatment)

    def _index_expected(self, path, *, parser=False):
        raw = path.read_bytes()
        if base._sha(raw) != self.source_pins[str(path)]['sha256']:
            raise RuntimeError('target source changed during registration')
        module = compile(raw, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize)
        for code in self._walk_codes(module):
            key = (code.co_filename, code.co_qualname)
            if parser and code.co_qualname == 'parse':
                self.targets[key] = {'id': 'yaml:parse', 'module': 'yaml', 'qualname': 'parse',
                    'phase': None, 'cache': False, 'firstlineno': code.co_firstlineno,
                    'source': str(path), 'counter_sites': {}, 'count_only_generator': True}
                self.stats['yaml:parse'] = {'calls': 0, 'returns': 0, 'unwinds': 0,
                    'inclusive_wall_ns': 0, 'inclusive_thread_cpu_ns': 0, 'counters': {}}
            if key in self.targets:
                self.expected_codes[key] = code

    @staticmethod
    def _walk_codes(code):
        yield code
        for value in code.co_consts:
            if isinstance(value, types.CodeType):
                yield from ThreadCPUObserver._walk_codes(value)

    def _bind(self, code):
        key = (code.co_filename, code.co_qualname)
        target = self.targets.get(key)
        if target is None:
            return
        if (code.co_firstlineno != target['firstlineno']
                or code != self.expected_codes.get(key)):
            self.valid = False
            raise RuntimeError('loaded target differs from pinned source code')
        if code in self.codes:
            return
        self.codes[code] = target
        self.bound_code_identities[id(code)] = code
        self.bound_targets.add(target['id'])
        events = sys.monitoring.events.PY_START | sys.monitoring.events.PY_RETURN
        if target['counter_sites']:
            events |= sys.monitoring.events.LINE
        sys.monitoring.set_local_events(self.tool, code, events)

    def _audit(self, event, arguments):
        if not self.started or self.closed or self.closing or not self.valid or event != 'exec':
            return
        code = arguments[0]
        if isinstance(code, types.CodeType) and code.co_filename in self.source_pins:
            for child in self._walk_codes(code):
                self._bind(child)

    def _bind_loaded(self):
        seen = set()
        def inspect_value(value):
            if id(value) in seen:
                return
            seen.add(id(value))
            if isinstance(value, types.FunctionType):
                for code in self._walk_codes(value.__code__):
                    self._bind(code)
            elif isinstance(value, (classmethod, staticmethod)):
                inspect_value(value.__func__)
            elif isinstance(value, type):
                for item in vars(value).values():
                    if isinstance(item, (types.FunctionType, classmethod, staticmethod)):
                        inspect_value(item)
            try:
                wrapped = vars(value).get('__wrapped__')
            except TypeError:
                wrapped = None
            if wrapped is not None:
                inspect_value(wrapped)
        for module in tuple(sys.modules.values()):
            if module is None:
                continue
            attributes = vars(module)
            if attributes.get('__file__') in self.source_pins:
                for value in tuple(attributes.values()):
                    inspect_value(value)

    def _origins(self):
        try:
            self.source_closure = self.closure_checker(self.root)
        except Exception as exc:
            self.valid = False
            self.source_closure = {'verified': False, 'error_type': type(exc).__name__}
            if not self.closing:
                raise
            return []
        rows = super()._origins()
        return rows

    def _treatment_counters(self):
        module = sys.modules.get('data_sheets_schema.native_schema_event_reuse')
        if module is None:
            return {'state': 'not_loaded', 'present_in_source': self.optional_treatment_pin is not None}
        path = self.root / 'src/data_sheets_schema/native_schema_event_reuse.py'
        if (self.optional_treatment_pin is None or vars(module).get('__file__') != str(path)
                or base._pin(path) != self.optional_treatment_pin):
            raise RuntimeError('treatment counter module is not the pinned diagnostic source')
        attrs = vars(module)
        counters, cache = attrs.get('_COUNTERS'), attrs.get('_CACHE')
        if type(counters) is not dict or type(cache) is not dict:
            # OrderedDict is used by bounded reuse; inspect it without invoking
            # a production helper or a user-defined mapping implementation.
            from collections import OrderedDict
            if type(counters) is not dict or type(cache) is not OrderedDict:
                raise RuntimeError('treatment counter container shape changed')
        if any(type(key) is not str or type(value) not in (int, bool) for key, value in counters.items()):
            raise RuntimeError('treatment counters are not primitive observations')
        rows = {'state': 'loaded', 'counters': dict(counters), 'entries': len(cache),
                'source': self.optional_treatment_pin}
        for name in ('_BYTES', '_EVENTS'):
            value = attrs.get(name)
            if type(value) is not int:
                raise RuntimeError('treatment cache bound counter changed shape')
            rows[name] = value
        return rows

    def _owner_event(self, event, code):
        if (self.closed or self.closing or not self.valid
                or self.bound_code_identities.get(id(code)) is not code):
            return False
        target = self.codes[code]
        if (code.co_filename != target['source'] or code.co_qualname != target['qualname']
                or code.co_firstlineno != target['firstlineno']):
            return False
        if threading.get_ident() != self.owner_thread:
            key = event + ':' + self.codes[code]['id']
            self.non_owner_events[key] = self.non_owner_events.get(key, 0) + 1
            return False  # Never DISABLE: that would also disable owner events.
        return True

    def _document(self, target, value):
        row = self.document_counts.setdefault(target, {'calls': 0, 'input_bytes': 0,
            'hash_counts': {}, 'hash_coverage_complete': True, 'non_text_inputs': 0})
        row['calls'] += 1
        if type(value) not in (str, bytes):
            row['non_text_inputs'] += 1
            return
        if len(value) > MAX_DOCUMENT_BYTES:
            row['hash_coverage_complete'] = False
            return
        raw = value.encode('utf-8') if type(value) is str else value
        row['input_bytes'] += len(raw)
        digest = hashlib.sha256(raw).hexdigest()
        if digest not in row['hash_counts'] and len(row['hash_counts']) >= MAX_DOCUMENT_HASHES:
            row['hash_coverage_complete'] = False
            return
        row['hash_counts'][digest] = row['hash_counts'].get(digest, 0) + 1

    def _start(self, code, offset):
        if not self._owner_event('start', code):
            return
        tick = time.monotonic_ns()
        self.callback_depth += 1
        try:
            frame = sys._getframe(1)
            if frame.f_code is not code:
                raise RuntimeError('monitoring frame differs from registered code')
            target = self.codes[code]
            self.stats[target['id']]['calls'] += 1
            if target.get('count_only_generator'):
                self.parser_frames.add(id(frame))
                self._document('yaml:parse_started', frame.f_locals.get('stream'))
                yaml_module = sys.modules.get('yaml')
                safe = yaml_module is not None and frame.f_locals.get('Loader') is vars(yaml_module).get('SafeLoader')
                self._inc(target, 'safe_loader_started' if safe else 'other_loader_started')
                return
            self.next_id += 1
            state = {'id': self.next_id, 'target': target['id'], 'wall': tick,
                'cpu': time.thread_time_ns(), 'pending_eviction': None}
            self.active[(self.owner_thread, id(frame))] = state
            argument = DOCUMENT_ARGUMENTS.get(target['id'])
            if argument:
                self._document(target['id'], frame.f_locals.get(argument))
            if target['id'] == 'schema_snapshot:_capture_native_schema':
                for _path, raw in frame.f_locals.get('members', ()):
                    self._document('native_schema_member_visits', raw)
            if target['qualname'] == '_base':
                self._inc(target, 'catalog_argument_present' if frame.f_locals.get('_catalogs') is not None else 'catalog_argument_absent')
            if target['qualname'] == 'DerivationCache._store':
                key, encoded = frame.f_locals.get('key'), frame.f_locals.get('encoded')
                product = key[0] if type(key) is tuple and key and key[0] in ('open', 'derive') else 'unknown'
                self._inc(target, 'store_product_' + product)
                if type(encoded) is bytes:
                    self._inc(target, 'store_product_' + product + '_bytes', len(encoded))
            if target['phase'] and self.stats[target['id']]['calls'] <= base.MAX_PHASE_EVENTS_PER_TARGET:
                state['phase_logged'] = True
                self._emit('phase_start', call=state['id'], target=target['id'], phase=target['phase'], thread=self.owner_thread)
            elif target['phase']:
                self._inc(target, 'phase_call_details_suppressed_at_bound')
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_ns += time.monotonic_ns() - tick
            self.callback_count += 1
            self.callback_depth -= 1

    def _line(self, code, lineno):
        if not self._owner_event('line', code):
            return
        tick = time.monotonic_ns()
        self.callback_depth += 1
        try:
            frame, target = sys._getframe(1), self.codes[code]
            if frame.f_code is not code:
                raise RuntimeError('monitoring line frame differs')
            state = self.active[(self.owner_thread, id(frame))]
            self._confirm_eviction(target, state, frame)
            if 'decode_line' in state:
                previous, started = state.pop('decode_line')
                self._inc(target, previous + '_next_line_observed')
                self._inc(target, previous + '_to_next_line_ns', tick - started)
            marker = target['counter_sites'].get(lineno)
            if marker:
                self._inc(target, marker + '_entries')
            if marker in ('typed_eviction', 'shared_eviction', 'legacy_open_eviction'):
                rows = base._cache_rows(frame, marker)
                if rows is None:
                    self._inc(target, 'eviction_state_unavailable')
                else:
                    victim = next(iter(rows), None)
                    product = victim[0] if type(victim) is tuple and victim and victim[0] in ('open', 'derive') else 'legacy_open' if marker == 'legacy_open_eviction' else 'unknown'
                    state['pending_eviction'] = (marker, len(rows), product)
            elif marker == 'derive_lookup':
                self._inc(target, 'derive_misses' if frame.f_locals.get('encoded') is None else 'derive_hits')
            elif marker == 'open_lookup':
                self._inc(target, 'open_misses' if frame.f_locals.get('hit') is None else 'open_hits')
                raw = frame.f_locals.get('raw_packet')
                if type(raw) is bytes:
                    self._inc(target, 'open_lookup_packet_bytes', len(raw))
            elif marker in ('warm_decode', 'derive_decode', 'shared_hit_decode', 'open_serialized_decode', 'open_legacy_copy'):
                raw = frame.f_locals.get('raw' if marker == 'warm_decode' else 'hit' if marker == 'open_serialized_decode' else 'encoded')
                if marker == 'shared_hit_decode':
                    cache, key = frame.f_locals.get('cache'), frame.f_locals.get('key')
                    raw = cache.get(key) if type(cache) is dict else None
                if type(raw) is bytes:
                    self._inc(target, marker + '_input_bytes', len(raw))
                state['decode'], state['decode_line'] = (marker, tick), (marker, tick)
            elif marker == 'validated_set_clear':
                values = frame.f_globals.get('_VALIDATED_BOUNDED_BYTES')
                if type(values) is set:
                    self._inc(target, 'validated_set_clear_entries_removed_if_success', len(values))
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_ns += time.monotonic_ns() - tick
            self.callback_count += 1
            self.callback_depth -= 1

    def _finish(self, code, frame, kind, value):
        tick = time.monotonic_ns()
        self.callback_depth += 1
        try:
            target = self.codes[code]
            if target.get('count_only_generator'):
                if id(frame) in self.parser_frames:
                    self.parser_frames.remove(id(frame))
                    self.stats[target['id']][kind] += 1
            else:
                super()._end(code, frame, kind, value, tick)
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_ns += time.monotonic_ns() - tick
            self.callback_count += 1
            self.callback_depth -= 1

    def _returned(self, code, offset, value):
        if self._owner_event('return', code):
            self._finish(code, sys._getframe(1), 'returns', value)

    def _unwound(self, code, offset, exception):
        if self._owner_event('unwind', code):
            self._finish(code, sys._getframe(1), 'unwinds', None)

    def _emit(self, event, **values):
        if threading.get_ident() != self.owner_thread:
            self.valid = False
            raise RuntimeError('observer output must be written by its owner thread')
        if event == 'phase_start':
            current = usage()
            self.phase_usage[values['call']] = {'target': values['target'], 'phase': values['phase'], 'started': current}
            values['rusage_enter'] = current
        elif event == 'phase_end':
            current = usage()
            previous = self.phase_usage.pop(values['call'], None)
            values['rusage_exit'] = current
            if previous:
                values['inclusive_rusage_delta'] = delta(previous['started'], current)
        elif event == 'observer_end':
            values['source_closure'] = self.source_closure
            values['non_owner_events_ignored'] = dict(self.non_owner_events)
        super()._emit(event, **values)
        if event in ('phase_start', 'phase_end', 'observer_error', 'observer_end'):
            os.fsync(self.fd)

    def _snapshot(self, reason):
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError('checkpoint CPU must be sampled on the owner thread')
        before = time.thread_time_ns()
        super()._snapshot(reason)
        current = usage()
        self.checkpoint_count += 1
        self._emit('thread_cpu_checkpoint', reason=reason, checkpoint=self.checkpoint_count,
            owner_thread=self.owner_thread, rusage=current,
            active_phases=[{'call': call, 'target': row['target'], 'phase': row['phase'],
                'inclusive_rusage_delta': delta(row['started'], current)} for call, row in self.phase_usage.items()],
            documents=self.document_counts, parser_inflight=len(self.parser_frames),
            treatment_cache=self._treatment_counters(),
            non_owner_events_ignored=dict(self.non_owner_events),
            bound_targets=sorted(self.bound_targets),
            checkpoint_thread_cpu_ns_before_current=self.checkpoint_thread_cpu_ns,
            limitation='nested phases overlap; observer overhead included; process rusage includes all threads; owner thread_cpu_ns excludes other threads')
        os.fsync(self.fd)
        self.checkpoint_thread_cpu_ns += time.thread_time_ns() - before

    def _alarm(self, signum, frame):
        if self.closed or self.closing or not self.valid:
            return
        if threading.get_ident() != self.owner_thread:
            self.valid = False
            return
        if self.callback_depth:
            self.checkpoint_pending = True
            return
        self.callback_depth += 1
        try:
            self.checkpoint_pending = False
            self._snapshot('owner_timer')
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_depth -= 1

    def start(self, *, arm_trace=True, configuration=None, periodic=True):
        try:
            return self._start_monitoring(arm_trace=arm_trace, configuration=configuration, periodic=periodic)
        except BaseException:
            self.valid = False
            self.close()
            raise

    def _start_monitoring(self, *, arm_trace, configuration, periodic):
        if self.started or not hasattr(sys, 'monitoring'):
            raise RuntimeError('fresh observer and Python sys.monitoring are required')
        if threading.get_ident() != self.owner_thread or threading.current_thread() is not threading.main_thread():
            raise RuntimeError('recorder observer must start on its owner main thread')
        if periodic and (signal.getsignal(signal.SIGALRM) is not signal.SIG_DFL or signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0)):
            raise RuntimeError('existing alarm handler/timer cannot be replaced')
        origins = self._origins()  # Refuse mixed source closure before monitoring.
        for candidate in (5, 4, 3, 2, 1, 0):
            if sys.monitoring.get_tool(candidate) is None:
                sys.monitoring.use_tool_id(candidate, 'd4d-owner-thread-cpu')
                self.tool = candidate
                break
        if self.tool is None:
            raise RuntimeError('no free monitoring tool')
        for event, callback in ((sys.monitoring.events.PY_START, self._start),
                (sys.monitoring.events.PY_RETURN, self._returned),
                (sys.monitoring.events.PY_UNWIND, self._unwound),
                (sys.monitoring.events.LINE, self._line)):
            sys.monitoring.register_callback(self.tool, event, callback)
        self.started = True
        sys.addaudithook(self._audit)
        self._audit_installed = True
        self._bind_loaded()
        # PY_UNWIND is global-only in CPython. No global call/line events.
        sys.monitoring.set_events(self.tool, sys.monitoring.events.PY_UNWIND)
        age = base.process_age()
        if arm_trace:
            self.trace_stream = (self.output / 'stack-170s.txt').open('xb', buffering=0)
            faulthandler.dump_traceback_later(max(0.001, 170 - age['seconds']),
                                            file=self.trace_stream, repeat=False, exit=False)
        self._emit('observer_start', helper=base._pin(Path(__file__).resolve()), root=str(self.root),
            python={'executable': sys.executable, 'version': sys.version},
            owner_thread=self.owner_thread, process_age=age, origins=origins,
            source_closure=self.source_closure, source_pins=self.source_pins,
            configuration=configuration, targets=list(self.targets.values()), absent_in_source=self.missing,
            timings='local ordinary-call thread CPU; count-only yaml.parse starts, never generator resumptions',
            overhead='no cProfile/global call events/background accounting; exec audit binds exact source code; global unwind is filtered; phase fsync/checkpoints are included',
            periodic_scope='SIGALRM executes on owner thread; callbacks may be delayed by C calls',
            checkpoint_seconds=self.checkpoint_seconds)
        if periodic:
            self._prior_alarm = signal.getsignal(signal.SIGALRM)
            self._alarm_installed = self._alarm
            signal.signal(signal.SIGALRM, self._alarm_installed)
            signal.setitimer(signal.ITIMER_REAL, self.checkpoint_seconds, self.checkpoint_seconds)
        atexit.register(self.close)
        self._snapshot('initial')
        return self

    def close(self):
        if self.closed:
            return
        if threading.get_ident() != self.owner_thread:
            self.valid = False
            return
        self.closing = True
        if self._alarm_installed is not None:
            if (signal.getsignal(signal.SIGALRM) is self._alarm_installed
                    and signal.getitimer(signal.ITIMER_REAL)[1] == self.checkpoint_seconds):
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, self._prior_alarm)
            else:
                self.valid = False  # Do not alter somebody else's replacement.
        try:
            super().close()
        finally:
            self.started = False


def install(root, output_parent):
    root, parent = Path(root).resolve(strict=True), Path(output_parent)
    if not parent.is_dir() or parent.resolve(strict=True) != parent or parent.is_relative_to(root):
        raise RuntimeError('observer output parent must be an existing exact external directory')
    return ThreadCPUObserver(root, parent / ('recorder-' + str(os.getpid()) + '-' + str(time.time_ns()))).start()


def install_from_config(root):
    if sys.argv[1:3] != ['provenance', 'record']:
        return None
    root = Path(root).resolve(strict=True)
    config = root / 'scripts/adhoc' / CONFIG_NAME
    if config.read_bytes() != CONFIG_BYTES:
        raise RuntimeError('thread observer config differs from declared bytes')
    parent = Path(base.json.loads(CONFIG_BYTES)['output_parent'])
    if not parent.is_dir() or parent.resolve(strict=True) != parent or parent.is_relative_to(root):
        raise RuntimeError('observer output parent must be existing and external')
    return ThreadCPUObserver(root, parent / ('recorder-' + str(os.getpid()) + '-' + str(time.time_ns()))).start(configuration=base._pin(config))


def preflight(root, output):
    """Import-only roster probe in a fresh process; never invokes the recorder.

    Run separately before the causal pair, with ordinary site processing like
    the actual recorder and OS network denial. This intentionally imports all
    target modules here; the actual install() path still imports none eagerly.
    """
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
    seen = ThreadCPUObserver(root, output / 'observer')
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
    report = {'kind': 'import_only_binding_preflight_not_recorder_trial',
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
    parser = argparse.ArgumentParser(description='Import-only U0 observer roster preflight; no recorder invocation.')
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = preflight(args.tree, args.out)
    print(base.json.dumps({'valid': result['valid'], 'bound_count': result['bound_count'],
        'absent_in_source': result['absent_in_source'], 'output': str(args.out)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
