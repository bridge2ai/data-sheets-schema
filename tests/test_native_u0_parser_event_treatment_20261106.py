"""Diagnostic native parser treatment parity, bounds and source seam; 2026-11-06.

Every behavioral case runs in a fresh -S -P -B subprocess with a package path
limited to a new patched overlay and the preserved frozen-current snapshot.
Changed source preimages come from Git objects; imported frozen project modules
are compared with those objects before a case is reported as passing.
No recorder, provider, native executable or acceptance trial is launched.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types


TOOL = Path(__file__).resolve().parents[1]
HELPER = TOOL / 'scripts/adhoc/native_u0_parser_event_treatment_20261106.py'
FROZEN = TOOL.parent / 'native-u0-20261106/frozen-current'


def load_helper():
    spec = importlib.util.spec_from_file_location('u0_parser_treatment_helper', HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def chain(function):
    try:
        return ('value', function())
    except Exception as error:
        rows = []
        while error is not None:
            rows.append((type(error).__module__, type(error).__qualname__, str(error)))
            error = error.__cause__
        return 'error', rows


def child(case):
    assert sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
    assert site.is_dir() and (venv / 'pyvenv.cfg').is_file()
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    helper = load_helper()
    assert helper.git(FROZEN, 'rev-parse', 'HEAD').decode().strip() == helper.BASE
    original = {path: helper.git(FROZEN, 'show', helper.BASE + ':' + path)
                for path in (helper.AUDIT, helper.SNAPSHOT)}
    changes = helper.build_changes(original[helper.AUDIT], original[helper.SNAPSHOT])
    with tempfile.TemporaryDirectory(prefix='u0-event-unit-') as temporary:
        overlay = Path(temporary).resolve()
        package_path = overlay / 'src/data_sheets_schema'
        package_path.mkdir(parents=True)
        for path, raw in changes.items():
            (overlay / path).write_bytes(raw)
        package = types.ModuleType('data_sheets_schema')
        package.__path__ = [str(package_path), str(FROZEN / 'src/data_sheets_schema')]
        package.__spec__ = importlib.util.spec_from_loader('data_sheets_schema', loader=None,
                                                       is_package=True)
        package.__spec__.submodule_search_locations = package.__path__
        sys.modules['data_sheets_schema'] = package
        from data_sheets_schema import audit_omissions as omissions
        from data_sheets_schema import schema_snapshot as snapshots
        import yaml
        ordinary = lambda raw: omissions._mapping(raw, 'native schema', limit=8_000_000)
        native = lambda raw: omissions._mapping(raw, 'native schema', limit=8_000_000,
                                                _native_events=True)
        original_parse = yaml.parse
        if case == 'preexisting-parser':
            yaml.parse = lambda *args, **kwargs: original_parse(*args, **kwargs)
        if case == 'preexisting-loader':
            class ForeignLoader(yaml.SafeLoader):
                pass
            yaml.SafeLoader = ForeignLoader
        from data_sheets_schema import native_schema_event_reuse as reuse
        schema = (b'id: https://example.org/native\nname: native\n'
                  b'prefixes: {ex: https://example.org/}\nclasses: {Dataset: {}}\n')

        if case == 'reuse-and-token':
            from data_sheets_schema import native_catalog_reuse
            assert native_catalog_reuse.runtime_token() is not None
            assert reuse.counters()['binding_supported'], reuse.counters()
            calls, validations = [], []
            mapping, validate = omissions._mapping, omissions._validate_json
            def observed(raw, label, **kwargs):
                calls.append((raw, label, kwargs))
                return mapping(raw, label, **kwargs)
            def checked(value, **kwargs):
                validations.append(kwargs)
                return validate(value, **kwargs)
            omissions._mapping, omissions._validate_json = observed, checked
            try:
                path = Path('/synthetic/native.yaml')
                first = snapshots._capture_native_schema(path, ((path, schema),), member_bytes=8_000_000)
                second = snapshots._capture_native_schema(path, ((path, schema),), member_bytes=8_000_000)
            finally:
                omissions._mapping, omissions._validate_json = mapping, validate
            assert first == second
            assert len(calls) == len(validations) == 2
            assert all(row[2] == {'limit': 8_000_000, '_native_events': True} for row in calls)
            assert reuse.counters()['parses'] == 1 and reuse.counters()['hits'] == 1
            assert native_catalog_reuse.runtime_token() is not None
            raw = b'x: &same [one, two]\ny: *same\nday: 2025-01-02\n'
            first_doc = native(raw)
            assert first_doc['x'] is first_doc['y']
            first_doc['x'].append('mutated')
            second_doc = native(raw)
            assert second_doc['x'] == ['one', 'two'] and second_doc['x'] is second_doc['y']
            assert native(raw) == ordinary(raw)

        elif case == 'refusal-parity':
            native(schema)  # Populate a valid warm entry before hostile inputs.
            fixtures = [b'a: 1\na: 2\n', b'x: &x {a: *x}\n', b'1: value\n',
                b'x: &base {a: 1}\ny: {<<: *base}\n', b'- list\n', b'x: .inf\n',
                b'x: [unfinished', b'x: !foreign value\n', b'x: *missing\n',
                b'x: &a value\ny: &a other\n', b'x: ' + b'[' * 70 + b'0' + b']' * 70 + b'\n',
                b'x: "\\uD800"\n', b'\xff', b'']
            for raw in fixtures:
                before = reuse.counters()['stored']
                expected = chain(lambda: ordinary(raw))
                assert chain(lambda: native(raw)) == expected, raw
                assert chain(lambda: native(raw)) == expected, raw
                if expected[0] == 'error':
                    assert reuse.counters()['stored'] == before
            # Actual logical traversal still rejects missing imports after
            # strict YAML construction; the event cache cannot admit a closure.
            path = Path('/synthetic/native.yaml')
            raw = schema + b'imports: [absent]\n'
            for _ in range(2):
                result = chain(lambda: snapshots._capture_native_schema(
                    path, ((path, raw),), member_bytes=8_000_000))
                assert result[0] == 'error' and 'outside the complete captured closure' in str(result)

        elif case == 'limits-and-bindings':
            assert native(schema) == ordinary(schema)
            assert native(schema) == ordinary(schema)
            for attribute, value in [('MAX_DEPTH', 1), ('MAX_NODES', 1),
                    ('_YAML_REPLAY_MAX_EVENTS', 1), ('_YAML_REPLAY_MAX_TEXT_BYTES', 1)]:
                prior = getattr(omissions, attribute)
                hits = reuse.counters()['hits']
                setattr(omissions, attribute, value)
                try:
                    assert chain(lambda: native(schema)) == chain(lambda: ordinary(schema))
                    assert reuse.counters()['hits'] == hits
                finally:
                    setattr(omissions, attribute, prior)
            hits = reuse.counters()['hits']
            yaml.parse = lambda *args, **kwargs: original_parse(*args, **kwargs)
            try:
                assert native(schema) == ordinary(schema)
                assert reuse.counters()['hits'] == hits
            finally:
                yaml.parse = original_parse
            old_loader = yaml.SafeLoader
            class ForeignLoader(old_loader):
                pass
            yaml.SafeLoader = ForeignLoader
            try:
                assert native(schema) == ordinary(schema)
                assert reuse.counters()['hits'] == hits
            finally:
                yaml.SafeLoader = old_loader
            # A changed exact-byte key derives independently; a stricter byte
            # limit still rejects before a cached parser stream is considered.
            modified = schema.replace(b'name: native', b'name: changed')
            before = reuse.counters()['parses']
            assert native(modified) == ordinary(modified)
            assert reuse.counters()['parses'] == before + 1
            assert chain(lambda: omissions._mapping(schema, 'native schema', limit=1,
                _native_events=True)) == chain(lambda: omissions._mapping(schema, 'native schema', limit=1))

        elif case == 'bounds-and-shape':
            for index in range(12):
                raw = schema.replace(b'name: native', f'name: native{index}'.encode())
                assert native(raw) == ordinary(raw)
                counts = reuse.counters()
                assert counts['entries'] <= reuse.MAX_ENTRIES
                assert counts['events'] <= reuse.MAX_TOTAL_EVENTS
                assert counts['payload_bytes'] <= reuse.MAX_PAYLOAD_BYTES
            previous = reuse.MAX_EVENTS_PER_ENTRY
            reuse.MAX_EVENTS_PER_ENTRY = 1
            try:
                assert native(schema) == ordinary(schema)
                assert reuse.counters()['fallbacks'] > 0
            finally:
                reuse.MAX_EVENTS_PER_ENTRY = previous
            for candidate in reuse._CACHE.values():
                assert type(candidate.raw) is bytes and type(candidate.records) is tuple
                def immutable(value):
                    return value is None or type(value) in (str, int, bool) or (
                        type(value) is tuple and all(immutable(item) for item in value))
                assert immutable(candidate.records)

        elif case in ('preexisting-parser', 'preexisting-loader'):
            assert reuse.counters()['binding_supported'] is False
            assert native(schema) == ordinary(schema)
            assert native(schema) == ordinary(schema)
            assert reuse.counters()['hits'] == reuse.counters()['stored'] == 0

        elif case == 'representative-schema':
            raw = helper.git(FROZEN, 'show', helper.BASE + ':src/data_sheets_schema/schema/data_sheets_schema_all.yaml')
            assert len(raw) >= 1_442_513
            first = native(raw)
            second = native(raw)
            assert first == second == ordinary(raw)
            counts = reuse.counters()
            assert counts['stored'] == counts['parses'] == counts['hits'] == 1, counts
            assert counts['fallbacks'] == 0, counts
            assert first is not second
        else:
            raise AssertionError('unknown case: ' + case)

        origins = []
        for name, module in tuple(sys.modules.items()):
            if not name.startswith('data_sheets_schema.') or not getattr(module, '__file__', None):
                continue
            path = Path(module.__file__).resolve()
            if path.is_relative_to(overlay):
                relative = str(path.relative_to(overlay))
                assert path.read_bytes() == changes[relative]
            else:
                assert path.is_relative_to(FROZEN), (name, str(path))
                relative = str(path.relative_to(FROZEN))
                assert path.read_bytes() == helper.git(FROZEN, 'show', helper.BASE + ':' + relative)
            origins.append(name)
        print(json.dumps({'case': case, 'counters': reuse.counters(), 'verified_modules': origins}, sort_keys=True))


if __name__ == '__main__':
    child(sys.argv[1])
else:
    import pytest

    @pytest.mark.parametrize('case', ['reuse-and-token', 'refusal-parity', 'limits-and-bindings',
        'bounds-and-shape', 'preexisting-parser', 'preexisting-loader', 'representative-schema'])
    def test_source_bound_native_parser_treatment(case, tmp_path):
        env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(tmp_path),
               'LANG': 'C', 'LC_ALL': 'C', 'PYTHONUTF8': '1',
               'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1',
               'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0'}
        result = subprocess.run([sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), case],
            env=env, cwd=tmp_path, capture_output=True, text=True, timeout=180)
        (tmp_path / 'child-result.json').write_text(json.dumps({'case': case,
            'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr},
            indent=2, sort_keys=True) + '\n')
        assert result.returncode == 0, result.stdout + result.stderr
        document = json.loads(result.stdout.splitlines()[-1])
        assert document['case'] == case
        assert document['verified_modules']

    def test_patch_changes_only_declared_native_seams_and_module():
        helper = load_helper()
        audit = helper.git(FROZEN, 'show', helper.BASE + ':' + helper.AUDIT)
        snapshot = helper.git(FROZEN, 'show', helper.BASE + ':' + helper.SNAPSHOT)
        changes = helper.build_changes(audit, snapshot)
        assert sorted(changes) == sorted([helper.AUDIT, helper.SNAPSHOT, helper.ADDED])
        assert changes[helper.SNAPSHOT].replace(b', _native_events=True', b'') == snapshot
        assert b'_native_events=None' in changes[helper.AUDIT]
        assert b'_validate_json(value, max_nodes=MAX_NODES, max_depth=MAX_DEPTH)' in changes[helper.AUDIT]
        with pytest.raises(ValueError, match='not unique'):
            helper.build_changes(changes[helper.AUDIT], changes[helper.SNAPSHOT])

    def test_applicator_refuses_existing_or_out_of_scope_tree(tmp_path):
        helper = load_helper()
        with pytest.raises(ValueError, match='new canonical'):
            helper.apply_treatment(tmp_path)
        with pytest.raises(ValueError, match='new canonical'):
            helper.apply_treatment(TOOL)
