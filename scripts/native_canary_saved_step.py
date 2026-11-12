#!/usr/bin/env python3
"""Explicit saved-input producer commands for the DRAFT G13 runbook.

No live probe/capture/launch entrypoints exist here. Constructors consume saved
files and enforce production source/runtime checks. Some read Git objects; run
inside an offline OS sandbox. No owner or review documents are manufactured.
The full chain is NOT validated on the protected-main base. See rehearsal log.
"""
import argparse
import json
from pathlib import Path
import sys

# scripts/ is adjacent only for this stand-alone CLI (safe-path is supported).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_native_canary_packet import physical, write_new


def produce(step, data):
    from data_sheets_schema import native_shared_contract as c
    if step == 'runtime':
        from data_sheets_schema.native_u4b_runtime import prepare_runtime, validate_prepared_runtime
        runtime = c.strict_json(Path(data['runtime_path']).read_bytes())
        value = prepare_runtime(runtime, **data['arguments'])
        validate_prepared_runtime(value)
        return {'runtime.json': c.canonical(value)}
    if step == 'preparation':
        from data_sheets_schema.native_execution_registration_v2 import prepare, verify_preparer
        value = prepare(**data)
        raw = c.canonical(value)
        body = verify_preparer(raw, job_id=data['job_id'])
        return {'preparation.json': raw, 'instruction.md': body['instruction'].encode('utf-8')}
    if step == 'composition':
        from data_sheets_schema.native_shared_controller_orchestration import compose, verified_composition
        raw = Path(data['preparation_path']).read_bytes()
        value = compose(raw, instruction_path=data['instruction_path'])
        wire = c.canonical(value)
        verified_composition(wire)
        return {'composition.json': wire}
    if step == 'expectation':
        from data_sheets_schema.native_shared_controller_orchestration import reconstruct_composition
        from data_sheets_schema import native_execution_authority_v2 as authority
        from data_sheets_schema.native_shared_permission_orchestration import loaded_permission_inputs
        from data_sheets_schema.native_permission_probe import require_u4_expectation
        composed, spec, _ = reconstruct_composition(Path(data['composition_path']).read_bytes())
        runtime = c.strict_json(composed['runtime_raw_json'].encode())
        system = Path(data['system_path']).read_bytes().decode('utf-8')
        dependencies = composed['dependencies']
        # Mirror registration orchestration's loader scope: an ordinary imported
        # policy cannot consume a classifier minted by the verified module set.
        with loaded_permission_inputs(dependencies) as (controls, _), \
                authority.loaded_verified_package_module('data_sheets_schema.native_shared_registration',
                    package_sources=dependencies['base']['package_sources']) as consumer:
            effective = system + consumer.policy.command_guidance(composed['policy'], classifier_projection=controls)
            value = consumer.permission_expectation(runtime, composed, spec, effective,
                Path(data['config_directory']), composed['dependencies'])
        require_u4_expectation(value)
        return {'expectation.json': c.canonical(value)}
    if step == 'registration':
        from data_sheets_schema.native_shared_registration_orchestration import registration, verified
        value = registration(**data)
        raw = c.canonical(value)
        verified(raw)
        return {'registration.json': raw}
    if step == 'review':
        from native_packet_review_inputs import validate_supplied
        raws = [Path(data[name]).read_bytes() for name in ('registration_path', 'review_path', 'launch_word_path')]
        validate_supplied(*raws)
        return {'review-validation.json': c.canonical({'scope': 'Saved declared byte bindings only; not human authentication, CI, full admission or authorization.', 'checked_sha256': [c.sha(raw) for raw in raws]})}
    raise ValueError('unknown saved step')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--step',choices=['runtime','preparation','composition','expectation','registration','review'],required=True)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--checkout',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    checkout=physical(args.checkout)
    if checkout!=Path(__file__).resolve().parents[1] or Path.cwd().resolve()!=checkout:
        raise ValueError('exact script checkout and working directory required')
    inputs=physical(args.inputs)
    out=physical(args.output,exists=False)
    physical(out.parent)
    if out.exists(): raise FileExistsError('refusing existing output: '+str(out))
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(checkout/'src'))
    from data_sheets_schema import native_shared_contract as c
    data=c.strict_json(inputs.read_bytes())
    # Existing production functions perform source and saved-input validation.
    # Collect bytes before writing: a refusal cannot leave a plausible proposal.
    outputs=produce(args.step,data)
    out.mkdir()
    for name,raw in outputs.items(): write_new(out/name,raw)
    print(json.dumps({'step':args.step,'outputs':list(outputs),'scope':'saved-input proposal only; no live effect or authorization'}))
    return 0

if __name__=='__main__': raise SystemExit(main())
