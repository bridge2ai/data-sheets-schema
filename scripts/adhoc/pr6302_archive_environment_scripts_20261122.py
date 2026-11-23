"""PR6302 disposable-environment console relocation, 2026-11-22.

Plan reads the original launcher/RECORD/entry-point metadata without imports.
Relocate runs only under the isolated clone interpreter, uses pip's official
ScriptMaker, and changes only copied launchers and their exact RECORD lines.
Own project launchers must already be quarantined for genuine editable install.
No source-environment writes, package installs, subprocesses or network calls.
"""
import argparse
import ast
import base64
import configparser
import csv
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile


OWN = {'d4d', 'fairscape-cli'}
PIP_CALLABLE = 'pip._internal.cli.main:main'
MAKER_SOURCE = 'pip/_vendor/distlib/scripts.py'
MAKER_SOURCES = (MAKER_SOURCE, 'pip/_vendor/distlib/util.py', 'pip/_internal/operations/install/wheel.py')
CALLABLE = r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*'
ENTRYPOINT = CALLABLE + r'(?: \[[A-Za-z0-9_.-]+(?:, *[A-Za-z0-9_.-]+)*\])?'
DATA_SCRIPTS = {
    'daff.py': ('daff', '1.3.46', 'daff-1.3.46.data/scripts/daff.py',
                'd140bf859c63ebfbd001eef30d0d3cae209b2eda2d243116489022ce5631eb38'),
    'dumppdf.py': ('pdfminer-six', '20221105', 'pdfminer.six-20221105.data/scripts/dumppdf.py',
                   'b61874017f27c9bfc41c17c74926af51a4f914463a3c2c4cd06f7783a60528d0'),
    'google': ('google', '3.0.0', 'google-3.0.0.data/scripts/google',
               '8af65475161401de46eea3ce4af5e142b4fc5a0b9b824bd1973fa412dcbfce52'),
    'jp.py': ('jmespath', '1.0.1', 'jmespath-1.0.1.data/scripts/jp.py',
              '3c33be32db89ef63e1efceabd80c34e70679ab6d86260b9ebfd1b4c415e8388f'),
    'jsonpointer': ('jsonpointer', '2.4', 'jsonpointer-2.4.data/scripts/jsonpointer',
                    '6a35d64ec634366648ebca9a42c18bca28e73d7539a994ddd549c63b87c669c9'),
    'num2words': ('num2words', '0.5.14', 'num2words-0.5.14.data/scripts/num2words',
                  '1e30aacca972194c3bd9ca45f4a1120d712975f36b413458a48528f12a0ca3fe'),
    'pdf2txt.py': ('pdfminer-six', '20221105', 'pdfminer.six-20221105.data/scripts/pdf2txt.py',
                   '3c542197ed474af21eedccdd6530d382354cd3eb3c32655444c1752f9c68b55c'),
    'pygrun': ('antlr4-python3-runtime', '4.9.3', 'antlr4_python3_runtime-4.9.3.data/scripts/pygrun',
               '02d4202c724d47965d015e9d62ad2f243359b840516db9629ce964d4e1150461'),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def ordinary(path):
    require(path.is_file() and not path.is_symlink(), 'regular unaliased file required: ' + str(path))
    return path.read_bytes()


def writable_payload(path, root, source=None):
    require(path.is_relative_to(root) and path.parent == path.parent.resolve(),
            'destination escapes physical clone')
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'destination requires a regular file without symlink or hardlink aliases')
    if source is not None:
        original = source.lstat()
        require((info.st_dev, info.st_ino) != (original.st_dev, original.st_ino),
                'destination shares the original source inode')
    return ordinary(path)


def pin(path):
    raw = ordinary(path)
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def require_pin(path, expected):
    raw = ordinary(path)
    require(type(expected['bytes']) is int and len(raw) == expected['bytes']
            and sha(raw) == expected['sha256'], 'input pin changed: ' + str(path))
    return raw


def source_site(source):
    require(source == source.resolve() and source.is_dir(), 'source venv must be physical')
    sites = list(source.glob('lib/python*/site-packages'))
    require(len(sites) == 1 and sites[0] == sites[0].resolve(), 'one physical source site required')
    return sites[0]


