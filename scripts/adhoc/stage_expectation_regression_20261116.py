"""Stage offline regression from codex 196 helpers, PR 5968, 2026-11-16.
Inputs: saved helper sources. Outputs: local through-expectation regression helper.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
source = root.parent / 'codex-step5e-preflight-20261116/scripts/adhoc'
base = (source / 'preflight_step5e_20261116.py').read_text()
chain = (source / 'preflight_step5e_saved_20261116.py').read_text()
header = '''"""Offline saved expectation regression for PR 5968, 2026-11-16.
Derived from codex 196 Step 5e producers. Inputs: project and scratch directory.
Outputs: prefix through expectation, foreign-origin refusal, byte evidence.
Invented saved runtime observations only; no native executable or provider call.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)
b = sys.modules[__name__]

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

'''
functions = base[base.index('def save('):base.index('def module(')]
functions += base[base.index('def inputs('):base.index('def parent(')]
functions += chain[chain.index('def write('):chain.index('def parent(')]
functions = functions.replace("    b.environment_probe() if not (SCRATCH / 'environment-probe.json').exists() else None\n", '')
functions = functions[:functions.index("    expected = b.load(expectation / 'expectation.json')")]
ending = '''    expected = b.load(expectation / 'expectation.json')
    assert expected and (expectation / 'expectation.json').stat().st_size > 0
    # Run the original invalid handoff against the genuine verified consumer.
    from data_sheets_schema.native_shared_controller_orchestration import reconstruct_composition
    from data_sheets_schema.native_shared_permission_orchestration import loaded_permission_inputs
    from data_sheets_schema import native_execution_authority_v2 as authority
    raw = (composition / 'composition.json').read_bytes()
    composed, foreign, _ = reconstruct_composition(raw)
    dependencies = composed['dependencies']
    with loaded_permission_inputs(dependencies) as (controls, _), authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_registration',
            package_sources=dependencies['base']['package_sources']) as consumer:
        effective = system.read_bytes().decode('utf-8') + consumer.policy.command_guidance(
            composed['policy'], classifier_projection=controls)
        try:
            consumer.permission_expectation(c.strict_json(composed['runtime_raw_json'].encode()),
                composed, foreign, effective, attempt / 'cli_config', dependencies)
        except ValueError as exc:
            assert 'registered inputs have no construction origin' in str(exc), str(exc)
            refusal = str(exc)
        else:
            raise AssertionError('foreign-origin RunSpec accepted')
        selected, own, _, runtime = consumer._selection(raw,
            preparation_raw=composed['preparation_raw_json'].encode('utf-8'),
            classifier_projection=controls)
        actual = consumer.permission_expectation(runtime, selected, own, effective,
            attempt / 'cli_config', dependencies)
        assert c.canonical(actual) == c.canonical(expected)
    assert not attempt.exists() and not Path(b.load(prefix / 'selection.json')['stage_root']).exists()
    b.save(packet / 'regression-result.json', dict(project=project,
        saved_expectation=b.pin(expectation / 'expectation.json'), foreign_origin_refusal=refusal,
        verified_consumer_matches_cli=True, native_execution=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', choices=('CHORUS', 'AI_READI'), required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    SCRATCH = args.scratch.resolve()
    assert not SCRATCH.is_relative_to(ROOT)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    chain(args.project)
'''
result = header + functions + ending
assert chr(64) not in result
(root / 'scripts/adhoc/expectation_scope_regression_20261116.py').write_text(result)
