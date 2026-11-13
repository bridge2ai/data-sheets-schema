#!/usr/bin/env python3
"""One-command offline D128 refresh for the native candidate, 2026-11-13.

Inputs: explicit later HEAD of codex/native-main-integration-20261112,
unchanged reviewed scanner and helper bytes, D146 postimages, frozen D128 evidence.
Outputs: new composition and comparison evidence, never an approval or source edit.
Serves the helper-1 owner-delivery/timings assignment; defaults to read-only plan.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = E / 'codex-development-efficiency-20261111'
S = R / 'scripts/adhoc'
SOURCE = E / 'codex-native-main-integration-20261112'
P = E.parent / 'data-sheets-schema'
EXPORTS = E / 'scratch-native-main-integration-20261112'
SCANS = E / 'scratch-native-h1-scanner-20261112'
PYTHON = P / '.venv/bin/python'
REVIEW = '99ac3432daab7f6161b321038986e489d5e6fd14'
BRANCH = 'codex/native-main-integration-20261112'
HELPERS = {
    'prepare_h1_d146_comparison_export_20261113.py': '5c0440e7c746cad1edeaf3d2cbf53caffbcd7ef0ca8b7c21b05cdae4e75b134b',
    'native_h1_owner_scanner_comparison_v3_20261113.py': '846299ee6bae87084272d32b2eb5eeb0810623f74d0ac2b2e57d2d81340122fb',
}
PROTECTED = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881',
    'src/download/prompts/canonical_hashes.yaml': 'd0de85f3da4bfa29a4bfc7ad6158abad5b3373a937a4e7e3b360217fa4eaf57f',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}
SKILL = '.claude/skills/d4d-generation-specificity-audit'
ASSETS = {
    SKILL + '/scan.py': '27b70f8309e6a1383ce5573d34e4c06440c347e8961e446f2261d9f5f9aa0dfb',
    SKILL + '/SKILL.md': 'e422b3b635f7330abaea1860b7156644d4a243417024cc4c36d126c4ab75a780',
    SKILL + '/exceptions.yaml': 'adb2376d10bf26558c022e31fda983b857311ba872972ccbdfc2ba5d141c9865',
    SKILL + '/tokens.yaml': '5dc373161654f6a1b897b778d0d82a046b59a568d7e57e4436e70975bca8d681',
}
OTHER_PINS = {
    'src/download/prompts/native_shared_receipt_policy_v1.md': '8b0695212d94380949ddc523963021b1edcb3ebb9b6a52291d36238a92779f1c',
    'tests/fixtures/native_d128_approved.json': '65330131940ca8be1cd4288ed3cca9ca980eafc665faa964fa443e8f44d63399',
}
EVIDENCE = E / 'scratch-native-u1u3/u3h/itemized-scanner-comparison.json'
EVIDENCE_SHA = '98e6d082db4df2176a452ab60bc83280406333ba339a96e30ae501aeb6957ada'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/var/empty', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': 'file', 'GIT_TERMINAL_PROMPT': '0',
       'GIT_OPTIONAL_LOCKS': '0', 'PYTHONOPTIMIZE': '0', 'UV_OFFLINE': '1', 'PIP_NO_INDEX': '1'}


def need(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def physical(path):
    need(path.absolute() == path.resolve(), 'symlink in input/output path: ' + str(path))
    return path


def git(root, *args):
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c',
        'core.hooksPath=/dev/null', *args], cwd=root, env=ENV, capture_output=True, check=True)
    return result.stdout


def quiet():
    need(not os.path.lexists(E / 'plans/native_quiet_window.lock'), 'quiet-window lock active')


def helper_commands(commit, suffix, digest):
    export = [str(PYTHON), '-I', '-B', str(S / next(iter(HELPERS))),
              '--commit', commit, '--label', 'h1-ci-' + suffix]
    comparison = [str(PYTHON), '-S', '-P', '-B', str(S / list(HELPERS)[1]),
        '--tree', str(EXPORTS / ('h1-ci-' + suffix) / 'tree'),
        '--source-commit', commit, '--candidate-commit', commit,
        '--scanner-review-commit', REVIEW, '--composition-manifest-sha256', digest,
        '--label', 'h1-d128-' + suffix]
    for path, value in PROTECTED.items():
        comparison.extend(['--approved-protected', path + '=' + value])
    return export, comparison


def preflight(commit, suffix):
    quiet()
    need(re.fullmatch('[0-9a-f]{40}', commit or '') is not None, 'full local commit required')
    need(re.fullmatch('[a-z0-9][a-z0-9-]{0,52}', suffix or '') is not None,
         'label suffix must be 1-53 lowercase letters/digits/hyphens')
    for path in (R, S, SOURCE, EXPORTS, SCANS, EVIDENCE):
        physical(path)
    for name, digest in HELPERS.items():
        need(sha(physical(S / name).read_bytes()) == digest, 'saved helper changed: ' + name)
    need(git(SOURCE, 'rev-parse', 'HEAD').decode().strip() == commit, 'assigned HEAD differs')
    need(git(SOURCE, 'branch', '--show-current').decode().strip() == BRANCH, 'assigned branch differs')
    need(git(SOURCE, 'rev-parse', '--is-shallow-repository').strip() == b'false', 'full local history required')
    need(not git(SOURCE, 'diff', '--name-only', 'HEAD').strip(), 'tracked candidate edits present')
    names = git(SOURCE, 'ls-tree', '-r', '--name-only', commit, '--', SKILL).decode().splitlines()
    need(set(names) == set(ASSETS), 'scanner asset roster changed; new scope review required')
    for path, digest in dict(PROTECTED, **ASSETS, **OTHER_PINS).items():
        need(sha(git(SOURCE, 'show', commit + ':' + path)) == digest
             and sha(physical(SOURCE / path).read_bytes()) == digest, 'pinned bytes changed: ' + path)
    for path, digest in ASSETS.items():
        need(sha(git(SOURCE, 'show', REVIEW + ':' + path)) == digest, 'reviewed scanner pin differs')
    need(sha(EVIDENCE.read_bytes()) == EVIDENCE_SHA, 'frozen D128 evidence changed')
    gitlink = git(SOURCE, 'ls-tree', commit, 'fairscape_models').split()[2].decode()
    git(P / 'fairscape_models', 'cat-file', '-e', gitlink + '^{commit}')
    for path in (EXPORTS / ('h1-ci-' + suffix), SCANS / ('h1-d128-' + suffix)):
        physical(path)
        need(not os.path.lexists(path), 'preserve existing output and choose another label: ' + str(path))
    return {'source_commit': commit, 'source_tree': git(SOURCE, 'rev-parse', commit + '^{tree}').decode().strip(),
            'scanner_review_commit': REVIEW, 'helper_sha256': HELPERS, 'scanner_assets_sha256': ASSETS,
            'protected_sha256': PROTECTED, 'other_pins': OTHER_PINS, 'evidence_sha256': EVIDENCE_SHA,
            'fairscape_gitlink': gitlink, 'wrapper_sha256': sha(Path(__file__).read_bytes()),
            'd128_gate_passed': False, 'instrument_approval_changed': False}


def invoke(command):
    quiet()
    result = subprocess.run(command, env=ENV, text=True, capture_output=True)
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise RuntimeError('helper failed; partial evidence retained; no automatic retry')
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', help='full current HEAD of the assigned candidate branch')
    parser.add_argument('--label', help='fresh output suffix, never an existing evidence label')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true', help='export and scan both baseline and candidate')
    mode.add_argument('--plan', action='store_true', help='read-only preflight (the default)')
    mode.add_argument('--self-check', action='store_true', help='synthetic comparator controls only')
    args = parser.parse_args()
    if args.self_check:
        name = list(HELPERS)[1]
        need(sha(physical(S / name).read_bytes()) == HELPERS[name], 'comparison helper changed')
        result = invoke([str(PYTHON), '-S', '-P', '-B', str(S / name), '--self-check'])
        print(json.dumps({'status': 'synthetic_controls_only', 'result': result}, sort_keys=True))
        return
    result = preflight(args.commit, args.label)
    export, comparison = helper_commands(args.commit, args.label, '<computed-manifest-sha256>')
    result.update(status='read_only_plan', export_command=export, comparison_command=comparison)
    if not args.run:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    exported = invoke(export)
    path = EXPORTS / ('h1-ci-' + args.label) / 'composition.json'
    manifest_raw = physical(path).read_bytes()
    digest = sha(manifest_raw)
    need(exported['path'] == str(path) and exported['sha256'] == digest, 'export output differs from persisted manifest')
    manifest = json.loads(manifest_raw)
    tree = physical(path.parent / 'tree')
    need(manifest['source_commit'] == manifest['composition_commit'] == args.commit
         and manifest['composition_tree'] == result['source_tree']
         and manifest['submodule']['gitlink'] == result['fairscape_gitlink'], 'export identity differs')
    need(not git(tree, 'remote').strip() and not git(tree / 'fairscape_models', 'remote').strip(), 'export has remotes')
    need(sha((tree / '.git/config').read_bytes()) == manifest['config_original_sha256'], 'export config changed')
    for name, expected in PROTECTED.items():
        need(sha(physical(tree / name).read_bytes()) == expected, 'export protected bytes differ')
    _, comparison = helper_commands(args.commit, args.label, digest)
    compared = invoke(comparison)
    report_path = SCANS / ('h1-d128-' + args.label) / 'comparison.json'
    report_raw = physical(report_path).read_bytes()
    report = json.loads(report_raw)
    md_path = report_path.with_suffix('.md')
    need(compared['path'] == str(report_path) and compared['sha256'] == sha(report_raw)
         and compared['markdown_sha256'] == sha(md_path.read_bytes()), 'comparison output differs from persisted report')
    need(report['status'] == 'complete_diagnostic_not_owner_approval'
         and report['source_branch_head'] == report['candidate_commit'] == args.commit
         and report['composition_manifest_sha256'] == digest
         and report['scanner_scope_review_commit'] == REVIEW
         and report['tool_assets_sha256'] == ASSETS
         and report['full_comparisons_present'] is True
         and report['d128_gate_passed'] is False
         and report['instrument_approval_changed'] is False, 'comparison is not complete diagnostic evidence')
    result.update(status=report['status'], comparison_command=comparison,
                  export_result=exported, comparison_result=compared)
    receipt = path.parent / 'refresh-command.json'
    with receipt.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    need(json.loads(receipt.read_bytes()) == result, 'persisted command receipt differs')
    print(json.dumps({'path': str(receipt), 'sha256': sha(receipt.read_bytes()),
                      'comparison': compared, 'd128_gate_passed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