def launcher_names(source):
    result = set()
    for path in (source / 'bin').iterdir():
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            prefix = stream.read(8192)
        if not prefix.startswith(b'#!'):
            continue
        line = prefix.split(b'\n', 1)[0]
        if b'python' in line.lower() or (line in (b'#!/bin/sh', b'#!/usr/bin/env sh')
                and b'exec' in prefix and b'python' in prefix):
            require(not path.is_symlink(), 'aliased Python launcher refused')
            result.add(path.name)
    return result


def record_rows(raw):
    rows = list(csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True))
    lines = raw.splitlines(keepends=True)
    require(len(rows) == len(lines) and all(len(row) == 3 for row in rows),
            'RECORD requires one bounded physical line per entry')
    return rows, lines


def hashed_payload(raw, encoded_hash, size):
    algorithm, separator, expected = encoded_hash.partition('=')
    require(separator and algorithm in ('sha256', 'sha384', 'sha512'), 'unsupported RECORD hash')
    actual = base64.urlsafe_b64encode(hashlib.new(algorithm, raw).digest()).rstrip(b'=').decode()
    require(actual == expected and size == str(len(raw)), 'launcher differs from owning RECORD')


def entry_points(path):
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    raw = ordinary(path)
    parser.read_string(raw.decode('utf-8'))
    return dict(parser.items('console_scripts')) if parser.has_section('console_scripts') else {}


def script_template(path):
    tree = ast.parse(ordinary(path))
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'SCRIPT_TEMPLATE' for target in node.targets)]
    require(len(values) == 1, 'official ScriptMaker template must be one literal')
    value = ast.literal_eval(values[0])
    require(type(value) is str, 'official ScriptMaker template is not text')
    return value


def maker_source_pins(source, audit):
    site = source_site(source)
    pip_rows = [row for row in audit['distributions'] if row['name'] == 'pip']
    require(len(pip_rows) == 1 and pip_rows[0]['version'] == '25.0.1', 'reviewed pip distribution differs')
    record_path = Path(pip_rows[0]['record']['path'])
    require(record_path.parent.parent == site and record_path.name == 'RECORD'
            and record_path.parent == record_path.parent.resolve(), 'pip RECORD escapes physical source site')
    record = require_pin(record_path, pip_rows[0]['record'])
    entries, _ = record_rows(record)
    pins = []
    for relative in MAKER_SOURCES:
        path = site / relative
        matches = [row for row in entries if os.path.abspath(site / row[0]) == str(path)]
        require(len(matches) == 1 and matches[0][1], 'official script generator lacks one hashed RECORD row')
        hashed_payload(ordinary(path), matches[0][1], matches[0][2])
        pins.append(pin(path))
    return pins


def wheel_script_bytes(data):
    raw = require_pin(Path(data['wheel']['path']), data['wheel'])
    with zipfile.ZipFile(io.BytesIO(raw)) as wheel:
        names = wheel.namelist()
        require(len(names) == len(set(names)) and data['member'] in names, 'wheel script member is not unique')
        records = [name for name in names if name.endswith('.dist-info/RECORD')]
        require(len(records) == 1, 'wheel script RECORD is ambiguous')
        record = wheel.read(records[0])
        require(sha(record) == data['record_sha256'], 'wheel script RECORD changed')
        entries, _ = record_rows(record)
        matches = [row for row in entries if row[0] == data['member']]
        require(len(matches) == 1, 'wheel script lacks one RECORD row')
        body = wheel.read(data['member'])
    hashed_payload(body, matches[0][1], matches[0][2])
    require(body.startswith(b'#!python\n') and type(data['bytes']) is int
            and len(body) == data['bytes'] and sha(body) == data['sha256'], 'reviewed wheel script payload differs')
    return body


