#!/usr/bin/env python3
"""Inventory RC-1 reviewer dependencies, 2026-11-19.

Inputs: the assigned source checkout and current report checkout script tree.
Outputs: sanitized complete ripgrep matches and pinned file inventories in the
assigned scratch directory. Serves the owner-approved agy reviewer-kind change.
No test, native, network, repository mutation or operational driver calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


BASE = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
WORK = BASE / 'codex196-agy-reviewer-20261119'
REPORT = BASE / 'codex-development-efficiency-20261111'
SCRATCH = BASE / 'scratch-codex196-agy-reviewer-20261119'
PATTERNS = (
    'reviewer_kind', 'claude.{0,60}codex_cli', 'codex_cli.{0,60}claude',
    'native_launch_review', 'review.bundle', 'Claude and Codex',
    'Codex and Claude', 'independent.*Claude', 'Claude.*independent',
)


def clean(value):
    return value.replace(chr(64), '(at)')


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True, choices=('before', 'after'))
    args = parser.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    inventories = []
    for name, root, scopes in (
            ('worktree', WORK, ['src', 'tests', 'scripts', 'utils']),
            ('report-scripts', REPORT, ['scripts/adhoc'])):
        command = ['rg', '--json', '--no-ignore', '--hidden', '--ignore-case']
        for pattern in PATTERNS:
            command.extend(['--regexp', pattern])
        command.extend(scopes)
        completed = subprocess.run(command, cwd=root, capture_output=True,
                                   text=True, check=False)
        if completed.returncode not in (0, 1):
            raise RuntimeError(clean(completed.stderr))
        raw_path = SCRATCH / f'reviewer-inventory-{args.label}-{name}.jsonl'
        write_new(raw_path, clean(completed.stdout).encode())
        grouped = {}
        for line in completed.stdout.splitlines():
            event = json.loads(line)
            if event['type'] != 'match':
                continue
            data = event['data']
            relative = data['path']['text']
            text = data['lines'].get('text')
            grouped.setdefault(relative, []).append({
                'line': data['line_number'],
                'text': clean(text.rstrip()) if text else None,
            })
        files = []
        for relative, matches in sorted(grouped.items()):
            files.append(dict(pin(root / relative), relative=relative,
                              matches=matches))
        inventories.append({'name': name, 'root': str(root), 'scopes': scopes,
                            'command': command, 'returncode': completed.returncode,
                            'raw_matches': pin(raw_path), 'files': files})
    all_test_rows = [row for inventory in inventories
                    if inventory['name'] == 'worktree' for row in inventory['files']
                    if row['relative'].startswith('tests/test_')
                    and row['relative'].endswith('.py')]
    relevant_tests = sorted(row['relative'] for row in all_test_rows
                            if any(re.search('reviewer_kind|native_launch_review|review.bundle',
                                             match['text'] or '', re.I)
                                   for match in row['matches']))
    prescribed_tests = [
        'tests/test_native_launch_review.py', 'tests/test_native_review_bundle_v3.py',
        'tests/test_native_launch_sequence.py', 'tests/test_native_launch_sequence_paths.py',
        'tests/test_native_launch_sequence_signals.py', 'tests/test_native_launch_entry.py',
        'tests/test_native_sequence_start.py',
    ]
    assert all((WORK / relative).is_file() for relative in prescribed_tests)
    runbook = BASE / 'plans/native_post_merge_runbook_DRAFT_20261114.md'
    stale_runbook_lines = [{'line': number, 'text': clean(line)}
                          for number, line in enumerate(runbook.read_text().splitlines(), 1)
                          if (('reviewer_kind' in line and 'claude' in line)
                              or 'one independent Claude reviewer' in line
                              or 'review-claude.md' in line
                              or 'independent `codex_cli` and `claude` reviewers' in line)]
    result = {
        'purpose': 'RC-1 complete relevant-scope reviewer dependency inventory',
        'label': args.label,
        'ignored_and_hidden_included': True,
        'binary_policy': 'Default ripgrep binary detection; source text is searched.',
        'sanitization': 'Literal character 64 is replaced with (at) in saved search text.',
        'native_or_test_or_network_calls': False,
        'helper': pin(Path(__file__).resolve()),
        'active_builder': pin(REPORT / 'scripts/adhoc/post_merge_fast_path_20261117.py'),
        'inventories': inventories,
        'referencing_test_files': relevant_tests,
        'required_test_roster': sorted(set(relevant_tests + prescribed_tests)),
        'broad_search_false_positive_tests': sorted(set(row['relative'] for row in all_test_rows)
                                                   - set(relevant_tests)),
        'consistency_disposition': {
            'active_builder': 'R fast-path builder emits the D160 codex_cli and agy pair; generated text also names legacy accepted codex_cli plus claude.',
            'worktree_runbook_text': 'No active reviewer-kind runbook text found in tests or utils. The matched Markdown files are historical fixtures and witness reports.',
            'source_adapter': 'scripts/native_packet_review_inputs.py delegates to the running validator and imposes no second reviewer-kind roster.',
            'historical_map': 'scripts/adhoc/map_native_packet_20261112.py explicitly describes the historical v2 contract; unchanged.',
            'historical_report_provenance': [
                'codex196_rehearsal_report_20261119.py',
                'codex196_rehearsal_controls_20261119.py',
                'codex196_rehearsal_runbook_20261119.py',
                'codex196_prestage_command_list_20261119.py',
                'prestage_20261119_versions/command-list-13121d89606625eb.py',
            ],
            'historical_preservation': 'Recorded handoffs, evidence and dated report producers remain unchanged; they describe the pinned earlier source.',
            'external_runbook_followup': {
                'file': pin(runbook), 'stale_lines': stale_runbook_lines,
                'owner': 'Claude lead',
                'disposition': 'Explicitly outside this edit scope. Lead must update or regenerate the installed operational reviewer prose before use; the existing installer preserves installed paragraphs.',
            },
            'tests_executed_by_this_helper': False,
        },
    }
    destination = SCRATCH / f'reviewer-inventory-{args.label}.json'
    write_new(destination, (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'result': pin(destination),
                      'test_files': result['referencing_test_files'],
                      'file_counts': {row['name']: len(row['files']) for row in inventories}},
                     indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
