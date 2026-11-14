"""#4354 U1 round 3, 2026-11-06: contract edits and bounded offline checks.

Inputs: round-two worktree and composed scratch; outputs: AST proof and logs.
Protected sources are only read. Each test has a deadline and quiet-lock guard.
"""
import ast
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback

from native_u1_round2_20261106 import ROOT, SCRATCH, COMPOSED, LOCK, environment, sha

LAST_LOCK_OBSERVED = 0.0

OVERLAYS = (
    '.claude/skills/d4d-generation-specificity-audit/scan.py',
    'src/data_sheets_schema/native_shared_render.py',
    'tests/test_audit_recall_leak_rendered.py',
    'tests/test_bc1_selection.py',
    'tests/test_generation_specificity_delegated.py',
    'tests/test_wave7_5213_d76_round2_binding.py',
    'tests/test_wave7_5213_d76_legacy_registration.py',
    'tests/test_native_u1_scanner_contracts.py',
)


def identities():
    protected = ('src/data_sheets_schema/shared_generation.py',
                 'src/download/prompts/canonical_hashes.yaml',
                 'tests/utils/run_spec_boundaries.py',
                 'tests/utils/run_spec_boundary_contracts.json')
    result = {'overlays': {}, 'protected': {}, 'packets': {}}
    for relative in OVERLAYS:
        raw = (ROOT/relative).read_bytes()
        assert (COMPOSED/relative).read_bytes() == raw, relative
        result['overlays'][relative] = sha(raw)
    for relative in protected:
        old = subprocess.check_output(['git', 'show', 'e0b868b0e:' + relative], cwd=ROOT,
                                      env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})
        assert (ROOT/relative).read_bytes() == old, relative
        result['protected'][relative] = sha(old)
    for name in ('shared_generation', 'api_runner_companion', 'canonical_hashes', 'run_spec_boundary_contracts'):
        metadata = json.loads((ROOT/'scripts/adhoc/native_u1_packets'/f'{name}.json').read_text())
        assert sha((COMPOSED/metadata['target']).read_bytes()) == metadata['postimage_sha256'], name
        result['packets'][name] = metadata['postimage_sha256']
    proof = json.loads((SCRATCH/'r3-executable-ast.json').read_text())
    before = subprocess.check_output(['git', 'show', 'e0b868b0e:' + proof['path']], cwd=ROOT,
                                     env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})
    after = (ROOT/proof['path']).read_bytes()
    assert sha(before) == proof['before_sha256'] and sha(after) == proof['after_sha256']
    assert executable(before) == executable(after)
    result['executable_ast'] = proof
    (SCRATCH/'r3-identities.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Verified overlays, four composed packets, protected bytes and AST proof.')


def executable(raw):
    tree = ast.parse(raw)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body.pop(0)
    return ast.dump(tree, include_attributes=False)


