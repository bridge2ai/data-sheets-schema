#!/usr/bin/env python3
"""Audit native scanner authority lineage. Inputs: frozen Git commits; output: JSON.
Serves helper1 native scanner pin review, 2026-11-12. Runs Git reads only; imports
no repository code, runs no tests, and writes only the requested new JSON report.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = 'e4985c1afcef9874be1c1e25736ce9d527af1428'
HEAD = '5d63d0a77dc43c064cfc2b376355f98009dd5b6e'
AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
SCANNER = '.claude/skills/d4d-generation-specificity-audit/scan.py'
PIN = 'bfdb5c86feb4c071ebf17e6ececa8fd60f1bc23bda98fefd42c0c211ecd7511a'
EXPECTED_CURRENT = 'b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558'
CHECKPOINTS = ('1a137b58860416a31618de44173180d021dfcc61',
               '382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b')
EXPECTED_LINEAGE = ('5503684eeaabe3305333d4eefb931f311f86c1e8',
                    'e282f05960a2b397844acb3ac5f140b1fe192cd8',
                    'd6f51f8ed3da7928e66e81fa48f47722a77bbdf5',
                    '033cd731f6d9a854143076a8bd13125d61101f92')
PROOF_HELPERS = ('_main_thread', 'launch_derivations', '_source_identity', '_own_callables', 'module_source_identity',
                 '_VerifiedBytesLoader', '_VerifiedBytesFinder', '_VerifiedAliasLoader',
                 '_verified_source_bytes', 'verified_source_module',
                 'loaded_verified_package_module', '_require_v2', 'dependency_identity',
                 '_package_roster', '_require_package_roster', 'require_committed',
                 'loaded_dependencies')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def definitions(raw):
    text = raw.decode('utf-8')
    lines = text.splitlines(keepends=True)
    result = {}
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [item.lineno for item in node.decorator_list])
            source = ''.join(lines[start - 1:node.end_lineno]).encode('utf-8')
            tree = ast.dump(node, include_attributes=False).encode('utf-8')
            result[node.name] = (source, tree, start, node.end_lineno)
    return result


def compare_definitions(before, after):
    old, new = definitions(before), definitions(after)
    rows = []
    for name in sorted(set(old) | set(new)):
        row = {'name': name, 'before_present': name in old, 'after_present': name in new}
        for label, values in (('before', old), ('after', new)):
            if name in values:
                source, tree, start, end = values[name]
                row[label + '_source_sha256'] = sha256(source)
                row[label + '_ast_sha256'] = sha256(tree)
                row[label + '_lines'] = [start, end]
        row['exact_source_equal'] = name in old and name in new and old[name][0] == new[name][0]
        row['normalized_ast_equal'] = name in old and name in new and old[name][1] == new[name][1]
        rows.append(row)
    return rows


def source_maps(raw):
    values = {}
    wanted = ('_NATIVE_V2_RENDER_SOURCES', '_NATIVE_V2_INTEGRATED_RENDER_SOURCES')
    for node in ast.parse(raw.decode('utf-8')).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in wanted:
            continue
        if not isinstance(node.value, ast.Dict):
            raise ValueError('source map is not a literal dictionary')
        mapping = {}
        for key, value in zip(node.value.keys, node.value.values):
            if key is None:
                if not isinstance(value, ast.Name) or value.id not in values:
                    raise ValueError('unrecognized source-map expansion')
                mapping.update(values[value.id])
            else:
                k, v = ast.literal_eval(key), ast.literal_eval(value)
                if type(k) is not str or type(v) is not str:
                    raise ValueError('source pin is not a pair of strings')
                mapping[k] = v
        values[target.id] = mapping
    if set(values) != set(wanted):
        raise ValueError('missing scanner source map')
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112'))
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[2] / 'notes/development_efficiency_20261111/handoffs/codex-h1-authority-audit-20261112.json')
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit('refusing to replace an existing evidence report')
    commands = []
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')

    def git(*parts):
        command = ['git', '-C', str(args.repo), *parts]
        completed = subprocess.run(command, env=env, capture_output=True, check=False)
        commands.append({'argv': command, 'returncode': completed.returncode,
                         'stdout': completed.stdout.decode('utf-8'),
                         'stderr': completed.stderr.decode('utf-8'),
                         'stdout_sha256': sha256(completed.stdout),
                         'stderr_sha256': sha256(completed.stderr)})
        if completed.returncode:
            raise RuntimeError('read-only Git command failed: ' + repr(parts))
        return completed.stdout

    source_cache = {}
    def source(commit, path):
        key = (commit, path)
        if key not in source_cache:
            source_cache[key] = git('show', commit + ':' + path)
        return source_cache[key]

    report = {'purpose': 'Reproducible source-pin history and narrow rendering-proof evidence',
              'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'repository': str(args.repo), 'baseline': BASE, 'candidate': HEAD,
              'helper_path': str(Path(__file__).resolve()),
              'helper_sha256': sha256(Path(__file__).read_bytes()),
              'restrictions': 'Read-only Git and Python AST parsing; no tests, scanners, repository imports, source edits or network.',
              'scope_limit': 'Rendering source proof only. Unchanged helpers do not establish whole-module semantic equality or native launch acceptance.',
              'raw_encoding': 'Command stdout/stderr decode exactly from JSON. Literal Unicode U+0040 is escaped in the JSON file.'}
    lineage = git('log', '--reverse', '--format=%H', BASE + '..' + HEAD, '--', AUTHORITY).decode().splitlines()
    if tuple(lineage) != EXPECTED_LINEAGE:
        raise ValueError('unexpected authority lineage')
    old_authority, new_authority = source(BASE, AUTHORITY), source(HEAD, AUTHORITY)
    if sha256(old_authority) != PIN or sha256(new_authority) != EXPECTED_CURRENT:
        raise ValueError('authority identity changed from the assigned audit inputs')
    report['baseline_authority_sha256'] = sha256(old_authority)
    report['candidate_authority_sha256'] = sha256(new_authority)
    report['lineage'] = []
    for commit in lineage:
        parent = git('rev-parse', commit + '^').decode().strip()
        raw = source(commit, AUTHORITY)
        prior = source(parent, AUTHORITY)
        files = git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()
        pin = source_maps(source(commit, SCANNER))['_NATIVE_V2_INTEGRATED_RENDER_SOURCES'][AUTHORITY]
        git('show', '--format=fuller', '--stat', commit)
        git('show', '--format=', commit, '--', AUTHORITY)
        report['lineage'].append({'commit': commit, 'parent': parent,
                                  'parent_authority_sha256': sha256(prior),
                                  'authority_sha256': sha256(raw),
                                  'scanner_authority_pin': pin,
                                  'scanner_touched': SCANNER in files,
                                  'changed_files': files,
                                  'pin_matches_source': pin == sha256(raw)})
    report['pin_history_stdout'] = git('log', '--format=%H %s', '-S', PIN, HEAD, '--', SCANNER).decode()
    report['net_authority_numstat'] = git('diff', '--numstat', BASE, HEAD, '--', AUTHORITY).decode()
    report['checkpoints'] = []
    for commit in CHECKPOINTS:
        pin = source_maps(source(commit, SCANNER))['_NATIVE_V2_INTEGRATED_RENDER_SOURCES'][AUTHORITY]
        digest = sha256(source(commit, AUTHORITY))
        report['checkpoints'].append({'commit': commit, 'authority_sha256': digest,
                                      'scanner_authority_pin': pin, 'pin_matches_source': pin == digest})
    baseline_scanner, candidate_scanner = source(BASE, SCANNER), source(HEAD, SCANNER)
    old_maps, new_maps = source_maps(baseline_scanner), source_maps(candidate_scanner)
    report['scanner_source_maps'] = {'baseline': old_maps, 'candidate': new_maps,
                                   'legacy_map_unchanged': old_maps['_NATIVE_V2_RENDER_SOURCES'] == new_maps['_NATIVE_V2_RENDER_SOURCES']}
    report['seven_other_integrated_pins'] = []
    for path, pin in sorted(new_maps['_NATIVE_V2_INTEGRATED_RENDER_SOURCES'].items()):
        if path == AUTHORITY:
            continue
        raw = source(HEAD, path)
        old_raw = source(BASE, path)
        report['seven_other_integrated_pins'].append({'path': path, 'expected_sha256': pin,
            'actual_sha256': sha256(raw), 'matches': sha256(raw) == pin,
            'baseline_sha256': sha256(old_raw), 'exact_source_equal_to_baseline': raw == old_raw})
    if len(report['seven_other_integrated_pins']) != 7:
        raise ValueError('integrated roster differs from expected eight-source contract')
    all_comparisons = compare_definitions(old_authority, new_authority)
    report['all_authority_top_level_comparisons'] = all_comparisons
    report['rendering_proof_helpers'] = [row for row in all_comparisons if row['name'] in PROOF_HELPERS]
    report['scanner_proof_function_comparisons'] = [row for row in compare_definitions(baseline_scanner, candidate_scanner)
        if row['name'] in ('_derive_native_v2_render', 'derive_native_shared_route')]
    report['semantic_change_summary'] = {
        EXPECTED_LINEAGE[0]: 'Adds source-bound launch-scoped schema-snapshot metadata reuse and lifetime/guard management.',
        EXPECTED_LINEAGE[1]: 'Clears tracked snapshot LRUs when donor state disappears or phase changes.',
        EXPECTED_LINEAGE[2]: 'Changes snapshot attestation from registry object identity to source name/path/digest plus fresh bytes; permits same-domain enabled reuse.',
        EXPECTED_LINEAGE[3]: 'Adds bounded immutable exact-source import syntax facts; live graph/policy decisions remain outside retention; cold fallback for unsupported producer state and small sources.'}
    report['synchronization_conclusion'] = {
        'fact': 'The four authority-changing commits omit the scanner file and all retain its old authority digest.',
        'inference': 'The scanner source dependency was not synchronized while authority changes landed; commit evidence does not identify motive or intentional waiver.'}
    report['commands'] = commands
    encoded = (json.dumps(report, indent=2, ensure_ascii=True) + '\n').replace(chr(64), '\\u0040').encode('utf-8')
    with args.out.open('xb') as stream:
        stream.write(encoded)
    persisted = args.out.read_bytes()
    if persisted != encoded or not persisted or chr(64).encode() in persisted:
        raise RuntimeError('persisted evidence verification failed')
    json.loads(persisted)
    print(json.dumps({'report': str(args.out), 'bytes': len(persisted), 'sha256': sha256(persisted),
                      'helper_sha256': report['helper_sha256'], 'git_commands': len(commands),
                      'unchanged_rendering_helpers': sum(row['exact_source_equal'] for row in report['rendering_proof_helpers']),
                      'seven_pin_matches': sum(row['matches'] for row in report['seven_other_integrated_pins'])}))


if __name__ == '__main__':
    main()
