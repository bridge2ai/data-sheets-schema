#!/usr/bin/env python3
# Purpose: offline NEWPROJ proof through builder, synthesis and registered judge.
# Inputs: invented source/record/sizing data; output: external proof JSON/artifacts.
# Generality F2/F3/F7/F8/F19, 2026-10-29. No provider or scientific rating.
import argparse
import hashlib
import json
from pathlib import Path
import yaml

from scripts import build_api_registrations as builder
from data_sheets_schema import chunking, shared_generation as shared
from data_sheets_schema.evaluation import registered_eval_runner as evaluator


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    bundle = folder / 'source.txt'
    bundle.write_text('Synthetic ocean temperature readings from station A, collected hourly.\n' * 12)
    manifest = folder / 'manifest.yaml'
    manifest.write_text(yaml.safe_dump({'projects': {'NEWPROJ': {'bundle': str(bundle),
        'sources': [{'id': 'station-observations', 'processed_file': 'source.txt',
                     'source_type': 'sensor observations'}]}},
        'scope': {'NEWPROJ': {'referent': 'Synthetic station observations',
                            'referent_note': 'Only station A observations in this bundle.'}}}))
    chunks, _ = chunking.write_manifest_for(bundle)
    # A fully declared synthetic sizing stand-in, not a prior scientific run.
    sizing = folder / 'sizing'
    sizing.mkdir()
    record_text = 'conforms_to_class: Dataset\nid: example:station\nname: Synthetic station observations\n'
    (sizing / 'NEWPROJ_full.yaml').write_text('# Synthetic sizing stand-in; no run claimed.\n' + record_text)
    (sizing / 'NEWPROJ_core.yaml').write_text('id: example:station\nname: Synthetic station observations\n')
    (sizing / 'NEWPROJ_coverage_receipt.yaml').write_text(yaml.safe_dump({
        'bundle_md5': hashlib.md5(bundle.read_bytes()).hexdigest(), 'chunks': []}))
    registration = folder / 'registration.json'
    reg = builder.build_registration('NEWPROJ', 'synthetic-generality-proof',
        source_manifest_path=manifest, bundle_path=bundle, chunk_manifest_path=chunks,
        registration_path=registration, synthesize_draft_context=True,
        context_dir=folder / 'contexts', sizing_record=sizing, sizing_stand_in=True,
        audit_limits={'max_paths': 80, 'max_inventory_bytes': 12288, 'max_workers': 4,
                      'aggregate_input_tokens': 4000000})
    context = json.loads(Path(reg['inputs']['context']['path']).read_bytes())
    assert context['vocabulary'] == {} and context['source_policy']['priority'] == ['sensor observations']
    assert reg['inputs']['profile']['name'] == 'neutral'
    assert 'B2AI_' not in json.dumps(context) and 'Bridge2AI' not in json.dumps(context)
    record = folder / 'record.yaml'
    record.write_text(record_text)
    applicability = folder / 'applicability.yaml'
    applicability.write_text('{}\n')
    pins = [reg['inputs'][key] for key in ('bundle', 'chunk_manifest', 'source_manifest', 'context')]
    pins += reg['inputs']['full_schema']['sources'] + reg['inputs']['core_schema']['sources']
    pins += [reg['runtime']['config']]
    files = {pin['path']: Path(pin['path']).read_bytes() for pin in pins if pin}
    files[str(registration)] = registration.read_bytes()
    captured = shared._capture_bytes(registration.read_bytes(), reg, files)
    provenance = folder / 'synthetic-provenance.yaml'
    provenance.write_text(yaml.safe_dump({'record_type': 'd4d_generation_provenance',
        'run': {**reg['run'], 'condition': reg['selection']['condition']},
        'shared_generation': {'authority': captured.identity()},
        'validation': {'artifacts': {'full': {'path': str(record),
            'md5': hashlib.md5(record.read_bytes()).hexdigest()}}}}))
    runtime = folder / 'never-executed-runtime'
    runtime.write_text('synthetic offline fixture\n')
    prepared = evaluator.prepare(registration, record, applicability, rubric='rubric20',
        instrument_version='5.0', context_sha256=sha(applicability.read_bytes()),
        provenance=provenance, provenance_sha256=sha(provenance.read_bytes()),
        comparison_arm='v10',
        model='claude-opus-5', canonical_model='claude-opus-5', context_window=1000000,
        base_url=evaluator.CBORG_BASE_URL, runtime=runtime, runtime_sha256=sha(runtime.read_bytes()),
        runtime_version='2.1.269')
    result = evaluator.execute(prepared, folder / 'not-created', dry_run=True, environ={})
    # Existing contract fixture supplies invented scores solely to test validation.
    from tests.test_registered_eval_runner import trace_for
    accepted, _ = evaluator._accept(prepared, trace_for(prepared))
    assert accepted['version'] == '5.0'
    assert result['model_calls'] == 0 and not (folder / 'not-created').exists()
    proof = {'project': 'NEWPROJ', 'profile': reg['inputs']['profile']['name'],
        'vocabulary': context['vocabulary'], 'source_policy': context['source_policy'],
        'registration_sha256': sha(registration.read_bytes()), 'context_sha256': sha(Path(reg['inputs']['context']['path']).read_bytes()),
        'evaluator_prepared': True, 'synthetic_reply_contract_accepted': True,
        'model_calls': result['model_calls'], 'sizing_basis': 'explicit synthetic stand-in',
        'scientific_scoring': 'not performed'}
    (folder / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    print(json.dumps(run(parser.parse_args().folder), indent=2))
