#!/usr/bin/env python3
"""Round 6 mutation evidence, 2026-11-08, U3-A R9-3 review.

Inputs: clean current worktree and exact base, dependency interpreter, case.
Outputs: plans/results under scratch-native-u3a-r6. Mutations and their
restorations are committed ONLY in the authorized existing worktree/branch.
No archives, scratch repositories, network, or native executable. Run MA first.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('mutation', ROOT / 'scripts/adhoc/mutate_native_u3a_round2_20261107.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
SCRATCH = ROOT.parent / 'scratch-native-u3a-r6'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--case', choices=tuple(helper.CASES))
    parser.add_argument('--remaining', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.remaining:
        if args.case or not args.run:
            parser.error('--remaining requires --run and no --case')
        for case in tuple(helper.CASES)[1:]:
            helper.quiet()
            command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
                       '--base', args.base, '--python', str(args.python), '--case', case, '--run']
            print('Starting ' + case, flush=True)
            subprocess.run(command, cwd=ROOT, env=helper.environment(), check=True)
        return 0
    if not args.case:
        parser.error('--case required')
    raw = helper.git(ROOT, 'show', args.base + ':' + helper.SOURCE)
    changed, edit = helper.mutate(raw, args.case)
    plan = {'case': args.case, 'base': args.base, 'edit': edit,
            'source_sha256': helper.sha(raw), 'mutated_source_sha256': helper.sha(changed),
            'node': helper.CASES[args.case][3]}
    if not args.run:
        print(json.dumps(plan, sort_keys=True))
        return 0
    helper.quiet()
    if helper.git(ROOT, 'status', '--porcelain'):
        raise RuntimeError('mutation requires clean authorized worktree')
    if helper.git(ROOT, 'branch', '--show-current').decode().strip() != 'codex/native-u3a-bridge-20261107':
        raise RuntimeError('wrong branch')
    if (ROOT / helper.SOURCE).read_bytes() != raw:
        raise RuntimeError('baseline source differs')
    if args.case != 'MA':
        canary = json.loads((SCRATCH / 'mutations/MA/result.json').read_bytes())
        if canary['base'] != args.base or canary['status'] != 'killed':
            raise RuntimeError('matching MA canary required')
    out = SCRATCH / 'mutations' / args.case
    out.mkdir(parents=True, exist_ok=False)
    helper.save(out / 'plan.json', plan)
    baseline = helper.run_tests(ROOT, out / 'baseline', args.python, plan['node'])
    if baseline['returncode'] != 0:
        raise RuntimeError('matched baseline failed')
    result = {**plan, 'baseline': baseline}
    helper.quiet()
    try:
        (ROOT / helper.SOURCE).write_bytes(changed)
        helper.git(ROOT, 'add', '--', helper.SOURCE)
        helper.git(ROOT, 'commit', '-qm', 'test: apply offline U3-A mutation ' + args.case)
        result['mutant_commit'] = helper.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
        result['mutant'] = helper.run_tests(ROOT, out / 'mutant', args.python, plan['node'])
        tested = result['mutant']
        result['status'] = 'killed' if tested['returncode'] == 1 and tested['failures'] else 'invalid'
    finally:
        (ROOT / helper.SOURCE).write_bytes(raw)
        helper.git(ROOT, 'add', '--', helper.SOURCE)
        helper.git(ROOT, 'commit', '-qm', 'test: restore source after U3-A mutation ' + args.case)
        result['restored_commit'] = helper.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
        helper.save(out / 'result.json', result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'killed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