def data_script_plan(source, audit, name, owner, installed):
    approved = DATA_SCRIPTS.get(name)
    require(approved is not None and (owner['name'], owner['version']) == approved[:2],
            'launcher is not a declared literal console entrypoint: ' + name)
    candidates = [row for row in audit['cache_inputs'] if row['kind'] == 'original_cached_wheel'
                  and (row['name'], row['version']) == approved[:2] and row['record_verified'] is True]
    require(candidates, 'reviewed wheel script lacks original cached wheel')
    candidate = sorted(candidates, key=lambda row: row['artifact']['path'])[0]
    wheel_raw = require_pin(Path(candidate['artifact']['path']), candidate['artifact'])
    with zipfile.ZipFile(io.BytesIO(wheel_raw)) as wheel:
        raw = wheel.read(approved[2])
    data = dict(wheel=candidate['artifact'], record_sha256=candidate['record_sha256'],
                member=approved[2], bytes=len(raw), sha256=approved[3])
    raw = wheel_script_bytes(data)
    require(installed == ('#!' + str(source / 'bin/python') + '\n').encode() + raw.split(b'\n', 1)[1],
            'original installed wheel script differs beyond its exact source shebang')
    return data


def data_script_shebang(clone, maker):
    selected = str(clone / 'bin/python')
    executable = os.fsencode(selected)
    # Reviewed pip25.0.1 distlib uses the Darwin 512-byte bound, including prefix/newline.
    require(sys.platform == 'darwin' and all(value > 32 and value != 127 for value in executable)
            and not any(character.isspace() or 127 <= ord(character) <= 159 for character in selected)
            and b'#' not in executable and len(executable) + 3 <= 512,
            'wheel script requires a simple bounded Darwin interpreter path')
    expected = b'#!' + executable + b'\n'
    require(maker._get_shebang('utf-8') == expected, 'official generator requires a nonsimple shebang')
    return expected


def render_data_script(data, path, clone, maker, official_wheel):
    raw = wheel_script_bytes(data)
    expected = data_script_shebang(clone, maker) + raw.split(b'\n', 1)[1]
    with path.open('xb') as stream:
        stream.write(raw)
    require(official_wheel.fix_script(str(path)) is True, 'official wheel script fixer did not accept original payload')
    require(ordinary(path) == expected, 'official wheel script fixer changed body or interpreter')
    return expected


