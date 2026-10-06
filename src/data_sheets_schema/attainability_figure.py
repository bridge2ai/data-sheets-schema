"""Categorical source-state figures from explicit checked aggregation sidecars.

This consumer never supplies source readings, scores, applicability or a cohort.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, fields
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import stat
import xml.etree.ElementTree as ET

from . import attainability_aggregation as aggregation
from .attainability import identical

FORMAT = 'd4d-attainability-figure-v1'
COLORS = {'supported': '#b8dbca', 'partly_supported': '#f2dc8c',
          'not_stated_in_source': '#e9c6b6', 'unknown': '#e0e0e0', 'conflict': '#cbb6df'}
LABELS = {'supported': 'Declared source supported', 'partly_supported': 'Declared partly supported',
          'not_stated_in_source': 'Declared source absent', 'unknown': 'Source state unknown',
          'conflict': 'Conflicting source readings'}
LIMITATIONS = (
    'Colors show declared source states, not a performance scale or scientific validation.',
    'Recorded scores, applicability and source states are separate dimensions.',
    'A supported zero is not a proven generator omission; an absent positive score is a review finding only.',
    'Captured integrity does not authenticate scientific readings, scope decisions or provider activity.',
    'Explicit row order is retained; unlike rubrics, denominators and selections are not pooled or ranked.',
)


@dataclass(frozen=True)
class Limits:
    envelope_bytes: int = 416 * aggregation.MIB
    artifact_bytes: int = 32 * aggregation.MIB
    svg_bytes: int = 8 * aggregation.MIB
    total_output_bytes: int = 128 * aggregation.MIB
    rows: int = 256
    items_per_row: int = 50
    rows_per_page: int = 4

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or not 0 < value <= field.default:
                raise ValueError('invalid or increased figure limit: ' + field.name)


DEFAULT_LIMITS = Limits()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class _File:
    spelling: str
    absolute: str
    resolved: str
    raw: bytes
    identity: tuple

    def pin(self):
        return {'path': self.spelling, 'absolute': self.absolute, 'resolved': self.resolved,
                'bytes': len(self.raw), 'sha256': _sha(self.raw), 'file_identity': list(self.identity)}

    def verify(self):
        now = _read(self.absolute, len(self.raw))
        if (now.resolved, now.identity, now.raw) != (self.resolved, self.identity, self.raw):
            raise ValueError('captured file changed: ' + self.spelling)


def _read(path, cap):
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ValueError('select a nonblank file path')
    absolute = Path(path).absolute()
    resolved = absolute.resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > cap:
        raise ValueError('expected bounded regular sidecar or implementation file')
    fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > cap:
            raise ValueError('expected bounded regular file')
        raw = stream.read(cap + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > cap or _identity(before) != _identity(after):
        raise ValueError('file changed or exceeds byte bound')
    if absolute.resolve(strict=True) != resolved or _identity(resolved.stat()) != _identity(after):
        raise ValueError('file identity changed during capture')
    return _File(str(path), str(absolute), str(resolved), raw, _identity(after))


def _checked(raw, limits):
    """Pure captured replay; saved report fields are never accepted on their own."""
    if type(limits) is not Limits:
        raise TypeError('expected fixed figure Limits')
    envelope = aggregation._json(raw, aggregation.DEFAULT_LIMITS, limits.envelope_bytes)
    aggregation._object(envelope, 'capture report', 'attainability sidecar')
    report = aggregation.recheck_captured(envelope['capture'])
    if not identical(report, envelope['report']):
        raise ValueError('saved report differs from captured derivation')
    if len(report['rows']) > limits.rows or any(
            len(row['source_inventory']) > limits.items_per_row for row in report['rows']):
        raise ValueError('figure row/item limit exceeded')
    return envelope, aggregation.canonical(report)


@dataclass(frozen=True)
class _Prepared:
    selected: _File
    implementation: tuple[_File, ...]
    checked_payload: bytes
    limits: Limits

    def report(self):
        return json.loads(self.checked_payload)


def prepare(path, *, limits=DEFAULT_LIMITS):
    """Capture one explicit sidecar, checking the complete report against its bytes."""
    if type(limits) is not Limits:
        raise TypeError('expected fixed figure Limits')
    selected = _read(path, limits.envelope_bytes)
    implementation = tuple(_read(p, aggregation.DEFAULT_LIMITS.source_bytes)
                           for p in (__file__, *(actual for _, actual in aggregation._SOURCE_FILES)))
    _, report = _checked(selected.raw, limits)
    for file in (selected, *implementation):
        file.verify()
    return _Prepared(selected, implementation, report, limits)


def _number(value):
    return '—' if value is None else str(value)


def _visible(value):
    # XML 1.0 cannot represent arbitrary JSON control characters. Display them
    # explicitly; the complete original values remain in checked_report.json.
    return ''.join(c if c in '\n\t' or (0x20 <= ord(c) <= 0xD7FF) or
                   (0xE000 <= ord(c) <= 0xFFFD) or (0x10000 <= ord(c) <= 0x10FFFF)
                   else f'\\u{ord(c):04x}' for c in str(value))


def _short(value, maximum=120):
    text = _visible(value).replace('\n', ' ').replace('\r', ' ')
    return text if len(text) <= maximum else text[:maximum-1] + '…'


def _cell_title(row, item):
    marker = item['item_id'] in {x['item_id'] for x in row['absent_positive_scores']}
    return _visible(json.dumps({'item': item,
        'display': f"{_number(item['recorded_score'])} / {LABELS[item['final_status']].lower()}",
        'recorded_absent_positive_review_finding': marker,
        'row_state': row['state'], 'row_reasons': row['reasons']}, ensure_ascii=False, sort_keys=True))


def _svg(rows, offset, page, cap):
    titles = {}
    title_bytes = 0
    for position, row in enumerate(rows):
        for n, item in enumerate(row['source_inventory']):
            title = _cell_title(row, item)
            title_bytes += len(title.encode('utf-8'))
            if title_bytes > cap // 2:
                raise ValueError('figure accessible-label byte limit exceeded')
            titles[f'row-{offset + position + 1}-item-{n + 1}'] = title
    from matplotlib.figure import Figure
    from matplotlib import rc_context
    from matplotlib.patches import Patch, Rectangle
    grid_heights = [.58 * ((len(row['source_inventory']) + 9) // 10) for row in rows]
    height = 1.8 + sum(.9 + grid + .4 for grid in grid_heights)
    with rc_context({'svg.fonttype': 'none', 'svg.hashsalt': FORMAT,
                     'text.usetex': False, 'text.parse_math': False}):
        fig = Figure(figsize=(16, height))
        cursor = height - 1
        for position, (row, grid_height) in enumerate(zip(rows, grid_heights)):
            bottom = cursor - .9 - grid_height
            axis = fig.add_axes((.05, bottom / height, .9, grid_height / height))
            cursor = bottom - .4
            index = offset + position
            items = row['source_inventory']; lines = (len(items) + 9) // 10
            axis.set_xlim(0, 10); axis.set_ylim(lines, 0); axis.set_axis_off()
            b = row['basis']; h = row['historical_bases']
            reason = ', '.join(x['code'] for x in row['reasons']) or 'none'
            axis.set_title(_short(f"Row {index + 1} | {row['evaluation']['path']}") + '\n' +
                f"Evaluation {row['evaluation']['sha256'][:12]} | Policy {row['policy']['sha256'][:12]} | "
                f"{row['state']} | row reasons: {_short(reason, 100)}\n" +
                f"Recorded total {_number(h['total'])}; fixed max {_number(h['fixed_max'])}; "
                f"N/A-adjusted max {_number(h['adjusted_max'])}; supported-item basis "
                f"{_number(b['attained'])}/{_number(b['attainable'])}", fontsize=9, loc='left', pad=8)
            for n, item in enumerate(items):
                col, line = n % 10, n // 10
                gid = f'row-{index + 1}-item-{n + 1}'
                patch = Rectangle((col, line), .97, .92, facecolor=COLORS[item['final_status']],
                                  edgecolor='#555555', linewidth=.5, gid=gid)
                axis.add_patch(patch)
                applicability = {'applicable': '', 'not_applicable': 'N/A', 'unknown': 'Applicability ?'}[item['applicability']]
                marker = ' | Review *' if item['item_id'] in {x['item_id'] for x in row['absent_positive_scores']} else ''
                axis.text(col + .485, line + .46,
                          f"{_short(item['item_id'], 30)}\n{_number(item['recorded_score'])} / {_number(item['maximum'])}\n{applicability}{marker}",
                          ha='center', va='center', fontsize=8)
        fig.suptitle(f'Declared source states — page {page}\n'
                     'Recorded score / maximum; — means null. N/A and applicability ? are independent of color.', fontsize=11)
        fig.legend(handles=[Patch(facecolor=COLORS[s], label=LABELS[s]) for s in COLORS],
                   loc='lower center', ncol=3, fontsize=8, bbox_to_anchor=(.5, .3 / height))
        fig.text(.5, .15 / height, 'Scientific readings are not authenticated. * Existing absent-positive review finding; no inferred quality verdict.',
                 ha='center', fontsize=8)
        stream = io.BytesIO(); fig.savefig(stream, format='svg', metadata={'Date': None, 'Description': ' '.join(LIMITATIONS)})
    # Full state/reasons are available in each SVG cell's accessible title.
    ns = 'http://www.w3.org/2000/svg'; ET.register_namespace('', ns)
    root = ET.fromstring(stream.getvalue())
    for element in root.iter():
        if element.attrib.get('id') in titles:
            title = ET.Element(f'{{{ns}}}title'); title.text = titles[element.attrib['id']]; element.insert(0, title)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def _csv(rows, cap):
    rows = iter(rows)
    first = next(rows)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(first), lineterminator='\n')
    writer.writeheader()
    output = bytearray(stream.getvalue().encode('utf-8'))
    def append(row):
        stream.seek(0); stream.truncate(0)
        # Every cell is a JSON value: null, zero, booleans and nested reasons
        # remain distinct. Quoted JSON strings cannot become spreadsheet formulas.
        writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                         for key, value in row.items()})
        raw = stream.getvalue().encode('utf-8')
        if len(output) + len(raw) > cap:
            raise ValueError('figure CSV byte limit exceeded')
        output.extend(raw)
    append(first)
    for row in rows:
        append(row)
    return bytes(output)


def _artifacts(report, payload, limits):
    artifacts = {}; total = 0
    def add(name, raw, cap=None):
        nonlocal total
        if len(raw) > (limits.artifact_bytes if cap is None else min(cap, limits.artifact_bytes)):
            raise ValueError('figure artifact byte limit exceeded: ' + name)
        total += len(raw)
        if total > limits.total_output_bytes:
            raise ValueError('figure total output byte limit exceeded')
        artifacts[name] = raw
    add('checked_report.json', payload + b'\n')
    rows = report['rows']
    add('rows.csv', _csv(({'selection_index': n + 1, **{k:v for k,v in row.items() if k != 'source_inventory'}}
                          for n, row in enumerate(rows)), limits.artifact_bytes))
    add('items.csv', _csv(({'selection_index': n + 1, 'evaluation': row['evaluation'],
                          'row_state': row['state'], 'row_reasons': row['reasons'], **item,
                          'absent_positive_review_finding': item['item_id'] in {x['item_id'] for x in row['absent_positive_scores']}}
                         for n, row in enumerate(rows) for item in row['source_inventory']), limits.artifact_bytes))
    for offset in range(0, len(rows), limits.rows_per_page):
        page = offset // limits.rows_per_page + 1
        add(f'attainability-{page:03}.svg', _svg(rows[offset:offset + limits.rows_per_page], offset, page, limits.svg_bytes), limits.svg_bytes)
    return artifacts


def _publish_file(directory_fd, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)


def publish(prepared, output_dir):
    """Publish exclusively; partial outputs are retained without a complete manifest."""
    if type(prepared) is not _Prepared:
        raise TypeError('expected prepare() result')
    expected_sources = tuple(str(Path(p).resolve(strict=True)) for p in
                             (__file__, *(actual for _, actual in aggregation._SOURCE_FILES)))
    if (type(prepared.selected) is not _File or type(prepared.implementation) is not tuple or
            any(type(file) is not _File for file in prepared.implementation) or
            tuple(file.resolved for file in prepared.implementation) != expected_sources):
        raise ValueError('prepared implementation source roster differs')
    # Even a constructed/replaced private object cannot introduce unchecked labels.
    envelope, payload = _checked(prepared.selected.raw, prepared.limits)
    if payload != prepared.checked_payload:
        raise ValueError('prepared report differs from captured derivation')
    report = json.loads(payload)
    original = Path(output_dir).absolute()
    if os.path.lexists(original):
        raise ValueError('figure destination must be new')
    parent = original.parent.resolve(strict=True); output = parent / original.name
    protected = aggregation.protected_paths(envelope) | {
        Path(file.resolved) for file in (prepared.selected, *prepared.implementation)}
    for name in protected:
        source = name.resolve()
        if output == source or output in source.parents or source in output.parents:
            raise ValueError('figure destination aliases a captured input or implementation')
    for file in (prepared.selected, *prepared.implementation):
        file.verify()
    artifacts = _artifacts(report, payload, prepared.limits)
    manifest = {'format': FORMAT, 'state': 'complete', 'selection_basis': 'one explicitly selected captured sidecar',
        'sidecar': prepared.selected.pin(), 'capture': {'sha256': _sha(aggregation.canonical(envelope['capture']))},
        'selection': report['selection'], 'checked_report': {'sha256': _sha(payload), 'bytes': len(payload)},
        'consumer_sources': [f.pin() for f in prepared.implementation],
        'runtime': {'python': platform.python_version(), 'matplotlib': importlib.metadata.version('matplotlib')},
        'rows': len(report['rows']), 'items': sum(len(r['source_inventory']) for r in report['rows']),
        'csv_encoding': 'Every data cell is a JSON value; decode after CSV parsing. Header names are plain text.',
        'limits': {f.name: getattr(prepared.limits, f.name) for f in fields(prepared.limits)},
        'limitations': list(LIMITATIONS),
        'artifacts': {n:{'sha256': _sha(raw), 'bytes': len(raw)} for n,raw in artifacts.items()}}
    manifest_raw = aggregation.canonical(manifest) + b'\n'
    if len(manifest_raw) > prepared.limits.artifact_bytes or sum(map(len, artifacts.values())) + len(manifest_raw) > prepared.limits.total_output_bytes:
        raise ValueError('figure manifest/total output byte limit exceeded')
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    def check_parent():
        if original.parent.resolve(strict=True) != parent or not os.path.samestat(os.fstat(parent_fd), parent.stat()):
            raise ValueError('publication parent changed')
    try:
        check_parent()
        for file in (prepared.selected, *prepared.implementation):
            file.verify()
        os.mkdir(original.name, mode=0o700, dir_fd=parent_fd)
        directory = os.open(original.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            def check_output():
                check_parent()
                if not os.path.samestat(os.fstat(directory), os.stat(original.name, dir_fd=parent_fd, follow_symlinks=False)):
                    raise ValueError('publication directory moved or replaced')
            check_output()
            for name, raw in artifacts.items():
                _publish_file(directory, name, raw)
            for name, raw in artifacts.items():
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                with os.fdopen(fd, 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read(len(raw)+1) != raw:
                        raise ValueError('published artifact changed: ' + name)
            for file in (prepared.selected, *prepared.implementation):
                file.verify()
            check_output()
            _publish_file(directory, 'manifest.json', manifest_raw)
            check_output()
        finally:
            os.close(directory)
    finally:
        os.close(parent_fd)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sidecar', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        publish(prepare(args.sidecar), args.output_dir)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
