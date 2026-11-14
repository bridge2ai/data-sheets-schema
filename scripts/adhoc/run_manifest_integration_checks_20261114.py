"""Run bounded offline integration checks for the D148 manifest merge.

Inputs: stage and external scratch directory. Outputs: logs, JUnit and invocation
JSON under scratch. Serves the Codex 196 integration handoff, 2026-11-14.
No provider, native binary, capture or reservation commands are launched here.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT.parents[1] / 'data-sheets-schema/.venv/bin/python'
BUILDER = [
    'tests/test_native_canary_packet_builder.py',
    'tests/test_native_canary_packet_rehearsal.py',
    'tests/test_native_packet_full_chain.py',
    'tests/test_native_probe_drafts.py',
    'tests/test_native_all_project_prefix.py',
]
SCANNER = [
    'tests/test_native_u1_scanner_contracts.py', 'tests/test_native_u3l_scanner.py',
    'tests/test_native_u5_scanner.py', 'tests/test_native_u5_scanner_comparison.py',
    'tests/test_native_d128_scanner_comparison.py', 'tests/test_native_h1_scanner_authority.py',
    'tests/test_native_u4b_a5_scanner.py', 'tests/test_native_generation_guard_v2.py',
    'tests/test_native_generation_frontdoor.py', 'tests/test_native_u3d_guard_contract.py',
    'tests/test_native_u4b_a3_frontdoor.py', 'tests/test_generation_specificity_skill.py',
    'tests/test_generation_specificity_delegated.py',
]
STAGES = {
    'prefix-canary': [BUILDER[0] + '::test_real_chorus_prefix'],
    'chain-canary': [BUILDER[2] + '::test_full_chain_canary'],
    'manifest': ['tests/test_native_environment_manifest.py', 'tests/test_native_environment_registration.py',
                 'tests/test_h3_resumed_report.py', 'tests/test_native_gate_stage_orchestrator.py'],
    'manifest-boundaries': ['tests/test_native_environment_dependencies.py', 'tests/test_native_environment_dispatch.py'],
    'registration': ['tests/test_native_execution_registration_v2.py', 'tests/test_native_shared_registration.py'],
    'builder': BUILDER,
    'retention': ['tests/test_native_incomplete_retention.py'],
    'scanner': SCANNER,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=STAGES)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--label')
    args = parser.parse_args()
    scratch = args.scratch.resolve(strict=True)
    if scratch == ROOT or scratch.is_relative_to(ROOT):
        raise ValueError('scratch must be outside the source tree')
    label = args.label or args.stage
    if Path(label).name != label:
        raise ValueError('label must be one filename component')
    log = scratch / (label + '.log')
    junit = scratch / (label + '.xml')
    command = [str(PYTHON), '-m', 'pytest', *STAGES[args.stage], '-n', '2',
        '--dist=loadfile', '-q', '-p', 'no:cacheprovider', '--tb=short',
        '--basetemp=' + str(scratch / (label + '-tmp')), '--junitxml=' + str(junit)]
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
    record = {'command': command, 'cwd': str(ROOT), 'stage': args.stage,
              'environment': {key: env[key] for key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE')},
              'started': time.time(), 'log': str(log), 'junit': str(junit)}
    invocation = scratch / (label + '-invocation.json')
    invocation.write_text(json.dumps(record, indent=2) + '\n')
    with log.open('xb') as stream:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
    record.update(returncode=result.returncode, seconds=time.time()-record['started'],
                  log_bytes=log.stat().st_size, junit_bytes=junit.stat().st_size if junit.exists() else None)
    invocation.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