def plan_scripts(source, audit, *, expected_launcher_count=173):
    site = source_site(source)
    require(audit['venv'] == str(source) and audit['site_packages'] == str(site)
            and audit['duplicate_distribution_names'] == [], 'audit source identity differs')
    rows = audit['python_launchers']
    require(type(expected_launcher_count) is int and expected_launcher_count > 0
            and len(rows) == expected_launcher_count and len({row['path'] for row in rows}) == len(rows),
            'reviewed launcher roster differs')
    require(launcher_names(source) == {Path(row['path']).name for row in rows}, 'current launcher roster differs')
    distributions = {row['record']['path']: row for row in audit['distributions']}
    version = site.parent.name.removeprefix('python')
    require(version == '3.13', 'reviewed pip alias spellings require Python3.13')
    aliases = {'pip', 'pip3', 'pip3.13', 'pip-3.13'}
    template = script_template(site / MAKER_SOURCE)
    planned = []
    for observed in rows:
        path = Path(observed['path'])
        require(path.parent == source / 'bin' and path.name not in ('', '.', '..'), 'launcher escapes source bin')
        raw = require_pin(path, observed)
        require(observed['owners'], 'launcher has no RECORD owner')
        owners, callables, packaged = [], set(), []
        for owner in observed['owners']:
            record = Path(owner['record_path'])
            require(record.parent.parent == site and record.name == 'RECORD'
                    and record.parent == record.parent.resolve(), 'owner RECORD escapes source site')
            distribution = distributions[str(record)]
            require((owner['name'], owner['version']) == (distribution['name'], distribution['version']),
                    'owner distribution identity differs')
            record_raw = require_pin(record, distribution['record'])
            require(sha(record_raw) == owner['record_sha256'], 'owner RECORD differs from audit')
            metadata_path = record.parent / 'METADATA'
            require(sha(ordinary(metadata_path)) == distribution['metadata_sha256'], 'owner metadata changed')
            entries, _ = record_rows(record_raw)
            matches = [(index, row) for index, row in enumerate(entries)
                       if os.path.abspath(site / row[0]) == str(path)]
            require(len(matches) == 1, 'launcher owner row is not unique')
            index, entry = matches[0]
            require(not Path(entry[0]).is_absolute() or
                    (owner['name'] == 'data-sheets-schema' and path.name in OWN),
                    'absolute third-party launcher RECORD target refused')
            require(entry == [owner['record_entry'], owner['recorded_hash'], owner['recorded_size']],
                    'launcher owner row differs from audit')
            points_path = record.parent / 'entry_points.txt'
            declared = [row for row in entries if os.path.abspath(site / row[0]) == str(points_path)]
            if points_path.exists():
                points_raw = ordinary(points_path)
                require(len(declared) == 1 and declared[0][1], 'entry point metadata lacks one hashed RECORD row')
                hashed_payload(points_raw, declared[0][1], declared[0][2])
                points = entry_points(points_path)
                points_pin = pin(points_path)
            else:
                require(path.name in DATA_SCRIPTS and not declared, 'entry point metadata is unexpectedly absent')
                points, points_pin = {}, None
            callable_value = points.get(path.name)
            alias = owner['name'] == 'pip' and owner['version'] == '25.0.1' and path.name in aliases
            if callable_value is None and alias:
                require(points.get('pip') == points.get('pip3') == PIP_CALLABLE, 'pip base entrypoints differ')
                callable_value = PIP_CALLABLE
            if callable_value is None:
                packaged.append(data_script_plan(source, audit, path.name, owner, raw))
            else:
                require(type(callable_value) is str and re.fullmatch(ENTRYPOINT, callable_value),
                    'launcher is not a declared literal console entrypoint: ' + path.name)
                require(path.name not in DATA_SCRIPTS, 'reviewed wheel script unexpectedly became an entrypoint')
            if entry[1]:
                hashed_payload(raw, entry[1], entry[2])
            else:
                require(alias and callable_value == PIP_CALLABLE and entry[2] == '', 'unreviewed hashless launcher')
                prefix, suffix = callable_value.split(':')
                expected = template % dict(module=prefix, import_name=suffix.split('.')[0], func=suffix)
                require(raw.startswith(('#!' + str(source / 'bin/python') + '\n').encode())
                        and ast.dump(ast.parse(raw)) == ast.dump(ast.parse(expected)),
                        'hashless pip alias differs from the official callable template')
            callables.add(callable_value)
            owners.append(dict(name=owner['name'], version=owner['version'],
                record_relative=record.relative_to(source).as_posix(), record_pin=pin(record),
                row_index=index, row=entry, metadata_pin=pin(metadata_path),
                entry_points_pin=points_pin, hashless_pip_alias=not bool(entry[1])))
        require(len(callables) == 1, 'shared RECORD owners disagree on launcher callable')
        require(not packaged or (len(packaged) == len(owners) and
                all(canonical(value) == canonical(packaged[0]) for value in packaged)),
                'shared owners disagree on reviewed wheel script')
        own = path.name in OWN
        require(all((owner['name'] == 'data-sheets-schema') is own for owner in owners),
                'own-project launcher scope differs')
        planned.append(dict(name=path.name, source_pin=pin(path), callable=next(iter(callables)),
                            wheel_data_script=packaged[0] if packaged else None,
                            owners=owners, skip_for_project_editable_install=own))
    return planned


