"""One fresh process invoking the unchanged packaged CLI and auditing its files."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from serialization_oracle import cli_yaml_bytes, verify_dataset, sidecar_with_cli_dataset, verify_sidecar


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def main():
    config = json.loads((HERE / 'configuration.enabled.json').read_text())
    bound = json.loads((HERE / 'configuration.bound.disabled.json').read_text())
    assert config == dict(bound, enabled=True)
    binding = config['binding']
    source = Path(binding['source'])
    form = sys.argv[1]
    items = [x for x in config['inputs'] if x['form'] == form]
    assert len(items) == 1
    item = items[0]
    output = Path(config['output'])
    input_path = output / 'inputs' / (form + '.json')
    dataset_path = output / form / (form + '_d4d.yaml')
    mapping_path = source / config['mapping_relative']
    schema_path = source / config['schema_relative']
    sidecar_path = dataset_path.with_name(dataset_path.stem + '_route_dispositions.json')
    report_path = dataset_path.with_name(dataset_path.stem + '_report.txt')
    origin_rows = []
    origin_findings = []
    cli_exit = None
    cli_error = None
    verification_error = None
    verified = None
    started = time.monotonic()
    argv = ['fairscape-cli', 'transform', str(input_path), '--mapping', str(mapping_path),
            '--output', str(dataset_path), '--report']
    prefixes = ('data_sheets_schema', 'fairscape_integration', 'transformation', 'validation',
                'src.data_sheets_schema', 'src.fairscape_integration', 'src.transformation', 'src.validation')
    def owned_origins():
        for name, module in sorted(tuple(sys.modules.items())):
            if not any(name == p or name.startswith(p + '.') for p in prefixes):
                continue
            filename = vars(module).get('__file__') if module is not None else None
            if not filename:
                continue
            path = Path(filename).resolve()
            row = {'module': name, **pin(path)}
            origin_rows.append(row)
            if not path.is_relative_to(source):
                origin_findings.append(row)
    try:
        assert Path.cwd() == source
        assert sys.version_info[:3] == tuple(config['python_version'])
        assert os.path.realpath(sys.executable) == os.path.realpath(binding['python']['path'])
        assert pin(binding['python']['path']) == binding['python']
        assert not dataset_path.parent.exists()
        assert all(not any(n == p or n.startswith(p + '.') for p in prefixes) for n in sys.modules)
        sys.path.insert(0, str(source / 'src'))
        sys.dont_write_bytecode = True
        spec = importlib.util.find_spec('fairscape_integration.cli')
        assert Path(spec.origin).resolve() == source / 'src/fairscape_integration/cli.py'
        cli_origin = pin(spec.origin)
        assert {k: cli_origin[k] for k in ('bytes', 'sha256')} == config['cli_expected']
        raw_input = input_path.read_bytes()
        assert len(raw_input) == item['raw_input_pin']['bytes']
        assert hashlib.sha256(raw_input).hexdigest() == item['raw_input_pin']['sha256']
        # Derive the byte oracle BEFORE CLI invocation, from the saved record only.
        export = json.loads(Path(config['export']['path']).read_text())
        selected = [r for r in export['rows'] if (r['arm'], r['input'], r['consumer'], r['order'])
                    == ('candidate', form, 'packaged', 'original')]
        assert len(selected) == 1
        oracle = selected[0]
        assert oracle['preparation_gate']['status'] == 'PREPARED'
        import yaml
        controls = json.loads(Path(config['serialization_controls_receipt']).read_text())
        for row in controls['yaml_pins']:
            assert pin(row['path']) == row
        assert str(Path(yaml.__file__).resolve()) == controls['yaml_module']
        expected_dataset_raw = cli_yaml_bytes(oracle['record'], yaml)
        control_oracle = next(row for row in controls['saved_oracles'] if row['form'] == form)
        assert control_oracle['cli_bytes'] == len(expected_dataset_raw)
        assert control_oracle['cli_sha256'] == hashlib.sha256(expected_dataset_raw).hexdigest()
        # Runtime code is the literal packaged command; no builder/gate replacement.
        original_argv = sys.argv
        sys.argv = argv
        try:
            runpy.run_module('fairscape_integration.cli', run_name='__main__', alter_sys=True)
        except SystemExit as exc:
            cli_exit = 0 if exc.code is None else exc.code if type(exc.code) is int else 1
            if cli_exit:
                cli_error = {'type': 'SystemExit', 'message': str(exc.code)}
        except BaseException as exc:
            cli_exit = 1
            cli_error = {'type': type(exc).__name__, 'message': str(exc)}
        else:
            cli_exit = 0
        finally:
            sys.argv = original_argv
        assert cli_exit == 0, cli_error
        expected_names = {dataset_path.name, sidecar_path.name, report_path.name}
        assert {p.name for p in dataset_path.parent.iterdir()} == expected_names
        assert all(p.is_file() and not p.is_symlink() for p in dataset_path.parent.iterdir())
        assert all(p.stat().st_size <= config['max_output_file_bytes'] for p in dataset_path.parent.iterdir())
        from data_sheets_schema import legacy_publication as publication
        raw = dataset_path.read_bytes()
        record = verify_dataset(raw, expected_dataset_raw, oracle['record'],
                                lambda text: yaml.load(text, Loader=publication._UniqueLoader))
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False,
                               separators=(',', ':')).encode('utf-8')
        assert hashlib.sha256(canonical).hexdigest() == item['record_canonical_json_sha256']
        # A second, explicit saved-byte gate verifies the actual retained file.
        assert publication.prepare_dataset(record, text=raw.decode('utf-8')) == raw
        expected = sidecar_with_cli_dataset(oracle['prepared_sidecar']['document'],
            item['record_oracle'], expected_dataset_raw, dataset_path)
        for key, path in [('schema', schema_path)]:
            actual_pin = pin(path)
            assert all(expected[key][k] == actual_pin[k] for k in ('bytes', 'sha256'))
            expected[key]['path'] = actual_pin['path']
        evidence = expected['evidence']
        assert len(evidence['sources']) == 1
        occurrence = evidence['sources'][0]
        snapshot = occurrence['snapshot']
        assert occurrence['display_name'] == item['raw_input_pin']['path']
        assert snapshot['original_file'] == item['raw_input_pin'] and snapshot['kind'] == 'original_file'
        assert snapshot['json_text'].encode('utf-8') == raw_input
        mapping_pin = pin(mapping_path)
        assert all(evidence['mapping'][k] == mapping_pin[k] for k in ('bytes', 'sha256'))
        evidence['mapping']['path'] = mapping_pin['path']
        occurrence['display_name'] = str(input_path)
        snapshot['original_file']['path'] = str(input_path)
        sidecar_raw = sidecar_path.read_bytes()
        verify_sidecar(sidecar_raw, expected)
        report = report_path.read_bytes().decode('utf-8')
        for text in ('RO-Crate to D4D Transformation Report', 'Input: ' + str(input_path),
                     'Output: ' + str(dataset_path), 'Mapping: ' + str(mapping_path),
                     'Constructed output keys:', 'Construction counts are not source coverage or validation success.',
                     'UNMAPPED RO-CRATE PROPERTIES'):
            assert text in report, text
        # Fixed report declarations derive from the retained full sidecar oracle,
        # never from calling the candidate's supplemental report helper.
        expected_rows = item['supplemental_report_rows']
        heading = 'SUPPLEMENTAL ROUTE ASSERTIONS\n'
        unmapped_heading = 'UNMAPPED RO-CRATE PROPERTIES\n'
        assert report.count(unmapped_heading) == 1
        unmapped = report.split(unmapped_heading, 1)[1]
        if expected_rows:
            assert report.count(heading) == 1
            section = report.split(heading, 1)[1].split(unmapped_heading, 1)[0]
            rows = [line for line in section.splitlines() if line.startswith('  {')]
            assert rows == ['  ' + encoded(row).decode('ascii') for row in expected_rows]
            for text in (
                'Present supplemental root assertions are accounted for in the disposition sidecar, outside the TSV property roster.',
                "Only 'constructed' indicates a Dataset value; declined/null assertions add no construction credit.",
                'Evidence accounting alone is not mapping, source coverage or validation success.'):
                assert text in section
            for row in expected_rows:
                assert row['property'] not in unmapped
        else:
            assert heading not in report
        verified = {'dataset': pin(dataset_path), 'sidecar': pin(sidecar_path), 'report': pin(report_path),
            'full_type_exact_record_equal': True, 'exact_dataset_bytes_equal': True,
            'actual_saved_byte_gate': 'PASS', 'sidecar_exact_after_declared_cli_bytes_and_locator_rebinding': True,
            'cli_serialization_oracle': {'source': 'saved full record before CLI',
                'bytes': len(expected_dataset_raw), 'sha256': hashlib.sha256(expected_dataset_raw).hexdigest()},
            'permitted_rebindings': ['dataset.path', 'dataset.bytes', 'dataset.sha256', 'schema.path', 'evidence.mapping.path',
                'evidence.sources[0].display_name', 'evidence.sources[0].snapshot.original_file.path'],
            'source_snapshot_raw_bytes_equal': True, 'report_labels_present': True,
            'supplemental_report_rows_exact': True, 'supplemental_report_rows': expected_rows,
            'cli_origin': cli_origin}
    except BaseException as exc:
        verification_error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        try:
            owned_origins()
        except BaseException as exc:
            origin_findings.append({'type': type(exc).__name__, 'message': str(exc)})
        passed = cli_exit == 0 and verification_error is None and not origin_findings and verified is not None
        receipt = {'form': form, 'passed': passed, 'literal_cli_argv': argv, 'cwd': str(source),
            'executable': sys.executable, 'version': list(sys.version_info[:3]),
            'sys_path': sys.path, 'cli_exit_code': cli_exit, 'cli_error': cli_error,
            'verification_error': verification_error, 'origin_rows': origin_rows,
            'origin_findings': origin_findings, 'verified': verified,
            'elapsed_seconds': time.monotonic() - started,
            'scope': 'One natural CLI publication plus one explicit actual saved-byte Dataset recheck; no provider or scientific scoring.'}
        with (output / 'receipts' / (form + '.worker.json')).open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
            stream.write('\n')
    return 0 if passed else cli_exit if type(cli_exit) is int and cli_exit else 2


if __name__ == '__main__':
    raise SystemExit(main())
