"""Root-only saved-record controls; no project imports or publication commands."""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run import require_natural_success
from serialization_oracle import (cli_yaml_bytes, encoded, same,
                                  sidecar_with_cli_dataset, verify_dataset, verify_sidecar)


CASES = [
    'writer_contract', 'natural_exit_accepted', 'forced_cleanup_refused', 'unicode_positive', 'historical_unicode_bytes_refused',
    'changed_text_refused', 'boolean_to_zero_refused', 'list_order_refused',
    'list_duplicate_removal_refused', 'mapping_order_bytes_refused',
    'unicode_codepoint_change_refused', 'sidecar_positive',
    'sidecar_digest_refused', 'sidecar_size_refused', 'sidecar_raw_text_refused',
    'sidecar_raw_text_removal_refused', 'historical_sidecar_binding_refused',
    'saved_CHORUS', 'saved_VOICE', 'saved_CM4AI_reduced',
    'saved_VOICE_provenance', 'saved_CM4AI_original',
]


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        raise SystemExit('Disabled: root must supply --run')
    config_path = HERE / 'configuration.disabled.json'
    config = json.loads(config_path.read_text())
    assert config['enabled'] is False and config['binding'] is None
    assert sys.version_info[:3] == tuple(config['python_version'])
    assert CASES == config['serialization_control_cases']
    result_path = Path(config['serialization_controls_receipt'])
    assert not os.path.lexists(result_path.parent)
    result_path.parent.mkdir()
    watched = [*config['pins'], pin(config_path)]
    yaml_pins = []
    outcomes = []
    saved = []
    error = None
    yaml_module = None
    def success(name):
        outcomes.append({'name': name, 'passed': True})
    def reject(name, operation, message):
        try:
            operation()
        except AssertionError as exc:
            assert str(exc) == message, (name, str(exc))
        else:
            raise AssertionError('Mutation was admitted: ' + name)
        success(name)
    try:
        for row in watched:
            assert pin(row['path']) == row, row['path']
        assert not any(n == 'data_sheets_schema' or n.startswith('data_sheets_schema.')
                       or n == 'fairscape_integration' or n.startswith('fairscape_integration.')
                       for n in sys.modules)
        import yaml
        yaml_module = str(Path(yaml.__file__).resolve())
        yaml_pins = [pin(p) for p in sorted(Path(yaml_module).parent.glob('*.py'))]
        assert yaml_pins
        cli = ast.parse((HERE / 'references/cli.py').read_text())
        transform = next(n for n in cli.body if isinstance(n, ast.FunctionDef) and n.name == 'transform')
        calls = [n for n in ast.walk(transform) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'prepare_dataset']
        assert len(calls) == 1
        options = {k.arg: ast.literal_eval(k.value) for k in calls[0].keywords if k.arg != 'context'}
        assert options == {'default_flow_style': False, 'sort_keys': False}
        publication = ast.parse((HERE / 'references/legacy_publication.py').read_text())
        prepare = next(n for n in publication.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare_dataset')
        encoding = next(value for name, value in zip(prepare.args.kwonlyargs, prepare.args.kw_defaults)
                        if name.arg == 'encoding')
        assert ast.literal_eval(encoding) == 'utf-8'
        dump = [n for n in ast.walk(prepare) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                and n.func.value.id == 'yaml' and n.func.attr == 'safe_dump']
        assert len(dump) == 1 and len(dump[0].args) == 1
        assert ast.dump(dump[0].args[0]) == "Name(id='dataset', ctx=Load())"
        assert len(dump[0].keywords) == 1 and dump[0].keywords[0].arg is None
        assert ast.dump(dump[0].keywords[0].value) == "Name(id='dump_options', ctx=Load())"
        success('writer_contract')
        execution = {'exit_code': 0}
        require_natural_success(None, execution, {'owned_group_absent': True, 'signals': []})
        success('natural_exit_accepted')
        for signal_name in ('SIGTERM', 'SIGKILL'):
            try:
                require_natural_success(None, execution,
                    {'owned_group_absent': True, 'signals': [signal_name]})
            except AssertionError as exc:
                assert exc.args == (execution,)
            else:
                raise AssertionError('Actual coordinator predicate admitted forced cleanup: ' + signal_name)
        success('forced_cleanup_refused')
        record = {'title': 'Alpha • café 🙂', 'keywords': ['first', 'first', 'second'],
                  'retained': False, 'zero': 0, 'nested': {'text': 'line\nquote"'}}
        expected = cli_yaml_bytes(record, yaml)
        assert b'\\u2022' in expected and b'\\U0001F642' in expected
        assert same(verify_dataset(expected, expected, record, yaml.safe_load), record)
        success('unicode_positive')
        old = yaml.safe_dump(record, default_flow_style=False, sort_keys=False, allow_unicode=True).encode('utf-8')
        assert same(yaml.safe_load(old), record) and old != expected
        byte_error = 'Published Dataset bytes differ from natural CLI serialization oracle'
        value_error = 'Published full Dataset differs from saved oracle'
        sidecar_error = 'Sidecar differs beyond declared CLI-byte and file-locator rebinding'
        reject('historical_unicode_bytes_refused', lambda: verify_dataset(old, expected, record, yaml.safe_load), byte_error)
        changes = [
            ('changed_text_refused', lambda r: r.update(title='different')),
            ('boolean_to_zero_refused', lambda r: r.update(retained=0)),
            ('list_order_refused', lambda r: r.update(keywords=list(reversed(r['keywords'])))),
            ('list_duplicate_removal_refused', lambda r: r.update(keywords=['first', 'second'])),
        ]
        for name, change in changes:
            altered = copy.deepcopy(record)
            change(altered)
            raw = cli_yaml_bytes(altered, yaml)
            reject(name, lambda raw=raw: verify_dataset(raw, expected, record, yaml.safe_load), value_error)
        reordered = dict(reversed(list(record.items())))
        assert same(reordered, record)
        reject('mapping_order_bytes_refused', lambda: verify_dataset(cli_yaml_bytes(reordered, yaml), expected, record, yaml.safe_load), byte_error)
        altered = copy.deepcopy(record)
        altered['title'] = altered['title'].replace('🙂', '🙃')
        reject('unicode_codepoint_change_refused', lambda: verify_dataset(cli_yaml_bytes(altered, yaml), expected, record, yaml.safe_load), value_error)
        historical = {'path': '/historical/synthetic.yaml', 'bytes': len(old), 'sha256': hashlib.sha256(old).hexdigest()}
        doc = {'dataset': historical, 'evidence': {'raw': 'whole • raw\ntext', 'values': [False, 0, 'x', 'x']}}
        sidecar = sidecar_with_cli_dataset(doc, historical, expected, '/release/synthetic.yaml')
        assert same(doc, {'dataset': historical, 'evidence': {'raw': 'whole • raw\ntext', 'values': [False, 0, 'x', 'x']}})
        assert sidecar['dataset']['bytes'] == len(expected)
        assert sidecar['dataset']['sha256'] == hashlib.sha256(expected).hexdigest()
        verify_sidecar(encoded(sidecar), sidecar)
        success('sidecar_positive')
        mutations = [
            ('sidecar_digest_refused', lambda s: s['dataset'].update(sha256=historical['sha256'])),
            ('sidecar_size_refused', lambda s: s['dataset'].update(bytes=historical['bytes'])),
            ('sidecar_raw_text_refused', lambda s: s['evidence'].update(raw='truncated')),
            ('sidecar_raw_text_removal_refused', lambda s: s['evidence'].pop('raw')),
        ]
        assert historical['bytes'] != len(expected) and historical['sha256'] != sidecar['dataset']['sha256']
        for name, mutation in mutations:
            altered = copy.deepcopy(sidecar)
            mutation(altered)
            reject(name, lambda altered=altered: verify_sidecar(encoded(altered), sidecar), sidecar_error)
        wrong_historical = dict(historical, bytes=historical['bytes'] + 1)
        reject('historical_sidecar_binding_refused', lambda: sidecar_with_cli_dataset(doc, wrong_historical, expected, '/release/synthetic.yaml'), 'Historical sidecar Dataset binding differs')
        export = json.loads(Path(config['export']['path']).read_text())
        for item in config['inputs']:
            rows = [r for r in export['rows'] if (r['arm'], r['input'], r['consumer'], r['order'])
                    == ('candidate', item['form'], 'packaged', 'original')]
            assert len(rows) == 1
            row = rows[0]
            assert row['preparation_gate']['status'] == 'PREPARED'
            historical_raw = Path(item['record_oracle']['path']).read_bytes()
            assert same(yaml.safe_load(historical_raw), row['record'])
            # Assert insertion order too; record equality alone does not prove byte order.
            assert list(yaml.safe_load(historical_raw)) == list(row['record'])
            raw = cli_yaml_bytes(row['record'], yaml)
            assert same(yaml.safe_load(raw), row['record'])
            canonical = json.dumps(row['record'], sort_keys=True, ensure_ascii=False,
                                   allow_nan=False, separators=(',', ':')).encode('utf-8')
            assert hashlib.sha256(canonical).hexdigest() == item['record_canonical_json_sha256']
            expected_sidecar = sidecar_with_cli_dataset(row['prepared_sidecar']['document'],
                item['record_oracle'], raw, '/declared-controls-only/' + item['form'] + '.yaml')
            assert same(expected_sidecar['evidence'], row['prepared_sidecar']['document']['evidence'])
            saved.append({'form': item['form'], 'historical_dataset': item['record_oracle'],
                'cli_bytes': len(raw), 'cli_sha256': hashlib.sha256(raw).hexdigest(),
                'canonical_sha256': hashlib.sha256(canonical).hexdigest(),
                'serialized_from': 'saved export full record with retained insertion order'})
            success('saved_' + item['form'])
        assert [r['name'] for r in outcomes] == CASES
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        changes = []
        for row in watched + yaml_pins:
            try:
                assert pin(row['path']) == row
            except BaseException as exc:
                changes.append({'path': row['path'], 'error': type(exc).__name__})
        project_imports = any(n == 'data_sheets_schema' or n.startswith('data_sheets_schema.')
                              or n == 'fairscape_integration' or n.startswith('fairscape_integration.')
                              for n in sys.modules)
        passed = error is None and not changes and not project_imports and [r['name'] for r in outcomes] == CASES
        result = {'passed': passed, 'error': error, 'cases': [r['name'] for r in outcomes],
            'outcomes': outcomes, 'configuration': pin(config_path), 'watched_pins': watched,
            'yaml_module': yaml_module, 'yaml_pins': yaml_pins, 'saved_oracles': saved,
            'version': list(sys.version_info[:3]), 'executable_realpath': os.path.realpath(sys.executable),
            'preserved': not changes, 'pin_changes': changes, 'project_imports': project_imports,
            'source_records_only': True, 'published_outputs_read': False,
            'scope': 'Saved-record byte-oracle controls only; no product CLI, schema gate or publication acceptance.'}
        with result_path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
            stream.write('\n')
        print(json.dumps({'passed': passed, 'controls': len(outcomes), 'error': error}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