def inventory(root):
    values = {}
    for parent, folders, files in os.walk(root, followlinks=False):
        require(not any((Path(parent) / name).is_symlink() for name in folders), 'clone has a directory alias')
        for name in files:
            path = Path(parent) / name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                values[relative] = dict(kind='symlink', target=os.readlink(path), mode=stat.S_IMODE(info.st_mode))
            else:
                require(stat.S_ISREG(info.st_mode), 'clone contains a nonregular payload')
                raw = path.read_bytes()
                values[relative] = dict(kind='file', bytes=len(raw), sha256=sha(raw), mode=stat.S_IMODE(info.st_mode))
    return values


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
           .replace(chr(64), '\\u0040') + '\n').encode()
    require(not path.exists() and not path.is_symlink(), 'preserve existing output')
    with path.open('xb') as stream:
        stream.write(raw)
    require(ordinary(path) == raw, 'output readback differs')
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def relocate_scripts(source, clone, plan, output):
    require(source == source.resolve() and clone == clone.resolve() and source != clone
            and not clone.is_relative_to(source) and not source.is_relative_to(clone), 'clone/source scopes overlap')
    require(Path(sys.executable).absolute() == clone / 'bin/python'
            and Path(sys.prefix) == clone and sys.flags.isolated and sys.dont_write_bytecode,
            'relocation requires clone/bin/python -I -B')
    require(not output.is_relative_to(source) and not output.is_relative_to(clone), 'evidence must be external')
    audit_raw = require_pin(Path(plan['audit']['path']), plan['audit'])
    audit = json.loads(audit_raw)
    require(sha(ordinary(Path(__file__))) == plan['helper_sha256'], 'relocation helper changed since planning')
    require(canonical(plan_scripts(source, audit)) == canonical(plan['scripts'])
            and canonical(maker_source_pins(source, audit)) == canonical(plan['scriptmaker_sources']),
            'original source or script plan changed')
    site = source_site(source)
    clone_site = clone / site.relative_to(source)
    require(all(not (clone / 'bin' / name).exists() for name in OWN), 'own console scripts must be quarantined first')
    require(not (clone_site / 'data_sheets_schema.pth').exists()
            and all(not (clone / owner['record_relative']).exists() for row in plan['scripts']
                    if row['skip_for_project_editable_install'] for owner in row['owners']),
            'own metadata/path helper must be quarantined first')
    active = [row for row in plan['scripts'] if not row['skip_for_project_editable_install']]
    require(launcher_names(clone) == {row['name'] for row in active}, 'copied launcher roster differs')
    for item in plan['scriptmaker_sources']:
        require_pin(clone / Path(item['path']).relative_to(source), item)
    records = {}
    for row in active:
        writable_payload(clone / 'bin' / row['name'], clone, source / 'bin' / row['name'])
        require_pin(clone / 'bin' / row['name'], row['source_pin'])
        for owner in row['owners']:
            relative = owner['record_relative']
            writable_payload(clone / relative, clone, source / relative)
            raw = require_pin(clone / relative, owner['record_pin'])
            records[relative] = raw
            for key in ('metadata_pin', 'entry_points_pin'):
                if owner[key] is None:
                    require(key == 'entry_points_pin' and
                            not (clone / relative).with_name('entry_points.txt').exists(),
                            'copied absent entrypoint metadata appeared')
                    continue
                original = Path(owner[key]['path'])
                require_pin(clone / original.relative_to(source), owner[key])
    before = inventory(clone)
    from pip._internal.operations.install.wheel import PipScriptMaker
    from pip._vendor.distlib.util import get_export_entry
    import pip._vendor.distlib.scripts as official
    import pip._vendor.distlib.util as official_util
    import pip._internal.operations.install.wheel as official_wheel
    require(all(Path(module.__file__).absolute() == clone_site / relative
                for module, relative in ((official, MAKER_SOURCE), (official_util, MAKER_SOURCES[1]),
                                         (official_wheel, MAKER_SOURCES[2]))),
            'official script generator import escaped the clone')
    require(Path(official.__file__).absolute() == clone_site / MAKER_SOURCE
            and ordinary(Path(official.__file__)) == ordinary(site / MAKER_SOURCE), 'ScriptMaker origin or bytes differ')
    rendered = Path(str(output) + '.rendered')
    rendered.mkdir(exist_ok=False)
    maker = PipScriptMaker(None, str(rendered))
    maker.executable = str(clone / 'bin/python')
    maker.variants, maker.clobber, maker.set_mode = {''}, False, True
    replacements, reports = {}, []
    for row in active:
        expected_path = rendered / row['name']
        if row['wheel_data_script'] is not None:
            expected = render_data_script(row['wheel_data_script'], expected_path, clone, maker, official_wheel)
        else:
            specification = row['name'] + ' = ' + row['callable']
            made = maker.make(specification)
            require(made == [str(expected_path)], 'ScriptMaker emitted an unexpected path/variant')
            entry = get_export_entry(specification)
            expected = maker._get_shebang('utf-8') + maker._get_script_text(entry).encode('utf-8')
        raw = ordinary(expected_path)
        require(raw == expected and str(source).encode() not in raw, 'ScriptMaker output or target differs')
        replacements[row['name']] = raw
        reports.append(dict(name=row['name'], callable=row['callable'], wheel_data_script=row['wheel_data_script'],
            source=row['source_pin'],
            generated=pin(expected_path), target=str(clone / 'bin' / row['name']),
            new_bytes=len(raw), new_sha256=sha(raw), owners=row['owners']))
    record_outputs = {}
    for relative, raw in records.items():
        entries, lines = record_rows(raw)
        changed = []
        for row in active:
            for owner in row['owners']:
                if owner['record_relative'] != relative:
                    continue
                index = owner['row_index']
                require(entries[index] == owner['row'], 'copied RECORD launcher row differs')
                body = replacements[row['name']]
                digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode()
                ending = '\r\n' if lines[index].endswith(b'\r\n') else '\n'
                stream = io.StringIO(newline='')
                csv.writer(stream, lineterminator=ending).writerow([entries[index][0], 'sha256=' + digest, str(len(body))])
                lines[index] = stream.getvalue().encode('utf-8')
                changed.append(index)
        new = b''.join(lines)
        _, old_lines = record_rows(raw)
        _, new_lines = record_rows(new)
        require(all(left == right for index, (left, right) in enumerate(zip(old_lines, new_lines))
                    if index not in changed), 'nonlauncher RECORD row changed')
        record_outputs[relative] = new
    # Complete all validation/rendering before touching the copied installation.
    for row in active:
        target = clone / 'bin' / row['name']
        writable_payload(target, clone, source / 'bin' / row['name'])
        require_pin(target, row['source_pin'])
        target.write_bytes(replacements[row['name']])
        require(ordinary(target) == replacements[row['name']], 'launcher readback differs')
    for relative, raw in record_outputs.items():
        writable_payload(clone / relative, clone, source / relative)
        require(ordinary(clone / relative) == records[relative], 'copied RECORD changed before update')
        (clone / relative).write_bytes(raw)
        require(ordinary(clone / relative) == raw, 'RECORD readback differs')
    after = inventory(clone)
    allowed = {'bin/' + row['name'] for row in active} | set(records)
    require(set(before) == set(after) and all(before[name] == after[name] for name in before if name not in allowed),
            'nonlauncher clone payload changed')
    require(canonical(plan_scripts(source, audit)) == canonical(plan['scripts'])
            and canonical(maker_source_pins(source, audit)) == canonical(plan['scriptmaker_sources']),
            'live source changed during clone relocation')
    return dict(kind='pr6302_archive_console_relocation', version=1, source_venv=str(source), clone_venv=str(clone),
        interpreter=str(clone / 'bin/python'), scriptmaker=pin(Path(official.__file__)),
        full_clone_before_sha256=sha(canonical(before)), full_clone_after_sha256=sha(canonical(after)),
        nonlauncher_payloads_unchanged=True, source_inputs_unchanged=True, scripts=reports,
        records=[dict(path=relative, before_sha256=sha(records[relative]), after_sha256=sha(raw),
                      changed_rows=[owner['row_index'] for row in active for owner in row['owners']
                                    if owner['record_relative'] == relative]) for relative, raw in record_outputs.items()],
        project_scripts_deferred=sorted(OWN))


