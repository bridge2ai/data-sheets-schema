"""Inventory U3-H registry-reading test files, 2026-11-09 (review P1-1).

Inputs: an explicit physical committed source tree and its tests, including
ignored Python files. Outputs: JSON file hashes, source-search candidates and
execution prerequisites. This script never imports project modules or runs
tests/builds/installers. Installed-wheel validation remains unavailable offline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
SCRATCH = EXEC / 'scratch-native-u1u3/u3h'
LOCK = EXEC / 'plans/native_quiet_window.lock'
READERS = {
    'tests/test_api_launcher.py': 'Detached real prompts check CLI reads registry and asserts every pin is current.',
    'tests/test_api_playbook_context.py': 'Direct prompt_files/disk_status reader.',
    'tests/test_pin_granularity.py': 'Direct pin status and real registry body-hash reader.',
    'tests/test_prompt_registry.py': 'Registry parsing, pinning, canonical status and CLI reader.',
    'tests/test_resources.py': 'Registry resource routing, pin provenance and current pin reader.',
    'tests/test_shared_generation_assets.py': 'Exact preservation of historical registry entries.',
    'tests/test_shared_generation_resources.py': 'Registry byte capture and resource authority checks.',
    'tests/test_shared_generation_scope_context.py': 'Selected evidence-policy canonical registry entry.',
    'tests/test_installed_wheel.py': 'Installed-package registry disk_status; network-dependent opt-in.',
    'tests/test_generation_record_schema.py': 'Companion metadata reads and hashes registry bytes.',
    'tests/test_american_english_rule.py': 'Prompts check CLI and canonical_prompt_status.',
    'tests/test_agentic_provenance_completeness.py': 'Canonical prompt status of retained canary record.',
    'tests/test_schema_straddle.py': 'Canonical prompt status of retained historical records.',
    'tests/test_historical_prompt_recovery.py': 'Canonical prompt status with historical recovery branch.',
}
NON_READER_MATCHES = {
    'tests/test_cli/test_render_gate.py': 'prompt_registry is a local patch.dict variable, not the module.',
    'tests/test_ci_sharding.py': 'registered_paths occurs only in an emitted regression node name.',
    'tests/test_wave7_5213_d76_registration.py': 'registered_paths occurs in the regression node name.',
}
PATTERN = re.compile(r'canonical_hashes|prompt_registry|canonical_prompt_status|'
                     r'registered_paths\(|pin_status\(')
# CLI argv lists may spell prompts/check on separate source lines. Search the
# complete file as well as named module/function references; a line-only search
# misses the real detached registry check in test_api_launcher.py.
CLI_CHECK_PATTERN = re.compile(r'''['"]prompts['"]\s*,\s*['"]check['"]|\bprompts\s+check\b''')
ENV = dict(PATH='/usr/bin:/bin', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='',
    GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
    GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
GIT = ['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
       '-c', 'core.fsmonitor=false', '-c', 'protocol.allow=never']


def quiet():
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet-window lock exists; stop registry inventory')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    quiet()
    result = subprocess.run([*GIT, *args], cwd=root, env=ENV, capture_output=True,
                            check=True, timeout=60)
    quiet()
    return result.stdout


def inventory(root=ROOT):
    """Return explicit reader identities and an ignore-independent candidate audit."""
    quiet()
    root = Path(root)
    need(root.is_absolute() and root.resolve(strict=True) == root, 'physical absolute source root required')
    need(EXEC.name == 'd4d-executions' and (root == ROOT or root.is_relative_to(SCRATCH)),
         'source is outside assigned worktree/private U3-H composition')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    git(root, 'diff-index', '--quiet', 'HEAD', '--')
    helper_path = Path(__file__).relative_to(ROOT).as_posix()
    need(git(root, 'show', head + ':' + helper_path) == Path(__file__).read_bytes(),
         'inventory helper differs from declared source commit')
    rows = []
    for name, reason in READERS.items():
        quiet()
        path = root / name
        need(path.resolve(strict=True) == path, 'reader source is aliased: ' + name)
        raw = path.read_bytes()
        need(raw == git(root, 'show', head + ':' + name), 'reader differs from declared commit: ' + name)
        rows.append(dict(path=name, bytes=len(raw), sha256=sha(raw), reason=reason,
            offline_execution=('unavailable_network_install_opt_in' if name.endswith('test_installed_wheel.py')
                               else 'eligible_with_declared_fixtures'),
            observed_result='not_run_by_inventory'))
    candidates = []
    # pathlib enumeration reads the physical tests tree, including gitignored
    # files; there is no Git/rg ignore filtering in this completeness check.
    for path in sorted((root / 'tests').rglob('*.py')):
        quiet()
        need(path.resolve(strict=True) == path, 'candidate test source is aliased: ' + str(path))
        raw = path.read_bytes()
        text = raw.decode('utf-8')
        lines = text.splitlines()
        hits = {number for number, line in enumerate(lines, 1) if PATTERN.search(line)}
        hits.update(text.count('\n', 0, match.start()) + 1
                    for match in CLI_CHECK_PATTERN.finditer(text))
        if hits:
            name = path.relative_to(root).as_posix()
            candidates.append(dict(path=name, sha256=sha(raw), lines=sorted(hits),
                classification=('reader' if name in READERS else
                                'reviewed_non_reader' if name in NON_READER_MATCHES else 'needs_review'),
                reason=READERS.get(name, NON_READER_MATCHES.get(name))))
    unclassified = [row['path'] for row in candidates if row['classification'] == 'needs_review']
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == head, 'source HEAD moved during inventory')
    git(root, 'diff-index', '--quiet', 'HEAD', '--')
    return dict(source_root=str(root), source_commit=head, inventory_kind='static_source_inventory',
        scope='Explicit registry readers and named canonical-status/companion consumers; '
              'not a dynamic transitive call census.',
        reader_count=len(rows), readers=rows, search_includes_ignored=True,
        candidate_pattern=PATTERN.pattern, cli_check_candidate_pattern=CLI_CHECK_PATTERN.pattern,
        candidates=candidates, unclassified_candidates=unclassified,
        source_inventory_complete=not unclassified,
        environment_requirements=[
            'Full committed archive with private Git metadata, HEAD and local historical objects.',
            'Retain data/rubric/, project/, CLAUDE.md, poetry.lock and committed prompt/schema assets.',
            'Keep corpus-dependent skips explicit when historical record fixtures are unavailable.',
            'Do not opt into D4D_INSTALL_TESTS: installed-wheel dependency installation needs network.',
            'Launcher registry checks create a local venv with --without-pip and reuse installed dependencies; no installation/network required.',
            'Run eligible files only with provider keys removed, network denied and external basetemp.',
        ],
        status=dict(tests_run=False, required_cohorts_complete=False,
                    installed_wheel_acceptance=False, native_acceptance=False),
        helper_sha256=sha(Path(__file__).read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    value = inventory(args.root)
    raw = json.dumps(value, indent=2, sort_keys=True) + '\n'
    if args.out is None:
        print(raw, end='')
    else:
        path = args.out
        need(path.is_absolute() and path.is_relative_to(SCRATCH), 'output must be under U3-H scratch')
        need(path.parent.resolve(strict=True) == path.parent, 'output parent is aliased or absent')
        quiet()
        with path.open('x') as stream:
            stream.write(raw)
        print(json.dumps(dict(output=str(path), sha256=sha(raw.encode()), reader_count=len(READERS),
                              source_inventory_complete=value['source_inventory_complete'])))


if __name__ == '__main__':
    main()