def forensics():
    """Reconstruct the old closed fixture without changing tested source."""
    from tests.test_generation_specificity_delegated import scopes
    original = subprocess.check_output(['git', 'show',
        'e0b868b0e:tests/test_generation_specificity_delegated.py'], cwd=ROOT,
        env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})
    constants = {}
    for node in ast.parse(original).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in {'RUNNER', 'SHARED', 'MODES', 'FILES'}):
            if isinstance(node.value, ast.Tuple):
                value = tuple(constants[x.id] if isinstance(x, ast.Name) else ast.literal_eval(x)
                              for x in node.value.elts)
            else:
                value = ast.literal_eval(node.value)
            constants[node.targets[0].id] = value
    target = SCRATCH/'r3-original-dispatch-fixture'
    assert not target.exists()
    for relative in constants['FILES']:
        destination = target/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((COMPOSED/relative).read_bytes())
    result = {'scope': 'Reproduced original fixture omission against the round-three composed selector/scanner; not an original retry-1 traceback.',
              'original_fixture_sha256': sha(original), 'files': constants['FILES']}
    try:
        scopes(target)
    except Exception as exc:
        result.update(error_type=type(exc).__name__, first_error=str(exc), traceback=traceback.format_exc())
    else:
        raise AssertionError('Original incomplete fixture unexpectedly passed')
    assert 'native_shared_render.py' in result['first_error']
    (SCRATCH/'r3-original-fixture-error.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['error_type'], result['first_error'])


def contracts():
    path = ROOT / 'src/data_sheets_schema/native_shared_render.py'
    old = path.read_text()
    baseline = subprocess.check_output(['git', 'show', 'e0b868b0e:' + str(path.relative_to(ROOT))],
                                       cwd=ROOT, env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})
    assert old.encode() == baseline, 'Contract producer requires untouched round-two source; retain existing proof.'
    descriptions = {
        'validate_spec': 'The constructor supplies a new selection before D76 origin capture;\n    reuse callers supply the same admitted selection or a non-executing replay\n    view. This checks selector consistency, not input origin or execution authority.',
        'bind_selection': 'The constructor supplies the validated native selection before D76\n    origin capture. Live capture must match the declared input paths and bytes;\n    replay skips live capture and grants no execution authority.',
        'metadata': 'The serializer supplies the same admitted native selection with its\n    immutable input and runtime captures, or a replay view holding validated\n    recorded metadata. Serialization grants no execution authority.',
        'restore': 'The replay constructor supplies a non-executing replay view and its\n    recorded metadata. Captured input spellings must match before metadata is\n    restored; restoration cannot authorize execution or live input fallback.',
        'commands': 'The renderer supplies the same admitted native selection and captured\n    toolchain/artifact paths, or a non-executing replay view. Returned command\n    text is descriptive and does not execute helpers or authorize a launch.',
        'instruction': 'The renderer supplies the same admitted native selection with captured\n    input/runtime authority, or a validated non-executing replay view. Rendering\n    does not establish helper availability or authorize native execution.',
    }
    new = old
    for name, description in descriptions.items():
        node = next(n for n in ast.parse(new).body if isinstance(n, ast.FunctionDef) and n.name == name)
        lines = new.splitlines(True)
        start = node.body[0].lineno - 1
        end = node.body[0].end_lineno if ast.get_docstring(node) else start
        lines[start:end] = ['    """RunSpec boundary: validated-caller\n\n',
                            '    RunSpec precondition: ' + description + '\n', '    """\n']
        new = ''.join(lines)
    assert executable(old) == executable(new)
    path.write_text(new)
    (COMPOSED / path.relative_to(ROOT)).write_text(new)
    (SCRATCH / 'r3-executable-ast.json').write_text(json.dumps({
        'path': str(path.relative_to(ROOT)), 'before_sha256': sha(old.encode()),
        'after_sha256': sha(new.encode()), 'executable_ast_equal': True,
        'executable_ast_sha256': sha(executable(new).encode()),
        'functions': list(descriptions)}, indent=2) + '\n')


