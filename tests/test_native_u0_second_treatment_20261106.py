"""U0 T2 source-bound initialization/cold-warm refusal probes, 2026-11-06.

Archive exact T1 source into external pytest storage, apply only the pure T2
transform, and run each case through ordinary package imports under inherited
OS network denial. No recorder, native executable, provider or existing writes.
"""
from __future__ import annotations
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile
import types

TOOL = Path(__file__).resolve().parents[1]
FROZEN = TOOL.parent / 'codex-native-u0-pair-treatment-20261106'
HELPER = TOOL / 'scripts/adhoc/native_u0_second_treatment_20261106.py'


def load_helper():
    spec = importlib.util.spec_from_file_location('t2_applier', HELPER)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def child(case, tree):
    original_read = Path.read_bytes
    if case == 'callback-source-unreadable':
        def selective_read(path):
            if str(path).endswith('/linkml/utils/rawloader.py'):
                raise PermissionError('synthetic unavailable callback source')
            return original_read(path)
        Path.read_bytes = selective_read
    if case == 'preloaded':
        import linkml.validator
    import yaml
    if case == 'foreign-preload':
        from linkml_runtime.utils import yamlutils
        yaml.error.Mark = type('ForeignMark', (yaml.reader.Mark,), {})
    from data_sheets_schema import native_shared_capture
    from data_sheets_schema import native_catalog_reuse as guard
    from data_sheets_schema import native_catalog_initialization as initialization
    from data_sheets_schema import native_schema_event_reuse as t1
    from data_sheets_schema import native_shared_receipts as receipts
    from data_sheets_schema import native_shared_contract as contract
    from data_sheets_schema import audit_omissions as omissions
    from data_sheets_schema import schema_snapshot as snapshots
    from linkml_runtime.linkml_model import meta
    from linkml_runtime.utils import yamlutils
    Path.read_bytes = original_read
    closure = runpy.run_path(str(tree / 'scripts/adhoc/native_u0_source_closure_20261106.py'))
    closure_start = closure['assert_source_closure'](tree)
    observations = {'case': case}
    raw = b'id: https://example.org/probe\nname: probe\nclasses: {Dataset: {}}\n'

    def selected(content):
        path = '/synthetic/full.yaml'
        artifact = contract.CapturedArtifact(contract.ArtifactPin('full_schema:0', path,
            len(content), contract.sha(content)), content)
        roles = (('probe', 'full_schema:0'),)
        capture = contract.SchemaClosureCapture(contract.schema_closure_sha((artifact,), roles),
            roles, 'full', 'Dataset', 'probe', (artifact,))
        selection = types.SimpleNamespace(schemas=(capture,),
            document=lambda: {'inputs': {'full_schema': {'root': path}}}, bounds=lambda: {})
        snapshot = snapshots.SchemaSnapshot((('probe', Path(path), content),), ('synthetic',))
        return selection, snapshot

    def refusal(fn):
        try:
            return ('value', fn())
        except Exception as exc:
            rows = []
            while exc is not None:
                rows.append((type(exc).__name__, str(exc)))
                exc = exc.__cause__
            return ('error', rows)

    def mutated(owner, name, value):
        sentinel = object(); old = vars(owner).get(name, sentinel)
        if type(owner) is types.FunctionType and name in ('__code__', '__defaults__', '__kwdefaults__'):
            old = getattr(owner, name)
        setattr(owner, name, value)
        try:
            assert guard.runtime_token() is None, (case, str(owner), name)
        finally:
            if old is sentinel:
                delattr(owner, name)
            else:
                setattr(owner, name, old)

    if case in ('foreign-preload', 'callback-source-unreadable'):
        assert guard.runtime_token() is None
        assert omissions._mapping(raw, 'native schema')
        if case == 'callback-source-unreadable':
            assert 'PermissionError' in initialization.INITIALIZATION_ERROR
    else:
        original_marker = guard.runtime_token()
        assert original_marker is not None, initialization.INITIALIZATION_ERROR
        selection, snapshot = selected(raw)
        context = receipts._ReceiptCatalogContext()
        first = context.schema_data(selection, snapshot)
        old_entry = context._entry
        assert context._entry_marker is original_marker
        assert context.schema_data(selection, snapshot) == first
        assert context._entry is old_entry

        if case == 'transition':
            assert t1._token(8_000_000) is not None
            native = lambda: omissions._mapping(raw, 'native schema', _native_events=True)
            native(); native()
            assert t1.counters()['hits'] == 1
            import linkml.validator
            marker = guard.runtime_token()
            assert marker is not None and marker is not original_marker
            assert context._typed_catalog(selection, Path('/synthetic/full.yaml'), snapshot) is None
            second = context.schema_data(selection, snapshot)
            assert second == first and context._entry is not old_entry
            assert context._entry_marker is marker and context._typed_marker is marker
            new_entry = context._entry
            assert context.schema_data(selection, snapshot) == second and context._entry is new_entry
            assert context._typed_catalog(selection, Path('/synthetic/full.yaml'), snapshot) == second[1]
            # T2 deliberately leaves T1's two late parser fallbacks unchanged.
            before = t1.counters()['fallbacks']; native()
            assert t1.counters()['fallbacks'] == before + 1
            observations['t1_counters'] = t1.counters()
            # Removing authority or changing the captured bytes remains a miss/refusal.
            bad = snapshots.SchemaSnapshot((('probe', Path('/synthetic/other.yaml'), raw),), ('synthetic',))
            assert refusal(lambda: context.schema_data(selection, bad))[0] == 'error'
            altered_selection, altered_snapshot = selected(raw.replace(b'probe\n', b'changed\n'))
            assert context._typed_catalog(altered_selection, Path('/synthetic/full.yaml'), altered_snapshot) is None
            observations['distinct_markers_and_catalog_rebuild'] = True

        elif case in ('mutations', 'preloaded'):
            if case != 'preloaded':
                import linkml.validator
            marker = guard.runtime_token(); assert marker is not None
            loader = sys.modules['linkml.utils.rawloader']
            for owner, name, value in (
                (yaml.error, 'Mark', lambda *a: None),
                (yaml.reader, 'Mark', lambda *a: None),
                (yaml, 'Mark', lambda *a: None),
                (yamlutils, 'YAMLMark', lambda *a: None),
                (yamlutils.YAMLMark, '__str__', lambda *a: 'foreign'),
                (yaml.reader.Mark, '__init__', lambda *a: None),
                (meta.SchemaDefinition, 'MissingRequiredField', lambda *a: None),
                (yamlutils.YAMLRoot, 'MissingRequiredField', lambda *a: None),
                (loader, 'isinstance', lambda *a: True), (loader, 'type', lambda *a: str),
                (loader, 'SchemaDefinition', object), (loader, 'YAMLRoot', object),
                (loader, 'mrf', lambda *a: None), (loader, '__name__', 'foreign'),
                (loader, '__builtins__', dict(vars(__import__('builtins')))),
                (yamlutils, 'ValueError', RuntimeError),
                (loader.mrf, '__defaults__', (None,)),
                (loader.mrf, '__code__', (lambda *a: None).__code__),
            ):
                mutated(owner, name, value)
                assert guard.runtime_token() is marker
            observations['mutations_refused'] = 18
            # An unsupported callback cannot authorize even owner-local reuse.
            prior = meta.SchemaDefinition.MissingRequiredField
            meta.SchemaDefinition.MissingRequiredField = lambda *a: None
            try:
                context.schema_data(selection, snapshot)
                entry = context._entry
                assert context._entry_marker is None
                context.schema_data(selection, snapshot)
                assert context._entry is not entry and context._typed_marker is None
            finally:
                meta.SchemaDefinition.MissingRequiredField = prior

        elif case == 'refusals':
            for initialized in (False, True):
                if initialized:
                    import linkml.validator
                for invalid in (b'name: probe\nclasses: {Dataset: {}}\n',
                                b'id: https://example.org/probe\nclasses: {Dataset: {}}\n',
                                raw + b'name: duplicate\n', raw + b'imports: [absent]\n'):
                    sel, snap = selected(invalid)
                    fresh = lambda: omissions._schema_with_root_bases(Path('/synthetic/full.yaml'), schema_snapshot=snap)
                    ctx = receipts._ReceiptCatalogContext()
                    expected = refusal(fresh)
                    assert refusal(lambda: ctx.schema_data(sel, snap)) == expected
                    assert refusal(lambda: ctx.schema_data(sel, snap)) == expected
                    if expected[0] == 'error':
                        assert ctx._entry is None
            # No filesystem/environment access is needed by hot eligibility.
            import builtins
            old_open, old_read = builtins.open, Path.read_bytes
            def denied(*a, **k):
                raise AssertionError('runtime guard attempted ambient IO')
            builtins.open, Path.read_bytes = denied, denied
            try:
                assert guard.runtime_token() is not None
            finally:
                builtins.open, Path.read_bytes = old_open, old_read
            observations['refusal_parity_and_no_runtime_io'] = True
        else:
            raise AssertionError('unknown case')
    closure_end = closure['assert_source_closure'](tree)
    observations.update(source_closure_start=closure_start, source_closure_end=closure_end,
                        callback_source_sha256=initialization.SOURCE_SHA256)
    print(json.dumps(observations, sort_keys=True))


