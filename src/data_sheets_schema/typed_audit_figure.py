"""Standalone Figure 7 from explicit, reconstructed typed assemblies (#4340).

The checked base report remains unchanged. This module adds a plot and joined
count tables; it neither classifies prose nor assigns scientific labels.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile

from . import audit_batches, audit_protocol, typed_audit, typed_audit_report
from . import figure_publication as publication

FORMAT = 'typed_audit_figure_v1'
KINDS = tuple(sorted(audit_protocol.KINDS)) + ('untyped',)
LIMITATIONS = [
    'Findings use audit-declared kinds; missing kind remains untyped without prose classification.',
    'Findings and omission candidates are separate count units, not quality measures.',
    'Scientific support, applicability, novelty and exhaustive recall remain unverified.',
    'Explicit selected assemblies do not establish a cohort or independent observations.',
    'Captured hashes establish local content associations, not provider authentication.',
    'The protected historical keyword Figure 7 and its selected data remain unchanged.',
]


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
                'sha256': _sha(self.raw), 'bytes': len(self.raw), 'file_identity': list(self.identity)}

    def verify(self):
        current = _read(self.absolute, len(self.raw))
        if current.resolved != self.resolved or current.identity != self.identity or current.raw != self.raw:
            raise ValueError(f'captured file changed: {self.spelling}')


def _read(path, limit):
    spelling = str(path)
    if not spelling.strip():
        raise ValueError('selected assembly path must be nonblank')
    absolute = Path(path).absolute()
    resolved = absolute.resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError(f'expected bounded regular file: {spelling}')
    fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError(f'expected bounded regular file: {spelling}')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > limit or _identity(before) != _identity(after):
        raise ValueError(f'file changed or exceeds byte bound: {spelling}')
    if absolute.resolve(strict=True) != resolved or _identity(resolved.stat()) != _identity(after):
        raise ValueError(f'file identity changed during capture: {spelling}')
    return _File(spelling, str(absolute), str(resolved), raw, _identity(after))


@dataclass(frozen=True)
class PreparedFigure:
    """Frozen checked base payload; created from raw assemblies by prepare()."""
    checked_payload: bytes
    selected: tuple[_File, ...]
    implementation: tuple[_File, ...]

    def report(self):
        """A private parsed copy of the captured, reconstructed base report."""
        return json.loads(self.checked_payload)


def prepare(paths) -> PreparedFigure:
    """Read explicit ordered files and reconstruct one complete base report.

    No saved report or caller-supplied acceptance object is an input. Captured
    schema/source authorities embedded in an assembly are never reopened.
    """
    if isinstance(paths, (str, bytes, dict)):
        raise ValueError('select an explicit ordered iterable of assembly paths')
    selected = []
    total = 0
    for index, path in enumerate(paths):
        if index >= typed_audit_report.MAX_ASSEMBLIES:
            raise ValueError('too many selected assemblies')
        if not isinstance(path, (str, Path)):
            raise ValueError('select assembly file paths, not report objects')
        capture = _read(path, typed_audit.MAX_ASSEMBLY_BYTES)
        total += len(capture.raw)
        if total > typed_audit_report.MAX_SELECTED_BYTES:
            raise ValueError('selected assembly bytes exceed report bound')
        selected.append(capture)
    implementation = tuple(_read(path, typed_audit.MAX_ASSEMBLY_BYTES) for path in
                           (__file__, typed_audit_report.__file__, publication.__file__))
    checked = typed_audit_report.build_report([(file.spelling, file.raw) for file in selected])
    for file in [*selected, *implementation]:
        file.verify()
    return PreparedFigure(audit_batches.canonical_bytes(checked), tuple(selected), implementation)


def _counts(report):
    findings, candidates = [], []
    for assembly in report['assemblies']:
        common = {'selection_index': assembly['selection_index'],
                  'assembly_sha256': assembly['identity']['assembly_sha256'],
                  'assembly_raw_sha256': assembly['source']['sha256']}
        for kind in KINDS:
            findings.append({**common, 'kind': kind,
                'classification_basis': 'untyped' if kind == 'untyped' else 'audit_declared_kind',
                'count_unit': 'final_findings',
                'count': assembly['counts']['findings_by_declared_kind'][kind]})
        candidates.append({**common, 'count_unit': 'omission_candidates',
                           **{key: assembly['counts'][key] for key in
                              ('candidates', 'retained_candidates', 'dropped_candidates')}})
    return findings, candidates


def _csv(fields, rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _svg(report):
    # The existing repository dev environment supplies plotting. No dependency
    # is imported or installed merely by importing the consumer/checking inputs.
    from matplotlib.figure import Figure
    from matplotlib import rc_context
    from matplotlib.ticker import MaxNLocator
    count = len(report['assemblies'])
    with rc_context({'svg.fonttype': 'none', 'svg.hashsalt': FORMAT,
                     'text.usetex': False, 'text.parse_math': False}):
        fig = Figure(figsize=(16, max(4.5, count * .43 + 2.5)), layout='constrained')
        left, right = fig.subplots(1, 2, sharey=True, width_ratios=[3, 2])
        offsets = [0] * count
        colors = ['#31688e', '#35b779', '#9467bd', '#b8860b', '#e377c2', '#21918c',
                  '#d95f02', '#636363', '#5c6bc0', '#bdbdbd']
        for index, kind in enumerate(KINDS):
            color = '#bdbdbd' if kind == 'untyped' else colors[index % (len(colors) - 1)]
            values = [row['counts']['findings_by_declared_kind'][kind] for row in report['assemblies']]
            left.barh(range(count), values, left=offsets, label=kind.replace('_', ' '),
                      color=color, hatch='///' if kind == 'untyped' else None)
            offsets = [a + b for a, b in zip(offsets, values)]
        retained = [row['counts']['retained_candidates'] for row in report['assemblies']]
        dropped = [row['counts']['dropped_candidates'] for row in report['assemblies']]
        right.barh(range(count), retained, label='Retained candidates', color='#3182bd')
        right.barh(range(count), dropped, left=retained, label='Dropped candidates', color='#969696')
        labels = [f"{row['selection_index']} | {row['identity']['assembly_sha256'][:12]}"
                  for row in report['assemblies']]
        left.set_yticks(range(count), labels, fontsize=8)
        left.invert_yaxis()
        left.set_ylabel('Explicit selection index | canonical assembly hash prefix')
        for axis, totals, label in ((left, offsets, 'Final finding count'),
                                    (right, [a + b for a, b in zip(retained, dropped)], 'Omission candidate count')):
            axis.set_xlabel(label)
            axis.xaxis.set_major_locator(MaxNLocator(integer=True))
            axis.set_xlim(0, max(1, max(totals)) * 1.2)
            for position, total in enumerate(totals):
                axis.annotate(str(total), (total, position), xytext=(4, 0), textcoords='offset points',
                              va='center', fontsize=8)
        left.set_title('Declared finding kinds; absent kind stays untyped')
        right.set_title('Candidate dispositions (a different count unit)')
        left.legend(loc='upper left', bbox_to_anchor=(0, -.18), ncol=3, fontsize=8)
        right.legend(loc='upper left', bbox_to_anchor=(0, -.18), fontsize=8)
        fig.suptitle('Figure 7 — checked typed audit declarations\n'
                     'Scientific support, novelty and recall remain unverified; selection is not an inferred cohort.', fontsize=11)
        stream = io.BytesIO()
        fig.savefig(stream, format='svg', metadata={'Date': None, 'Description': ' '.join(LIMITATIONS)})
        return stream.getvalue()


def _artifacts(prepared, report):
    findings, candidates = _counts(report)
    common = ['selection_index', 'assembly_sha256', 'assembly_raw_sha256']
    return {'fig07_typed_audits.svg': _svg(report),
            'checked_audits.json': prepared.checked_payload,
            'checked_audits.csv': typed_audit_report.csv_bytes(report),
            'finding_counts.csv': _csv(common + ['kind', 'classification_basis', 'count_unit', 'count'], findings),
            'candidate_counts.csv': _csv(common + ['count_unit', 'candidates', 'retained_candidates', 'dropped_candidates'], candidates)}


def _protected(prepared, report):
    paths = {Path(file.resolved) for file in [*prepared.selected, *prepared.implementation]}
    # Names are protected without reading absent or changed historical schema
    # files; acceptance came only from the captured assembly closure.
    paths.update(Path(row['path']).resolve() for assembly in report['assemblies']
                 for row in assembly['identity']['schema_sources'])
    return paths


def _publish_file(directory_fd, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)


def publish(prepared: PreparedFigure, output_dir: str | Path):
    """Publish a fresh complete figure, or retain a distinguishable partial dir.

    Integrity reads recheck selected files but never derive new plot values.
    Existing files/directories and aliases are never replaced or cleaned up.
    """
    if not isinstance(prepared, PreparedFigure):
        raise ValueError('expected prepare() output from checked assembly bytes')
    expected = tuple(str(Path(p).resolve(strict=True)) for p in
                     (__file__, typed_audit_report.__file__, publication.__file__))
    if tuple(file.resolved for file in prepared.implementation) != expected:
        raise ValueError('prepared implementation source roster differs')
    output = Path(output_dir).absolute()
    if os.path.lexists(output):
        raise ValueError('figure destination must be new')
    output = output.parent.resolve(strict=True) / output.name
    report = prepared.report()
    for source in _protected(prepared, report):
        if output == source or output in source.parents or source in output.parents:
            raise ValueError('figure destination aliases a selected input or captured schema authority')
    for file in [*prepared.selected, *prepared.implementation]:
        file.verify()
    artifacts = _artifacts(prepared, report)
    manifest = {'format': FORMAT, 'state': 'complete',
                'selection_basis': 'explicit ordered raw assembly files',
                'selection': [file.pin() for file in prepared.selected],
                'consumer_sources': [file.pin() for file in prepared.implementation],
                'checked_base_report': {'format': report['format'], 'sha256': _sha(prepared.checked_payload),
                                       'bytes': len(prepared.checked_payload),
                                       'scope': 'Unchanged base export; the standalone consumer adds the plotted Figure 7.'},
                'assemblies': [{'selection_index': row['selection_index'], 'source': row['source'],
                                'assembly_sha256': row['identity']['assembly_sha256'],
                                'packet_sha256': row['identity']['packet_sha256']}
                               for row in report['assemblies']],
                'count_units': {'finding_counts.csv': 'final findings, each counted once by kind',
                                'candidate_counts.csv': 'declared omission candidates by disposition'},
                'limitations': list(LIMITATIONS),
                'artifacts': {name: {'sha256': _sha(raw), 'bytes': len(raw)} for name, raw in artifacts.items()}}
    with tempfile.TemporaryDirectory(prefix='d4d-typed-audit-figure-') as staging:
        for name, raw in artifacts.items():
            (Path(staging) / name).write_bytes(raw)
        for file in [*prepared.selected, *prepared.implementation]:
            file.verify()
    output.mkdir(mode=0o700)
    directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    committed = False
    try:
        if not os.path.samestat(os.fstat(directory), output.stat(follow_symlinks=False)):
            raise ValueError('publication directory identity changed')
        for name, raw in artifacts.items():
            _publish_file(directory, name, raw)
        for name, raw in artifacts.items():
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(fd, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read(len(raw) + 1) != raw:
                    raise ValueError(f'published artifact changed: {name}')
        def verify_completion():
            if not os.path.samestat(os.fstat(directory), output.stat(follow_symlinks=False)):
                raise ValueError('publication directory moved or replaced')
            for file in [*prepared.selected, *prepared.implementation]:
                file.verify()
            for name, raw in artifacts.items():
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                with os.fdopen(fd, 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read(len(raw) + 1) != raw:
                        raise ValueError(f'published artifact changed: {name}')
            if not os.path.samestat(os.fstat(directory), output.stat(follow_symlinks=False)):
                raise ValueError('publication directory moved or replaced')
        publication.complete(directory, 'manifest.json', audit_batches.canonical_bytes(manifest), verify_completion)
        committed = True
    finally:
        publication.close_descriptor(directory, committed=committed)
    return manifest