def installed_script_rows(clone, *, data_scripts=None):
    """Read final installation metadata without importing installed packages."""
    site = source_site(clone)
    scripts = {name: [] for name in launcher_names(clone)}
    distributions, identities = [], set()
    aliases = {'pip', 'pip3', 'pip3.13', 'pip-3.13'}
    data_scripts = {} if data_scripts is None else data_scripts
    require(site.parent.name == 'python3.13', 'reviewed final interpreter version differs')
    for folder in sorted(site.glob('*.dist-info')):
        require(folder == folder.resolve() and folder.is_dir(), 'distribution directory alias refused')
        metadata = ordinary(folder / 'METADATA')
        headers = BytesParser().parsebytes(metadata, headersonly=True)
        require(len(headers.get_all('Name', [])) == len(headers.get_all('Version', [])) == 1,
                'distribution requires unique name and version')
        name = re.sub(r'[-_.]+', '-', headers['Name']).lower()
        version = headers['Version']
        require(name not in identities, 'duplicate installed distribution identity')
        identities.add(name)
        record = folder / 'RECORD'
        record_raw = ordinary(record)
        rows, _ = record_rows(record_raw)
        targets = {}
        for index, entry in enumerate(rows):
            require(entry[0] and not Path(entry[0]).is_absolute(), 'absolute or empty final RECORD target refused')
            target = Path(os.path.abspath(site / entry[0]))
            require(target.is_relative_to(clone) and target.parent == target.parent.resolve(),
                    'final RECORD target escapes physical clone')
            require(target not in targets, 'duplicate final RECORD target')
            targets[target] = (index, entry)
        own_metadata = targets.get(folder / 'METADATA')
        require(own_metadata is not None, 'distribution metadata lacks a RECORD row')
        hashed_payload(metadata, own_metadata[1][1], own_metadata[1][2])
        distributions.append(dict(name=name, version=version, record=pin(record)))
        points_path = folder / 'entry_points.txt'
        points = {}
        if points_path.exists():
            points_row = targets.get(points_path)
            require(points_row is not None, 'entry points lack a RECORD row')
            hashed_payload(ordinary(points_path), points_row[1][1], points_row[1][2])
            points = entry_points(points_path)
        require(all(name in scripts for name in points),
                'declared console entrypoint is missing or is not a Python launcher')
        for target, (index, entry) in targets.items():
            if target.parent != clone / 'bin' or target.name not in scripts:
                continue
            raw = writable_payload(target, clone)
            hashed_payload(raw, entry[1], entry[2])
            value = points.get(target.name)
            if value is None and name == 'pip' and version == '25.0.1' and target.name in aliases:
                require(points.get('pip') == points.get('pip3') == PIP_CALLABLE, 'final pip alias callable differs')
                value = PIP_CALLABLE
            packaged = data_scripts.get(target.name)
            if packaged is not None:
                require(value is None and (name, version) == DATA_SCRIPTS[target.name][:2],
                        'final wheel-script owner or undeclared callable differs')
            else:
                require(type(value) is str and re.fullmatch(ENTRYPOINT, value),
                        'final launcher lacks a literal declared callable: ' + target.name)
            scripts[target.name].append(dict(name=name, version=version, callable=value,
                record=pin(record), row_index=index, row=entry, metadata=pin(folder / 'METADATA'),
                entry_points=pin(points_path) if points_path.exists() else None))
    require(scripts and OWN.issubset(scripts), 'final project launchers are missing')
    result = []
    for name, owners in sorted(scripts.items()):
        require(owners, 'unowned final Python launcher: ' + name)
        callables = {owner['callable'] for owner in owners}
        require(len(callables) == 1, 'final shared launcher callable conflict')
        require(all((owner['name'] == 'data-sheets-schema') is (name in OWN) for owner in owners),
                'final own-project launcher scope differs')
        result.append(dict(name=name, callable=next(iter(callables)), owners=owners,
                           wheel_data_script=data_scripts.get(name),
                           installed=pin(clone / 'bin' / name)))
    require(set(data_scripts).issubset(scripts), 'final reviewed wheel script is missing')
    return result, maker_source_pins(clone, dict(distributions=distributions))