def check(name, command, root=COMPOSED):
    global LAST_LOCK_OBSERVED
    # Creation monitoring is distinct from polling an existing lock for
    # removal. Once observed, wait at least 60 seconds before checking removal.
    delay = LAST_LOCK_OBSERVED + 60 - time.monotonic()
    if delay > 0:
        time.sleep(delay)
    while LOCK.exists():
        LAST_LOCK_OBSERVED = time.monotonic()
        print('Quiet window: waiting 60 seconds', flush=True)
        time.sleep(60)
    logpath = SCRATCH / (name + '.log')
    assert not logpath.exists(), logpath
    with logpath.open('w') as log:
        log.write(json.dumps({'command': command, 'root': str(root), 'started': time.time()}) + '\n')
        log.flush()
        proc = subprocess.Popen(command, cwd=root, env=environment(root), stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        start = time.monotonic()
        next_lock_check = start + 1
        reason = None
        while proc.poll() is None:
            try:
                proc.wait(timeout=max(0.001, min(next_lock_check, start + 3600) - time.monotonic()))
                break
            except subprocess.TimeoutExpired:
                pass
            now = time.monotonic()
            if now >= next_lock_check:
                if LOCK.exists():
                    LAST_LOCK_OBSERVED = now
                    reason = 'quiet-window interruption'
                next_lock_check = now + 1
            if now - start >= 3600:
                reason = '3600-second deadline'
            if reason:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                break
        code = 124 if reason == '3600-second deadline' else proc.returncode
        log.write(f'\nU1_CHECK_EXIT={code}; reason={reason}; elapsed={time.monotonic()-start:.2f}\n')
    assert logpath.stat().st_size
    print(f'{name}: {code}, {reason}', flush=True)
    return code


def retry_interrupted():
    batches = json.loads((SCRATCH/'r3-batches.json').read_text())
    rows = []
    for number, files in enumerate(batches, 1):
        log = (SCRATCH/f'r3-batch-{number:02}.log').read_text()
        repaired_fixture = ('tests/test_wave7_5213_d76_legacy_registration.py' in files
                            and 'U1_CHECK_EXIT=1;' in log)
        if not repaired_fixture and not any(f'U1_CHECK_EXIT={code}' in log for code in (-15, 124)):
            continue
        for index, relative in enumerate(files, 1):
            attempt = 0
            while True:
                attempt += 1
                name = f'r3-retry-batch-{number:02}-file-{index:02}-attempt-{attempt:02}'
                code = check(name, [sys.executable, '-m', 'pytest', relative,
                             '-n', '2', '-vv', '--tb=short', '-p', 'no:cacheprovider',
                             '--junitxml=' + str(SCRATCH/(name+'.xml'))])
                rows.append({'batch': number, 'file': relative, 'name': name, 'exit': code})
                (SCRATCH/'r3-retry-roster.json').write_text(json.dumps(rows, indent=2) + '\n')
                if code != -15:
                    break


if __name__ == '__main__':
    if sys.argv[1] == 'contracts':
        contracts()
    elif sys.argv[1] == 'identities':
        identities()
    elif sys.argv[1] == 'forensics':
        forensics()
    elif sys.argv[1] == 'progress':
        for log in sorted(SCRATCH.glob('r3-batch-[0-9]*.log')):
            pending = set()
            text = log.read_text()
            for line in text.splitlines():
                if line.startswith('tests/'):
                    pending.add(line.strip())
                match = re.search(r'\b(?:PASSED|FAILED|ERROR|XFAIL|SKIPPED) (tests/.*)', line)
                if match:
                    pending.discard(match.group(1).strip())
            if 'U1_CHECK_EXIT=' not in text:
                elapsed = time.time() - json.loads(text.splitlines()[0])['started']
                print(log.name, f'elapsed={elapsed:.0f}s', 'unfinished nodes:', sorted(pending), flush=True)
    elif sys.argv[1] == 'check':
        raise SystemExit(check(sys.argv[2], sys.argv[3:]))
    elif sys.argv[1] == 'batches':
        canary_xml = SCRATCH/'r3-batch-canary.xml'
        code = check('r3-batch-canary', [sys.executable, '-m', 'pytest',
                     'tests/test_native_shared_render.py::test_native_instruction_roundtrip_uses_only_sole_runtime',
                     '-n', '2', '-vv', '--tb=short', '-p', 'no:cacheprovider',
                     '--junitxml=' + str(canary_xml)])
        assert code == 0 and canary_xml.is_file() and canary_xml.stat().st_size
        assert '1 passed' in (SCRATCH/'r3-batch-canary.log').read_text()
        print('Batch canary artifact and passing summary verified before fan-out.', flush=True)
        roster = (SCRATCH / 'regression-roster.txt').read_text().splitlines()
        assert len(roster) == 66 and len(set(roster)) == 66
        batches = [roster[i:i+5] for i in range(0, len(roster), 5)]
        (SCRATCH / 'r3-batches.json').write_text(json.dumps(batches, indent=2) + '\n')
        for index, batch in enumerate(batches, 1):
            check(f'r3-batch-{index:02}', [sys.executable, '-m', 'pytest', *batch,
                  '-n', '2', '-vv', '--tb=short', '-p', 'no:cacheprovider',
                  '--junitxml=' + str(SCRATCH / f'r3-batch-{index:02}.xml')])
    elif sys.argv[1] == 'resume-files':
        manifest = SCRATCH/'r3-batches.json'
        original = json.loads(manifest.read_text())
        assert len(original) == 14
        assert not (SCRATCH/'r3-batch-10.log').exists()
        saved = SCRATCH/'r3-original-batches.json'
        assert not saved.exists()
        saved.write_text(manifest.read_text())
        batches = original[:9] + [[relative] for group in original[9:] for relative in group]
        assert [relative for group in batches for relative in group] == [relative for group in original for relative in group]
        manifest.write_text(json.dumps(batches, indent=2) + '\n')
        # The previous controller was waiting on the same lock. Preserve its
        # removal-poll interval across this explicit controller handoff.
        time.sleep(60)
        code = check('r3-resume-canary', [sys.executable, '-m', 'pytest',
            'tests/test_native_shared_render.py::test_native_instruction_roundtrip_uses_only_sole_runtime',
            '-n', '2', '-vv', '--tb=short', '-p', 'no:cacheprovider',
            '--junitxml=' + str(SCRATCH/'r3-resume-canary.xml')])
        assert code == 0 and (SCRATCH/'r3-resume-canary.xml').stat().st_size
        assert '1 passed' in (SCRATCH/'r3-resume-canary.log').read_text()
        for index, batch in enumerate(batches[9:], 10):
            check(f'r3-batch-{index:02}', [sys.executable, '-m', 'pytest', *batch,
                  '-n', '2', '-vv', '--tb=short', '-p', 'no:cacheprovider',
                  '--junitxml=' + str(SCRATCH/f'r3-batch-{index:02}.xml')])
    elif sys.argv[1] == 'gates':
        check('r3-scanner-controls-final', [sys.executable, '-m', 'pytest',
              'tests/test_native_u1_scanner_contracts.py', '-n', '2', '-q', '--tb=short', '-p', 'no:cacheprovider'])
        check('r3-scanner', [sys.executable, '.claude/skills/d4d-generation-specificity-audit/scan.py',
              '--report', str(SCRATCH/'r3-scanner.md'), '--json', str(SCRATCH/'r3-scanner.json')])
        check('r3-specificity-guards', [sys.executable, '-m', 'pytest',
              'tests/test_generation_specificity_skill.py', 'tests/test_neutral_generation_schema.py',
              'tests/test_profiles.py', 'tests/test_external_dataset_onboarding.py',
              '-n', '2', '-q', '--tb=short', '-p', 'no:cacheprovider'])
    elif sys.argv[1] == 'postflight':
        canary = check('r3-postflight-canary', [sys.executable, '-m', 'pytest',
            'tests/test_native_shared_render.py::test_native_instruction_roundtrip_uses_only_sole_runtime',
            '-n', '2', '-vv', '--tb=short', '-p', 'no:cacheprovider',
            '--junitxml=' + str(SCRATCH/'r3-postflight-canary.xml')])
        assert canary == 0 and (SCRATCH/'r3-postflight-canary.xml').stat().st_size
        assert '1 passed' in (SCRATCH/'r3-postflight-canary.log').read_text()
        retry_interrupted()
        check('r3-scanner-controls-semantic', [sys.executable, '-m', 'pytest',
              'tests/test_native_u1_scanner_contracts.py', '-n', '2', '-q', '--tb=short', '-p', 'no:cacheprovider'])
        check('r3-original-fixture-reproduction', [sys.executable, str(Path(__file__).resolve()), 'forensics'])
        check('r3-specificity-guards-retry', [sys.executable, '-m', 'pytest',
              'tests/test_generation_specificity_skill.py', 'tests/test_neutral_generation_schema.py',
              'tests/test_profiles.py', 'tests/test_external_dataset_onboarding.py',
              '-n', '2', '-q', '--tb=short', '-p', 'no:cacheprovider'])
        check('r3-m7-discovery-control', [sys.executable, '-m', 'pytest',
              'tests/test_generation_specificity_skill.py::TestDiscovery::test_the_deterministic_arms_are_derived_from_the_code',
              'tests/test_generation_specificity_skill.py::TestDiscovery::test_every_model_facing_module_is_in_a_discovered_closure',
              '-n', '2', '-q', '--tb=short', '-p', 'no:cacheprovider'], SCRATCH/'baseline-8bc90e93d')
        check('r3-m7-legacy-isolation-control', [sys.executable, '-m', 'pytest',
              'tests/test_wave7_5213_d76_legacy_registration.py',
              '-n', '2', '-q', '--tb=short', '-p', 'no:cacheprovider'], SCRATCH/'baseline-8bc90e93d')
