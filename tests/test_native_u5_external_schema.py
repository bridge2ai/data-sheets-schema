"""U5 named 3.2.0 input measurements; no installed-schema or live acceptance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from data_sheets_schema import api_runner as api
from data_sheets_schema import audit_omissions as omissions
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import native_shared_selection as selection
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_native_shared_selection import declaration, pin, save

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT.parent / 'scratch-native-u5-prep'
SCHEMA_COMMIT = '5e382f0c423fa8b0a331340adcdfac5a328bd6b3'
BASE_COMMIT = 'd258611c5381bd7cf973817ebd2b6a04f65818b3'


def checked_input(label, expected_commit):
    directory = SCRATCH / label
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    assert manifest['commit'] == expected_commit
    tree = directory / 'tree'
    assert manifest['tree'] == str(tree)
    for name, identity in manifest['files'].items():
        raw = (tree / name).read_bytes()
        assert len(raw) == identity['bytes']
        assert hashlib.sha256(raw).hexdigest() == identity['sha256']
    return tree, manifest


def test_external_320_capture_rebuild_and_cold_warm_catalog(declaration, monkeypatch, tmp_path):
    tree, manifest = checked_input('schema-' + SCHEMA_COMMIT[:9], SCHEMA_COMMIT)
    folder = tree / 'src/data_sheets_schema/schema'
    for kind, constant, filename in (
            ('full', 'FULL_SCHEMA_PATH', 'data_sheets_schema.yaml'),
            ('core', 'CORE_SCHEMA_PATH', 'data_sheets_schema_core.yaml')):
        path = folder / filename
        monkeypatch.setattr(api, constant, path)
        snapshot = capture_schema(path, strict=True)
        declaration['inputs'][kind + '_schema']['root'] = str(path)
        declaration['inputs'][kind + '_schema']['sources'] = [
            {'name': str(name), **pin(p, raw)} for name, p, raw in snapshot.sources]
    save(declaration)
    captured = selection.capture(declaration['registration_path'])
    snapshot = receipts.schema_snapshot(captured)
    expected = omissions._json(omissions._schema(snapshot.sources[0][1], schema_snapshot=snapshot, logical_paths=True))
    context = receipts._ReceiptCatalogContext()
    cold = context.schema_data(captured, snapshot)
    entry = context._entry
    warm = context.schema_data(captured, snapshot)
    assert context._entry is entry and entry is not None
    assert cold[0] == warm[0]
    assert omissions._json(cold[1]) == omissions._json(warm[1]) == expected
    assert 'version: 3.2.0' in (folder / 'data_sheets_schema.yaml').read_text()
    # Modify only the synthetic live bundle; the external schema export remains
    # byte-identical and no protected input is edited.
    Path(declaration['inputs']['bundle']['path']).write_text('Live bundle changed after capture.\n')
    rebuilt = selection.rebuild(captured.registration, captured.authority, captured.schemas, captured.receipt_policy)
    assert rebuilt == captured
    checked_input('schema-' + SCHEMA_COMMIT[:9], SCHEMA_COMMIT)
    witness = {'schema_commit': SCHEMA_COMMIT, 'schema_files': manifest['files'],
               'catalog_sha256': hashlib.sha256(expected.encode()).hexdigest(),
               'catalog_bytes': len(expected.encode()), 'declared_bases': list(cold[0]),
               'same_capture_replay': True, 'cold_warm_equal': True,
               'retained_catalog': entry is context._entry,
               'scope': 'named external schema input, not installed-schema acceptance'}
    (tmp_path / 'external-schema-evidence.json').write_text(json.dumps(witness, indent=2, sort_keys=True) + '\n')


def test_same_external_320_api_instruction_before_after(tmp_path):
    baseline, _ = checked_input('baseline-' + BASE_COMMIT[:9], BASE_COMMIT)
    schema, _ = checked_input('schema-' + SCHEMA_COMMIT[:9], SCHEMA_COMMIT)
    folder = schema / 'src/data_sheets_schema/schema'
    helper = ROOT / 'scripts/adhoc/native_u5_api_render_20261108.py'
    # Environment was stripped before this pytest process. Pass only explicit
    # software-peer inputs; the enclosing OS sandbox still denies networking.
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'VIRTUAL_ENV') if k in os.environ}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    for label, source in (('before', baseline), ('after', ROOT)):
        out = tmp_path / label
        command = [sys.executable, '-P', '-B', str(helper), '--source-root', str(source),
                   '--schema-dir', str(folder), '--input-dir', str(tmp_path / 'inputs'), '--out', str(out)]
        result = subprocess.run(command, cwd=source, env=env, capture_output=True, timeout=600)
        (tmp_path / (label + '.stdout')).write_bytes(result.stdout)
        (tmp_path / (label + '.stderr')).write_bytes(result.stderr)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        assert (out / 'instruction.txt').stat().st_size > 0
        witness = json.loads((out / 'witness.json').read_bytes())
        assert witness['source_root'] == str(source)
        assert witness['schema_directory'] == str(folder)
    assert (tmp_path / 'before/instruction.txt').read_bytes() == (tmp_path / 'after/instruction.txt').read_bytes()
    checked_input('baseline-' + BASE_COMMIT[:9], BASE_COMMIT)
    checked_input('schema-' + SCHEMA_COMMIT[:9], SCHEMA_COMMIT)
