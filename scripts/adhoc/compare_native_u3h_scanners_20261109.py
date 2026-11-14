#!/usr/bin/env python3
"""Itemise U3-H scanner comparisons for the owner, 2026-11-09 (P3-1).

Inputs: completed scanner run directories for literal saved main, literal U3-F2,
and the candidate; optional explicitly supplementary F2 private composition.
Outputs: a fresh JSON evidence file, with source/tool/input identities, complete
raw arrays and occurrence-preserving comparisons. No scanner or project module
is executed. Historical d258611c5 acceptance is never changed or substituted.

Run with --help for arguments. The parent driver runs scans sequentially first.
An exit-2 literal F2 result stays incomplete even if its supplementary composition
derives. Exact object equality and coordinate-only observations are separate.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
MAIN = 'cf50d9a1c059f3b5030103378ccef33619475dde'
F2 = '77bfa23368af201b77585f334ed0456ed1d40f01'
SKILL = '.claude/skills/d4d-generation-specificity-audit'
ARRAYS = ('hits', 'violations', 'test_dependencies')
# The retained U5 source-export mask, used identically for each physical-input
# census. The entire committed Git roster is also retained, including entries
# outside this mask. No .gitignore rule is used to establish input completeness.
MASK = ('src', 'tests', 'utils', 'configs', '.claude', '.github', 'pyproject.toml',
        'Makefile', 'project', 'notes', 'scripts', 'CLAUDE.md', 'CLAUDE.local.md',
        'data/preprocessed/source_manifest.yaml')
ENV = dict(PATH='/usr/bin:/bin', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='',
           GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
           GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
GIT = ['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
       '-c', 'core.fsmonitor=false', '-c', 'protocol.allow=never']


def need(condition, message):
    if not condition:
        raise ValueError(message)


def quiet():
    need(not os.path.lexists(LOCK), 'quiet window is active')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def read_json(path):
    raw = path.read_bytes()
    need(bool(raw), 'empty JSON: ' + str(path))
    return json.loads(raw), sha(raw)


def physical(path, *, within=SCRATCH):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path
         and path.is_relative_to(within), 'nonphysical or unassigned input: ' + str(path))
    return path


def git(*args, cwd=ROOT):
    quiet()
    result = subprocess.run([*GIT, *args], cwd=cwd, env=ENV, capture_output=True,
                            check=True, timeout=60)
    quiet()
    return result.stdout


def option(command, name):
    need(isinstance(command, list) and command.count(name) == 1,
         'scanner command lacks a unique ' + name)
    index = command.index(name)
    need(index + 1 < len(command), 'scanner command has no value for ' + name)
    return command[index + 1]


def selected(relative):
    return any(relative == prefix or relative.startswith(prefix + '/') for prefix in MASK)


def source_inputs(tree, expected):
    """Pin committed identity and every physical input under the declared mask."""
    need(git('rev-parse', 'HEAD', cwd=tree).decode().strip() == expected,
         'source HEAD differs from recorded identity')
    git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
    raw = git('ls-tree', '-r', '-z', 'HEAD', cwd=tree)
    roster, by_path = [], {}
    for record in raw.split(b'\0'):
        if not record:
            continue
        left, raw_path = record.split(b'\t', 1)
        mode, kind, oid = left.decode('ascii').split()
        relative = raw_path.decode('utf-8', errors='strict')
        need(relative not in by_path, 'duplicate Git input path')
        row = dict(path=relative, mode=mode, kind=kind, git_oid=oid)
        roster.append(row)
        by_path[relative] = row
    physical_rows = []
    for relative, row in sorted(by_path.items()):
        if not selected(relative) or row['kind'] != 'blob':
            continue
        quiet()
        path = tree / relative
        info = path.lstat()
        if row['mode'] == '120000':
            need(stat.S_ISLNK(info.st_mode), 'tracked symlink replaced: ' + relative)
            payload = os.fsencode(os.readlink(path))
            need(path.resolve(strict=True).is_relative_to(tree),
                 'input symlink leaves source tree: ' + relative)
        else:
            need(stat.S_ISREG(info.st_mode) and not path.is_symlink(),
                 'tracked input is not a regular file: ' + relative)
            payload = path.read_bytes()
        oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
        need(oid == row['git_oid'], 'physical input differs from Git blob: ' + relative)
        physical_rows.append(dict(row, bytes=len(payload), sha256=sha(payload)))
    # Include ignored extras in this refusal. This is deliberately independent
    # of an ordinary rg/git-ls-files miss. Submodule roots are recorded by their
    # gitlink identity; their contents are outside this declared comparison.
    gitlinks = {path for path, row in by_path.items() if row['kind'] == 'commit'}
    extra = []
    for prefix in MASK:
        base = tree / prefix
        if not os.path.lexists(base):
            continue
        if base.is_dir() and not base.is_symlink():
            paths = []
            for folder, dirs, files in os.walk(base, followlinks=False):
                relative_folder = Path(folder).relative_to(tree).as_posix()
                if relative_folder in gitlinks:
                    dirs[:] = []
                    continue
                for name in tuple(dirs):
                    candidate = Path(folder) / name
                    if candidate.is_symlink():
                        paths.append(candidate)
                        dirs.remove(name)
                paths.extend(Path(folder) / name for name in files)
        else:
            paths = [base]
        extra.extend(path.relative_to(tree).as_posix() for path in paths
                     if path.relative_to(tree).as_posix() not in by_path)
    need(not extra, 'uncommitted/ignored scanner inputs found: ' + repr(sorted(set(extra))))
    git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
    return dict(commit=expected, tree=git('rev-parse', 'HEAD^{tree}', cwd=tree).decode().strip(),
                committed_roster=roster, committed_roster_sha256=sha(raw),
                committed_roster_encoding='git ls-tree -r -z HEAD',
                physical_input_mask=list(MASK), physical_inputs=physical_rows,
                physical_inputs_sha256=sha(encoded(physical_rows)),
                uncommitted_or_ignored_inputs=[], source_clean=True)


def load_run(label, directory, expected, tool_commit, *, supplementary=False):
    directory = physical(directory)
    run, run_sha = read_json(physical(directory / 'run.json'))
    need(run['source_commit'] == expected, label + ': unexpected source commit')
    need(run['tool_commit'] == tool_commit, label + ': candidate tool commit differs')
    need(run.get('exit_code') in (0, 1, 2), label + ': unsupported scanner exit')
    need(run.get('process_group_gone') is True and run.get('tool_unchanged') is True
         and run.get('tool_assets_unchanged') is True and 0 <= run['seconds'] < 3300,
         label + ': scanner completion/stability/cleanup evidence missing')
    command = run['command']
    need(command.count('--full-json') == 1, label + ': full arrays not requested')
    tree = physical(option(command, '--root'))
    need(Path(option(command, '--json')) == directory / 'scanner.json',
         label + ': scanner output path differs')
    assets = run['tool_assets_sha256']
    expected_names = git('ls-tree', '-r', '--name-only', tool_commit, SKILL).decode().splitlines()
    need(set(assets) == set(expected_names), label + ': scanner asset roster differs')
    tools = [Path(value) for value in command if value.endswith('/' + SKILL + '/scan.py')]
    need(len(tools) == 1 and tools[0].resolve(strict=True) == tools[0],
         label + ': scanner executable path is not unique/physical')
    for relative, digest in assets.items():
        need(digest == sha(git('show', tool_commit + ':' + relative)),
             label + ': scanner asset differs: ' + relative)
        live = tools[0].parent / Path(relative).relative_to(SKILL)
        need(live.resolve(strict=True) == live and sha(live.read_bytes()) == digest,
             label + ': recorded scanner asset changed after scan: ' + relative)
    need(run['tool_sha256'] == assets[SKILL + '/scan.py'], label + ': scanner identity mismatch')
    result = dict(label=label, supplementary=supplementary, run_directory=str(directory),
                  source_root=str(tree), source=source_inputs(tree, expected),
                  tool_commit=tool_commit, tool_assets_sha256=assets, run_json_sha256=run_sha,
                  exit_code=run['exit_code'], process_group_gone=True,
                  seconds=run['seconds'], arrays=None, derivation_complete=False)
    log = directory / 'scanner.log'
    if log.is_file():
        raw = log.read_bytes()
        result.update(scanner_log_sha256=sha(raw), scanner_log=raw.decode('utf-8', errors='replace'))
    output = directory / 'scanner.json'
    if run['exit_code'] in (0, 1):
        document, digest = read_json(physical(output))
        need(digest == run.get('scanner_json_sha256'), label + ': output digest differs')
        need(all(isinstance(document.get(name), list) and
                 all(isinstance(row, dict) for row in document[name]) for name in ARRAYS),
             label + ': complete finding arrays missing')
        result.update(scanner_json_sha256=digest,
                      arrays={name: document[name] for name in ARRAYS}, derivation_complete=True)
    else:
        need(not output.exists() and 'scanner_json_sha256' not in run,
             label + ': incomplete scan has ambiguous stale JSON')
    return result


def identity(row, *, omit=()):
    return encoded({key: value for key, value in row.items() if key not in omit})


def diff_array(before, after):
    """Each list occurrence is accounted for exactly once; duplicates survive."""
    old, new = set(range(len(before))), set(range(len(after)))

    def pair(key):
        available = defaultdict(deque)
        for index in sorted(new):
            available[key(after[index])].append(index)
        pairs = []
        for index in sorted(old):
            queue = available[key(before[index])]
            if queue:
                other = queue.popleft()
                pairs.append((index, other))
        for index, other in pairs:
            old.remove(index)
            new.remove(other)
        return pairs

    exact = pair(identity)
    relocated = pair(lambda row: identity(row, omit=('line',)))
    # This anchor never certifies semantic equivalence. It merely presents
    # residual changes at a corresponding lexical finding together; full
    # objects and every changed field remain available for owner disposition.
    anchor_keys = ('path', 'category', 'pattern', 'match', 'context', 'snippet')
    changed = pair(lambda row: encoded({key: row[key] for key in anchor_keys if key in row}))

    def row(pair, disposition):
        i, j = pair
        differing = sorted(key for key in set(before[i]) | set(after[j])
                           if (key in before[i]) != (key in after[j])
                           or before[i].get(key) != after[j].get(key))
        return dict(before_index=i, after_index=j, before=before[i], after=after[j],
                    differing_fields=differing, disposition=disposition)

    rows = [row(pair, 'coordinate_only_observed_not_an_equality_waiver') for pair in relocated]
    need(all(item['differing_fields'] == ['line'] for item in rows),
         'relocation included a non-coordinate change')
    semantic = [row(pair, 'changed_fields_require_explicit_disposition') for pair in changed]
    removed = [dict(before_index=i, before=before[i], disposition='removal_requires_explicit_disposition')
               for i in sorted(old)]
    added = [dict(after_index=i, after=after[i], disposition='addition_requires_explicit_disposition')
             for i in sorted(new)]
    before_indices = [i for i, _ in exact] + [i for i, _ in relocated] + [i for i, _ in changed] + sorted(old)
    after_indices = [j for _, j in exact] + [j for _, j in relocated] + [j for _, j in changed] + sorted(new)
    need(sorted(before_indices) == list(range(len(before))) and
         sorted(after_indices) == list(range(len(after))), 'occurrence conservation failed')
    return dict(before_count=len(before), after_count=len(after), exact_arrays_equal=before == after,
                exact_matches=[dict(before_index=i, after_index=j) for i, j in exact],
                exact_match_count=len(exact), relocations=rows, changed_fields=semantic,
                removed=removed, added=added, occurrence_conservation=True,
                only_order_changed=(before != after and not rows and not semantic and not removed and not added))


def compare(before, after):
    if not before['derivation_complete'] or not after['derivation_complete']:
        return dict(before=before['label'], after=after['label'],
                    status='unmet_incomplete_derivation', exact_arrays_equal=None, arrays=None,
                    incomplete_sides=[row['label'] for row in (before, after) if not row['derivation_complete']])
    arrays = {name: diff_array(before['arrays'][name], after['arrays'][name]) for name in ARRAYS}
    return dict(before=before['label'], after=after['label'], status='itemised_for_owner_no_gate_replacement',
                exact_arrays_equal=all(value['exact_arrays_equal'] for value in arrays.values()), arrays=arrays)


def self_check():
    """Small local accounting controls; no source imports or scanner execution."""
    a = dict(path='a.py', line=1, category='sample', match='x', snippet='x', role='old')
    b = dict(a, line=2)
    c = dict(a, line=3, role='new')
    d = dict(path='new.py', line=4, snippet='new')
    rows = diff_array([a, a, a, dict(path='gone.py')], [a, b, c, d])
    need(rows['exact_match_count'] == 1 and len(rows['relocations']) == 1
         and len(rows['changed_fields']) == 1 and len(rows['removed']) == 1
         and len(rows['added']) == 1, 'duplicate/relocation/semantic self-check failed')
    need(diff_array([a, b], [b, a])['only_order_changed'], 'order self-check failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main', type=Path, required=True, help='same-tool scan of literal saved main cf50')
    parser.add_argument('--f2', type=Path, required=True, help='same-tool scan of literal F2 77b; exit2 stays unmet')
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--candidate-source', required=True, help='full private composition commit SHA')
    parser.add_argument('--tool-source', required=True, help='full committed candidate scanner SHA')
    parser.add_argument('--f2-composed', type=Path, help='optional supplementary F2 composition, never a substitute')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    quiet()
    need(ROOT.parent.name == 'd4d-executions', 'assigned worktree required')
    for value in (args.candidate_source, args.tool_source):
        need(len(value) == 40 and all(char in '0123456789abcdef' for char in value), 'full SHA required')
    need(git('rev-parse', args.tool_source + '^{commit}').decode().strip() == args.tool_source,
         'tool source is not the stated local commit')
    physical(args.out.parent, within=SCRATCH / 'u3h')
    need(not os.path.lexists(args.out), 'output must be fresh')
    self_check()
    inputs = [load_run('saved_main_cf50', args.main, MAIN, args.tool_source),
              load_run('literal_f2_77b', args.f2, F2, args.tool_source),
              load_run('candidate', args.candidate, args.candidate_source, args.tool_source)]
    comparisons = [compare(inputs[0], inputs[2]), compare(inputs[1], inputs[2])]
    if args.f2_composed:
        metadata, _ = read_json(physical(args.f2_composed / 'run.json'))
        source = metadata['source_commit']
        root = physical(option(metadata['command'], '--root'))
        need(git('show', '-s', '--format=%P', source, cwd=root).decode().strip() == F2,
             'supplementary F2 composition is not a direct single-parent child of literal F2')
        supplementary = load_run('supplementary_f2_private_composition', args.f2_composed,
                                 source, args.tool_source, supplementary=True)
        inputs.append(supplementary)
        comparisons.append(compare(supplementary, inputs[2]))
    result = dict(status='prepared_itemised_comparisons_not_owner_retirement',
                  historical_d258_comparison_changed=False, historical_gate_retired=False,
                  native_acceptance=False, helper_sha256=sha(Path(__file__).read_bytes()),
                  literal_main=MAIN, literal_f2=F2, inputs=inputs, comparisons=comparisons,
                  same_candidate_tool=True, occurrence_semantics='zero-based source array indices; duplicates preserved',
                  saved_main_exact_nine=(inputs[0]['derivation_complete'] and inputs[2]['derivation_complete']
                      and len(inputs[0]['arrays']['violations']) == 9
                      and inputs[0]['arrays']['violations'] == inputs[2]['arrays']['violations']),
                  owner_decision_pending=True)
    quiet()
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with args.out.open('xb') as stream:
        stream.write(raw)
    need(args.out.read_bytes() == raw, 'output write verification failed')
    print(json.dumps(dict(output=str(args.out), sha256=sha(raw),
                          comparisons=[dict(before=row['before'], after=row['after'], status=row['status'],
                                            exact_arrays_equal=row['exact_arrays_equal']) for row in comparisons],
                          saved_main_exact_nine=result['saved_main_exact_nine'])))


if __name__ == '__main__':
    main()