def verify_scripts(clone, output, *, source, plan):
    """Render official launchers in external evidence only; do not mutate clone."""
    require(clone == clone.resolve() and clone.is_dir()
            and Path(sys.executable).absolute() == clone / 'bin/python' and Path(sys.prefix) == clone
            and sys.flags.isolated and sys.dont_write_bytecode, 'verification requires clone/bin/python -I -B')
    require(not output.is_relative_to(clone), 'verification evidence must be external')
    audit = json.loads(require_pin(Path(plan['audit']['path']), plan['audit']))
    require(plan['source_venv'] == str(source) and sha(ordinary(Path(__file__))) == plan['helper_sha256']
            and canonical(plan_scripts(source, audit)) == canonical(plan['scripts']),
            'final verification original plan or source changed')
    packaged = {row['name']: row['wheel_data_script'] for row in plan['scripts']
                if row['wheel_data_script'] is not None}
    require(set(packaged) == set(DATA_SCRIPTS), 'final reviewed wheel-script roster differs')
    rows, source_pins = installed_script_rows(clone, data_scripts=packaged)
    require(canonical(maker_source_pins(source, audit)) == canonical(plan['scriptmaker_sources']),
            'original script generator source changed')
    require(len(source_pins) == len(plan['scriptmaker_sources']), 'final generator source roster differs')
    for current, original in zip(source_pins, plan['scriptmaker_sources']):
        require_pin(Path(current['path']), original)
    before = inventory(clone)
    from pip._internal.operations.install.wheel import PipScriptMaker
    from pip._vendor.distlib.util import get_export_entry
    import pip._vendor.distlib.scripts as official
    import pip._vendor.distlib.util as official_util
    import pip._internal.operations.install.wheel as official_wheel
    site = source_site(clone)
    for module, relative, expected_pin in zip((official, official_util, official_wheel), MAKER_SOURCES, source_pins):
        require(Path(module.__file__).absolute() == site / relative, 'final ScriptMaker import escaped clone')
        require_pin(Path(module.__file__), expected_pin)
    rendered = Path(str(output) + '.rendered')
    rendered.mkdir(exist_ok=False)
    maker = PipScriptMaker(None, str(rendered))
    maker.executable = str(clone / 'bin/python')
    maker.variants, maker.clobber, maker.set_mode = {''}, False, True
    reports = []
    for row in rows:
        expected_path = rendered / row['name']
        if row['wheel_data_script'] is not None:
            expected = render_data_script(row['wheel_data_script'], expected_path, clone, maker, official_wheel)
        else:
            specification = row['name'] + ' = ' + row['callable']
            require(maker.make(specification) == [str(expected_path)], 'final ScriptMaker emitted an unexpected path')
            entry = get_export_entry(specification)
            expected = maker._get_shebang('utf-8') + maker._get_script_text(entry).encode('utf-8')
        raw = ordinary(expected_path)
        require(raw == expected, 'final official rendering differs')
        require(ordinary(clone / 'bin' / row['name']) == raw,
                'installed launcher differs from exact clone interpreter rendering: ' + row['name'])
        reports.append(dict(**row, rendered=pin(expected_path)))
    after = inventory(clone)
    require(before == after, 'read-only launcher verification changed the clone')
    require(canonical(plan_scripts(source, audit)) == canonical(plan['scripts']),
            'original source or wheel-script cache changed during final verification')
    return dict(kind='pr6302_archive_console_verification', version=1, clone_venv=str(clone),
                interpreter=str(clone / 'bin/python'), scriptmaker_sources=source_pins,
                scripts=reports, clone_unchanged=True, clone_inventory_sha256=sha(canonical(after)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('plan', 'relocate', 'verify'))
    parser.add_argument('--source-venv', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--audit-sha256')
    parser.add_argument('--clone-venv', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--plan-sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.output == args.output.absolute() and args.output.parent == args.output.parent.resolve()
            and not args.output.exists() and not args.output.is_symlink(), 'fresh physical external output required')
    require(args.source_venv is not None and args.source_venv == args.source_venv.resolve()
            and not args.output.is_relative_to(args.source_venv), 'physical source and external output required')
    if args.mode == 'plan':
        raw = ordinary(args.audit)
        require(sha(raw) == args.audit_sha256, 'explicit audit pin differs')
        value = dict(kind='pr6302_archive_console_plan', version=1, source_venv=str(args.source_venv),
            audit=pin(args.audit), helper_sha256=sha(ordinary(Path(__file__))),
            scriptmaker_sources=maker_source_pins(args.source_venv, json.loads(raw)),
            scripts=plan_scripts(args.source_venv, json.loads(raw)))
    else:
        raw = ordinary(args.plan)
        require(sha(raw) == args.plan_sha256, 'explicit script plan pin differs')
        plan = json.loads(raw)
        require(plan['kind'] == 'pr6302_archive_console_plan' and type(plan['version']) is int
                and plan['version'] == 1 and plan['source_venv'] == str(args.source_venv), 'script plan identity differs')
        if args.mode == 'relocate':
            value = relocate_scripts(args.source_venv, args.clone_venv, plan, args.output)
        else:
            value = verify_scripts(args.clone_venv, args.output, source=args.source_venv, plan=plan)
        value['plan_sha256'] = args.plan_sha256
    print(json.dumps(save(args.output, value), sort_keys=True))


if __name__ == '__main__':
    main()