if __name__ == '__main__':
    child(sys.argv[1], Path(sys.argv[2]).resolve())
else:
    import pytest

    @pytest.fixture(scope='module')
    def source_tree(tmp_path_factory):
        helper = load_helper()
        root = tmp_path_factory.mktemp('t2-source').resolve()
        archive = helper.git(FROZEN, 'archive', helper.BASE, 'src/data_sheets_schema',
                             'scripts/adhoc/native_u0_source_closure_20261106.py')
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(root, filter='data')
        changes = helper.build_changes((root / helper.GUARD).read_bytes(), (root / helper.RECEIPTS).read_bytes())
        for name, raw in changes.items():
            (root / name).write_bytes(raw)
        for name, raw in changes.items():
            compile(raw, str(root / name), 'exec')
        return root

    @pytest.mark.parametrize('case', ['transition', 'mutations', 'preloaded', 'foreign-preload',
                                    'callback-source-unreadable', 'refusals'])
    def test_source_bound_catalog_initialization(case, source_tree, tmp_path):
        env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(tmp_path),
            'LANG': 'C', 'LC_ALL': 'C', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONPATH': str(source_tree / 'src'), 'PIP_NO_INDEX': '1',
            'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}
        result = subprocess.run([sys.executable, '-P', '-B', str(Path(__file__).resolve()), case,
            str(source_tree)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
        (tmp_path / 'child-result.json').write_text(json.dumps({'case': case, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
        assert result.returncode == 0, result.stdout + result.stderr
        data = json.loads(result.stdout.splitlines()[-1])
        assert data['source_closure_end']['project_finder_first']
        assert data['case'] == case

    def test_second_treatment_exact_scope_and_repeated_patch_refusal():
        helper = load_helper()
        guard = helper.git(FROZEN, 'show', helper.BASE + ':' + helper.GUARD)
        receipts = helper.git(FROZEN, 'show', helper.BASE + ':' + helper.RECEIPTS)
        changes = helper.build_changes(guard, receipts)
        assert sorted(changes) == sorted((helper.GUARD, helper.RECEIPTS, helper.ADDED))
        with pytest.raises(ValueError):
            helper.build_changes(changes[helper.GUARD], changes[helper.RECEIPTS])
