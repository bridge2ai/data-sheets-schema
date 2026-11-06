"""Diagnostic-only native schema parser reuse; U0 causal pair, 2026-11-06.

Input: exact native schema UTF-8 text. Output: fresh strict construction plus
an optional immutable parser-event candidate. No admission result is retained.
Copied by native_u0_parser_event_treatment_20261106.py into a fresh diagnostic
source only. This payload is not installed into the tooling tree's package.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
import re
import sys
from threading import Lock
import types

import yaml


# M7 5c952d210 uses 131072 events and 8M scalar/tag/anchor characters for one
# checked stream. Its saved merged-schema pin is 1,442,513 bytes. Four entries
# allow full/core plus small imports without an unbounded process cache. These
# are retention-accounting/event limits, not claims about exact Python RSS.
# payload_bytes counts UTF-8 input twice, semantic event strings, and an
# explicitly estimated 128 bytes/event allowance. It is neither a serialized
# size nor a measurement of retained Python-object memory; exact event-count,
# source-byte and semantic-character limits independently bound retention.
MAX_ENTRIES = 4
MAX_EVENTS_PER_ENTRY = 131_072
MAX_TOTAL_EVENTS = 262_144
MAX_EVENT_CHARS = 8_000_000
MAX_PAYLOAD_BYTES = 40_000_000
MAX_INPUT_BYTES = 8_000_000

_EVENT_FIELDS = {
    'StreamStartEvent': ('encoding',), 'StreamEndEvent': (),
    'DocumentStartEvent': ('explicit', 'version', 'tags'),
    'DocumentEndEvent': ('explicit',), 'AliasEvent': ('anchor',),
    'ScalarEvent': ('anchor', 'tag', 'implicit', 'value', 'style'),
    'SequenceStartEvent': ('anchor', 'tag', 'implicit', 'flow_style'),
    'SequenceEndEvent': (),
    'MappingStartEvent': ('anchor', 'tag', 'implicit', 'flow_style'),
    'MappingEndEvent': (),
}
_MODULES = (yaml, yaml.reader, yaml.scanner, yaml.parser, yaml.loader, yaml.tokens,
            yaml.events, yaml.error)


def _setting(value):
    """Cheap structural binding snapshot; never inspect files or hash code."""
    if value is None or type(value) in (str, bytes, int, float, bool):
        return type(value), value
    if type(value) in (tuple, list):
        return type(value), tuple(_setting(item) for item in value)
    if type(value) is dict:
        return dict, tuple((_setting(key), _setting(item)) for key, item in value.items())
    if type(value) in (set, frozenset):
        return type(value), frozenset(_setting(item) for item in value)
    if isinstance(value, re.Pattern):
        return re.Pattern, value.pattern, value.flags
    if isinstance(value, type):
        return type, value
    if type(value) is types.FunctionType:
        if value.__closure__ is not None or value.__dict__:
            raise TypeError('unsupported parser function closure or attributes: '
                            + value.__module__ + '.' + value.__qualname__)
        module = sys.modules.get(value.__module__)
        if (not value.__module__.startswith('yaml') or module is None
                or value.__globals__ is not vars(module)
                or value.__code__.co_filename != getattr(module, '__file__', None)):
            raise TypeError('unshipped parser function present before binding: '
                            + value.__module__ + '.' + value.__qualname__)
        return (types.FunctionType, value, value.__code__, id(value.__globals__),
                _setting(value.__defaults__), _setting(value.__kwdefaults__))
    if isinstance(value, (classmethod, staticmethod)):
        return type(value), _setting(value.__func__)
    if isinstance(value, property):
        return property, _setting(value.fget), _setting(value.fset), _setting(value.fdel)
    if isinstance(value, (types.BuiltinFunctionType, types.MethodDescriptorType,
                          types.WrapperDescriptorType, types.GetSetDescriptorType,
                          types.MemberDescriptorType)):
        return type(value), value
    if isinstance(value, types.ModuleType):
        return types.ModuleType, value
    raise TypeError('unsupported parser binding state: ' + type(value).__module__
                    + '.' + type(value).__qualname__)


def _bindings():
    # Parser dependencies only; composition/constructor/resolver validation is
    # fresh on every replay. In particular LinkML's supported construct_mapping
    # wrapper is not part of yaml.parse's event producer and must not disable
    # this cache. Mutation never becomes a newly accepted parser baseline.
    if (type(yaml.parse) is not types.FunctionType or yaml.parse.__module__ != 'yaml'
            or yaml.parse.__name__ != 'parse' or yaml.parse.__globals__ is not vars(yaml)
            or yaml.parse.__code__.co_filename != yaml.__file__
            or yaml.SafeLoader is not yaml.loader.SafeLoader
            or yaml.SafeLoader.__module__ != 'yaml.loader'
            or yaml.SafeLoader.__name__ != 'SafeLoader'
            or yaml.SafeLoader.__bases__ != (yaml.reader.Reader, yaml.scanner.Scanner,
                yaml.parser.Parser, yaml.composer.Composer,
                yaml.constructor.SafeConstructor, yaml.resolver.Resolver)):
        raise TypeError('unsupported initial parser or SafeLoader binding')
    rows, classes = [], set()
    parser_classes = {yaml.SafeLoader, yaml.reader.Reader, yaml.scanner.Scanner, yaml.parser.Parser}
    event_modules = {'yaml.events', 'yaml.tokens', 'yaml.error', 'yaml.reader',
                     'yaml.scanner', 'yaml.parser'}
    for module in _MODULES:
        members = []
        for name, value in sorted(vars(module).items()):
            if isinstance(value, type) and value.__module__.startswith('yaml'):
                if value in parser_classes or value.__module__ in event_modules:
                    classes.add(value)
                members.append((name, value))
            elif type(value) is types.FunctionType and value.__module__.startswith('yaml'):
                members.append((name, _setting(value)))
            elif isinstance(value, types.ModuleType):
                members.append((name, value))
        rows.append((module, tuple(members)))
    class_rows = []
    for cls in sorted(classes, key=lambda value: (value.__module__, value.__qualname__)):
        class_rows.append((cls, cls.__bases__, tuple(
            (name, _setting(value)) for name, value in sorted(vars(cls).items())
            if name not in ('__dict__', '__weakref__'))))
    initializers = tuple(_setting(value.__init__) for value in (
        yaml.composer.Composer, yaml.constructor.SafeConstructor, yaml.resolver.Resolver))
    return tuple(rows), tuple(class_rows), initializers, yaml.parse, yaml.SafeLoader, yaml.error.Mark


_BOUND_ERROR = None
try:
    _BOUND = _bindings()
except (TypeError, ValueError, AttributeError, RecursionError) as exc:
    _BOUND = None
    _BOUND_ERROR = type(exc).__name__ + ': ' + str(exc)


def _token(limit):
    from . import audit_omissions as omissions
    try:
        if _BOUND is None or _bindings() != _BOUND:
            return None
        return (limit, omissions.MAX_DEPTH, omissions.MAX_NODES,
                omissions._YAML_REPLAY_MAX_EVENTS, omissions._YAML_REPLAY_MAX_TEXT_BYTES,
                MAX_ENTRIES, MAX_EVENTS_PER_ENTRY, MAX_TOTAL_EVENTS,
                MAX_EVENT_CHARS, MAX_PAYLOAD_BYTES, MAX_INPUT_BYTES)
    except (TypeError, ValueError, AttributeError, RecursionError):
        return None


def _freeze(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is tuple:
        return tuple(_freeze(item) for item in value)
    if type(value) is dict and all(type(key) is str and type(item) is str for key, item in value.items()):
        return ('__tags__', tuple(value.items()))
    raise TypeError('unsupported YAML event field')


def _thaw(value):
    if type(value) is tuple and len(value) == 2 and value[0] == '__tags__':
        return dict(value[1])
    return value


def _mark(mark, buffer, checked):
    if mark is None:
        return None
    if type(mark) is not yaml.error.Mark:
        raise TypeError('unsupported YAML mark or buffer')
    # Reader marks share one source buffer. Compare its content once, then
    # require identity; O(source bytes * event count) would defeat the cache.
    if not checked:
        if mark.buffer != buffer:
            raise TypeError('unsupported YAML mark buffer content')
        checked.append(mark.buffer)
    elif mark.buffer is not checked[0]:
        raise TypeError('YAML mark buffer identity changed within one parse')
    values = (mark.name, mark.index, mark.line, mark.column, mark.pointer)
    if type(values[0]) is not str or any(type(value) is not int for value in values[1:]):
        raise TypeError('unsupported YAML mark fields')
    return values


def _fresh_mark(mark, buffer):
    if mark is None:
        return None
    name, index, line, column, pointer = mark
    return yaml.error.Mark(name, index, line, column, buffer, pointer)


def _fresh_events(records, buffer):
    result = deque()
    for name, start, end, fields in records:
        cls = getattr(yaml.events, name)
        result.append(cls(start_mark=_fresh_mark(start, buffer),
            end_mark=_fresh_mark(end, buffer), **{key: _thaw(value) for key, value in fields}))
    return result


@dataclass(frozen=True)
class _Candidate:
    raw: bytes
    token: tuple
    records: tuple
    payload_bytes: int
    event_count: int


_CACHE = OrderedDict()
_LOCK = Lock()
_BYTES = 0
_EVENTS = 0
_COUNTERS = {'documents': 0, 'parses': 0, 'hits': 0, 'fallbacks': 0, 'stored': 0}


def counters():
    with _LOCK:
        return {**_COUNTERS, 'entries': len(_CACHE), 'payload_bytes': _BYTES,
                'events': _EVENTS, 'binding_supported': _BOUND is not None,
                'binding_error': _BOUND_ERROR,
                'payload_accounting_scope': 'UTF-8 plus 128/event estimate, not serialized bytes or measured RSS'}


def _fallback(text):
    from . import audit_omissions as omissions
    with _LOCK:
        _COUNTERS['fallbacks'] += 1
    return omissions._load_yaml(text), None


def load_native(text, *, limit):
    """Return freshly composed data and uncommitted immutable parse evidence."""
    from . import audit_omissions as omissions
    with _LOCK:
        _COUNTERS['documents'] += 1
    token = _token(limit)
    if token is None or type(text) is not str:
        return _fallback(text)
    try:
        raw = text.encode('utf-8')
    except UnicodeError:
        return _fallback(text)
    if not raw or len(raw) > min(limit, MAX_INPUT_BYTES):
        return _fallback(text)
    key = raw, token
    with _LOCK:
        candidate = _CACHE.get(key)
        if candidate is not None:
            _CACHE.move_to_end(key)
            _COUNTERS['hits'] += 1
    buffer = text + '\0'
    if candidate is None:
        records, depth, chars, checked_buffer = [], 0, 0, []
        payload_bytes = len(raw) * 2 + 1  # exact input plus shared mark text
        parser = yaml.parse(text, Loader=yaml.SafeLoader)
        reusable = False
        with _LOCK:
            _COUNTERS['parses'] += 1
        try:
            for event in parser:
                name = type(event).__name__
                if name not in _EVENT_FIELDS or type(event) is not getattr(yaml.events, name):
                    break
                if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                    depth += 1
                elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                    depth -= 1
                if depth > omissions.MAX_DEPTH:
                    break
                fields = tuple((key, _freeze(getattr(event, key))) for key in _EVENT_FIELDS[name])
                # Preserve M7's scalar/anchor/tag/directive retention budget.
                strings = [getattr(event, key, None) for key in ('anchor', 'tag', 'value')]
                for key, value in (getattr(event, 'tags', None) or {}).items():
                    strings.extend((key, value))
                chars += sum(len(value) for value in strings if isinstance(value, str))
                payload_bytes += 128 + sum(len(value.encode('utf-8')) for value in strings if isinstance(value, str))
                if (len(records) >= min(MAX_EVENTS_PER_ENTRY, omissions._YAML_REPLAY_MAX_EVENTS)
                        or chars > MAX_EVENT_CHARS
                        or payload_bytes > min(MAX_PAYLOAD_BYTES, omissions._YAML_REPLAY_MAX_TEXT_BYTES)):
                    break
                records.append((name, _mark(event.start_mark, buffer, checked_buffer),
                                _mark(event.end_mark, buffer, checked_buffer), fields))
            else:
                reusable = bool(records and records[-1][0] == 'StreamEndEvent')
        except (yaml.YAMLError, UnicodeError, TypeError, AttributeError, ValueError):
            pass
        finally:
            parser.close()
        if not reusable or _token(limit) != token:
            return _fallback(text)
        candidate = _Candidate(raw, token, tuple(records), payload_bytes, len(records))
    # Constructor/resolver state is not cached; compose from fresh events on
    # every call, then let the original _read/_mapping validate the result.
    events = _fresh_events(candidate.records, buffer)
    loader = omissions._EventReplayLoader(text, events)
    try:
        value = loader.get_single_data()
    finally:
        loader.dispose()
        events.clear()
    return value, candidate


def retain_native(candidate, *, limit):
    """Called only after original JSON/node/depth and mapping-shape validation."""
    global _BYTES, _EVENTS
    if type(candidate) is not _Candidate or _token(limit) != candidate.token:
        return
    if (candidate.payload_bytes > MAX_PAYLOAD_BYTES
            or candidate.event_count > min(MAX_EVENTS_PER_ENTRY, MAX_TOTAL_EVENTS)):
        return
    key = candidate.raw, candidate.token
    with _LOCK:
        if key in _CACHE:
            return
        while _CACHE and (len(_CACHE) >= MAX_ENTRIES
                or _BYTES + candidate.payload_bytes > MAX_PAYLOAD_BYTES
                or _EVENTS + candidate.event_count > MAX_TOTAL_EVENTS):
            _, old = _CACHE.popitem(last=False)
            _BYTES -= old.payload_bytes
            _EVENTS -= old.event_count
        if MAX_ENTRIES <= 0:
            return
        _CACHE[key] = candidate
        _BYTES += candidate.payload_bytes
        _EVENTS += candidate.event_count
        _COUNTERS['stored'] += 1
