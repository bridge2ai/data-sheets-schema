#!/usr/bin/env python3
"""H1 offline same-tool scanner comparison and frozen D128 accounting, 2026-11-12.

Purpose: helper-1 authority-pin review; no approval expansion or launch authority.
Inputs: assigned branch, private four-packet composition, fixed main Git objects,
        frozen D128 JSON, and the dependency venv interpreter invoked -S -P -B.
Outputs: fresh sibling scratch exports, isolated scan logs, full arrays, exact
         occurrence/position ledgers, D128 coverage and itemized Markdown.
Provenance: occurrence logic derives from compare_native_u3l_20261109.py;
source/tool census derives from U3-H; the three comparisons derive from U3-M.
Independent static review found H1-F3 (post-output crash misread as exit-1
violations) and H1-F4 (numeric process-group reuse during cleanup). The helper
requires exact matching worker/process statuses and uses observed PID/birth-time
identities; self-check includes bounded synthetic controls for both findings.
No project/native imports, shared refs/config edits, network or provider calls.

The supplied composition is read only. Both sources are exported again from
Git, including EVERY tracked blob in the historical scanner mask; a sparse
checkout is never accepted as proof that the whole mask was scanned. Outputs
are exclusive-create; an interrupted label must be preserved, not reused.
Exit 0: complete diagnostic (not D128 acceptance); 2: incomplete/refused evidence.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime, timezone
import errno
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
ASSIGNED = EXEC / 'codex-native-main-integration-20261112'
SCRATCH = EXEC / 'scratch-native-h1-scanner-20261112'
LOCK = EXEC / 'plans/native_quiet_window.lock'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
SCANNER_SCOPE_REVIEW_COMMIT = '66fecb7be53aea49e371e224593203990f33763e'
OLD_MAIN = 'cf50d9a1c059f3b5030103378ccef33619475dde'
OLD_CANDIDATE = '660b2d884c3032f0eca61fcfd3ae523fcbbe9614'
SKILL = '.claude/skills/d4d-generation-specificity-audit'
MASK = ('src', 'tests', 'utils', 'configs', '.claude', '.github', 'pyproject.toml',
        'Makefile', 'project', 'notes', 'scripts', 'CLAUDE.md', 'CLAUDE.local.md',
        'data/preprocessed/source_manifest.yaml')
ARRAYS = ('hits', 'violations', 'test_dependencies')
EVIDENCE = EXEC / 'scratch-native-u1u3/u3h/itemized-scanner-comparison.json'
EVIDENCE_SHA = '98e6d082db4df2176a452ab60bc83280406333ba339a96e30ae501aeb6957ada'
FIXTURE_REL = 'tests/fixtures/native_d128_approved.json'
FIXTURE_SHA = '65330131940ca8be1cd4288ed3cca9ca980eafc665faa964fa443e8f44d63399'
POST = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881',
    'src/download/prompts/canonical_hashes.yaml': '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}
MAX_EXPORT_BYTES = 500_000_000
MAX_EXPORT_FILES = 15000
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/var/empty', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': '',
       'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}
GIT = ['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
       '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false']


def need(condition, message):
    if not condition:
        raise ValueError(message)


def quiet():
    need(not os.path.lexists(LOCK), 'quiet-window lock exists; preserve evidence and stop')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def same(left, right):
    return encoded(left) == encoded(right)


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def decode(raw):
    def invalid(value):
        raise ValueError('non-finite JSON value: ' + value)
    return json.loads(raw, object_pairs_hook=strict_pairs, parse_constant=invalid)


def physical(path, within=None):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path,
         'expected physical absolute path: ' + str(path))
    if within is not None:
        need(path.is_relative_to(within), 'outside assigned root: ' + str(path))
    return path


def write(path, raw):
    need(not os.path.lexists(path), 'output already exists: ' + str(path))
    with path.open('xb') as stream:
        stream.write(raw)
    need(path.read_bytes() == raw, 'persisted bytes differ: ' + str(path))
    return sha(raw)


def save(path, value):
    return write(path, (json.dumps(value, indent=2, sort_keys=True,
                  ensure_ascii=False, allow_nan=False).replace(chr(64), '\\u0040') + '\n').encode())


def git(*args, cwd=ASSIGNED):
    quiet()
    proc = subprocess.run([*GIT, *args], cwd=cwd, env=ENV, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=180)
    need(proc.returncode == 0, 'local Git failed: ' + repr(args) + '\n' + proc.stderr.decode(errors='replace'))
    quiet()
    return proc.stdout


def full_sha(value):
    need(type(value) is str and re.fullmatch('[0-9a-f]{40}', value) is not None, 'full immutable SHA required')
    return value


def blob(repo, commit, path):
    return git('show', full_sha(commit) + ':' + path, cwd=repo)


def selected(path):
    return any(path == prefix or path.startswith(prefix + '/') for prefix in MASK)


def inventory(repo, commit):
    raw = git('ls-tree', '-r', '-l', '-z', full_sha(commit), cwd=repo)
    roster, files = [], {}
    total = 0
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid, size = metadata.decode('ascii').split()
        relative = name.decode('utf-8', errors='strict')
        path = PurePosixPath(relative)
        need(not path.is_absolute() and '..' not in path.parts and path.as_posix() == relative,
             'unsafe Git path: ' + relative)
        row = dict(path=relative, mode=mode, kind=kind, git_oid=oid,
                   bytes=None if size == '-' else int(size))
        roster.append(row)
        if selected(relative):
            need(kind == 'blob' and mode in ('100644', '100755'),
                 'scanner scope has unsupported nonregular Git input: ' + relative)
            need(relative not in files, 'duplicate Git input: ' + relative)
            files[relative] = row
            total += row['bytes']
    need(files and len(files) <= MAX_EXPORT_FILES and total <= MAX_EXPORT_BYTES,
         'scanner export exceeds retained 15000-file / 500 MB bound')
    required = ('CLAUDE.md', 'data/preprocessed/source_manifest.yaml',
                'src/data_sheets_schema/api_runner.py', '.claude/commands/d4d-full-core.md',
                'src/data_sheets_schema/schema/data_sheets_schema.yaml',
                'tests/test_neutral_generation_schema.py', 'pyproject.toml', 'Makefile')
    need(all(path in files for path in required), 'required scanner input absent from commit')
    need(all(any(path.startswith(root + '/') for path in files) for root in
             ('src', 'notes', 'scripts', 'tests', '.claude', '.github', 'utils', 'configs', 'project')),
         'required scanner input root is empty')
    return dict(commit=commit, tree=git('rev-parse', commit + '^{tree}', cwd=repo).decode().strip(),
                committed_roster=roster, committed_roster_sha256=sha(raw),
                committed_roster_encoding='git ls-tree -r -l -z', physical_input_mask=list(MASK),
                selected=files, selected_count=len(files), selected_bytes=total)


def census(tree, expected):
    need(git('rev-parse', 'HEAD', cwd=tree).decode().strip() == expected['commit'], 'export HEAD moved')
    rows, found = [], set()
    # Enumerate the entire fresh export, including hidden and ignored paths.
    # The private .git is metadata; no other untracked or ignored file is accepted.
    for folder, dirs, names in os.walk(tree, followlinks=False):
        if Path(folder) == tree:
            dirs.remove('.git')
        for name in dirs:
            need(not (Path(folder) / name).is_symlink(), 'directory symlink in scanner export')
        for name in names:
            path = Path(folder) / name
            relative = path.relative_to(tree).as_posix()
            need(relative in expected['selected'], 'unexpected/ignored scanner input: ' + relative)
            need(stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink(), 'nonregular physical scanner input')
            row = expected['selected'][relative]
            raw = path.read_bytes()
            need(len(raw) == row['bytes'] and hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_oid'],
                 'physical input differs from Git blob: ' + relative)
            need(bool(path.stat().st_mode & 0o111) == (row['mode'] == '100755'), 'input executable mode differs')
            found.add(relative)
            rows.append(dict(row, sha256=sha(raw)))
    need(found == set(expected['selected']), 'scanner export missing tracked inputs: ' + repr(sorted(set(expected['selected']) - found)))
    rows.sort(key=lambda row: row['path'])
    config = tree / '.git/config'
    need(not git('remote', cwd=tree).strip(), 'private scanner source must not have remotes')
    return dict(physical_inputs=rows, physical_inputs_sha256=sha(encoded(rows)),
                uncommitted_or_ignored_inputs=[], source_complete=True,
                private_config_sha256=sha(config.read_bytes()), private_config_armed=False)


def materialize(repo, commit, destination):
    quiet()
    expected = inventory(repo, commit)
    destination.mkdir()
    tree = destination / 'tree'
    tree.mkdir()
    # archive can honour export-ignore; the complete Git inventory check below
    # deliberately refuses any omission rather than accepting a smaller scope.
    present = [prefix for prefix in MASK if any(name == prefix or name.startswith(prefix + '/') for name in expected['selected'])]
    archive = git('archive', '--format=tar', commit, '--', *present, cwd=repo)
    need(len(archive) <= MAX_EXPORT_BYTES + 20_000_000, 'archive exceeds bounded export size')
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as stream:
        for item in stream:
            name = PurePosixPath(item.name)
            need(not name.is_absolute() and '..' not in name.parts, 'unsafe archive member')
            if item.isdir():
                continue
            need(item.isfile() and item.name in expected['selected'] and item.name not in seen,
                 'unexpected archive member: ' + item.name)
            row = expected['selected'][item.name]
            need(item.size == row['bytes'], 'archive/Git byte count differs')
            raw = stream.extractfile(item).read()
            need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_oid'], 'archive/Git blob differs')
            path = tree / item.name
            path.parent.mkdir(parents=True, exist_ok=True)
            write(path, raw)
            path.chmod(0o755 if row['mode'] == '100755' else 0o644)
            seen.add(item.name)
    need(seen == set(expected['selected']), 'archive omitted committed scanner inputs')
    git('init', '-q', '--template=', '--object-format=sha1', cwd=tree)
    objects = physical(Path(git('rev-parse', '--path-format=absolute', '--git-path', 'objects', cwd=repo).decode().strip()))
    need('\n' not in str(objects), 'newline in object-store path')
    write(tree / '.git/objects/info/alternates', (str(objects) + '\n').encode())
    # HEAD is private metadata. No update-ref or shared repository mutation.
    (tree / '.git/HEAD').write_text(commit + '\n')
    need((tree / '.git/HEAD').read_text() == commit + '\n', 'private detached HEAD did not persist')
    result = dict(expected, source_repository=str(repo), source_root=str(tree),
                  archive_sha256=sha(archive), archive_bytes=len(archive), **census(tree, expected))
    save(destination / 'source.json', result)
    return tree, result


def fields(before, after):
    return sorted(key for key in set(before) | set(after)
                  if (key in before) != (key in after) or not same(before.get(key), after.get(key)))


def diff_array(before, after):
    need(type(before) is list and type(after) is list and all(type(row) is dict for row in before + after), 'finding array must contain objects')
    left, right = set(range(len(before))), set(range(len(after)))
    def pair(key):
        available = defaultdict(deque)
        for j in sorted(right):
            available[key(after[j])].append(j)
        pairs = []
        for i in sorted(left):
            matches = available[key(before[i])]
            if matches:
                pairs.append((i, matches.popleft()))
        for i, j in pairs:
            left.remove(i)
            right.remove(j)
        return pairs
    exact = pair(encoded)
    moved = pair(lambda row: encoded({k: v for k, v in row.items() if k != 'line'}))
    anchors = ('path', 'category', 'pattern', 'match', 'context', 'snippet')
    changed = pair(lambda row: encoded({k: row[k] for k in anchors if k in row}))
    def record(pairing):
        i, j = pairing
        return dict(before_index=i, after_index=j, before=before[i], after=after[j], differing_fields=fields(before[i], after[j]))
    relocations, semantic = [record(row) for row in moved], [record(row) for row in changed]
    need(all(row['differing_fields'] == ['line'] for row in relocations), 'relocation changed another field')
    need(sorted([i for i, j in exact + moved + changed] + list(left)) == list(range(len(before))) and
         sorted([j for i, j in exact + moved + changed] + list(right)) == list(range(len(after))), 'occurrence conservation failed')
    positional = []
    for index in range(max(len(before), len(after))):
        old, new = index < len(before), index < len(after)
        if old and new and same(before[index], after[index]):
            continue
        row = dict(index=index, before_present=old, after_present=new)
        if old:
            row['before'] = before[index]
        if new:
            row['after'] = after[index]
        if old and new:
            row['differing_fields'] = fields(before[index], after[index])
        positional.append(row)
    equal = same(before, after)
    return dict(before_count=len(before), after_count=len(after), before_sha256=sha(encoded(before)),
                after_sha256=sha(encoded(after)), exact_arrays_equal=equal,
                exact_matches=[dict(before_index=i, after_index=j) for i, j in exact], exact_match_count=len(exact),
                relocations=relocations, changed_fields=semantic,
                removed=[dict(before_index=i, before=before[i]) for i in sorted(left)],
                added=[dict(after_index=j, after=after[j]) for j in sorted(right)],
                positional_differences=positional, only_order_changed=(not equal and not moved and not changed and not left and not right),
                occurrence_conservation=True)


def compare(label, before, after):
    need(set(before) == set(after) == set(ARRAYS), 'incomplete array roster')
    result = {name: diff_array(before[name], after[name]) for name in ARRAYS}
    return dict(label=label, arrays=result, exact_arrays_equal=all(row['exact_arrays_equal'] for row in result.values()))


def frozen_approval():
    fixture = physical(ASSIGNED / FIXTURE_REL)
    evidence_path = physical(EVIDENCE)
    fixture_raw, evidence_raw = fixture.read_bytes(), evidence_path.read_bytes()
    need(sha(fixture_raw) == FIXTURE_SHA and sha(evidence_raw) == EVIDENCE_SHA, 'frozen D128 evidence changed')
    approved, evidence = decode(fixture_raw), decode(evidence_raw)
    need(approved['decision'] == 'D128' and type(approved['version']) is int and approved['version'] == 1 and
         approved['source_evidence_sha256'] == EVIDENCE_SHA and approved['baseline']['commit'] == OLD_MAIN and
         approved['reference_candidate']['commit'] == OLD_CANDIDATE, 'frozen D128 identity differs')
    frozen = {}
    for key, label, commit, prefix in (('baseline', 'saved_main_cf50', OLD_MAIN, 'before'), ('candidate', 'candidate', OLD_CANDIDATE, 'after')):
        matches = [row for row in evidence['inputs'] if row['label'] == label]
        need(len(matches) == 1, 'nonunique frozen input')
        row = matches[0]
        need(row['derivation_complete'] is True and row['source']['commit'] == commit and
             same(row['tool_assets_sha256'], approved['tool_assets_sha256']), 'frozen input source/tool differs')
        need(set(row['arrays']) == set(ARRAYS), 'frozen full-array roster differs')
        for name in ARRAYS:
            need(sha(encoded(row['arrays'][name])) == approved['arrays'][name][prefix + '_sha256'] and
                 len(row['arrays'][name]) == approved['arrays'][name][prefix + '_count'], 'frozen ordered array differs')
        need(same(row['arrays']['violations'], approved['exact_violations']) and len(row['arrays']['violations']) == 9,
             'frozen violation objects differ')
        need(row['source']['physical_input_mask'] == list(MASK), 'historical input mask differs')
        frozen[key] = row
    return approved, frozen


def delta_key(row):
    return encoded({name: row[name] for name in ('before', 'after', 'differing_fields') if name in row})


def coverage(comparison, approved):
    """Map exact finite delta occurrences; no inferred semantic equivalence."""
    result = {}
    for name in ARRAYS:
        ledger, historical = comparison['arrays'][name], approved['arrays'][name]
        groups = {}
        for kind in ('relocations', 'changed_fields', 'removed', 'added'):
            available = defaultdict(deque)
            for index, row in enumerate(historical[kind]):
                available[delta_key(row)].append(index)
            rows = []
            for index, row in enumerate(ledger[kind]):
                matches = available[delta_key(row)]
                old_index = matches.popleft() if matches else None
                rows.append(dict(current_delta_index=index, historical_delta_index=old_index,
                    exact_finite_object_delta_match=old_index is not None,
                    disposition='same_finite_object_delta_only' if old_index is not None else 'new_difference_requires_owner_review',
                    current=row, historical=None if old_index is None else historical[kind][old_index]))
            groups[kind] = rows
        result[name] = dict(delta_occurrences=groups,
            exact_ordered_before_matches_approval=ledger['before_sha256'] == historical['before_sha256'],
            exact_ordered_after_matches_approval=ledger['after_sha256'] == historical['after_sha256'],
            positional_differences_retained=True)
    return dict(arrays=result, finite_object_matching_is_not_approval=True,
                tool_scope_approved=False, approval_expanded=False,
                scope='An exact finite delta may be identifiable in D128, but new source/tool/order identities remain unapproved.')


def self_check():
    a = dict(path='a.py', line=1, snippet='x')
    b = dict(path='b.py', line=2, snippet='y')
    ledger = diff_array([deepcopy(a), deepcopy(a), deepcopy(b), dict(path='gone.py')],
                        [deepcopy(a), dict(a, line=3), dict(b, role='changed'), dict(path='new.py')])
    need(ledger['exact_matches'] == [dict(before_index=0, after_index=0)] and
         all(len(ledger[name]) == 1 for name in ('relocations', 'changed_fields', 'removed', 'added')), 'duplicate accounting control failed')
    reordered = diff_array([a, b, a], [a, a, b])
    need(reordered['only_order_changed'] and len(reordered['positional_differences']) == 2, 'ordering control failed')
    for changed in (dict(a, line=True), dict(a, line=1.0)):
        typed = diff_array([a], [changed])
        need(not typed['exact_arrays_equal'] and typed['relocations'][0]['differing_fields'] == ['line'], 'typed line control failed')
    need(diff_array([a], [dict(a, extra=None)])['changed_fields'][0]['differing_fields'] == ['extra'], 'missing/null control failed')
    need(diff_array([dict(a, detail=[1])], [dict(a, detail=[True])])['changed_fields'][0]['differing_fields'] == ['detail'], 'nested JSON type control failed')
    need(diff_array([a, a], [a, a])['exact_arrays_equal'], 'unchanged duplicates control failed')
    toy = {name: [deepcopy(a)] for name in ARRAYS}
    toy_after = {name: [dict(a, line=2), dict(path='new.py')] for name in ARRAYS}
    toy_comparison = compare('synthetic', toy, toy_after)
    toy_approved = {'arrays': toy_comparison['arrays']}
    mapped = coverage(toy_comparison, toy_approved)
    need(all(row['exact_finite_object_delta_match'] for group in mapped['arrays'].values()
             for rows in group['delta_occurrences'].values() for row in rows), 'finite-delta coverage control failed')
    toy_after['hits'].append(dict(path='new.py'))
    repeated = coverage(compare('duplicate addition', toy, toy_after), toy_approved)
    need([row['exact_finite_object_delta_match'] for row in repeated['arrays']['hits']['delta_occurrences']['added']] == [True, False],
         'coverage reused one historical occurrence twice')
    worker_status = worker_status_controls()
    process_identity = process_identity_controls()
    return dict(status='synthetic_comparator_controls_passed', real_scans_run=False, d128_gate_passed=False,
                controls=['duplicate_occurrences', 'pure_order', 'Boolean_integer', 'float_integer', 'missing_null', 'nested_types', 'unchanged_duplicates', 'finite_delta_coverage', 'no_reuse_of_historical_occurrences',
                          'worker_status_null_refused', 'worker_status_bool_refused', 'worker_status_mismatch_refused', 'observed_pid_reuse_refused',
                          'worker_returncode_matches_os_exit', 'recycled_process_identity_not_signalled'],
                protocol_repairs={'H1-F3': worker_status, 'H1-F4': process_identity})


def dependency_site():
    need(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode,
         'invoke the dependency venv Python with -S -P -B')
    prefix = Path(sys.executable).absolute().parent.parent
    site = prefix / 'lib' / ('python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor)) / 'site-packages'
    need((prefix / 'pyvenv.cfg').is_file(), 'dependency interpreter is not a venv')
    physical(site)
    need((site / 'yaml/__init__.py').is_file(), 'physical PyYAML dependency is absent')
    return site


def child_environment(out):
    return dict(ENV, PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(out / 'home'), TMPDIR=str(out / 'tmp'),
                PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
                UV_OFFLINE='1', PIP_NO_INDEX='1', LANG='en_US.UTF-8')


def scope_audit(tool, source, yaml):
    """Record the reviewed scanner's actual discovery roots and asset rules.

    This AST-only audit never imports scanner or generation modules. Its caller
    also pins the entire scanner to the reviewed source commit, so these checks
    are evidence about this instrument, not a generic proof for future scanners.
    """
    raw = tool.read_bytes()
    parsed = ast.parse(raw)
    constants = {target.id: node.value for node in parsed.body if isinstance(node, ast.Assign)
                 for target in node.targets if isinstance(target, ast.Name)}
    values = {name: ast.literal_eval(constants[name]) for name in
              ('PYTHON_ROOTS', 'PROJECT_MEMORY', 'PROJECT_SETTINGS', 'SESSION_DESCRIBED')}
    need(values['PYTHON_ROOTS'] == ('src', 'notes', 'scripts'), 'reviewed Python discovery roots changed')
    paths = list(values['PROJECT_MEMORY']) + list(values['PROJECT_SETTINGS']) + [row[0] for row in values['SESSION_DESCRIBED']]
    need(all(selected(path) for path in paths), 'discovery path escapes the committed scanner mask')
    named = constants['NAMED_PATH']
    need(isinstance(named, ast.Call) and named.args, 'named-path expression changed')
    named_pattern = ast.literal_eval(named.args[0])
    need('(?:\\.claude|\\.github|src|scripts|notes)' in named_pattern, 'named-text discovery roots changed')
    names = ('_walk_sources', 'discover', 'derive_toolchain', 'discover_model_facing_assets',
             '_schema_closure', 'scan_tests', 'model_input_files')
    functions = {node.name: node for node in parsed.body if isinstance(node, ast.FunctionDef)}
    need(all(name in functions for name in names), 'a reviewed scope function disappeared')
    lines = raw.splitlines(keepends=True)
    function_evidence = {name: dict(line=functions[name].lineno, end_line=functions[name].end_lineno,
                         sha256=sha(b''.join(lines[functions[name].lineno - 1:functions[name].end_lineno]))) for name in names}
    runtime_path = source / 'src/data_sheets_schema/agentic_runtime.py'
    runtime = ast.parse(runtime_path.read_bytes())
    runtime_constants = {target.id: node.value for node in runtime.body if isinstance(node, ast.Assign)
                         for target in node.targets if isinstance(target, ast.Name)}
    schemas = ast.literal_eval(runtime_constants['SCHEMAS'])
    toolchain = next(node for node in runtime.body if isinstance(node, ast.FunctionDef) and node.name == 'toolchain')
    directories = sorted({item.value for node in ast.walk(toolchain) if isinstance(node, ast.For)
                          and isinstance(node.iter, (ast.Tuple, ast.List)) for item in node.iter.elts
                          if isinstance(item, ast.Constant) and type(item.value) is str})
    need(schemas and directories and all(selected(path) for path in list(schemas) + directories),
         'actual source toolchain assets escape the materialized mask')
    need(all((source / path).is_file() for path in schemas) and all((source / path).is_dir() for path in directories),
         'actual source toolchain assets are missing')
    registry = yaml.safe_load((source / 'src/download/prompts/canonical_hashes.yaml').read_bytes())
    pins = registry.get('files', {})
    need(type(pins) is dict and pins and all(type(path) is str and selected(path) for path in pins),
         'canonical prompt registry points outside the materialized mask')
    need(all((source / path).is_file() for path in pins), 'a canonical prompt registry input is missing')
    # The scanner follows non-LinkML schema imports relative to the containing
    # module. Check that full closure against materialized files as well.
    seen, todo = set(), [source / 'src/data_sheets_schema/schema' / name
                         for name in ('data_sheets_schema.yaml', 'data_sheets_schema_core.yaml')]
    while todo:
        path = todo.pop().resolve()
        need(path.is_relative_to(source) and selected(path.relative_to(source).as_posix()) and path.is_file(),
             'schema discovery escapes the materialized mask or loses an input')
        if path in seen:
            continue
        seen.add(path)
        document = yaml.safe_load(path.read_bytes()) or {}
        for name in document.get('imports') or []:
            if not name.startswith('linkml:'):
                todo.append(path.parent / (name + '.yaml'))
    return dict(reviewed_scanner_commit=SCANNER_SCOPE_REVIEW_COMMIT, reviewed_scanner_sha256=sha(raw),
                scanner_functions=function_evidence, declared_discovery_values=values,
                named_path_pattern=named_pattern, source_runtime_sha256=sha(runtime_path.read_bytes()),
                source_toolchain_schemas=list(schemas), source_toolchain_directories=directories,
                canonical_prompt_paths=sorted(pins), schema_closure=sorted(path.relative_to(source).as_posix() for path in seen),
                model_facing_asset_rule='Only descendants of model-facing src/data_sheets_schema module directories; the complete src tree is materialized.',
                other_reads='Prompt sets/protocols are under src/download/prompts; test dependencies are under tests; the explicit shared-input content file is data/preprocessed/source_manifest.yaml. Templated bundle patterns are read from source/playbook text, not loaded as source documents.',
                excluded_top_level_paths='The reviewed scanner has no generic docs, README or config discovery root; configs and project are included conservatively. Full scanner bytes and function hashes bind this conclusion.',
                full_historical_mask_materialized=True, future_instrument_scope_not_assumed=True)


def worker(args):
    need(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode, 'isolated scanner startup flags missing')
    out = physical(args.worker, SCRATCH)
    plan = decode((out / 'worker-plan.json').read_bytes())
    dependencies = physical(Path(plan['dependency_site']))
    tool = physical(Path(plan['tool']))
    source = physical(Path(plan['source']))
    need(source.is_relative_to(out.parent) and tool.is_relative_to(out.parent), 'worker source/tool outside fresh run')
    need(not any(name.startswith('data_sheets_schema') for name in sys.modules), 'project module imported before scanner')
    # Appending a physical dependency directory does not run its .pth hooks.
    # No checkout or source directory is put on the import path.
    sys.path.append(str(dependencies))
    sock = socket.socket()
    try:
        try:
            sock.bind(('127.0.0.1', 0))
        except OSError as exc:
            need(exc.errno == errno.EPERM, 'unexpected network-denial witness error')
        else:
            raise ValueError('network sandbox did not deny local bind')
    finally:
        sock.close()
    import yaml
    yaml_file = physical(Path(yaml.__file__), dependencies)
    need(sha(tool.read_bytes()) == plan['tool_sha256'], 'scanner changed before child execution')
    save(out / 'scope-audit.json', scope_audit(tool, source, yaml))
    witness = dict(dependency_site=str(dependencies), yaml_file=str(yaml_file), yaml_sha256=sha(yaml_file.read_bytes()),
                   sys_path=list(sys.path), project_modules_imported=False, dependency_pth_executed=False,
                   startup_flags=dict(no_site=True, safe_path=True, dont_write_bytecode=True), network_bind_denied=True)
    save(out / 'environment.json', witness)
    code = None
    try:
        sys.argv = plan['scanner_argv']
        runpy.run_path(str(tool), run_name='__main__')
        code = 0
    except SystemExit as exc:
        code = exc.code if type(exc.code) is int else (0 if exc.code is None else 2)
    finally:
        imported = [name for name in sys.modules if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.')]
        save(out / 'worker-outcome.json', dict(returncode=code, unexpected_project_modules=imported,
                                             source_imports_absent=not imported))
    need(not imported, 'scanner imported project modules')
    return code


def sandbox_profile(out, sources):
    # Scan trees are immutable even though output lives in the same new run.
    return ('(version 1)\n(allow default)\n(deny network*)\n'
            '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n'
            '(deny file-write* (require-all (require-not (subpath ' + json.dumps(str(out)) + ')) '
            '(require-not (literal "/dev/null")) (require-not (literal "/dev/tty"))))\n'
            + ''.join('(deny file-write* (subpath ' + json.dumps(str(path)) + '))\n' for path in sources))


class OwnedProcesses:
    """Track only observed descendants by PID and birth time; never inspect CPU."""
    def __init__(self, psutil, child):
        self.psutil = psutil
        self.known = {(child.pid, psutil.Process(child.pid).create_time())}
        self.errors = []

    def live(self):
        result = []
        for pid, created in tuple(self.known):
            try:
                process = self.psutil.Process(pid)
                if process.create_time() == created and process.is_running() and process.status() != self.psutil.STATUS_ZOMBIE:
                    result.append(process)
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)
        return result

    def observe(self):
        for process in self.live():
            try:
                for child in process.children(recursive=True):
                    try:
                        self.known.add((child.pid, child.create_time()))
                    except self.psutil.NoSuchProcess:
                        pass
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)

    def signal(self, number):
        self.observe()
        for process in self.live():
            try:
                process.send_signal(number)
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.Error as exc:
                self.errors.append(type(exc).__name__)


def worker_completion_valid(code, worker_result, cleanup_verified, reason):
    """Exit 1 is findings only when the worker explicitly completed with 1."""
    return (reason is None and cleanup_verified is True and type(code) is int and code in (0, 1) and
            type(worker_result) is dict and worker_result.get('source_imports_absent') is True and
            type(worker_result.get('returncode')) is int and worker_result['returncode'] == code)


def worker_status_controls():
    cases = []
    for label, code, recorded, expected in (
            ('completed_zero', 0, 0, True), ('completed_one', 1, 1, True),
            ('post_output_crash_null', 1, None, False), ('Boolean_worker', 1, True, False),
            ('Boolean_process', True, 1, False), ('mismatched_status', 1, 0, False),
            ('incomplete_status', 2, 2, False)):
        actual = worker_completion_valid(code, dict(source_imports_absent=True, returncode=recorded), True, None)
        need(actual is expected, 'worker-status control failed: ' + label)
        cases.append(dict(case=label, process_status=code, worker_status=recorded,
                          accepted=actual, expected=expected))
    need(not worker_completion_valid(1, None, True, None), 'missing worker witness accepted')
    need(not worker_completion_valid(1, dict(source_imports_absent=True, returncode=1), False, None), 'unverified cleanup accepted')
    return dict(status='synthetic_controls_passed', cases=cases,
                scope='Pure completion-predicate controls; no scanner, subprocess or real process.')


def process_identity_controls():
    class MissingProcess(Exception):
        pass

    class ProcessError(Exception):
        pass

    states = {1: dict(created=10.0, children=[2], live=True),
              2: dict(created=20.0, children=[], live=True),
              3: dict(created=30.0, children=[], live=True)}
    signals = []

    class FakeProcess:
        def __init__(self, pid):
            if pid not in states:
                raise MissingProcess()
            self.pid, self.created = pid, states[pid]['created']

        def create_time(self):
            return self.created

        def is_running(self):
            return self.pid in states and states[self.pid]['live'] and states[self.pid]['created'] == self.created

        def status(self):
            return 'running'

        def children(self, recursive=True):
            return [FakeProcess(pid) for pid in states[self.pid]['children']]

        def send_signal(self, number):
            if not self.is_running():
                raise MissingProcess()
            signals.append(dict(pid=self.pid, created=self.created, signal=number))

    class FakePsutil:
        NoSuchProcess = MissingProcess
        Error = ProcessError
        STATUS_ZOMBIE = 'zombie'
        Process = FakeProcess

    child = type('SyntheticChild', (), {'pid': 1})()
    tracker = OwnedProcesses(FakePsutil, child)
    tracker.observe()
    need((2, 20.0) in tracker.known, 'synthetic descendant was not observed')
    # PID 2 is reused by an unrelated process after the original descendant
    # disappears. It is no longer a child of PID 1 and must never be signalled.
    states[2]['created'] = 99.0
    states[1]['children'] = []
    tracker.signal(signal.SIGTERM)
    need([row['pid'] for row in signals] == [1], 'reused or unowned PID was signalled')
    need((2, 99.0) not in tracker.known and not tracker.errors, 'foreign identity became owned')
    return dict(status='synthetic_controls_passed', observed_identities=sorted(tracker.known),
                reused_pid=2, reused_birth_time=99.0, unowned_pid=3, signals=signals,
                reused_pid_signalled=False, unowned_pid_signalled=False,
                scope='In-memory fake process table only; no real process observation or signals.')


def scan_one(label, source, source_info, tool, tool_commit, assets, out, dependencies, timeout):
    quiet()
    out.mkdir()
    (out / 'home').mkdir()
    (out / 'tmp').mkdir()
    profile = out / 'network-denied.sb'
    write(profile, sandbox_profile(out, [source, tool.parents[3]]).encode())
    scanner_argv = [str(tool), '--root', str(source), '--report', str(out / 'scanner.md'),
                    '--json', str(out / 'scanner.json'), '--tokens', str(tool.with_name('tokens.yaml')),
                    '--exceptions', str(tool.with_name('exceptions.yaml')), '--full-json']
    plan = dict(dependency_site=str(dependencies), source=str(source), tool=str(tool), tool_sha256=sha(tool.read_bytes()), scanner_argv=scanner_argv)
    save(out / 'worker-plan.json', plan)
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable, '-S', '-P', '-B',
               str(Path(__file__).resolve()), '--worker', str(out)]
    env = child_environment(out)
    save(out / 'plan.json', dict(command=command, environment=env, timeout_seconds=timeout,
         sandbox_sha256=sha(profile.read_bytes()), helper_sha256=sha(Path(__file__).read_bytes())))
    # Only process identity/cleanup uses psutil. No CPU/load diagnostic runs.
    # A plain dependency path entry cannot execute editable .pth files.
    if str(dependencies) not in sys.path:
        sys.path.append(str(dependencies))
    import psutil
    physical(Path(psutil.__file__), dependencies)
    start = time.monotonic()
    reason, child, owned, forced = None, None, None, False
    with (out / 'scanner.log').open('xb') as stream:
        try:
            quiet()
            child = subprocess.Popen(command, cwd=source, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            owned = OwnedProcesses(psutil, child)
            while child.poll() is None:
                owned.observe()
                if os.path.lexists(LOCK):
                    reason = 'quiet_window_acquired'
                    break
                if time.monotonic() - start >= timeout:
                    reason = 'deadline'
                    break
                time.sleep(0.25)
        except BaseException as exc:
            reason = type(exc).__name__ + ': ' + str(exc)
        finally:
            if owned is not None:
                owned.observe()
                if owned.live():
                    forced = True
                    owned.signal(signal.SIGTERM)
                    until = time.monotonic() + 5
                    while owned.live() and time.monotonic() < until:
                        time.sleep(0.1)
                    if owned.live():
                        owned.signal(signal.SIGKILL)
            elif child is not None and child.poll() is None:
                # Only the Popen handle we created; its signal implementation
                # checks whether that child has exited before sending a signal.
                forced = True
                child.terminate()
            if child is not None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    reason = reason or 'cleanup_timeout'
                    child.kill()
                    child.wait(timeout=5)
    duration = time.monotonic() - start
    code = None if child is None else child.returncode
    output = out / 'scanner.json'
    worker_file = out / 'worker-outcome.json'
    worker_result = decode(worker_file.read_bytes()) if worker_file.is_file() else None
    survivors = [] if owned is None else [process.pid for process in owned.live()]
    observation_errors = [] if owned is None else owned.errors
    cleanup_verified = owned is not None and not survivors and not observation_errors and not forced
    complete = worker_completion_valid(code, worker_result, cleanup_verified, reason)
    arrays = None
    if complete:
        need(output.is_file() and output.stat().st_size > 0, 'complete scanner lacks persisted JSON')
        document = decode(output.read_bytes())
        need(type(document.get('exit')) is int and document['exit'] == code and document.get('commit') == source_info['commit'],
             'scanner JSON exit/source disagrees with completed child')
        need((out / 'scanner.md').is_file() and (out / 'scanner.md').stat().st_size > 0, 'scanner report was not persisted')
        need(all(type(document.get(name)) is list and all(type(row) is dict for row in document[name]) for name in ARRAYS), 'scanner omitted complete arrays')
        arrays = {name: document[name] for name in ARRAYS}
        need(type(document.get('surfaces')) is dict and all(path in source_info['selected'] for path in document['surfaces']),
             'scanner emitted a surface outside the complete committed input roster')
        need(all(type(row.get('path')) is str and row['path'] in source_info['selected'] for rows in arrays.values() for row in rows),
             'finding path lies outside the complete committed input roster')
    after = census(source, source_info)
    need(same(after, {key: source_info[key] for key in after}), 'source bytes/config changed during scan')
    current_assets = {path: sha((tool.parents[3] / path).read_bytes()) for path in assets}
    need(same(current_assets, assets), 'scanner assets changed during scan')
    result = dict(label=label, source_commit=source_info['commit'], source=source_info,
                  source_root=str(source), tool_commit=tool_commit, tool_assets_sha256=assets,
                  tool_sha256=assets[SKILL + '/scan.py'], command=[sys.executable, '-S', '-P', '-B', *scanner_argv],
                  actual_worker_command=command, exit_code=code, seconds=duration, interruption=reason,
                  observed_descendants_gone=cleanup_verified, forced_cleanup=forced,
                  cleanup_scope='Observed descendants by PID and birth time only; no claim about never-observed orphans.',
                  observed_processes=[] if owned is None else sorted(owned.known),
                  observed_surviving_pids=survivors, observation_errors=observation_errors,
                  tool_unchanged=True, tool_assets_unchanged=True,
                  derivation_complete=complete, arrays=arrays, scanner_log_sha256=sha((out / 'scanner.log').read_bytes()),
                  worker=worker_result)
    if (out / 'scope-audit.json').is_file():
        result['input_scope_audit'] = decode((out / 'scope-audit.json').read_bytes())
        result['input_scope_audit_sha256'] = sha((out / 'scope-audit.json').read_bytes())
    if output.is_file():
        result['scanner_json_sha256'] = sha(output.read_bytes())
    save(out / 'run.json', result)
    need(complete, label + ' did not derive complete arrays; inspect retained run.json and scanner.log')
    return result


def markdown(value, path):
    lines = ['# H1 scanner comparison', '', 'Diagnostic only. D128 approval is unchanged; this is not a native acceptance or launch gate.', '',
             'Full arrays, objects, order and occurrence ledgers: `' + str(path) + '`.', '',
             'The current API protected postimage remains outside the D127 approved bytes.', '']
    for i, comparison in enumerate(value['comparisons']):
        lines += ['## ' + comparison['label'], '']
        for name, ledger in comparison['arrays'].items():
            lines.append(f"- {name}: {ledger['before_count']} to {ledger['after_count']}; exact={ledger['exact_match_count']}; "
                         f"line={len(ledger['relocations'])}; fields={len(ledger['changed_fields'])}; additions={len(ledger['added'])}; "
                         f"removals={len(ledger['removed'])}; ordered equality={ledger['exact_arrays_equal']}.")
            for kind in ('relocations', 'changed_fields', 'added', 'removed'):
                for j, row in enumerate(ledger[kind]):
                    old, new = row.get('before', {}), row.get('after', {})
                    lines.append(f"  - {kind}: before[{row.get('before_index')}] {old.get('path')}:{old.get('line')} to "
                                 f"after[{row.get('after_index')}] {new.get('path')}:{new.get('line')}; fields={row.get('differing_fields')}; "
                                 f"full objects `/comparisons/{i}/arrays/{name}/{kind}/{j}`.")
            lines.append(f"  - {len(ledger['positional_differences'])} positional records in `/comparisons/{i}/arrays/{name}/positional_differences`; not additional occurrence counts.")
        lines.append('')
    lines += ['## Full current violations', '', 'Both ordered arrays are retained below, including duplicate occurrences.', '']
    for key in ('baseline', 'candidate'):
        lines += ['### ' + key, '', '```json', json.dumps(value[key]['arrays']['violations'], indent=2, ensure_ascii=False).replace(chr(64), '\\u0040'), '```', '']
    lines += ['## Approval coverage', '', 'Every nonexact current delta is itemized under `/d128_coverage/arrays` with its full current object(s), exact historical delta match or new-difference classification.',
              'An exact object match does not approve the changed scanner asset map, source identities, array order or occurrence indices.',
              'D128 gate passed: false. Instrument approval changed: false.', '', '## Scanner asset changes', '']
    for row in value['tool_asset_delta']:
        lines.append('- `' + row['path'] + '`: `' + str(row.get('before_sha256')) + '` to `' + str(row.get('after_sha256')) + '`.')
    return ('\n'.join(lines) + '\n').replace(chr(64), '[U+0040]').encode()


def main(args):
    need(ROOT.name == 'codex-development-efficiency-20261111' and EXEC.name == 'd4d-executions', 'helper is outside its assigned repository')
    physical(ROOT)
    physical(ASSIGNED)
    quiet()
    if args.self_check:
        witness = dict(self_check(), helper_path=str(Path(__file__).resolve()),
                       helper_sha256=sha(Path(__file__).read_bytes()))
        print(json.dumps(witness, sort_keys=True))
        return 0
    need(args.tree is not None and args.label is not None, '--tree and --label are required')
    need(re.fullmatch('[a-z0-9][a-z0-9-]{0,60}', args.label) is not None, 'literal fresh label required')
    need(1 <= args.timeout_seconds <= 3300, 'per-scan deadline must be 1 to 3300 seconds')
    dependencies = dependency_site()
    tree = physical(args.tree, SCRATCH)
    need(tree.name == 'tree' and tree.parent.parent == SCRATCH, 'expected private composition directly under the assigned scratch root')
    manifest_path = physical(tree.parent / 'composition.json', SCRATCH)
    manifest_raw = manifest_path.read_bytes()
    manifest = decode(manifest_raw)
    need(manifest['status'] == 'composed_not_tested' and manifest['tree'] == str(tree), 'private composition manifest is not ready')
    candidate_commit = full_sha(manifest['composition_commit'])
    tool_commit = full_sha(manifest['source_commit'])
    need(git('rev-parse', 'HEAD', cwd=tree).decode().strip() == candidate_commit, 'private composition HEAD differs')
    need(git('rev-parse', 'HEAD').decode().strip() == tool_commit, 'assigned candidate moved since composition')
    need(git('branch', '--show-current').decode().strip() == 'codex/native-main-integration-20261112', 'wrong assigned branch')
    need(not git('remote', cwd=tree).strip(), 'supplied private composition has a remote')
    supplied_config = physical(tree / '.git/config', tree)
    need(sha(supplied_config.read_bytes()) == manifest['config_original_sha256'],
         'restore the supplied private test-only Git config before scanner comparison')
    need(set(git('diff', '--name-only', tool_commit, candidate_commit, cwd=tree).decode().splitlines()) == set(POST), 'composition changes more than the four protected files')
    for path, expected in POST.items():
        need(sha(blob(tree, candidate_commit, path)) == expected and sha((tree / path).read_bytes()) == expected, 'private protected postimage differs: ' + path)
        need(blob(ASSIGNED, tool_commit, path) == blob(ASSIGNED, MAIN, path) == (ASSIGNED / path).read_bytes(), 'protected branch bytes differ from main: ' + path)
    approved, frozen = frozen_approval()
    controls = self_check()
    SCRATCH.mkdir(exist_ok=True)
    physical(SCRATCH)
    out = SCRATCH / args.label
    need(not os.path.lexists(out), 'run label already exists; preserve it and choose a new label')
    out.mkdir()
    result = dict(kind='native_h1_scanner_comparison', version=1, started_utc=datetime.now(timezone.utc).isoformat(),
                  status='incomplete', source_branch_head=tool_commit, main=MAIN,
                  supplied_composition=str(tree), composition_manifest_sha256=sha(manifest_raw),
                  helper_path=str(Path(__file__).resolve()), helper_sha256=sha(Path(__file__).read_bytes()),
                  controls=controls, d128_gate_passed=False, instrument_approval_changed=False,
                  proposed_api_owner_approval='pending_not_covered_by_D127', protected_branch_equal_main=True,
                  scope='Same committed scanner over complete identical-mask Git exports; no generation import, provider, publication or launch authority.')
    try:
        base_tree, base_info = materialize(ASSIGNED, MAIN, out / 'baseline-source')
        candidate_tree, candidate_info = materialize(tree, candidate_commit, out / 'candidate-source')
        tool = candidate_tree / SKILL / 'scan.py'
        need(tool.read_bytes() == blob(ASSIGNED, SCANNER_SCOPE_REVIEW_COMMIT, SKILL + '/scan.py'),
             'scanner differs from the static input-scope review; review its read paths before continuing')
        names = git('ls-tree', '-r', '--name-only', tool_commit, '--', SKILL).decode().splitlines()
        need(names and len(set(names)) == len(names), 'scanner asset roster missing or duplicated')
        assets = {}
        for name in names:
            path = physical(candidate_tree / name, candidate_tree)
            expected = blob(ASSIGNED, tool_commit, name)
            need(path.read_bytes() == expected, 'private scanner asset differs from committed tool')
            assets[name] = sha(expected)
        result['tool_assets_sha256'] = assets
        result['frozen_approval'] = approved
        result['frozen_inputs'] = frozen
        result['tool_asset_delta'] = [dict(path=name, before_sha256=approved['tool_assets_sha256'].get(name), after_sha256=assets.get(name))
             for name in sorted(set(assets) | set(approved['tool_assets_sha256'])) if assets.get(name) != approved['tool_assets_sha256'].get(name)]
        # Main is the first real unit on this identical scanner path; verify its
        # persisted full arrays and immutable inputs before starting the second.
        result['baseline'] = scan_one('current_main', base_tree, base_info, tool, tool_commit, assets, out / 'scan-main', dependencies, args.timeout_seconds)
        result['candidate'] = scan_one('current_candidate', candidate_tree, candidate_info, tool, tool_commit, assets, out / 'scan-candidate', dependencies, args.timeout_seconds)
        result['comparisons'] = [compare(label, before, after) for label, before, after in (
            ('current_main_vs_current_candidate', result['baseline']['arrays'], result['candidate']['arrays']),
            ('frozen_D128_main_vs_current_main', frozen['baseline']['arrays'], result['baseline']['arrays']),
            ('frozen_D128_candidate_vs_current_candidate', frozen['candidate']['arrays'], result['candidate']['arrays']))]
        result['d128_coverage'] = coverage(result['comparisons'][0], approved)
        result['reference_arrays_match'] = all(row['exact_arrays_equal'] for row in result['comparisons'][1:])
        need(same(frozen_approval(), (approved, frozen)), 'retained D128 evidence changed during comparison')
        need(manifest_path.read_bytes() == manifest_raw and git('rev-parse', 'HEAD').decode().strip() == tool_commit, 'supplied input identity changed')
        need(sha(supplied_config.read_bytes()) == manifest['config_original_sha256'], 'supplied private test-only Git config changed')
        for export, identity in ((base_tree, base_info), (candidate_tree, candidate_info)):
            checked = census(export, identity)
            need(same(checked, {key: identity[key] for key in checked}), 'final export census differs')
        for path in POST:
            need((ASSIGNED / path).read_bytes() == blob(ASSIGNED, MAIN, path), 'protected branch changed during comparison')
        quiet()
        result.update(status='complete_diagnostic_not_owner_approval', private_configs_armed=False,
                      protected_branch_equal_main=True, full_comparisons_present=True)
    except BaseException as exc:
        result['failure'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        result['ended_utc'] = datetime.now(timezone.utc).isoformat()
        target = out / 'comparison.json'
        digest = save(target, result)
        if result['status'] == 'complete_diagnostic_not_owner_approval':
            md_digest = write(out / 'comparison.md', markdown(result, target))
        else:
            md_digest = write(out / 'comparison.md', ('# H1 scanner comparison incomplete\n\n' + result.get('failure', 'No completion evidence.') + '\n\nFull retained evidence: `' + str(target) + '`.\nD128 gate passed: false.\n').encode())
        print(json.dumps(dict(path=str(target), sha256=digest, markdown_sha256=md_digest, status=result['status']), sort_keys=True))
    return 0 if result['status'] == 'complete_diagnostic_not_owner_approval' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, help='read-only private four-packet composition under assigned H1 scratch')
    parser.add_argument('--label', help='fresh direct-child output label')
    parser.add_argument('--timeout-seconds', type=int, default=3000)
    parser.add_argument('--self-check', action='store_true', help='invented comparator controls only; no source export or scan')
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    raise SystemExit(worker(args) if args.worker else main(args))
