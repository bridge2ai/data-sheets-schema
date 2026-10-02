"""Offline identity/normalizer check for this fixed draft, never an approval gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_sheets_schema.duplicate_keys import duplicate_keys_in
from data_sheets_schema.evaluation_context import PREDICATES, context_digest, load_context


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify(root: Path, packet: Path) -> dict:
    """Check committed content against the manifest; no writes or network calls."""
    manifest_bytes = (packet / 'review_manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest['status'] == 'DRAFT_PENDING_HUMAN_SCIENTIFIC_REVIEW', 'draft status changed')
    require(manifest['human_review_status'] == 'pending', 'human review status changed')
    require(manifest['evaluation_authorized'] is False, 'draft cannot authorize evaluation')
    projects = {'AI_READI', 'CHORUS', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC'}
    require(set(manifest['contexts']) == projects, 'five contexts required')
    require(set(manifest['sources']) == projects, 'five source bundles required')

    def read_pin(relative: str, pin: dict) -> bytes:
        path = (root / relative).resolve()
        require(path.is_relative_to(root.resolve()), f'path outside repository: {relative}')
        raw = path.read_bytes()
        require(digest(raw) == pin['sha256'], f'SHA256 mismatch: {relative}')
        require(len(raw) == pin['bytes'], f'byte count mismatch: {relative}')
        return raw

    for name, pin in manifest['reviewed_input_pins'].items():
        read_pin(name, pin)
    for name, pin in manifest['artifacts'].items():
        read_pin(name, pin)
    source_lines = {}
    for project, pin in manifest['sources'].items():
        source_lines[project] = read_pin(pin['path'], pin).splitlines(keepends=True)
        require(len(source_lines[project]) == pin['physical_lines'], f'line count: {project}')

    evidence = json.loads((packet / 'evidence.json').read_bytes())
    require(set(evidence['decisions']) == projects, 'five decision sets required')
    unknowns = []
    for project, pin in manifest['contexts'].items():
        read_pin(pin['path'], pin)
        path = root / pin['path']
        require(not duplicate_keys_in(path), f'duplicate context key: {project}')
        normalized = load_context(path)
        require(set(normalized) == PREDICATES, f'seven predicates required: {project}')
        require(context_digest(normalized) == pin['normalized_context_sha256'], f'normalized digest: {project}')
        values = {name: declaration['value'] for name, declaration in normalized.items()}
        require(values == pin['values'], f'predicate values: {project}')
        require(set(evidence['decisions'][project]) == PREDICATES, f'seven decisions required: {project}')
        require(pin['human_review']['status'] == 'pending', f'human review not pending: {project}')
        require(pin['human_review']['reviewer'] is None, f'draft names a reviewer: {project}')
        require(pin['human_review']['approved_context_sha256'] is None, f'draft approval: {project}')
        for name, declaration in normalized.items():
            decision = evidence['decisions'][project][name]
            require(decision['value'] is declaration['value'], f'decision value: {project}.{name}')
            require(bool(decision['citation_ids']), f'citations missing: {project}.{name}')
            for citation_id in decision['citation_ids']:
                require(evidence['citations'][citation_id]['project'] == project,
                        f'cross-project citation: {project}.{name}')
            if declaration['value'] is None:
                unknowns.append(f'{project}.{name}')

    for name, citation in evidence['citations'].items():
        project = citation['project']
        require(citation['bundle_path'] == manifest['sources'][project]['path'], f'bundle path: {name}')
        lines = source_lines[project]
        first, last = citation['start_line'], citation['end_line']
        require(1 <= first <= last <= len(lines), f'citation bounds: {name}')
        headers = [index for index in range(first) if lines[index].startswith(b'FILE: ')]
        require(bool(headers), f'FILE header missing: {name}')
        header = headers[-1]
        require(header + 1 == citation['file_header_line'], f'FILE header line: {name}')
        require(lines[header].decode().strip() == 'FILE: ' + citation['source_filename'],
                f'source filename: {name}')
        require(not any(line.startswith(b'FILE: ') for line in lines[first:last]),
                f'citation crosses a source boundary: {name}')
        excerpt = b''.join(lines[first - 1:last])
        require(digest(excerpt) == citation['excerpt_sha256'], f'excerpt SHA256: {name}')
        require(excerpt.decode() == citation['excerpt'], f'excerpt text: {name}')

    require(manifest['contexts']['CHORUS']['sha256'] ==
            'c20d016a74e5850bf8e6eb9a04ac86f6ed086f6de862b6f1c92cdcfcefe9f26e',
            'prior CHORUS context must remain byte-identical')
    require(manifest['contexts']['CHORUS']['normalized_context_sha256'] ==
            '9dbc7a148f43e37b20867fa933bf82cb36f8976ebc0a7faaef71dd52c766bc43',
            'prior CHORUS normalized context must remain identical')
    return {'identity_checks': 'passed', 'contexts_loaded_by_existing_normalizer': len(projects),
            'predicate_declarations': sum(len(d) for d in evidence['decisions'].values()),
            'citations_checked': len(evidence['citations']), 'unresolved_predicates': sorted(unknowns),
            'manifest_sha256': digest(manifest_bytes), 'human_review_status': 'pending',
            'evaluation_authorized': False}


if __name__ == '__main__':
    packet_path = Path(__file__).resolve().parent
    try:
        print(json.dumps(verify(packet_path.parents[1], packet_path), indent=2))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        raise SystemExit(f'Draft identity check failed: {exc}') from exc
