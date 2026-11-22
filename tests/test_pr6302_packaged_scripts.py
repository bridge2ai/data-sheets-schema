"""Pure software controls for original wheel-script preservation; no installation."""
import base64
import copy
import csv
import hashlib
import io
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from scripts.adhoc import pr6302_archive_environment_scripts_20261122 as launchers


def _record(rows):
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\n').writerows(rows)
    return stream.getvalue().encode()


def _fixture(tmp_path, monkeypatch, *, payload=b'#!python\nprint("software fixture")\n'):
    source = tmp_path / 'original'
    source.mkdir()
    name, owner_name, version = 'daff.py', 'daff', '1.3.46'
    member = 'daff-1.3.46.data/scripts/daff.py'
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b'=').decode()
    record = _record([[member, 'sha256=' + digest, str(len(payload))],
                      ['daff-1.3.46.dist-info/RECORD', '', '']])
    wheel = tmp_path / 'software-fixture.whl'
    with zipfile.ZipFile(wheel, 'w') as bundle:
        bundle.writestr(member, payload)
        bundle.writestr('daff-1.3.46.dist-info/RECORD', record)
    candidate = dict(kind='original_cached_wheel', name=owner_name, version=version,
                     artifact=launchers.pin(wheel), record_verified=True,
                     record_sha256=launchers.sha(record))
    audit = dict(cache_inputs=[candidate])
    owner = dict(name=owner_name, version=version)
    # Only these explicitly labelled software controls replace a production pin.
    monkeypatch.setitem(launchers.DATA_SCRIPTS, name,
                        (owner_name, version, member, launchers.sha(payload)))
    installed = ('#!' + str(source / 'bin/python') + '\n').encode() + payload.split(b'\n', 1)[1]
    return source, audit, name, owner, installed, payload


def test_original_wheel_payload_and_exact_source_shebang_are_both_required(tmp_path, monkeypatch):
    source, audit, name, owner, installed, payload = _fixture(tmp_path, monkeypatch)
    before = copy.deepcopy(audit)
    data = launchers.data_script_plan(source, audit, name, owner, installed)
    assert launchers.wheel_script_bytes(data) == payload
    assert audit == before
    for changed in (installed + b'\n', installed.replace(b'original', b'other', 1),
                    installed.replace(b'fixture', b'changed', 1)):
        with pytest.raises(ValueError, match='original installed'):
            launchers.data_script_plan(source, audit, name, owner, changed)
    for changed_owner in (dict(name='other', version=owner['version']),
                          dict(name=owner['name'], version='1.3.45')):
        with pytest.raises(ValueError, match='not a declared'):
            launchers.data_script_plan(source, audit, name, changed_owner, installed)
    with pytest.raises(ValueError, match='not a declared'):
        launchers.data_script_plan(source, audit, 'unknown.py', owner, installed)


def test_original_wheel_and_member_record_pins_reject_drift(tmp_path, monkeypatch):
    source, audit, name, owner, installed, _ = _fixture(tmp_path, monkeypatch)
    data = launchers.data_script_plan(source, audit, name, owner, installed)
    for field, value, message in (
            ('record_sha256', '0' * 64, 'RECORD changed'),
            ('sha256', '0' * 64, 'payload differs'),
            ('bytes', float(data['bytes']), 'payload differs'),
            ('bytes', True, 'payload differs'),
            ('member', 'daff-1.3.46.data/scripts/other.py', 'member is not unique')):
        changed = copy.deepcopy(data)
        changed[field] = value
        with pytest.raises(ValueError, match=message):
            launchers.wheel_script_bytes(changed)
    path = Path(data['wheel']['path'])
    path.write_bytes(path.read_bytes() + b'tamper')
    with pytest.raises(ValueError, match='input pin changed'):
        launchers.wheel_script_bytes(data)


def test_nonstandard_cached_shebang_remains_refused(tmp_path, monkeypatch):
    for index, first_line in enumerate((b'#!python3', b'#!pythonw', b'#!python\r', b'#!/usr/bin/python')):
        selected = tmp_path / str(index)
        selected.mkdir()
        source, audit, name, owner, installed, _ = _fixture(
            selected, monkeypatch, payload=first_line + b'\nprint("fixture")\n')
        with pytest.raises(ValueError, match='payload differs'):
            launchers.data_script_plan(source, audit, name, owner, installed)


def _maker(clone):
    return SimpleNamespace(_get_shebang=lambda encoding: ('#!' + str(clone / 'bin/python') + '\n').encode())


def test_official_fixer_output_must_preserve_every_body_byte(tmp_path, monkeypatch):
    source, audit, name, owner, installed, payload = _fixture(
        tmp_path, monkeypatch, payload=b'#!python\n# body ' + bytes([64]) + b'\r\nprint("fixture")\n')
    data = launchers.data_script_plan(source, audit, name, owner, installed)
    clone = tmp_path / 'clone'
    monkeypatch.setattr(launchers.sys, 'platform', 'darwin')
    calls = []
    def fixer(path):
        selected = Path(path)
        raw = selected.read_bytes()
        calls.append(raw)
        selected.write_bytes(('#!' + str(clone / 'bin/python') + '\n').encode() + raw.split(b'\n', 1)[1])
        return True
    rendered = tmp_path / 'rendered'
    result = launchers.render_data_script(data, rendered, clone, _maker(clone), SimpleNamespace(fix_script=fixer))
    assert calls == [payload]
    assert rendered.read_bytes() == result
    assert result.split(b'\n', 1)[1] == payload.split(b'\n', 1)[1]
    def changed_body(path):
        fixer(path)
        selected = Path(path)
        selected.write_bytes(selected.read_bytes() + b'changed')
        return True
    with pytest.raises(ValueError, match='changed body or interpreter'):
        launchers.render_data_script(data, tmp_path / 'changed', clone, _maker(clone),
                                     SimpleNamespace(fix_script=changed_body))
    assert launchers.wheel_script_bytes(data) == payload


def test_darwin_path_bound_and_official_simple_shebang_are_required(monkeypatch):
    monkeypatch.setattr(launchers.sys, 'platform', 'darwin')
    clone = Path('/' + 'x' * (509 - len('/bin/python') - 1))
    assert len(launchers.data_script_shebang(clone, _maker(clone))) == 512
    for path in (Path(str(clone) + 'x'), Path('/clone space'), Path('/clone#hash'),
                 Path('/clone\nline'), Path('/clone' + chr(160))):
        with pytest.raises(ValueError, match='simple bounded Darwin'):
            launchers.data_script_shebang(path, _maker(path))
    ordinary = Path('/clone')
    wrapped = SimpleNamespace(_get_shebang=lambda encoding: b'#!/bin/sh\n')
    with pytest.raises(ValueError, match='nonsimple shebang'):
        launchers.data_script_shebang(ordinary, wrapped)
    monkeypatch.setattr(launchers.sys, 'platform', 'linux')
    with pytest.raises(ValueError, match='simple bounded Darwin'):
        launchers.data_script_shebang(ordinary, _maker(ordinary))
