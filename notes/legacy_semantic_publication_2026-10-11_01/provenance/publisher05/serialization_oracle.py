"""External #4943 oracle for the unchanged packaged transform serialization.

Expected values are historical saved records, never a current published record.
The exact options mirror cli.transform -> legacy_publication.prepare_dataset.
This module neither calls that producer nor changes schema/publication checks.
"""
import copy
import hashlib
import json


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


def cli_yaml_bytes(record, yaml_module):
    # Omitting allow_unicode is intentional: the real CLI omits it as well.
    return yaml_module.safe_dump(record, default_flow_style=False,
                                 sort_keys=False).encode('utf-8')


def verify_dataset(raw, expected_raw, expected_record, load):
    record = load(raw.decode('utf-8'))
    assert same(record, expected_record), 'Published full Dataset differs from saved oracle'
    assert raw == expected_raw, 'Published Dataset bytes differ from natural CLI serialization oracle'
    return record


def sidecar_with_cli_dataset(document, historical_pin, expected_raw, dataset_path):
    expected = copy.deepcopy(document)
    assert expected['dataset'] == historical_pin, 'Historical sidecar Dataset binding differs'
    expected['dataset'] = {'path': str(dataset_path), 'bytes': len(expected_raw),
                           'sha256': hashlib.sha256(expected_raw).hexdigest()}
    return expected


def verify_sidecar(raw, expected):
    assert raw == encoded(expected), 'Sidecar differs beyond declared CLI-byte and file-locator rebinding'
    assert same(json.loads(raw), expected)
