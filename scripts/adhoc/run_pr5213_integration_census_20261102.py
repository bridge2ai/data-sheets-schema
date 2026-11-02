#!/usr/bin/env python3
"""Run the committed #5212 eligibility census from the #5213 merge, 2026-11-02.

Inputs: pristine pinned git-archive source/proof and explicit full HEAD. Output:
fresh external census, source/import/deadline/sandbox evidence. No provider,
network, GitHub, corpus writes or implicit old-ref wrapper. Uses the already
reviewed round-three supervisor and observer; no pytest process is launched.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
CENSUS = 'scripts/adhoc/d70_corpus_eligibility_20261030.py'


def load_runner():
    # Its bootstrap enforces -S -P -B, adds the existing dependency directory
    # without executing site or .pth files, and loads the pinned local helpers.
    spec = importlib.util.spec_from_file_location('integration_census_runner',
        HERE / 'run_d76_round3_validation_20261102.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def child(runner):
    tree, output = Path(os.environ['D76_TREE']), Path(os.environ['D76_OUTPUT'])
    plan = json.loads((output / 'plan.json').read_text())
    runner.establish_child()  # installs the same evidence-recording offline guard
    runner.common.save(output / 'bootstrap.json', runner.runtime())
    result = {'completed': False, 'census_ref': plan['head']}
    status = 1
    try:
        sys.argv = [str(tree / CENSUS), '--ref', plan['head'], '--output', str(output / 'census.json')]
        runpy.run_path(str(tree / CENSUS), run_name='__main__')
        census = json.loads((output / 'census.json').read_text())
        if census['ref'] != plan['head'] or census['parse_errors'] or census['counts']['v8_changes']:
            raise ValueError('census identity/parse/V8 invariant failed')
        result.update(completed=True, counts=census['counts'],
                      census_sha256=runner.common.sha((output / 'census.json').read_bytes()))
        status = 0
    except BaseException as exc:
        result.update(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        try:
            baseline = json.loads((output / 'source-before.json').read_text())
            result['origins'] = runner.common.origins(tree, baseline)
            result['origins_verified'] = True
        except BaseException as exc:
            result.update(origins_verified=False, origin_error=repr(exc))
            status = 1
        runner.common.save(output / 'child-result.json', result)
    return status


def run(args, runner):
    common = runner.common
    if args.output.exists() or args.output.is_relative_to(args.tree):
        raise ValueError('fresh evidence directory outside frozen source required')
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        raise ValueError('mandatory reviewed macOS sandbox unavailable')
    before = common.source(args.tree)
    if before['head'] != args.expect_head or not before['tracked_exact']:
        raise ValueError('exact frozen HEAD required')
    status_args = ('status', '--ignored', '--porcelain=v1', '--untracked-files=all')
    status_before = common.git(args.tree, *status_args).decode()
    if status_before:
        raise ValueError('census requires pristine source including ignored files')
    archived = json.loads(args.archive_proof.read_text())
    if (archived['head'] != args.expect_head or archived['git_tree'] != before['tree']
            or archived['destination'] != str(args.tree)
            or archived['source_method'] != 'git archive; metadata initialized afterwards without checkout'):
        raise ValueError('archive proof does not bind exact census source')
    for proof in (archived, archived['fairscape']):
        archive = Path(proof['archive'])
        if archive.is_symlink() or runner.archive_sha(archive) != proof['archive_sha256']:
            raise ValueError('retained archive changed')
    common.fairscape(args.tree, before)
    helpers = [Path(__file__).resolve(), Path(runner.__file__).resolve(), runner.PROFILE,
               HERE / 'd76_suite_common_20261031.py', HERE / 'd76_phase_accounting_20261031.py',
               HERE / 'd76_round3_hygiene_20261102.py', HERE / 'd76_round3_pytest_observer_20261102.py',
               args.tree / CENSUS]
    hashes = {str(path): common.sha(path.read_bytes()) for path in helpers}
    # A different helper tree would weaken the final-head claim even if source
    # imports are pinned; require all census machinery to come from this archive.
    if any(not path.is_relative_to(args.tree) for path in helpers):
        raise ValueError('invoke the census wrapper from the same final archive')
    if hashes[str(runner.PROFILE)] != runner.PROFILE_SHA:
        raise ValueError('reviewed network profile changed')
    args.output.mkdir(parents=True)
    (args.output / 'temporary').mkdir()
    common.save(args.output / 'source-before.json', before)
    args.notes_ci_job = None
    args.metrics = False
    env, removed = runner.scrubbed_environment(args)
    policy = args.output / 'network-profile.sb'
    policy.write_bytes(runner.PROFILE.read_bytes())
    command = ['/usr/bin/sandbox-exec', '-D', 'LOCAL_ROOT=' + str(args.output), '-f', str(policy),
               sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), '--child']
    common.save(args.output / 'plan.json', {'head': args.expect_head, 'git_tree': before['tree'],
        'worktree': str(args.tree), 'archive_proof': str(args.archive_proof),
        'archive_proof_sha256': common.sha(args.archive_proof.read_bytes()),
        'command': command, 'census_command': [CENSUS, '--ref', args.expect_head, '--output', str(args.output / 'census.json')],
        'helper_sha256': hashes, 'removed_environment_names': removed,
        'deadline_seconds': args.deadline_seconds, 'network': 'inherited mandatory loopback-only OS policy plus recorded Python guard'})
    started = time.monotonic()
    with (args.output / 'census.log').open('x') as stream:
        code, timed_out = runner.execute_bounded(command, args, env, stream)
    after = common.source(args.tree)
    common.save(args.output / 'source-after.json', after)
    status_after = common.git(args.tree, *status_args).decode()
    child_path = args.output / 'child-result.json'
    result = json.loads(child_path.read_text()) if child_path.is_file() else {}
    denials = {path.name: common.sha(path.read_bytes()) for path in args.output.glob('guard-denials-*.jsonl')}
    proofs = {'source_unchanged': before == after, 'hygiene_unchanged': status_before == status_after == '',
        'helpers_unchanged': all(common.sha(Path(path).read_bytes()) == digest for path, digest in hashes.items()),
        'origins_verified': result.get('origins_verified') is True,
        'zero_guard_denials': not denials, 'sandbox_loaded': (args.output / 'bootstrap.json').is_file(),
        'census_completed': result.get('completed') is True}
    common.save(args.output / 'outcome.json', {'head': args.expect_head, 'returncode': code,
        'deadline_expired': timed_out, 'wall_seconds': time.monotonic() - started,
        'counts': result.get('counts'), 'proofs': proofs,
        'passed': code == 0 and not timed_out and all(proofs.values()),
        'guard_denials': denials, 'hygiene_before': status_before, 'hygiene_after': status_after,
        'census_sha256': result.get('census_sha256'), 'child_result_sha256': common.sha(child_path.read_bytes()) if child_path.is_file() else None})
    return 0 if code == 0 and not timed_out and all(proofs.values()) else 1


def main():
    runner = load_runner()
    if sys.argv[1:] == ['--child']:
        return child(runner)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--expect-head', required=True)
    parser.add_argument('--archive-proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deadline-seconds', type=int, default=1800)
    args = parser.parse_args()
    if not 1 <= args.deadline_seconds <= 7200:
        raise ValueError('bounded deadline required')
    args.tree, args.archive_proof, args.output = (path.resolve() for path in (args.tree, args.archive_proof, args.output))
    return run(args, runner)


if __name__ == '__main__':
    raise SystemExit(main())
