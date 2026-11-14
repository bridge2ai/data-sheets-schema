#!/usr/bin/env python3
"""Derive G07's external-scratch offline runner, 2026-11-12.

Input: committed G04 runner. Output: a new sibling helper, never overwritten.
Only output/source routing and an offline scanner mode change; preserve sandbox,
origin witnesses, credential removal, deadlines and observed-process cleanup.
"""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'scripts/adhoc/run_native_main_integration_tests_20261112.py'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '113ecce07179b62f3406d0c85e078d58bbcddfad7fec18a14268e425fdb85c42'
text = raw.decode()


def replace(old, new, count=1):
    global text
    assert text.count(old) == count, old
    text = text.replace(old, new)


replace('"""Offline G04/G05 integration test runner, 2026-11-12.',
        '"""Offline G07 packet and capture test runner, 2026-11-12.')
replace('Purpose: validate the main-targeted native candidate without composition arming.',
        'Purpose: validate the assigned branch or its exact private packet composition.')
replace('Outputs: new .temp/native-main-integration/tests cohort directories inside this\nworktree,',
        'Outputs: new sibling scratch-native-main-integration-20261112/tests cohorts,')
replace('ROOT = Path(__file__).resolve().parents[2]\nif ROOT.name != "codex-native-main-integration-20261112":\n    raise RuntimeError("runner is restricted to the assigned integration worktree")',
        'SCRIPT_ROOT = Path(__file__).resolve().parents[2]\nROOT = SCRIPT_ROOT\nif SCRIPT_ROOT.name != "codex-native-main-integration-20261112":\n    raise RuntimeError("runner helper must stay in the assigned branch")')
replace('SCRATCH = ROOT / ".temp/native-main-integration/tests"',
        'SCRATCH_BASE = EXECUTIONS / "scratch-native-main-integration-20261112"\nSCRATCH = SCRATCH_BASE / "tests"')
replace('"""Deny network/native execution and writes outside the assigned worktree."""',
        '"""Deny network/native execution and writes outside source plus sibling scratch."""')
replace("'  (require-not (subpath ' + json.dumps(str(ROOT)) + '))\\n'",
        "'  (require-not (subpath ' + json.dumps(str(ROOT)) + '))\\n'\n        '  (require-not (subpath ' + json.dumps(str(SCRATCH_BASE)) + '))\\n'")
replace('"test output must stay under the assigned worktree test root"',
        '"test output must stay under the assigned sibling scratch root"')
replace('[sys.executable, "-P", "-B", str(Path(__file__).resolve()), "--child-check"],',
        '[sys.executable, "-P", "-B", str(Path(__file__).resolve()), "--tree", str(ROOT), "--child-check"],')
replace('    import pytest\n    command =', '''    if args.scanner:
        command = [sys.executable, '-P', '-B', str(ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'),
                   '--root', str(ROOT), '--report', str(out / 'scanner.md'), '--json', str(out / 'scanner.json'), '--full-json']
        save(out / 'scanner-command.json', {'args': command})
        code = subprocess.call(command, cwd=ROOT, env=os.environ.copy())
        save(out / 'origins-after.json', origin_witness())
        save(out / 'worker-outcome.json', {'returncode': code, 'source_origin_checks_passed': True})
        return code
    import pytest
    command =''')
replace('               "--out", str(out), "--workers", str(args.workers),',
        '               "--tree", str(ROOT), "--out", str(out), "--workers", str(args.workers),')
replace('    command += args.nodes\n    commit =',
        '    if args.scanner:\n        command += ["--scanner"]\n    command += args.nodes\n    commit =')
replace('    parser.add_argument("--out", type=Path)',
        '    parser.add_argument("--tree", type=Path, required=True)\n    parser.add_argument("--scanner", action="store_true")\n    parser.add_argument("--out", type=Path)')
replace('    args = parser.parse_args()\n    if args.child_check:', '''    args = parser.parse_args()
    global ROOT
    tree = args.tree.absolute()
    if tree.resolve(strict=True) != tree:
        parser.error('source tree must be a physical path')
    if tree != SCRIPT_ROOT:
        if tree.name != 'tree' or tree.parent.parent != SCRATCH_BASE:
            parser.error('only assigned branch or private G07 composition is allowed')
        manifest = json.loads((tree.parent / 'composition.json').read_bytes())
        if manifest.get('status') != 'composed_not_tested' or manifest.get('tree') != str(tree):
            parser.error('private composition manifest is not ready')
        commit = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip()
        if commit != manifest['composition_commit']:
            parser.error('private source HEAD differs from composition manifest')
        for row in manifest['packets']:
            if digest(tree / row['path']) != row['postimage_sha256']:
                parser.error('private protected postimage changed')
    ROOT = tree
    if args.child_check:''')
replace('    if args.out is None or not args.nodes:\n        parser.error("--out and at least one explicit tests/ node are required")',
        '    if args.out is None or (not args.nodes and not args.scanner) or (args.nodes and args.scanner):\n        parser.error("--out and either explicit tests/ nodes or --scanner are required")')
target = ROOT / 'scripts/adhoc/run_native_g07_tests_20261112.py'
with target.open('x') as stream:
    stream.write(text)
assert target.read_text() == text
print(str(target)); print(hashlib.sha256(target.read_bytes()).hexdigest())
