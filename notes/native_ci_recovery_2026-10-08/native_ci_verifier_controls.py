"""Synthetic metadata controls for external verifier #4679; no repo imports."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import zipfile


BASE = Path(__file__).resolve().parent
DRIVER = BASE / 'verify_native_ci_artifact.py'
spec = importlib.util.spec_from_file_location('external_artifact_verifier', DRIVER)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def make_archive(directory, bad):
    expected = {'run_id': 1, 'pr_head': 'a' * 40, 'merge_sha': 'b' * 40,
                'tree_sha': 'c' * 40,
                'files': {name: verifier.pin(b'invented source declaration') for name in verifier.SOURCE_NAMES}}
    source = {'head': expected['merge_sha'], 'tree': expected['tree_sha'],
              'files': expected['files'], 'scope': 'Invented metadata-only control, not actual source provenance.'}
    archive_path = directory / 'synthetic.zip'
    with zipfile.ZipFile(archive_path, 'x') as zipped:
        zipped.writestr('selection.json', encoded({'format': 'native_ci_selection_v1',
            'cases': verifier.CASES, 'source': source}))
        for index, node in enumerate(verifier.CASES):
            raw = bad if index == 0 else encoded({'state': 'failed', 'runtime_gates_passed': False,
                'gates': {'live_attribution': {'result': {'phase_history': {'pending_tool_ids': []}}}},
                'captured_files': {}})
            target = hashlib.sha256(node.encode()).hexdigest()
            inventory = {'.': {'type': 'directory', 'mode': 0o710},
                         'actual-result.json': {'type': 'file', 'mode': 0o640, **verifier.pin(raw)}}
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w:gz', dereference=False) as archive:
                root = tarfile.TarInfo('case'); root.type = tarfile.DIRTYPE; root.mode = 0o710
                archive.addfile(root)
                member = tarfile.TarInfo('case/actual-result.json'); member.mode = 0o640; member.size = len(raw)
                archive.addfile(member, io.BytesIO(raw))
            tar_bytes = buffer.getvalue()
            manifest = {'format': 'native_ci_synthetic_case_v1', 'node_id': node, 'worker': 'gw0',
                'source': source, 'declared_limits': verifier.LIMITS, 'status': 'retained',
                'original_case': '/invented/metadata-only/' + verifier.CASES[node],
                'test_outcome': {'call': {'outcome': 'failed', 'duration_seconds': 0.25},
                                 'teardown': {'outcome': 'passed', 'duration_seconds': 0.01}},
                'before': inventory, 'archived': inventory, 'after': inventory, 'unchanged': True,
                'archive': verifier.pin(tar_bytes), 'scientific_acceptance': 'not_assessed',
                'case_completeness': 'not_assessed',
                'availability': {name: inventory.get(name, {}).get('type', 'absent') for name in verifier.KNOWN}}
            zipped.writestr('gw0/' + target + '/manifest.json', encoded(manifest))
            zipped.writestr('gw0/' + target + '/case.tar.gz', tar_bytes)
    archive_pin = verifier.file_pin(archive_path)
    metadata = {'id': 1, 'name': 'native-synthetic-cases-' + expected['merge_sha'] + '-1-1-shard1',
                'workflow_run': {'id': 1, 'head_sha': expected['pr_head']},
                'size_in_bytes': archive_pin['bytes'], 'digest': 'sha256:' + archive_pin['sha256']}
    (directory / 'metadata.json').write_bytes(encoded(metadata))
    (directory / 'expected.json').write_bytes(encoded(expected))
    return archive_path, metadata, expected


def main():
    output = Path(tempfile.mkdtemp(prefix='native-ci-verifier-controls-', dir=BASE))
    controls = []
    fixtures = [('malformed', b'not JSON'), ('truncated', b'{"state":'),
                ('null_result', b'{"gates":{"live_attribution":{"result":null}}}')]
    for label, bad in fixtures:
        selected = output / label; selected.mkdir()
        archive, metadata, expected = make_archive(selected, bad)
        result = verifier.verify(archive, metadata, expected)
        assert len(result['cases']) == 2
        first = next(row for row in result['cases'] if row['node_id'] == next(iter(verifier.CASES)))
        other = next(row for row in result['cases'] if row is not first)
        assert first['capture_status'] == 'retained'
        assert first['matches_archived_inventory'] and first['before_archived_after_equal'] and first['archive_pin_matches']
        assert first['diagnostic']['status'] == 'diagnostic_error'
        assert first['diagnostic']['native_completion'] == 'not_inferred'
        assert other['diagnostic']['result_available'] is True
        (selected / 'verified.json').write_bytes(encoded(result))
        controls.append({'name': label, 'passed': True, 'archive': verifier.file_pin(archive)})
    exact = output / 'exact-cap.json'; exact.write_bytes(b'{}' + b' ' * (verifier.MAX_METADATA_BYTES - 2))
    assert verifier.read_json_file(exact) == {}
    controls.append({'name': 'metadata_exact_32MiB_accepted', 'passed': True})
    overflow = output / 'over-cap.json'; overflow.write_bytes(exact.read_bytes() + b' ')
    try:
        verifier.read_json_file(overflow)
    except ValueError as exc:
        assert 'local metadata bound exceeded' in str(exc)
    else:
        raise AssertionError('32MiB+1 accepted')
    controls.append({'name': 'metadata_32MiB_plus_one_refused', 'passed': True})
    exponent = output / 'overflow-exponent.json'; exponent.write_bytes(b'{"duration_seconds":1e999}')
    try:
        verifier.read_json_file(exponent)
    except ValueError as exc:
        assert 'non-finite JSON numeric exponent' in str(exc)
    else:
        raise AssertionError('1e999 accepted')
    controls.append({'name': 'exponent_overflow_refused', 'passed': True})
    assert verifier.strict_json(b'{"duration_seconds":1.25}') == {'duration_seconds': 1.25}
    controls.append({'name': 'finite_duration_preserved', 'passed': True})
    report = {'format': 'external_verifier_synthetic_controls_v1', 'issue': 4679,
              'driver': {'name': DRIVER.name, **verifier.pin(DRIVER.read_bytes())},
              'control_source': verifier.pin(Path(__file__).read_bytes()), 'controls': controls,
              'scope': 'Invented metadata archives only. No native execution, repository imports, filesystem extraction or replay.'}
    (output / 'controls.json').write_bytes(encoded(report))
    print(output.name, 'controls_passed', len(controls))


if __name__ == '__main__':
    main()
