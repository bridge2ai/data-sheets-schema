#!/usr/bin/env python3
"""H1 public completion failure diagnosis, 2026-11-12.
Inputs: one completed test case, fixed installed dependency sources and df012 git blobs.
Output: a local finding JSON; no tests, imports of target code, scans or network.
Serves helper-1 integration; preserves the synthetic HOME guard and evidence.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import stat
import subprocess
import textwrap

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = E / 'codex-development-efficiency-20261111'
W = E / 'codex-native-main-integration-20261112'
S = E / 'scratch-native-h1-scanner-20261112'
T = S / 'tests/h1-public-completion'
CASE = T / 'cases/popen-gw0/test_actual_public_correction_0/native26'
HOME_CASE = CASE / 'synthetic-runtime/synthetic-home'
SITE = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/lib/python3.13/site-packages')
HEAD = 'df0122254cc7c9fe10470ee9eabc26c71a411a14'
OUT = R / 'notes/development_efficiency_20261111/handoffs/codex-h1-public-home-finding-20261112.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8 * 1024 * 1024:
            raise ValueError('refuse nonregular or unbounded input: ' + str(path))
        raw = stream.read()
        after = os.fstat(stream.fileno())
    for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'):
        if getattr(before, field) != getattr(after, field):
            raise ValueError('input changed during read: ' + str(path))
    return raw


def selected(raw, ranges):
    lines = raw.decode('utf-8').splitlines()
    return [{'first_line': start, 'last_line': min(end, len(lines)),
             'text': '\n'.join(lines[start - 1:end])} for start, end in ranges]


def file_evidence(path, ranges=None):
    raw = read_regular(path)
    result = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
    if ranges:
        result['excerpts'] = selected(raw, ranges)
    return result


def git(args):
    command = ['git', '-C', str(W), *args]
    result = subprocess.run(command, check=True, capture_output=True, timeout=30)
    return {'argv': command, 'returncode': result.returncode,
            'stdout_sha256': sha(result.stdout),
            'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()}


def census(path):
    # scandir includes hidden and ignored entries; recurse only physical directories.
    root = path.lstat()
    if not stat.S_ISDIR(root.st_mode) or path.resolve(strict=True) != path:
        raise ValueError('case HOME must be a physical directory')
    result = []
    def visit(directory):
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                info = entry.stat(follow_symlinks=False)
                target = Path(entry.path)
                row = {'path': str(target), 'relative_path': str(target.relative_to(path)),
                       'mode': info.st_mode, 'size': info.st_size,
                       'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns,
                       'birthtime_seconds': getattr(info, 'st_birthtime', None),
                       'symlink': stat.S_ISLNK(info.st_mode)}
                if stat.S_ISREG(info.st_mode):
                    row.update(file_evidence(target))
                elif stat.S_ISLNK(info.st_mode):
                    row['target'] = os.readlink(target)
                result.append(row)
                if stat.S_ISDIR(info.st_mode):
                    visit(target)
    visit(path)
    return result


def main():
    if OUT.exists():
        raise FileExistsError('preserve existing finding: ' + str(OUT))
    log = file_evidence(T / 'pytest.log', [(285, 342), (346, 405), (417, 420)])
    transcript = read_regular(CASE / 'native-attempt/transcript.jsonl')
    control = read_regular(CASE / 'native-attempt/control.jsonl')
    census_rows = census(HOME_CASE)
    sources = {
        'pystow_init': ('pystow/__init__.py', [(48, 55)]),
        'pystow_constants': ('pystow/constants.py', [(19, 69)]),
        'pystow_utils': ('pystow/utils.py', [(960, 1026)]),
        'pystow_api': ('pystow/api.py', [(71, 90)]),
        'pystow_impl': ('pystow/impl.py', [(51, 88)]),
        'oaklib_constants': ('oaklib/constants.py', [(1, 16)]),
        'oaklib_init': ('oaklib/__init__.py', [(1, 14)]),
        'oaklib_selector': ('oaklib/selector.py', [(1, 20)]),
        'term_cli': ('linkml_term_validator/cli.py', [(11, 25)]),
        'term_plugins': ('linkml_term_validator/plugins/__init__.py', [(1, 9)]),
        'term_base': ('linkml_term_validator/plugins/base.py', [(1, 16)]),
    }
    source_files = {key: file_evidence(SITE / relative, ranges)
                    for key, (relative, ranges) in sources.items()}
    constants = ast.parse(read_regular(SITE / 'pystow/constants.py'))
    assignment = next(node for node in constants.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'README_TEXT' for t in node.targets))
    if not isinstance(assignment.value, ast.Call) or not isinstance(assignment.value.args[0], ast.Constant):
        raise ValueError('unexpected README literal shape')
    expected_readme = (textwrap.dedent(assignment.value.args[0].value) + '\n').encode()
    actual_readme = read_regular(HOME_CASE / '.data/README.md')
    blobs = {}
    for relative in (
        'src/data_sheets_schema/native_runtime_profiles.py',
        'src/data_sheets_schema/native_model_aliases.py',
        'src/data_sheets_schema/native_shared_observations.py',
        'src/data_sheets_schema/native_shared_controller_orchestration.py',
        'tests/fixtures/native_shared_execution/fake_cli.py',
        'tests/utils/native_synthetic_evidence.py',
    ):
        blobs[relative] = git(['show', HEAD + ':' + relative])
    report = {
        'kind': 'h1_public_home_finding', 'date': '2026-11-12', 'source_commit': HEAD,
        'scope': 'Read-only completed artifacts and source; no target imports or executions; no baseline rerun.',
        'case_home_only': str(HOME_CASE), 'census_method': 'os.scandir includes hidden/ignored entries; lstat and no-follow regular-file reads; no symlink recursion',
        'home_census': census_rows,
        'observed_result': 'Public completion failed when observing the successful shared-test-9 full_terms result: empty synthetic HOME refusal, then same refusal during final-publication runtime validation.',
        'pytest_evidence': log,
        'transcript': {**file_evidence(CASE / 'native-attempt/transcript.jsonl'),
                       'last_six_lines': transcript.decode().splitlines()[-6:]},
        'control': {**file_evidence(CASE / 'native-attempt/control.jsonl'),
                    'last_five_lines': control.decode().splitlines()[-5:]},
        'peer': file_evidence(CASE / 'synthetic-runtime/ordinary-python-test-peer', [(175, 190), (219, 239)]),
        'python_paths': file_evidence(T / 'venv/lib/python3.13/site-packages/native_integration_paths.pth', [(1, 20)]),
        'installed_source_evidence': source_files,
        'readme_literal_comparison': {'method': 'stdlib AST literal extraction plus textwrap.dedent and print newline; target module never imported',
                                     'exact_bytes_equal': expected_readme == actual_readme,
                                     'expected_sha256': sha(expected_readme), 'actual_sha256': sha(actual_readme)},
        'git_evidence': blobs,
        'unchanged_runtime_since_prepin': git(['diff', '5d63d0a77', HEAD, '--',
             'src/data_sheets_schema/native_runtime_profiles.py',
             'src/data_sheets_schema/native_model_aliases.py',
             'tests/utils/native_synthetic_evidence.py']),
        'h2_observation_diff': git(['diff', '8a00bb828', HEAD, '--',
                                  'src/data_sheets_schema/native_shared_observations.py']),
        'creator_classification': {
            'status': 'strong source/artifact/timestamp-consistent inference; creator syscall was not traced',
            'path': 'full_terms command imports linkml_term_validator.cli -> plugins/base -> oaklib -> selector/constants -> pystow; pystow import runs ensure_readme and oaklib constants calls pystow.module("oaklib").',
            'environment': 'fixed Python peer launches Bash command subprocess.run without env override; runtime fixture supplies empty synthetic HOME. No provider credentials are implicated.',
            'timing': 'control admits shared-test-9 at 2026-11-12T19:22:50.246970Z; README and oaklib directory birthtimes are 2026-11-12T11:22:53-0800.',
            'limitations': 'No per-process file-creation trace; no old-head reproduction; no claim that every integration gate or public completion passed.'},
        'model_alias_progress': {
            'evidence': 'Captured assistant frames use synthetic-native-returned-model, and control admits commands through full_terms. Current observation code validates the explicit requested/returned pair rather than requiring both labels equal the requested value.',
            'conclusion': 'This attempt advanced past the former model-label refusal into later runtime revalidation; it remains failed and does not establish completed acceptance.',
            'limit': 'No paired baseline run or full post-failure acceptance inference.'},
        'proposed_disposition': 'Separate follow-up: reproduce the term-validator import side effect in bounded isolated child storage, then isolate helper cache writes outside guarded synthetic HOME through a reviewed explicit test-peer/environment contract. Preserve the empty-HOME and credential guards; do not delete evidence or allowlist arbitrary HOME contents. Any fixed-peer change requires its deliberate digest update and focused refusal coverage before a newly authorized public rerun.',
        'helper': file_evidence(Path(__file__)),
    }
    raw = (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + '\n').replace(chr(64), '\\u0040').encode()
    with OUT.open('xb') as stream:
        stream.write(raw)
    persisted = read_regular(OUT)
    if persisted != raw or not persisted:
        raise RuntimeError('output verification failed')
    print(json.dumps({'output': str(OUT), 'sha256': sha(persisted),
                      'helper_sha256': report['helper']['sha256'],
                      'readme_exact_literal_match': expected_readme == actual_readme}))


if __name__ == '__main__':
    main()
